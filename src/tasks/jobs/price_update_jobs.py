"""Price update jobs for stock monitoring."""

import asyncio
import logging
import time
from typing import Any

from arq import create_pool
from arq.connections import ArqRedis

from src.clients.fugle_client import FugoClient
from src.clients.redis_client import StockRedisClient
from src.clients.yfinance_client import YFinanceClient
from src.config import settings
from src.stocks.schema import StockSource

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

        # Priority order:
        # 1. No cache or incomplete cache (highest priority)
        # 2. Expired cache sorted by elapsed time (largest → smallest)
        high_priority_ids = []  # No cache or incomplete cache
        expired_with_elapsed = []  # [(stock_id, elapsed)] for sorting

        for stock_id, result in zip(active_stock_ids, results):
            # Handle exceptions - skip problematic stocks (avoid avalanche)
            if isinstance(result, Exception):
                logger.error(f"Failed to check stock_id {stock_id}: {result}")
                continue  # Don't add to update list on error

            info = result

            # No record or incomplete cache -> highest priority
            if info is None:
                high_priority_ids.append(stock_id)
                logger.debug(f"stock_id {stock_id}: no cache record, highest priority")
            elif info.get("incomplete"):
                # Incomplete cache (only symbol/source) -> highest priority
                high_priority_ids.append(stock_id)
                logger.debug(f"stock_id {stock_id}: incomplete cache, highest priority")
            else:
                elapsed = current_time - info.get("updated_at", 0)
                if elapsed >= threshold_seconds:
                    expired_with_elapsed.append((stock_id, elapsed))
                    logger.debug(
                        f"stock_id {stock_id}: {elapsed}s old (threshold {threshold_seconds}s), needs update"
                    )

        # Sort expired cache by elapsed time (largest first = most outdated first)
        expired_with_elapsed.sort(key=lambda x: x[1], reverse=True)
        expired_ids = [stock_id for stock_id, _ in expired_with_elapsed]

        # Combine: high priority first, then sorted expired
        stock_ids_to_update = high_priority_ids + expired_ids

        logger.info(
            f"Identified {len(stock_ids_to_update)} stocks needing updates "
            f"(high_priority={len(high_priority_ids)}, expired={len(expired_ids)})"
        )

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

        # Step 4: Dispatch batch jobs concurrently into API-specific queue
        enqueue_tasks = [
            redis_pool.enqueue_job(
                "update_stock_prices_batch",
                batch,
                _queue_name="api_queue"  # Send to dedicated API queue
            )
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
    no_price_stock_ids = []  # Stocks confirmed to have no price data (remove from Redis)

    # Fetch Fugle prices concurrently
    if fugle_symbols:
        fugle_client = FugoClient()
        fugle_tasks = [
            fugle_client.get_intraday_quote(symbol) for stock_id, symbol in fugle_symbols
        ]
        fugle_results = await asyncio.gather(*fugle_tasks, return_exceptions=True)

        for (stock_id, symbol), result in zip(fugle_symbols, fugle_results):
            if isinstance(result, Exception):
                # API failed - don't remove, let next retry handle it
                logger.warning(f"Fugle API failed for stock_id {stock_id} ({symbol}): {result}")
            elif result and result.lastPrice is not None:
                fugle_prices[stock_id] = float(result.lastPrice)
            else:
                # Confirmed no price data - remove from Redis
                logger.warning(f"No price data from Fugle for stock_id {stock_id} ({symbol})")
                no_price_stock_ids.append(stock_id)

    # Fetch YFinance prices concurrently (using run_in_threadpool)
    if yfinance_symbols:
        yfinance_client = YFinanceClient()
        yfinance_tasks = [
            yfinance_client.get_current_price(symbol) for stock_id, symbol in yfinance_symbols
        ]
        yfinance_results = await asyncio.gather(*yfinance_tasks, return_exceptions=True)

        for (stock_id, symbol), result in zip(yfinance_symbols, yfinance_results):
            if isinstance(result, Exception):
                # API failed - don't remove, let next retry handle it
                logger.warning(f"YFinance API failed for stock_id {stock_id} ({symbol}): {result}")
            elif result is not None:
                yfinance_prices[stock_id] = result
            else:
                # Confirmed no price data - remove from Redis
                logger.warning(f"No price data from YFinance for stock_id {stock_id} ({symbol})")
                no_price_stock_ids.append(stock_id)

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

    # Step 5: Remove stocks with confirmed no price data from Redis
    if no_price_stock_ids:
        remove_tasks = [redis_client.delete_stock_info(stock_id) for stock_id in no_price_stock_ids]
        remove_results = await asyncio.gather(*remove_tasks, return_exceptions=True)

        removed_count = 0
        for stock_id, res in zip(no_price_stock_ids, remove_results):
            if isinstance(res, Exception):
                logger.warning(f"Failed to delete stock_id {stock_id} from Redis: {res}")
            else:
                removed_count += 1

        logger.info(f"Removed {removed_count}/{len(no_price_stock_ids)} stocks with no price data from Redis")
    else:
        logger.debug("No stocks to remove from Redis")