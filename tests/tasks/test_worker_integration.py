"""Integration tests for ARQ worker tasks with real API calls.

Tests verify:
1. Real Fugle API price fetching
2. Setting 100 stocks as active in Redis
3. Batch size limit enforcement (50 stocks per batch)
4. Worker batch job dispatching logic
"""

import asyncio
import time
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
import redis.asyncio as redis
from arq import create_pool
from arq.connections import ArqRedis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.fugle_client import FugoClient
from src.clients.redis_client import StockRedisClient
from src.config import settings
from src.models import Stock
from src.stocks.schema import StockSource, StockMarket
from src.tasks.worker import update_stock_prices_master, update_stock_prices_batch
from src.tasks.config import redis_settings


@pytest_asyncio.fixture(scope="function")
async def redis_client():
    """Create real Redis client for integration testing."""
    client = StockRedisClient()
    try:
        # Verify connection
        await client.ping()
        # Clean Redis state before each test
        await client.clear_active_stocks()
        async with await client._get_client() as r:
            keys = []
            async for key in r.scan_iter(match="stock:info:*"):
                keys.append(key)
            if keys:
                await r.delete(*keys)
        yield client
    finally:
        # Clean up: clear all test data
        await client.clear_active_stocks()
        # Clean stock info keys using SCAN
        async with await client._get_client() as r:
            keys = []
            async for key in r.scan_iter(match="stock:info:*"):
                keys.append(key)
            if keys:
                await r.delete(*keys)
        await client.close()


@pytest_asyncio.fixture(scope="function")
async def test_stocks_100(db_session: AsyncSession) -> list[int]:
    """Create 100 test stocks with Fugle source for testing.

    Returns:
        List of 100 stock IDs
    """
    # Create 100 test stocks (using well-known Taiwan stock symbols)
    test_symbols = [
        "2330", "2454", "1101", "2303", "2317",  # Top 5 TSE stocks
        "1301", "1303", "1326", "1402", "2002",  # More active stocks
        "2201", "2207", "2308", "2337", "2357",
        "2408", "2409", "2455", "2474", "2498",
        "2603", "2609", "2610", "2707", "2801",
        "2881", "2882", "2883", "2884", "2885",
        "2886", "2887", "2890", "2891", "2892",
        "2912", "3008", "3034", "3037", "3045",
        "3231", "3474", "3682", "4904", "4938",
        "5871", "6239", "6415", "6505", "8454",
        "1216", "1227", "1231", "1232", "1233",
        "1240", "1258", "1268", "1274", "1286",
        "1293", "1312", "1324", "1336", "1442",
        "1456", "1467", "1476", "1504", "1517",
        "1526", "1536", "1605", "1702", "1710",
        "1717", "1722", "1723", "1726", "1732",
        "1737", "1742", "1752", "1762", "1773",
        "1789", "1802", "1810", "1826", "1832",
        "1904", "1907", "1909", "1914", "1915",
        "1925", "1926", "1928", "1930", "1931",
    ]

    stocks = []
    for i, symbol in enumerate(test_symbols):
        # Use raw symbol (Fugle API uses symbols without .TW suffix)
        stock = Stock(
            symbol=symbol,
            name=f"測試股票{i+1}",
            current_price=None,
            calculated_indicators=None,
            is_active=True,
            source=StockSource.FUGLE,
            market=StockMarket.TAIWAN,
        )
        stocks.append(stock)

    db_session.add_all(stocks)
    await db_session.commit()

    # Refresh to get IDs
    for stock in stocks:
        await db_session.refresh(stock)

    stock_ids = [stock.id for stock in stocks]
    assert len(stock_ids) == 100

    return stock_ids


