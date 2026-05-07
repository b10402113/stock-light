"""Sync jobs for database and Redis synchronization."""

import asyncio
import logging
from typing import Any

from sqlalchemy import select

from src.clients.redis_client import StockRedisClient
from src.database import SessionFactory
from src.models import Stock
from src.users.model import User  # Import User to resolve relationship dependencies

logger = logging.getLogger(__name__)


async def sync_active_stocks_to_redis(ctx: dict[str, Any]) -> None:
    """Sync active stocks from PostgreSQL to Redis.

    Runs every 5 minutes (configurable). Logic:
    1. Query all active stocks from database (id, symbol, source)
    2. Add each stock_id to Redis set (stocks:active)
    3. Pre-populate stock:info hash with symbol and source

    This ensures Redis stays in sync with database changes (new stocks added,
    stocks deactivated, etc.).

    Args:
        ctx: ARQ context dict with 'redis_pool'
    """
    logger.info("Starting sync active stocks to Redis task")

    redis_pool = ctx["redis"]
    redis_client = StockRedisClient(pool=redis_pool)

    try:
        async with SessionFactory() as session:
            # Query all stocks where is_active=True with stock_id, symbol, source
            result = await session.execute(
                select(Stock.id, Stock.symbol, Stock.source).where(Stock.is_active == True)
            )
            rows = result.all()

            logger.info(f"Found {len(rows)} active stocks in database")

            if rows:
                # Add all active stock_ids to Redis set
                # Pre-populate stock:info:{stock_id} hash with ONLY symbol and source fields
                # Price and updated_at will be set by batch task on next update
                for stock_id, symbol, source in rows:
                    await redis_client.add_active_stock(stock_id)
                    # Set only symbol and source fields (no price/updated_at yet)
                    client = await redis_client._get_client()
                    key = redis_client._stock_info_key(stock_id)
                    await client.hset(
                        key, mapping={"symbol": symbol, "source": str(source)}
                    )

                logger.info(f"Synced {len(rows)} active stocks to Redis")
            else:
                logger.warning("No active stocks found in database")

    except Exception as exc:
        logger.error(f"Sync active stocks task failed: {exc}")
        raise


async def persist_redis_to_database(ctx: dict[str, Any]) -> None:
    """Persistence cron job to flush Redis stock prices to PostgreSQL.

    Runs every 15 minutes. Logic:
    1. Fetch all active stock_ids from Redis
    2. Get cached stock info (including symbol) for each stock_id
    3. Batch update PostgreSQL stocks table by symbol

    Args:
        ctx: ARQ context dict with 'redis_pool'
    """
    logger.info("Starting Redis to PostgreSQL persistence task")

    redis_pool = ctx["redis"]
    redis_client = StockRedisClient(pool=redis_pool)

    try:
        # Step 1: Get active stock_ids from Redis
        active_stock_ids = await redis_client.get_active_stocks()
        logger.info(f"Found {len(active_stock_ids)} active stocks in Redis")

        if not active_stock_ids:
            logger.info("No active stocks to persist")
            return

        # Step 2: Fetch all stock info from Redis concurrently
        tasks = [redis_client.get_stock_info(stock_id) for stock_id in active_stock_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        stock_updates = []  # [(symbol, price)]
        for stock_id, result in zip(active_stock_ids, results):
            if isinstance(result, Exception):
                logger.warning(f"Failed to get Redis info for stock_id {stock_id}: {result}")
                continue
            if result is None:
                logger.warning(f"No Redis data for stock_id {stock_id}")
                continue
            if result.get("incomplete"):
                logger.warning(f"Incomplete cache for stock_id {stock_id}, skipping")
                continue

            symbol = result.get("symbol")
            price = result.get("price")

            if symbol and price is not None:
                stock_updates.append((symbol, price))
            else:
                logger.warning(f"Missing symbol or price for stock_id {stock_id}")

        logger.info(f"Prepared {len(stock_updates)} stock updates for database")

        # Step 3: Batch update PostgreSQL by symbol
        if stock_updates:
            async with SessionFactory() as session:
                # Use bulk update for efficiency
                for symbol, price in stock_updates:
                    # Find stock by symbol and update current_price
                    stmt = (
                        select(Stock)
                        .where(Stock.symbol == symbol)
                        .with_for_update()
                    )
                    result = await session.execute(stmt)
                    stock = result.scalar_one_or_none()

                    if stock:
                        stock.current_price = price
                    else:
                        logger.warning(f"Stock {symbol} not found in database")

                await session.commit()
                logger.info(f"Persisted {len(stock_updates)} stock prices to database")
        else:
            logger.warning("No stock prices to persist")

    except Exception as exc:
        logger.error(f"Persistence task failed: {exc}")
        raise