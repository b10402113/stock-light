"""Indicator calculation jobs."""

import datetime
import logging
from typing import Any

from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from src.clients.yfinance_client import YFinanceClient
from src.config import settings
from src.database import SessionFactory
from src.logging_config import get_console
from src.stock_indicator.calculator import calculate_indicators_from_prices
from src.stock_indicator.schema import IndicatorType, parse_indicator_key
from src.stock_indicator.service import StockIndicatorService
from src.stocks.schema import DailyPriceBase
from src.stocks.service import DailyPriceService, StockService

logger = logging.getLogger(__name__)
console = get_console()

REDIS_INDICATOR_RETRY_PREFIX = "indicator:retry:"
REDIS_INDICATOR_FAILED_KEY = "indicator:failed"
REDIS_INDICATOR_ERROR_PREFIX = "indicator:error:"  # Store error reason
REDIS_INDICATOR_UPDATED_KEY = "indicator:updated:last_minute"  # Track updated stocks


async def update_indicator(ctx: dict[str, Any]) -> dict[str, Any]:
    """Calculate indicators for stocks with active subscriptions.

    Cron job running every minute. Queries indicator_subscriptions table,
    extracts required indicators, and calculates them for each stock.

    Flow:
    1. Query stocks with active indicator subscriptions
    2. For each stock:
       - Get required indicator keys from subscriptions
       - Fetch historical prices from daily_prices (or yfinance fallback)
       - Calculate indicators and upsert to stock_indicator table
    3. Handle errors gracefully, track failures in Redis

    Args:
        ctx: ARQ context dict with 'redis'

    Returns:
        dict with processing statistics
    """
    logger.info("[job]Starting update_indicator job[/job]")
    console.print("[time]━━━ Indicator Update ━━━[/time]")

    redis_pool = ctx["redis"]

    result = {
        "stocks_processed": 0,
        "indicators_calculated": 0,
        "yfinance_fetches": 0,
        "errors": [],
        "success": False,
        "updated_stocks": [],
    }

    try:
        async with SessionFactory() as db:
            # Get stocks with active indicator subscriptions
            stock_ids = await StockIndicatorService.get_stocks_with_indicators(db)
            console.print(f"{stock_ids}")
            if not stock_ids:
                logger.info("No stocks with indicator subscriptions")
                console.print("[info]No stocks with indicator subscriptions[/info]")
                result["success"] = True
                return result

            logger.info(f"Processing [stock]{len(stock_ids)}[/stock] stocks for indicator calculation")
            console.print(f"[cyan]Processing {len(stock_ids)} stocks...[/cyan]")

            # Process stocks with progress bar
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("[cyan]Calculating indicators...", total=len(stock_ids))

                for sid in stock_ids:
                    try:
                        # Check retry count and error reason for failed stocks
                        retry_count = await redis_pool.get(
                            f"{REDIS_INDICATOR_RETRY_PREFIX}{sid}"
                        )
                        error_reason = await redis_pool.get(
                            f"{REDIS_INDICATOR_ERROR_PREFIX}{sid}"
                        )
                        if retry_count and int(retry_count) >= settings.INDICATOR_MAX_RETRIES:
                            error_msg = error_reason.decode() if error_reason else "unknown error"
                            logger.warning(
                                f"[warning]Stock [stock]{sid}[/stock] exceeded max retries ({int(retry_count)}), "
                                f"skipping - [error]original error: {error_msg}[/error]"
                            )
                            console.print(
                                f"[yellow]⚠ Stock {sid} skipped (max retries) - {error_msg}[/yellow]"
                            )
                            progress.advance(task)
                            continue

                        # Get stock info
                        stock = await StockService.get_by_id(db, sid)
                        if not stock or stock.is_deleted:
                            logger.warning(f"Stock [stock]{sid}[/stock] not found or deleted, skipping")
                            progress.advance(task)
                            continue

                        # Get required indicator keys for this stock
                        required_keys = await StockIndicatorService.get_required_indicator_keys(
                            db, sid
                        )

                        if not required_keys:
                            logger.info(f"No indicator subscriptions for stock [stock]{sid}[/stock], skipping")
                            progress.advance(task)
                            continue

                        # Determine minimum required days based on indicator keys
                        min_days = _get_min_required_days(required_keys)
                        logger.info(
                            f"Stock [stock]{sid}[/stock]: needs [time]{min_days}[/time] days for [job]{len(required_keys)}[/job] indicators"
                        )

                        # Fetch historical prices from daily_prices table
                        prices = await DailyPriceService.get_latest_prices(db, sid, n=min_days + 20)

                        # If insufficient data, fetch from yfinance
                        if len(prices) < min_days:
                            logger.info(
                                f"Stock [stock]{sid}[/stock]: insufficient data ([warning]{len(prices)} < {min_days}[/warning]), fetching yfinance"
                            )

                            fetched_prices = await _fetch_prices_from_yfinance(
                                stock.symbol,
                                stock.market,
                                min_days + 30,
                            )

                            if fetched_prices:
                                await DailyPriceService.bulk_insert_prices(db, sid, fetched_prices)
                                prices = await DailyPriceService.get_latest_prices(
                                    db, sid, n=min_days + 20
                                )
                                result["yfinance_fetches"] += 1
                                logger.info(
                                    f"Stock [stock]{sid}[/stock]: fetched [success]{len(fetched_prices)}[/success] prices from yfinance"
                                )
                            else:
                                error_reason = f"yfinance fetch failed for symbol {stock.symbol} (market={stock.market})"
                                logger.warning(f"[warning]Stock [stock]{sid}[/stock]: {error_reason}[/warning]")
                                await _track_failed_stock(redis_pool, sid, error_reason)
                                progress.advance(task)
                                continue

                        if len(prices) < min_days:
                            error_reason = f"insufficient data ({len(prices)} < {min_days}) after yfinance fallback"
                            logger.warning(f"[warning]Stock [stock]{sid}[/stock]: {error_reason}[/warning]")
                            await _track_failed_stock(redis_pool, sid, error_reason)
                            progress.advance(task)
                            continue

                        # Prepare price data for calculation (oldest to newest)
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
                            from src.stock_indicator.schema import StockIndicatorUpsert

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
                                f"Stock [stock]{sid}[/stock]: calculated [success]{len(calculated)}[/success] indicators, upserted [job]{count}[/job]"
                            )

                            # Track updated stock in Redis for subscription check
                            await redis_pool.sadd(REDIS_INDICATOR_UPDATED_KEY, str(sid))
                            await redis_pool.expire(REDIS_INDICATOR_UPDATED_KEY, 120)
                            result["updated_stocks"].append(sid)

                            # Clear retry count and error reason on success
                            await redis_pool.delete(f"{REDIS_INDICATOR_RETRY_PREFIX}{sid}")
                            await redis_pool.delete(f"{REDIS_INDICATOR_ERROR_PREFIX}{sid}")

                        result["stocks_processed"] += 1
                        progress.advance(task)

                    except Exception as e:
                        error_reason = str(e)
                        error_msg = f"Stock [stock]{sid}[/stock]: {error_reason}"
                        logger.error(f"[error]{error_msg}[/error]", exc_info=True)
                        result["errors"].append(error_msg)
                        await _track_failed_stock(redis_pool, sid, error_reason)
                        progress.advance(task)
                        continue

        result["success"] = True

        # Print summary table
        table = Table(title="Indicator Update Summary", show_header=True, header_style="bold cyan")
        table.add_column("Metric", style="dim")
        table.add_column("Count", justify="right")
        table.add_row("Stocks Processed", str(result["stocks_processed"]))
        table.add_row("Indicators Calculated", str(result["indicators_calculated"]))
        table.add_row("Stocks Updated", str(len(result["updated_stocks"])))
        table.add_row("YFinance Fetches", str(result["yfinance_fetches"]))
        table.add_row("Errors", str(len(result["errors"])))
        console.print(table)

        logger.info(
            f"[success]update_indicator completed[/success]: processed [stock]{result['stocks_processed']}[/stock] stocks, "
            f"calculated [job]{result['indicators_calculated']}[/job] indicators, "
            f"updated [stock]{len(result['updated_stocks'])}[/stock] stocks for subscription check, "
            f"yfinance fetches: [time]{result['yfinance_fetches']}[/time]"
        )

    except Exception as e:
        result["errors"].append(f"Job error: {str(e)}")
        logger.error(f"[error]update_indicator job failed: {e}[/error]", exc_info=True)
        result["success"] = False

    return result


