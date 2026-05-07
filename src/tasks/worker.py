"""ARQ worker for stock price updates.

Defines WorkerSettings with cron jobs and task functions for stock monitoring.
"""

import asyncio
import logging
import time
from typing import Any

from arq import cron, create_pool
from arq.connections import ArqRedis

from src.clients.redis_client import StockRedisClient
from src.config import settings
from src.tasks.config import redis_settings

logger = logging.getLogger(__name__)


async def update_stock_prices_master(ctx: dict[str, Any]) -> None:
    """Master task that identifies stocks needing updates and dispatches batch jobs.

    Runs every minute via cron. Logic:
    1. Fetch active stocks from Redis (stocks:active)
    2. Check each stock's updated_at timestamp concurrently
    3. Add to update list if updated_at >= 5 minutes old or no record
    4. Split into batches of 50 stocks
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
        # Step 1: Get active stocks
        active_stocks = await redis_client.get_active_stocks()
        logger.info(f"Found {len(active_stocks)} active stocks")

        if not active_stocks:
            logger.info("No active stocks to update")
            return

        # Step 2: Identify stocks needing updates (concurrently to avoid N+1)
        current_time = int(time.time())
        threshold_seconds = settings.STOCK_UPDATE_INTERVAL

        # Use asyncio.gather to fetch all stock info concurrently
        tasks = [redis_client.get_stock_info(symbol) for symbol in active_stocks]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        stocks_to_update = []
        for symbol, result in zip(active_stocks, results):
            # Handle exceptions - skip problematic stocks (avoid avalanche)
            if isinstance(result, Exception):
                logger.error(f"Failed to check {symbol}: {result}")
                continue  # Don't add to update list on error

            info = result

            # No record or too old -> needs update
            if info is None:
                stocks_to_update.append(symbol)
                logger.debug(f"{symbol}: no cache record, needs update")
            else:
                elapsed = current_time - info.get("updated_at", 0)
                if elapsed >= threshold_seconds:
                    stocks_to_update.append(symbol)
                    logger.debug(
                        f"{symbol}: {elapsed}s old (threshold {threshold_seconds}s), needs update"
                    )

        logger.info(f"Identified {len(stocks_to_update)} stocks needing updates")

        if not stocks_to_update:
            logger.info("No stocks need updating")
            return

        # Step 3: Split into batches
        batch_size = settings.STOCK_BATCH_SIZE
        batches = [
            stocks_to_update[i:i + batch_size]
            for i in range(0, len(stocks_to_update), batch_size)
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


async def update_stock_prices_batch(ctx: dict[str, Any], batch: list[str]) -> None:
    """Batch task to update stock prices (Phase 3 - placeholder).

    Args:
        ctx: ARQ context dict
        batch: List of stock symbols to update
    """
    logger.info(f"Batch task placeholder: {len(batch)} stocks to update")
    # Phase 3 will implement:
    # - Fetch prices from Fugle/YFinance API
    # - Update Redis cache
    # - Persist to database


async def startup(ctx: dict[str, Any]) -> None:
    """Worker startup hook."""
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


async def shutdown(ctx: dict[str, Any]) -> None:
    """Worker shutdown hook."""
    logger.info("ARQ worker shutting down")


class WorkerSettings:
    """ARQ worker configuration.

    Run with: arq src.tasks.worker.WorkerSettings
    """

    functions = [update_stock_prices_master, update_stock_prices_batch]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = redis_settings

    # Job configuration
    job_timeout = settings.ARQ_JOB_TIMEOUT
    max_tries = settings.ARQ_MAX_TRIES

    # Cron jobs - run master task every minute
    cron_jobs = [
        cron(
            update_stock_prices_master,
            minute=set(range(60)),  # Every minute: 0, 1, 2, ..., 59
            run_at_startup=False,  # Don't run immediately on worker start
        )
    ]