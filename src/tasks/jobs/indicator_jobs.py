"""Indicator calculation jobs."""

import logging
from typing import Any

from sqlalchemy import select

from src.database import SessionFactory
from src.stock_indicator.calculator import calculate_indicators_from_prices
from src.stock_indicator.schema import StockIndicatorUpsert
from src.stock_indicator.service import StockIndicatorService
from src.stocks.model import DailyPrice, Stock
from src.stocks.service import DailyPriceService, StockService

logger = logging.getLogger(__name__)


async def calculate_stock_indicators(
    ctx: dict[str, Any],
    stock_id: int | None = None,
) -> dict[str, Any]:
    """Calculate indicators for stocks with active subscriptions.

    This job periodically fetches stocks that:
    1. Have is_active=True
    2. Have at least one indicator subscription

    For each stock, it:
    1. Fetches historical prices
    2. Calculates required indicators based on subscriptions
    3. Stores results in stock_indicator table

    Args:
        ctx: ARQ context dict
        stock_id: Optional specific stock ID to calculate (if None, calculate all active stocks)

    Returns:
        dict with processing statistics
    """
    logger.info("Starting indicator calculation job")

    result = {
        "stocks_processed": 0,
        "indicators_calculated": 0,
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
                    # Get stock info
                    stock = await StockService.get_by_id(db, sid)
                    if not stock or not stock.is_active:
                        logger.warning(f"Stock {sid} not found or inactive, skipping")
                        continue

                    # Get required indicator keys for this stock
                    required_keys = await StockIndicatorService.get_required_indicator_keys(
                        db, sid
                    )

                    if not required_keys:
                        logger.info(f"No indicator subscriptions for stock {sid}, skipping")
                        continue

                    # Fetch historical prices (need enough for indicator calculation)
                    # Most indicators need at least 30-50 days of data
                    prices = await DailyPriceService.get_latest_prices(db, sid, n=100)

                    if len(prices) < 30:
                        logger.warning(
                            f"Stock {sid} has insufficient price data ({len(prices)} days), skipping"
                        )
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

                    result["stocks_processed"] += 1

                except Exception as e:
                    error_msg = f"Stock {sid}: {str(e)}"
                    logger.error(error_msg)
                    result["errors"].append(error_msg)
                    continue

        result["success"] = True
        logger.info(
            f"Indicator calculation completed: processed {result['stocks_processed']} stocks, "
            f"calculated {result['indicators_calculated']} indicators"
        )

    except Exception as e:
        result["errors"].append(f"Job error: {str(e)}")
        logger.error(f"Indicator calculation job failed: {e}")
        result["success"] = False

    return result