"""Backtest jobs for fetching missing historical prices."""

import datetime
import logging
from typing import Any


from src.clients.fugle_client import FugoClient
from src.clients.yfinance_client import YFinanceClient
from src.database import SessionFactory
from src.stocks.schema import DailyPriceBase, StockSource
from src.stocks.service import DailyPriceService, StockService

logger = logging.getLogger(__name__)


async def fetch_missing_daily_prices(
    ctx: dict[str, Any],
    stock_id: int,
    date_ranges: list[dict[str, str]],
) -> dict[str, Any]:
    """Fetch missing historical prices and insert to DailyPrice.

    Args:
        ctx: ARQ context
        stock_id: Stock ID
        date_ranges: Missing date ranges [{"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}, ...]

    Returns:
        {"stock_id": int, "fetched_count": int, "success": bool, "error": str | None}
    """
    logger.info(f"Starting fetch_missing_daily_prices for stock_id={stock_id}")

    fetched_count = 0
    success = True
    error_msg = None

    try:
        # Get stock info and source
        async with SessionFactory() as db:
            stock = await StockService.get_by_id(db, stock_id)
            if not stock:
                raise ValueError(f"Stock not found: {stock_id}")

            symbol = stock.symbol
            source = stock.source

        logger.info(f"Stock: id={stock_id}, symbol={symbol}, source={source}")

        # Convert date_ranges from dict to tuple format
        ranges = [
            (datetime.date.fromisoformat(r["start_date"]), datetime.date.fromisoformat(r["end_date"]))
            for r in date_ranges
        ]

        # Fetch historical prices - ALWAYS use YFinance (free)
        all_prices = []

        yfinance_client = YFinanceClient()
        for start, end in ranges:
            prices = await yfinance_client.get_historical_prices(
                symbol,
                start.isoformat(),
                end.isoformat(),
            )
            for p in prices:
                all_prices.append(
                    DailyPriceBase(
                        date=p["date"],
                        open=p["open"],
                        high=p["high"],
                        low=p["low"],
                        close=p["close"],
                        volume=p["volume"],
                    )
                )

        logger.info(f"Fetched {len(all_prices)} historical prices from API")

        # Bulk insert to database (upsert)
        if all_prices:
            async with SessionFactory() as db:
                count = await DailyPriceService.bulk_insert_prices(db, stock_id, all_prices)
                fetched_count = count
                logger.info(f"Inserted/updated {count} prices to database")

    except Exception as e:
        success = False
        error_msg = str(e)
        logger.error(f"fetch_missing_daily_prices failed: {e}")

    return {
        "stock_id": stock_id,
        "fetched_count": fetched_count,
        "success": success,
        "error": error_msg,
    }