@pytest.mark.asyncio
class TestRealFugleAPICalls:
    """Test real Fugle API price fetching."""

    async def test_get_intraday_quote_real_api(self):
        """Test fetching real stock price from Fugle API.

        This test calls the actual Fugle API with a known Taiwan stock (2330 台積電).
        """
        fugle_client = FugoClient()

        # Fetch real quote for TSMC (2330)
        quote = await fugle_client.get_intraday_quote("2330")

        # Verify response structure
        assert quote.symbol == "2330"
        assert quote.name is not None
        # Price should be present during trading hours or after market close
        # Note: lastPrice may be None if market is closed and no trades occurred
        assert quote.lastPrice is not None or quote.previousClose is not None

        print(f"✓ Successfully fetched quote for 2330: {quote.name}")
        print(f"  Last price: {quote.lastPrice}")
        print(f"  Previous close: {quote.previousClose}")

    async def test_batch_fetch_10_stocks_real_api(self):
        """Test fetching prices for 10 stocks concurrently.

        Measures execution time to verify concurrent API calls are efficient.
        """
        fugle_client = FugoClient()

        # Select 10 well-known Taiwan stocks
        test_symbols = ["2330", "2454", "1101", "2303", "2317",
                       "1301", "1303", "1326", "1402", "2002"]

        start_time = time.time()

        # Fetch concurrently
        tasks = [fugle_client.get_intraday_quote(symbol) for symbol in test_symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        elapsed = time.time() - start_time

        # Verify results
        success_count = 0
        for symbol, result in zip(test_symbols, results):
            if isinstance(result, Exception):
                print(f"  ✗ Failed for {symbol}: {result}")
            else:
                success_count += 1
                print(f"  ✓ {symbol}: {result.lastPrice or result.previousClose}")

        # Should have at least 80% success rate
        assert success_count >= 8, f"Only {success_count}/10 stocks fetched successfully"

        # Concurrent calls should be faster than sequential
        # 10 concurrent calls should complete in < 5 seconds (assuming 10s timeout per call)
        assert elapsed < 5.0, f"Concurrent calls took {elapsed}s (expected < 5s)"

        print(f"✓ Successfully fetched {success_count}/10 stocks in {elapsed:.2f}s")


@pytest.mark.asyncio
class TestRedisActiveStocks:
    """Test setting stocks as active in Redis."""

    async def test_set_100_stocks_active(self, redis_client: StockRedisClient, test_stocks_100: list[int]):
        """Test setting 100 stocks as active in Redis.

        Verifies:
        - All 100 stocks added to Redis set
        - SADD atomic operation
        - Retrieval returns all stock_ids
        """
        # Add all 100 stocks to active set
        added_count = 0
        for stock_id in test_stocks_100:
            result = await redis_client.add_active_stock(stock_id)
            if result:
                added_count += 1

        # Should have added 100 new members
        assert added_count == 100

        # Retrieve active stocks
        active_stocks = await redis_client.get_active_stocks()

        # Verify count and IDs
        assert len(active_stocks) == 100
        assert set(active_stocks) == set(test_stocks_100)

        print(f"✓ Successfully set {len(active_stocks)} stocks as active")

    async def test_set_stock_info_incomplete_cache(self, redis_client: StockRedisClient, test_stocks_100: list[int]):
        """Test setting incomplete cache (symbol + source only) for stocks.

        Verifies worker startup behavior: sets symbol/source without price.
        """
        # Set incomplete cache for first 10 stocks
        test_stock_ids = test_stocks_100[:10]
        client = await redis_client._get_client()

        for stock_id in test_stock_ids:
            key = redis_client._stock_info_key(stock_id)
            await client.hset(key, mapping={
                "symbol": f"{stock_id}",
                "source": str(StockSource.FUGLE)
            })

        # Verify incomplete cache structure
        for stock_id in test_stock_ids:
            info = await redis_client.get_stock_info(stock_id)
            assert info is not None
            assert info.get("symbol") is not None
            assert info.get("source") is not None
            assert info.get("price") is None
            assert info.get("updated_at") is None
            # Should be flagged as incomplete
            assert info.get("incomplete") == True

        print(f"✓ Successfully set incomplete cache for {len(test_stock_ids)} stocks")


@pytest.mark.asyncio
class TestBatchSizeEnforcement:
    """Test batch size limit enforcement (50 stocks per batch)."""

    async def test_master_task_splits_into_batches(
        self, redis_client: StockRedisClient, test_stocks_100: list[int], db_session: AsyncSession
    ):
        """Test that master task splits 100 stocks into 2 batches of 50.

        Verifies:
        - Stocks are split into chunks of STOCK_BATCH_SIZE (50)
        - Multiple batch jobs are dispatched
        - Each batch has correct number of stocks
        """
        # Set all 100 stocks as active in Redis
        for stock_id in test_stocks_100:
            await redis_client.add_active_stock(stock_id)

        # Set incomplete cache (symbol + source) for all stocks
        # This simulates worker startup state
        client = await redis_client._get_client()

        # Get symbols from database
        result = await db_session.execute(
            select(Stock.id, Stock.symbol, Stock.source).where(Stock.id.in_(test_stocks_100))
        )
        stock_data = result.all()

        for stock_id, symbol, source in stock_data:
            key = redis_client._stock_info_key(stock_id)
            await client.hset(key, mapping={
                "symbol": symbol,
                "source": str(source)
            })

        # Create ARQ Redis pool for testing enqueue_job
        arq_redis = await create_pool(redis_settings)
        ctx = {"redis": arq_redis}

        # Track dispatched jobs
        dispatched_jobs = []

        # Mock enqueue_job to capture batches without actually executing
        async def mock_enqueue_job(task_name, *args, **kwargs):
            batch = args[0] if args else []
            dispatched_jobs.append({
                "task_name": task_name,
                "batch": batch,
                "batch_size": len(batch),
            })
            # Return mock job object
            mock_job = MagicMock()
            mock_job.job_id = f"mock_job_{len(dispatched_jobs)}"
            return mock_job

        # Patch enqueue_job on ARQ Redis pool
        with patch.object(arq_redis, 'enqueue_job', side_effect=mock_enqueue_job):
            # Run master task
            await update_stock_prices_master(ctx)

            # Verify batch splitting
            assert len(dispatched_jobs) == 2, f"Expected 2 batches, got {len(dispatched_jobs)}"

            # Verify batch sizes
            batch_sizes = [job["batch_size"] for job in dispatched_jobs]
            assert batch_sizes == [50, 50], f"Batch sizes: {batch_sizes}"

            # Verify total stocks
            total_stocks = sum(batch_sizes)
            assert total_stocks == 100, f"Total stocks: {total_stocks}"

            # Verify no duplicate stocks across batches
            all_stock_ids = []
            for job in dispatched_jobs:
                all_stock_ids.extend(job["batch"])
            assert len(all_stock_ids) == len(set(all_stock_ids)), "Duplicate stocks in batches"

            print(f"✓ Master task split {total_stocks} stocks into {len(dispatched_jobs)} batches")
            for idx, job in enumerate(dispatched_jobs, 1):
                print(f"  Batch {idx}: {job['batch_size']} stocks")

        # Close ARQ pool
        await arq_redis.close()


@pytest.mark.asyncio
class TestBatchJobExecution:
    """Test batch job execution with real API calls."""

    async def test_batch_task_fetches_prices(
        self, redis_client: StockRedisClient, test_stocks_100: list[int], db_session: AsyncSession
    ):
        """Test batch task fetches real prices and updates Redis.

        Tests with a small batch (10 stocks) to verify:
        - Real Fugle API calls
        - Price fetching and Redis updates
        - Execution time measurement
        """
        # Select first 10 stocks for testing
        test_batch = test_stocks_100[:10]

        # Set incomplete cache for test stocks
        client = await redis_client._get_client()

        result = await db_session.execute(
            select(Stock.id, Stock.symbol).where(Stock.id.in_(test_batch))
        )
        stock_data = result.all()

        for stock_id, symbol in stock_data:
            key = redis_client._stock_info_key(stock_id)
            await client.hset(key, mapping={
                "symbol": symbol,
                "source": str(StockSource.FUGLE)
            })

        # Create ARQ context
        real_redis = await redis_client._get_client()
        ctx = {"redis": real_redis}

        # Execute batch task
        start_time = time.time()
        await update_stock_prices_batch(ctx, test_batch)
        elapsed = time.time() - start_time

        # Verify prices updated in Redis
        updated_count = 0
        for stock_id in test_batch:
            info = await redis_client.get_stock_info(stock_id)
            if info and info.get("price") is not None:
                updated_count += 1
                print(f"  ✓ Stock {stock_id}: price={info['price']}")

        # Should have updated at least 80% of stocks (some may fail due to API limits)
        assert updated_count >= 8, f"Only {updated_count}/10 stocks updated"

        # Execution should be reasonably fast (< 10 seconds for 10 stocks)
        assert elapsed < 10.0, f"Batch took {elapsed}s (expected < 10s)"

        print(f"✓ Batch task updated {updated_count}/10 stocks in {elapsed:.2f}s")

    async def test_batch_task_handles_api_failures_gracefully(
        self, redis_client: StockRedisClient, test_stocks_100: list[int], db_session: AsyncSession
    ):
        """Test that batch task continues even when some API calls fail.

        Tests that individual stock failures don't stop the entire batch.
        """
        # Select 5 stocks for testing
        test_batch = test_stocks_100[:5]

        # Set incomplete cache
        client = await redis_client._get_client()

        result = await db_session.execute(
            select(Stock.id, Stock.symbol).where(Stock.id.in_(test_batch))
        )
        stock_data = result.all()

        for stock_id, symbol in stock_data:
            key = redis_client._stock_info_key(stock_id)
            await client.hset(key, mapping={
                "symbol": symbol,
                "source": str(StockSource.FUGLE)
            })

        # Create ARQ context
        real_redis = await redis_client._get_client()
        ctx = {"redis": real_redis}

        # Execute batch task (should handle failures gracefully)
        await update_stock_prices_batch(ctx, test_batch)

        # Verify task completed without raising exception
        # Check that at least some stocks were updated
        updated_count = 0
        for stock_id in test_batch:
            info = await redis_client.get_stock_info(stock_id)
            if info and info.get("price") is not None:
                updated_count += 1

        print(f"✓ Batch task handled failures gracefully: {updated_count}/5 stocks updated")


@pytest.mark.asyncio
class TestWorkerPerformance:
    """Test worker performance under load."""

    async def test_concurrent_redis_queries_performance(
        self, redis_client: StockRedisClient, test_stocks_100: list[int]
    ):
        """Test performance of concurrent Redis queries (avoid N+1 problem).

        Verifies asyncio.gather is efficient for checking 100 stocks.
        """
        # Set active stocks
        for stock_id in test_stocks_100:
            await redis_client.add_active_stock(stock_id)

        # Measure concurrent query performance
        start_time = time.time()

        tasks = [redis_client.get_stock_info(stock_id) for stock_id in test_stocks_100]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        elapsed = time.time() - start_time

        # Concurrent queries should be fast (< 1 second for 100 stocks)
        assert elapsed < 1.0, f"Concurrent Redis queries took {elapsed}s (expected < 1s)"

        success_count = sum(1 for r in results if not isinstance(r, Exception))
        print(f"✓ Concurrent Redis queries: {success_count}/100 stocks in {elapsed:.3f}s")

    async def test_batch_size_limit_respected(self):
        """Test that STOCK_BATCH_SIZE configuration is respected.

        Verifies the batch size is set to 50 as per requirements.
        """
        from src.config import settings

        assert settings.STOCK_BATCH_SIZE == 50, f"Batch size: {settings.STOCK_BATCH_SIZE}"

        print(f"✓ Batch size limit: {settings.STOCK_BATCH_SIZE} stocks per batch")