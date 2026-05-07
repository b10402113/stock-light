"""ARQ worker for stock price updates.

Defines WorkerSettings with cron jobs and task functions for stock monitoring.
"""

import asyncio
import logging
import time
from typing import Any

from arq import cron, create_pool
from arq.connections import ArqRedis
from sqlalchemy import select

from src.clients.fugle_client import FugoClient
from src.clients.redis_client import StockRedisClient
from src.clients.yfinance_client import YFinanceClient
from src.config import settings
from src.database import SessionFactory
from src.models import Stock  # Import Stock from models package
from src.users.model import User  # Import User to resolve relationship dependencies
from src.stocks.schema import StockSource
from src.tasks.config import redis_settings

logger = logging.getLogger(__name__)


async def update_stock_prices_master(ctx: dict[str, Any]) -> None:
    """Master task that identifies stocks needing updates and dispatches batch jobs.

    Runs every minute via cron. Logic:
    1. Fetch active stock_ids from Redis (stocks:active)
    2. Check each stock's updated_at timestamp concurrently
    3. Add to update list if updated_at >= 5 minutes old or no record
    4. Split into batches of 50 stock_ids
    5. Dispatch batch jobs using enqueue_job

    Args:
        ctx: ARQ context dict with 'redis_pool' for enqueueing jobs
    """
    logger.info("Starting stock price update master task")

    # Use ARQ's shared redis_pool to avoid creating new connections
    redis_pool = ctx["redis"]

    # Create Redis client using the existing pool (no connection overhead)
    redis_client = StockRedisClient(pool=redis_pool)

    try:
        # Step 1: Get active stock_ids
        active_stock_ids = await redis_client.get_active_stocks()
        logger.info(f"Found {len(active_stock_ids)} active stocks")

        if not active_stock_ids:
            logger.info("No active stocks to update")
            return

        # Step 2: Identify stocks needing updates (concurrently to avoid N+1)
        current_time = int(time.time())
        threshold_seconds = settings.STOCK_UPDATE_INTERVAL

        # Use asyncio.gather to fetch all stock info concurrently
        tasks = [redis_client.get_stock_info(stock_id) for stock_id in active_stock_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        stock_ids_to_update = []
        for stock_id, result in zip(active_stock_ids, results):
            # Handle exceptions - skip problematic stocks (avoid avalanche)
            if isinstance(result, Exception):
                logger.error(f"Failed to check stock_id {stock_id}: {result}")
                continue  # Don't add to update list on error

            info = result

            # No record or too old -> needs update
            if info is None:
                stock_ids_to_update.append(stock_id)
                logger.debug(f"stock_id {stock_id}: no cache record, needs update")
            elif info.get("incomplete"):
                # Incomplete cache (only symbol/source) -> needs update
                stock_ids_to_update.append(stock_id)
                logger.debug(f"stock_id {stock_id}: incomplete cache, needs update")
            else:
                elapsed = current_time - info.get("updated_at", 0)
                if elapsed >= threshold_seconds:
                    stock_ids_to_update.append(stock_id)
                    logger.debug(
                        f"stock_id {stock_id}: {elapsed}s old (threshold {threshold_seconds}s), needs update"
                    )

        logger.info(f"Identified {len(stock_ids_to_update)} stocks needing updates")

        if not stock_ids_to_update:
            logger.info("No stocks need updating")
            return

        # Step 3: Split into batches
        batch_size = settings.STOCK_BATCH_SIZE
        batches = [
            stock_ids_to_update[i:i + batch_size]
            for i in range(0, len(stock_ids_to_update), batch_size)
        ]

        logger.info(f"Split into {len(batches)} batches")

        # Step 4: Dispatch batch jobs concurrently
        enqueue_tasks = [
            redis_pool.enqueue_job("update_stock_prices_batch", batch)
            for batch in batches
        ]

        enqueue_results = await asyncio.gather(*enqueue_tasks, return_exceptions=True)

        success_count = 0
        for idx, (batch, res) in enumerate(zip(batches, enqueue_results), 1):
            if isinstance(res, Exception):
                logger.error(f"Failed to enqueue batch {idx}: {res}")
            else:
                success_count += 1
                logger.info(f"Dispatched batch {idx}/{len(batches)}: {len(batch)} stocks, job_id={res.job_id}")

        logger.info(f"Master task complete: dispatched {success_count}/{len(batches)} batch jobs")

    except Exception as exc:
        logger.error(f"Master task failed: {exc}")
        raise
    # No need to close redis_client - using shared pool from ARQ


async def update_stock_prices_batch(ctx: dict[str, Any], batch: list[int]) -> None:
    """Batch task to update stock prices with source-based API routing.

    Logic:
    1. Get symbol and source info from Redis for each stock_id (no database query)
    2. Partition into Fugle stocks and YFinance stocks by symbol
    3. Fetch prices concurrently from appropriate APIs
    4. Use Redis Pipeline for batch updates

    Args:
        ctx: ARQ context dict with 'redis_pool'
        batch: List of stock IDs to update
    """
    logger.info(f"Starting batch update for {len(batch)} stock_ids")

    if not batch:
        logger.warning("Empty batch received")
        return

    redis_pool = ctx["redis"]
    redis_client = StockRedisClient(pool=redis_pool)

    # Step 1: Get symbol and source info from Redis (no database query needed)
    stock_symbol_map = {}  # {stock_id: symbol}
    stock_source_map = {}  # {stock_id: source}

    tasks = [redis_client.get_stock_info(stock_id) for stock_id in batch]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for stock_id, result in zip(batch, results):
        if isinstance(result, Exception):
            logger.warning(f"Failed to get Redis info for stock_id {stock_id}: {result}")
            continue
        if result is None:
            logger.warning(f"No Redis data for stock_id {stock_id}, skipping")
            continue

        symbol = result.get("symbol")
        source = result.get("source")

        if symbol and source is not None:
            stock_symbol_map[stock_id] = symbol
            stock_source_map[stock_id] = source
        else:
            logger.warning(f"Missing symbol or source for stock_id {stock_id}")

    logger.info(f"Got symbol/source info from Redis for {len(stock_symbol_map)} stocks")

    # Step 2: Partition stocks by source (using symbols for API calls)
    fugle_symbols = []  # [(stock_id, symbol)]
    yfinance_symbols = []  # [(stock_id, symbol)]

    for stock_id in stock_symbol_map:
        symbol = stock_symbol_map[stock_id]
        source = stock_source_map[stock_id]

        if source == StockSource.FUGLE:
            fugle_symbols.append((stock_id, symbol))
        elif source == StockSource.YFINANCE:
            yfinance_symbols.append((stock_id, symbol))

    logger.info(f"Partitioned: {len(fugle_symbols)} Fugle, {len(yfinance_symbols)} YFinance")

    # Step 3: Fetch prices concurrently
    fugle_prices = {}  # {stock_id: price}
    yfinance_prices = {}  # {stock_id: price}

    # Fetch Fugle prices concurrently
    if fugle_symbols:
        fugle_client = FugoClient()
        fugle_tasks = [
            fugle_client.get_intraday_quote(symbol) for stock_id, symbol in fugle_symbols
        ]
        fugle_results = await asyncio.gather(*fugle_tasks, return_exceptions=True)

        for (stock_id, symbol), result in zip(fugle_symbols, fugle_results):
            if isinstance(result, Exception):
                logger.warning(f"Fugle API failed for stock_id {stock_id} ({symbol}): {result}")
            elif result and result.lastPrice is not None:
                fugle_prices[stock_id] = float(result.lastPrice)
            else:
                logger.warning(f"No price data from Fugle for stock_id {stock_id} ({symbol})")

    # Fetch YFinance prices concurrently (using run_in_threadpool)
    if yfinance_symbols:
        yfinance_client = YFinanceClient()
        yfinance_tasks = [
            yfinance_client.get_current_price(symbol) for stock_id, symbol in yfinance_symbols
        ]
        yfinance_results = await asyncio.gather(*yfinance_tasks, return_exceptions=True)

        for (stock_id, symbol), result in zip(yfinance_symbols, yfinance_results):
            if isinstance(result, Exception):
                logger.warning(f"YFinance API failed for stock_id {stock_id} ({symbol}): {result}")
            elif result is not None:
                yfinance_prices[stock_id] = result
            else:
                logger.warning(f"No price data from YFinance for stock_id {stock_id} ({symbol})")

    # Combine all fetched prices with stock_id, symbol, source info
    stock_data = []
    for stock_id in fugle_prices:
        symbol = stock_symbol_map[stock_id]
        stock_data.append((stock_id, symbol, fugle_prices[stock_id], StockSource.FUGLE))

    for stock_id in yfinance_prices:
        symbol = stock_symbol_map[stock_id]
        stock_data.append((stock_id, symbol, yfinance_prices[stock_id], StockSource.YFINANCE))

    logger.info(f"Successfully fetched {len(stock_data)} prices")

    # Step 4: Use Redis Pipeline for batch updates
    if stock_data:
        try:
            count = await redis_client.batch_set_stock_prices(stock_data)
            logger.info(f"Updated {count} stocks in Redis cache")
        except Exception as exc:
            logger.error(f"Redis Pipeline failed: {exc}")
            raise  # Raise to trigger ARQ retry
    else:
        logger.warning("No prices to update in Redis")


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


class WorkerSettings:
    """ARQ worker configuration.

    Run with: arq src.tasks.worker.WorkerSettings
    """

    functions = [
        update_stock_prices_master,
        update_stock_prices_batch,
        persist_redis_to_database,
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = redis_settings

    # Job configuration
    job_timeout = settings.ARQ_JOB_TIMEOUT
    max_tries = settings.ARQ_MAX_TRIES
    max_jobs = 1  # Limit concurrent batch jobs to prevent rate limit exceeded

    # Cron jobs - configurable via .env
    cron_jobs = [
        # Master task: schedule configurable via CRON_MASTER_MINUTES
        cron(
            update_stock_prices_master,
            minute=settings.parse_cron_minutes(settings.CRON_MASTER_MINUTES),
            run_at_startup=False,  # Don't run immediately on worker start
        ),
        # Persistence task: schedule configurable via CRON_PERSIST_MINUTES
        cron(
            persist_redis_to_database,
            minute=settings.parse_cron_minutes(settings.CRON_PERSIST_MINUTES),
            run_at_startup=False,
        ),
    ]