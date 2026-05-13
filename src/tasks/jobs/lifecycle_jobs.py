"""Lifecycle hooks for ARQ worker startup and shutdown."""

import logging
from typing import Any

from sqlalchemy import select

from src.clients.redis_client import StockRedisClient
from src.database import SessionFactory
from src.stocks.model import Stock
from src.users.model import User  # Import User to resolve relationship dependencies

logger = logging.getLogger(__name__)


async def startup(ctx: dict[str, Any]) -> None:
    """Worker startup hook.

    Initializes logging and loads active stocks with stock_id, symbol, source from database to Redis.
    Only sets symbol and source fields - price and updated_at will be set by batch task on first update.
    """
    # Configure only our module's logger (not ARQ's)
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    # Prevent propagation to root logger (avoid duplicate logs)
    logger.propagate = False
    logger.info("ARQ worker starting")

    # Load active stocks with stock_id, symbol, source from database to Redis
    try:
        redis_pool = ctx["redis"]
        redis_client = StockRedisClient(pool=redis_pool)

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
                # Price and updated_at will be set by batch task on first update
                for stock_id, symbol, source in rows:
                    await redis_client.add_active_stock(stock_id)
                    # Set only symbol and source fields (no price/updated_at yet)
                    client = await redis_client._get_client()
                    key = redis_client._stock_info_key(stock_id)
                    await client.hset(
                        key, mapping={"symbol": symbol, "source": str(source)}
                    )

                logger.info(f"Loaded {len(rows)} active stocks with stock_id to Redis")
            else:
                logger.warning("No active stocks found in database")

    except Exception as exc:
        logger.error(f"Failed to load active stocks: {exc}")
        # Don't raise - allow worker to continue running


async def shutdown(ctx: dict[str, Any]) -> None:
    """Worker shutdown hook."""
    logger.info("ARQ worker shutting down")