"""Indicator calculation jobs."""

import datetime
import logging
import time
from typing import Any

from sqlalchemy import select

from src.clients.yfinance_client import YFinanceClient
from src.config import settings
from src.database import SessionFactory
from src.stock_indicator.calculator import calculate_indicators_from_prices
from src.stock_indicator.schema import (
    IndicatorType,
    StockIndicatorUpsert,
    parse_indicator_key,
)
from src.stock_indicator.service import StockIndicatorService
from src.stocks.model import DailyPrice, Stock
from src.stocks.schema import DailyPriceBase
from src.stocks.service import DailyPriceService, StockService

logger = logging.getLogger(__name__)

# Redis keys for tracking failed stocks
REDIS_INDICATOR_FAILED_KEY = "indicator:failed"
REDIS_INDICATOR_RETRY_PREFIX = "indicator:retry:"


async def calculate_stock_indicators(
    ctx: dict[str, Any],
    stock_id: int | None = None,
) -> dict[str, Any]:
    """Calculate indicators for stocks with active subscriptions.

    This job periodically fetches stocks that have indicator subscriptions.

    For each stock, it:
    1. Checks daily_prices table for available historical data
    2. Falls back to yfinance API if data is insufficient
    3. Calculates required indicators based on subscriptions
    4. Stores results in stock_indicator table with BIGINT updated_at timestamp

    Error handling:
    - Logs errors for individual stock failures without stopping batch
    - Tracks failed stocks in Redis with retry count
    - Skips stocks that exceed max retries

    Args:
        ctx: ARQ context dict with 'redis'
        stock_id: Optional specific stock ID to calculate (if None, calculate all)

    Returns:
        dict with processing statistics
    """
    logger.info("Starting indicator calculation job")

    redis_pool = ctx["redis"]

    result = {
        "stocks_processed": 0,
        "indicators_calculated": 0,
        "stocks_skipped": 0,
        "yfinance_fetches": 0,
        "errors": [],
        "success": False,
    }

    try:
        async with SessionFactory() as db:
            # Get stocks to process
            if stock_id:
                stock_ids = [stock_id]
            else:
                # Get all stocks with active indicator subscriptions
                stock_ids = await StockIndicatorService.get_stocks_with_indicators(db)

            logger.info(f"Processing {len(stock_ids)} stocks for indicator calculation")

            for sid in stock_ids:
                try:
                    # Check retry count for failed stocks
                    retry_count = await redis_pool.get(f"{REDIS_INDICATOR_RETRY_PREFIX}{sid}")
                    if retry_count and int(retry_count) >= settings.INDICATOR_MAX_RETRIES:
                        logger.warning(
                            f"Stock {sid} exceeded max retries ({retry_count}), skipping"
                        )
                        result["stocks_skipped"] += 1
                        continue

                    # Get stock info
                    stock = await StockService.get_by_id(db, sid)
                    if not stock or stock.is_deleted:
                        logger.warning(f"Stock {sid} not found or deleted, skipping")
                        continue

                    # Get required indicator keys for this stock
                    required_keys = await StockIndicatorService.get_required_indicator_keys(
                        db, sid
                    )

                    if not required_keys:
                        logger.info(f"No indicator subscriptions for stock {sid}, skipping")
                        continue

                    # Determine minimum required days based on indicator keys
                    min_days = _get_min_required_days(required_keys)
                    logger.info(
                        f"Stock {sid}: needs {min_days} days of data for {len(required_keys)} indicators"
                    )

                    # Fetch historical prices from daily_prices table
                    prices = await DailyPriceService.get_latest_prices(db, sid, n=min_days + 20)

                    # If insufficient data, fetch from yfinance
                    if len(prices) < min_days:
                        logger.info(
                            f"Stock {sid}: insufficient data ({len(prices)} < {min_days}), fetching from yfinance"
                        )

                        fetched_prices = await _fetch_prices_from_yfinance(
                            stock.symbol,
                            stock.market,
                            min_days + 30,  # Fetch extra days for buffer
                        )

                        if fetched_prices:
                            # Upsert fetched prices to daily_prices table
                            await DailyPriceService.bulk_insert_prices(db, sid, fetched_prices)

                            # Re-fetch from database after insertion
                            prices = await DailyPriceService.get_latest_prices(
                                db, sid, n=min_days + 20
                            )
                            result["yfinance_fetches"] += 1
                            logger.info(
                                f"Stock {sid}: fetched {len(fetched_prices)} prices from yfinance"
                            )
                        else:
                            logger.warning(f"Stock {sid}: failed to fetch prices from yfinance")
                            await _track_failed_stock(redis_pool, sid)
                            continue

                    if len(prices) < min_days:
                        logger.warning(
                            f"Stock {sid}: still insufficient data after yfinance fetch"
                        )
                        await _track_failed_stock(redis_pool, sid)
                        continue

                    # Prepare price data for calculation
                    # Prices are in descending order (newest first), reverse to oldest-first
                    prices_asc = list(reversed(prices))
                    closes = [p.close for p in prices_asc]
                    ohlcs = [(p.open, p.high, p.low, p.close) for p in prices_asc]

                    # Calculate indicators
                    calculated = calculate_indicators_from_prices(
                        closes=closes,
                        ohlcs=ohlcs,
                        indicator_keys=required_keys,
                    )

                    # Upsert to database
                    if calculated:
                        indicators_to_upsert = [
                            StockIndicatorUpsert(
                                stock_id=sid,
                                indicator_key=key,
                                data=data,
                            )
                            for key, data in calculated.items()
                        ]

                        count = await StockIndicatorService.bulk_upsert_indicators(
                            db, indicators_to_upsert
                        )
                        result["indicators_calculated"] += count
                        logger.info(
                            f"Stock {sid}: calculated {len(calculated)} indicators, upserted {count}"
                        )

                        # Clear retry count on success
                        await redis_pool.delete(f"{REDIS_INDICATOR_RETRY_PREFIX}{sid}")

                    result["stocks_processed"] += 1

                except Exception as e:
                    error_msg = f"Stock {sid}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    result["errors"].append(error_msg)
                    await _track_failed_stock(redis_pool, sid)
                    continue

        result["success"] = True
        logger.info(
            f"Indicator calculation completed: processed {result['stocks_processed']} stocks, "
            f"calculated {result['indicators_calculated']} indicators, "
            f"yfinance fetches: {result['yfinance_fetches']}, "
            f"skipped: {result['stocks_skipped']}"
        )

    except Exception as e:
        result["errors"].append(f"Job error: {str(e)}")
        logger.error(f"Indicator calculation job failed: {e}", exc_info=True)
        result["success"] = False

    return result


