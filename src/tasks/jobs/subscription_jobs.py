"""Subscription data preparation jobs."""

import logging
import time
from typing import Any

from arq import create_pool
from arq.connections import ArqRedis

from src.clients.fugle_client import FugoClient
from src.clients.redis_client import StockRedisClient
from src.clients.yfinance_client import YFinanceClient
from src.database import SessionFactory
from src.stocks.schema import DailyPriceBase, StockSource
from src.stocks.service import DailyPriceService, StockService

logger = logging.getLogger(__name__)


async def prepare_subscription_data(
    ctx: dict[str, Any],
    stock_id: int,
) -> dict[str, Any]:
    """Prepare stock data for subscription monitoring.

    This job is triggered when a user subscribes to a stock that doesn't have
    active monitoring or sufficient historical data.

    Steps:
    1. Add stock to Redis active set
    2. Fetch current price and update Redis cache
    3. Fetch 100 days of historical prices
    4. Insert historical prices to database (upsert)

    Args:
        ctx: ARQ context dict with 'redis_pool'
        stock_id: Stock ID to prepare

    Returns:
        dict with stock_id, status, and any error message
    """
    logger.info(f"Starting subscription data preparation for stock_id={stock_id}")

    redis_pool = ctx["redis"]
    redis_client = StockRedisClient(pool=redis_pool)

    result = {
        "stock_id": stock_id,
        "added_to_redis": False,
        "current_price_fetched": False,
        "historical_prices_count": 0,
        "success": False,
        "error": None,
    }

    try:
        # Step 1: Get stock info from database
        async with SessionFactory() as db:
            stock = await StockService.get_by_id(db, stock_id)
            if not stock:
                raise ValueError(f"Stock not found: {stock_id}")

            symbol = stock.symbol
            source = stock.source

        logger.info(f"Stock: id={stock_id}, symbol={symbol}, source={source}")

        # Step 2: Add stock to Redis active set
        added = await redis_client.add_active_stock(stock_id)
        result["added_to_redis"] = added
        logger.info(f"Added stock_id={stock_id} to Redis active set: {added}")

        # Step 3: Fetch current price from API and update Redis
        current_price = None
        if source == StockSource.FUGLE:
            fugle_client = FugoClient()
            quote = await fugle_client.get_intraday_quote(symbol)
            if quote and quote.lastPrice is not None:
                current_price = float(quote.lastPrice)
                await redis_client.set_stock_price(
                    stock_id, symbol, current_price, StockSource.FUGLE
                )
                result["current_price_fetched"] = True
                logger.info(f"Fetched current price from Fugle: {current_price}")

        elif source == StockSource.YFINANCE:
            yfinance_client = YFinanceClient()
            price = await yfinance_client.get_current_price(symbol)
            if price is not None:
                current_price = price
                await redis_client.set_stock_price(
                    stock_id, symbol, current_price, StockSource.YFINANCE
                )
                result["current_price_fetched"] = True
                logger.info(f"Fetched current price from YFinance: {current_price}")

        if current_price is None:
            logger.warning(f"Failed to fetch current price for stock_id={stock_id}")

        # Step 4: Fetch historical prices (100 days) - ALWAYS use YFinance (free)
        # Calculate date range for last 100 trading days (approximately 140 calendar days)
        import datetime
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=140)

        historical_prices = []

        # Always use YFinance for historical prices (free API)
        yfinance_client = YFinanceClient()
        prices = await yfinance_client.get_historical_prices(
            symbol,
            start_date.isoformat(),
            end_date.isoformat(),
        )
        for p in prices:
            historical_prices.append(
                DailyPriceBase(
                    date=p["date"],
                    open=p["open"],
                    high=p["high"],
                    low=p["low"],
                    close=p["close"],
                    volume=p["volume"],
                )
            )

        logger.info(f"Fetched {len(historical_prices)} historical prices from API")

        # Step 5: Insert historical prices to database (upsert)
        if historical_prices:
            async with SessionFactory() as db:
                count = await DailyPriceService.bulk_insert_prices(
                    db, stock_id, historical_prices
                )
                result["historical_prices_count"] = count
                logger.info(f"Inserted/updated {count} historical prices to database")

        result["success"] = True
        logger.info(f"Subscription data preparation completed for stock_id={stock_id}")

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Subscription data preparation failed for stock_id={stock_id}: {e}")
        # Don't raise - let ARQ handle retry logic
        result["success"] = False

    return result