def _get_min_required_days(indicator_keys: list[str]) -> int:
    """Calculate minimum required days of price data for given indicators."""
    min_days = 30  # Default minimum

    for key in indicator_keys:
        try:
            ind_type, params, _ = parse_indicator_key(key)

            if ind_type == IndicatorType.RSI:
                period = params[0] if params else 14
                min_days = max(min_days, period + 1)

            elif ind_type == IndicatorType.SMA:
                period = params[0] if params else 20
                min_days = max(min_days, period)

            elif ind_type == IndicatorType.KDJ:
                k_period = params[0] if params else 9
                min_days = max(min_days, k_period)

            elif ind_type == IndicatorType.MACD:
                slow_period = params[1] if len(params) > 1 else 26
                signal_period = params[2] if len(params) > 2 else 9
                min_days = max(min_days, slow_period + signal_period)

        except ValueError:
            continue

    return min_days


async def _fetch_prices_from_yfinance(
    symbol: str,
    market: str,
    days: int,
) -> list[DailyPriceBase] | None:
    """Fetch historical prices from yfinance API."""
    try:
        end_date = datetime.date.today()
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


async def _track_failed_stock(redis_pool, stock_id: int, error_reason: str = "") -> None:
    """Track failed stock in Redis for retry management.

    Args:
        redis_pool: Redis connection pool
        stock_id: Stock ID that failed
        error_reason: Description of why the stock failed
    """
    retry_key = f"{REDIS_INDICATOR_RETRY_PREFIX}{stock_id}"
    error_key = f"{REDIS_INDICATOR_ERROR_PREFIX}{stock_id}"

    current = await redis_pool.get(retry_key)
    retry_count = int(current) if current else 0
    retry_count += 1

    await redis_pool.set(retry_key, str(retry_count), ex=3600)
    await redis_pool.sadd(REDIS_INDICATOR_FAILED_KEY, str(stock_id))

    # Store error reason for better debugging
    if error_reason:
        await redis_pool.set(error_key, error_reason, ex=3600)

    logger.warning(
        f"[warning]Stock [stock]{stock_id}[/stock] marked as failed "
        f"(retry #{retry_count}) - [error]{error_reason}[/error]"
    )