def _get_min_required_days(indicator_keys: list[str]) -> int:
    """Calculate minimum required days of price data for given indicators.

    Args:
        indicator_keys: List of indicator keys (e.g., ["RSI_14_D", "MACD_12_26_9_D"])

    Returns:
        int: Minimum number of days required
    """
    min_days = 30  # Default minimum

    for key in indicator_keys:
        try:
            ind_type, params, _ = parse_indicator_key(key)

            if ind_type == IndicatorType.RSI:
                # RSI needs period + 1 days
                period = params[0] if params else 14
                min_days = max(min_days, period + 1)

            elif ind_type == IndicatorType.SMA:
                # SMA needs period days
                period = params[0] if params else 20
                min_days = max(min_days, period)

            elif ind_type == IndicatorType.KDJ:
                # KDJ needs k_period days
                k_period = params[0] if params else 9
                min_days = max(min_days, k_period)

            elif ind_type == IndicatorType.MACD:
                # MACD needs slow_period + signal_period days
                slow_period = params[1] if len(params) > 1 else 26
                signal_period = params[2] if len(params) > 2 else 9
                min_days = max(min_days, slow_period + signal_period)

        except ValueError:
            # Skip invalid keys
            continue

    return min_days


async def _fetch_prices_from_yfinance(
    symbol: str,
    market: str,
    days: int,
) -> list[DailyPriceBase] | None:
    """Fetch historical prices from yfinance API.

    Args:
        symbol: Stock symbol
        market: Stock market (e.g., "TW")
        days: Number of days to fetch

    Returns:
        list[DailyPriceBase] | None: Price data or None if failed
    """
    try:
        end_date = datetime.date.today()
        # Fetch more calendar days to get enough trading days
        start_date = end_date - datetime.timedelta(days=int(days * 1.5))

        yfinance_client = YFinanceClient()
        prices_data = await yfinance_client.get_historical_prices(
            symbol,
            start_date.isoformat(),
            end_date.isoformat(),
            market,
        )

        if not prices_data:
            return None

        prices = [
            DailyPriceBase(
                date=p["date"],
                open=p["open"],
                high=p["high"],
                low=p["low"],
                close=p["close"],
                volume=p["volume"],
            )
            for p in prices_data
        ]

        return prices

    except Exception as e:
        logger.error(f"Failed to fetch prices from yfinance for {symbol}: {e}")
        return None


async def _track_failed_stock(redis_pool, stock_id: int) -> None:
    """Track failed stock in Redis for retry management.

    Args:
        redis_pool: Redis connection pool from ARQ
        stock_id: Stock ID that failed
    """
    retry_key = f"{REDIS_INDICATOR_RETRY_PREFIX}{stock_id}"

    # Get current retry count
    current = await redis_pool.get(retry_key)
    retry_count = int(current) if current else 0

    # Increment retry count
    retry_count += 1

    # Set retry count with 1 hour expiry
    await redis_pool.set(retry_key, str(retry_count), ex=3600)

    # Add to failed set for monitoring
    await redis_pool.sadd(REDIS_INDICATOR_FAILED_KEY, str(stock_id))

    logger.warning(f"Stock {stock_id} marked as failed (retry #{retry_count})")