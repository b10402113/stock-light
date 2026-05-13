"""Integration tests for prepare_subscription_data ARQ job with real yfinance API.

Tests verify:
1. Real yfinance API historical price fetching (100 days)
2. Redis active stock set population
3. Current price fetching and storage
4. Database insertion of historical prices
5. Error handling for invalid stock symbols
"""

import asyncio
import datetime
import time
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.redis_client import StockRedisClient
from src.clients.yfinance_client import YFinanceClient
from src.stocks.model import Stock, DailyPrice
from src.stocks.schema import StockSource, StockMarket, DailyPriceBase
from src.stocks.service import DailyPriceService
from src.tasks.jobs.subscription_jobs import prepare_subscription_data


@pytest_asyncio.fixture(scope="function")
async def redis_client_clean(redis_container):
    """Create Redis client for testing with clean state."""
    redis_url = f"redis://{redis_container.get_container_host_ip()}:{redis_container.get_exposed_port(6379)}"
    client = StockRedisClient(redis_url=redis_url)
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
async def test_yfinance_stock(db_session: AsyncSession) -> Stock:
    """Create a test stock with YFINANCE source for testing."""
    stock = Stock(
        symbol="AAPL",
        name="Apple Inc.",
        is_active=True,
        source=StockSource.YFINANCE,
        market=StockMarket.US,
    )
    db_session.add(stock)
    await db_session.commit()
    await db_session.refresh(stock)
    return stock


@pytest_asyncio.fixture(scope="function")
async def test_yfinance_stock_2(db_session: AsyncSession) -> Stock:
    """Create a second test stock with YFINANCE source."""
    stock = Stock(
        symbol="MSFT",
        name="Microsoft Corporation",
        is_active=True,
        source=StockSource.YFINANCE,
        market=StockMarket.US,
    )
    db_session.add(stock)
    await db_session.commit()
    await db_session.refresh(stock)
    return stock


@pytest_asyncio.fixture(scope="function")
async def test_invalid_stock(db_session: AsyncSession) -> Stock:
    """Create a test stock with invalid symbol for error testing."""
    stock = Stock(
        symbol="INVALID123XYZ",
        name="Invalid Stock",
        is_active=True,
        source=StockSource.YFINANCE,
        market=StockMarket.US,
    )
    db_session.add(stock)
    await db_session.commit()
    await db_session.refresh(stock)
    return stock


@pytest.mark.asyncio
class TestRealYFinanceAPICalls:
    """Test real yfinance API calls."""

    async def test_get_current_price_real_api(self):
        """Test fetching real current price from yfinance API.

        This test calls the actual yfinance API for AAPL (Apple).
        """
        yfinance_client = YFinanceClient()

        # Fetch real current price for AAPL
        price = await yfinance_client.get_current_price("AAPL")

        # Verify response
        assert price is not None
        assert price > 0

        print(f"✓ Successfully fetched current price for AAPL: ${price:.2f}")

    async def test_get_historical_prices_real_api(self):
        """Test fetching real historical prices from yfinance API.

        Fetches 100 days of historical prices for AAPL.
        """
        yfinance_client = YFinanceClient()

        # Calculate date range for ~100 trading days (140 calendar days)
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=140)

        # Fetch historical prices
        prices = await yfinance_client.get_historical_prices(
            "AAPL",
            start_date.isoformat(),
            end_date.isoformat(),
        )

        # Verify response
        assert len(prices) > 0
        # Should have approximately 100 trading days (weekends/holidays excluded)
        assert len(prices) >= 80, f"Expected ~100 prices, got {len(prices)}"

        # Verify price structure
        first_price = prices[0]
        assert "date" in first_price
        assert "open" in first_price
        assert "high" in first_price
        assert "low" in first_price
        assert "close" in first_price
        assert "volume" in first_price

        # Verify OHLCV consistency
        assert first_price["high"] >= first_price["low"]
        assert first_price["high"] >= first_price["open"]
        assert first_price["high"] >= first_price["close"]
        assert first_price["low"] <= first_price["open"]
        assert first_price["low"] <= first_price["close"]

        print(f"✓ Successfully fetched {len(prices)} historical prices for AAPL")
        print(f"  First: {first_price['date']} - O:{first_price['open']} H:{first_price['high']} L:{first_price['low']} C:{first_price['close']}")

    async def test_batch_fetch_multiple_stocks_real_api(self):
        """Test fetching prices for multiple stocks concurrently.

        Measures execution time to verify concurrent API calls are efficient.
        """
        yfinance_client = YFinanceClient()

        # Select 5 well-known US stocks
        test_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

        start_time = time.time()

        # Fetch current prices concurrently
        tasks = [yfinance_client.get_current_price(symbol) for symbol in test_symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        elapsed = time.time() - start_time

        # Verify results
        success_count = 0
        for symbol, result in zip(test_symbols, results):
            if isinstance(result, Exception):
                print(f"  ✗ Failed for {symbol}: {result}")
            elif result is None:
                print(f"  ✗ No price for {symbol}")
            else:
                success_count += 1
                print(f"  ✓ {symbol}: ${result:.2f}")

        # Should have at least 80% success rate
        assert success_count >= 4, f"Only {success_count}/5 stocks fetched successfully"

        # Concurrent calls should complete in reasonable time
        # yfinance uses threadpool, so concurrent calls still have some overhead
        assert elapsed < 30.0, f"Concurrent calls took {elapsed}s (expected < 30s)"

        print(f"✓ Successfully fetched {success_count}/5 stocks in {elapsed:.2f}s")


@pytest.mark.asyncio
class TestPrepareSubscriptionDataJob:
    """Test prepare_subscription_data ARQ job execution."""

    async def test_prepare_data_full_workflow(
        self,
        redis_client_clean: StockRedisClient,
        test_yfinance_stock: Stock,
        db_session: AsyncSession,
    ):
        """Test full workflow of prepare_subscription_data job.

        Verifies:
        - Stock added to Redis active set
        - Current price fetched and stored in Redis
        - Historical prices (100 days) fetched and stored in database
        """
        from contextlib import asynccontextmanager

        # Create ARQ context
        redis_pool = await redis_client_clean._get_client()
        ctx = {"redis": redis_pool}

        # Create async context manager that yields test session
        @asynccontextmanager
        async def test_session_factory():
            yield db_session

        with patch('src.tasks.jobs.subscription_jobs.SessionFactory', test_session_factory):
            # Execute job
            result = await prepare_subscription_data(ctx, test_yfinance_stock.id)

        # Verify job result
        assert result["stock_id"] == test_yfinance_stock.id
        assert result["success"] is True
        assert result["added_to_redis"] is True
        assert result["current_price_fetched"] is True
        assert result["historical_prices_count"] > 0
        assert result["error"] is None

        # Verify stock in Redis active set
        active_stocks = await redis_client_clean.get_active_stocks()
        assert test_yfinance_stock.id in active_stocks

        # Verify current price in Redis
        stock_info = await redis_client_clean.get_stock_info(test_yfinance_stock.id)
        assert stock_info is not None
        assert stock_info.get("price") is not None
        assert float(stock_info["price"]) > 0

        # Verify historical prices in database
        stmt = select(DailyPrice).where(DailyPrice.stock_id == test_yfinance_stock.id)
        db_result = await db_session.execute(stmt)
        prices = list(db_result.scalars().all())

        assert len(prices) >= 80, f"Expected ~100 prices, got {len(prices)}"

        # Verify price data structure
        for price in prices[:5]:
            assert price.open > 0
            assert price.high >= price.low
            assert price.high >= price.open
            assert price.high >= price.close
            assert price.low <= price.open
            assert price.low <= price.close

        print(f"✓ Job completed successfully for stock_id={test_yfinance_stock.id}")
        print(f"  Redis active: {test_yfinance_stock.id in active_stocks}")
        print(f"  Current price: ${stock_info['price']}")
        print(f"  Historical prices: {len(prices)} records")

    async def test_prepare_data_multiple_stocks(
        self,
        redis_client_clean: StockRedisClient,
        test_yfinance_stock: Stock,
        test_yfinance_stock_2: Stock,
        db_session: AsyncSession,
    ):
        """Test preparing data for multiple stocks sequentially.

        Verifies job handles multiple stocks independently.
        Note: In production, ARQ worker manages concurrent jobs with separate sessions.
        """
        from contextlib import asynccontextmanager

        redis_pool = await redis_client_clean._get_client()
        ctx = {"redis": redis_pool}

        # Create async context manager that yields test session
        @asynccontextmanager
        async def test_session_factory():
            yield db_session

        with patch('src.tasks.jobs.subscription_jobs.SessionFactory', test_session_factory):
            # Execute jobs sequentially (concurrent would require separate sessions)
            result1 = await prepare_subscription_data(ctx, test_yfinance_stock.id)
            result2 = await prepare_subscription_data(ctx, test_yfinance_stock_2.id)
            results = [result1, result2]

        # Verify both jobs succeeded
        for result in results:
            assert result["success"] is True
            assert result["historical_prices_count"] > 0

        # Verify both stocks in Redis active set
        active_stocks = await redis_client_clean.get_active_stocks()
        assert test_yfinance_stock.id in active_stocks
        assert test_yfinance_stock_2.id in active_stocks

        # Verify both stocks have prices in database
        for stock in [test_yfinance_stock, test_yfinance_stock_2]:
            stmt = select(DailyPrice).where(DailyPrice.stock_id == stock.id)
            db_result = await db_session.execute(stmt)
            prices = list(db_result.scalars().all())
            assert len(prices) >= 80

        print(f"✓ Prepared data for 2 stocks successfully")
        print(f"  {test_yfinance_stock.symbol}: {results[0]['historical_prices_count']} prices")
        print(f"  {test_yfinance_stock_2.symbol}: {results[1]['historical_prices_count']} prices")


@pytest.mark.asyncio
class TestErrorHandling:
    """Test error handling in prepare_subscription_data job."""

    async def test_invalid_stock_symbol(
        self,
        redis_client_clean: StockRedisClient,
        test_invalid_stock: Stock,
        db_session: AsyncSession,
    ):
        """Test job handles invalid stock symbols gracefully.

        Verifies:
        - Job still succeeds (graceful error handling)
        - Stock added to Redis active set (for monitoring)
        - Current price fetch fails (logs warning)
        - No historical prices inserted
        """
        from contextlib import asynccontextmanager

        redis_pool = await redis_client_clean._get_client()
        ctx = {"redis": redis_pool}

        # Create async context manager that yields test session
        @asynccontextmanager
        async def test_session_factory():
            yield db_session

        with patch('src.tasks.jobs.subscription_jobs.SessionFactory', test_session_factory):
            # Execute job with invalid stock
            result = await prepare_subscription_data(ctx, test_invalid_stock.id)

        # Job should complete successfully (graceful error handling)
        assert result["stock_id"] == test_invalid_stock.id
        assert result["success"] is True
        assert result["added_to_redis"] is True
        # Price fetch should fail for invalid symbol
        assert result["current_price_fetched"] is False
        # No historical prices for invalid symbol
        assert result["historical_prices_count"] == 0

        # Stock should still be added to Redis active set (for monitoring)
        active_stocks = await redis_client_clean.get_active_stocks()
        assert test_invalid_stock.id in active_stocks

        # No historical prices should be inserted
        stmt = select(DailyPrice).where(DailyPrice.stock_id == test_invalid_stock.id)
        db_result = await db_session.execute(stmt)
        prices = list(db_result.scalars().all())
        assert len(prices) == 0

        print(f"✓ Job handled invalid symbol gracefully")
        print(f"  Added to Redis: {test_invalid_stock.id in active_stocks}")
        print(f"  Price fetch failed: {result['current_price_fetched'] is False}")
        print(f"  No historical prices: {result['historical_prices_count']}")

    async def test_stock_not_in_database(
        self,
        redis_client_clean: StockRedisClient,
        db_session: AsyncSession,
    ):
        """Test job handles non-existent stock_id gracefully.

        Verifies job returns error for invalid stock_id.
        """
        from contextlib import asynccontextmanager

        redis_pool = await redis_client_clean._get_client()
        ctx = {"redis": redis_pool}

        # Create async context manager that yields test session
        @asynccontextmanager
        async def test_session_factory():
            yield db_session

        with patch('src.tasks.jobs.subscription_jobs.SessionFactory', test_session_factory):
            # Execute job with non-existent stock_id
            result = await prepare_subscription_data(ctx, 999999)

        # Job should fail gracefully
        assert result["stock_id"] == 999999
        assert result["success"] is False
        assert result["error"] is not None
        assert "not found" in result["error"].lower()

        print(f"✓ Job handled non-existent stock_id gracefully")
        print(f"  Error: {result['error']}")


@pytest.mark.asyncio
class TestRedisIntegration:
    """Test Redis integration for subscription data preparation."""

    async def test_redis_active_set_population(
        self,
        redis_client_clean: StockRedisClient,
        test_yfinance_stock: Stock,
    ):
        """Test adding stock to Redis active set.

        Verifies SADD operation and retrieval.
        """
        # Add stock to active set
        added = await redis_client_clean.add_active_stock(test_yfinance_stock.id)
        assert added is True

        # Verify stock is in active set
        active_stocks = await redis_client_clean.get_active_stocks()
        assert test_yfinance_stock.id in active_stocks

        print(f"✓ Stock {test_yfinance_stock.id} added to Redis active set")

    async def test_redis_price_storage(
        self,
        redis_client_clean: StockRedisClient,
        test_yfinance_stock: Stock,
    ):
        """Test storing current price in Redis.

        Verifies HSET operation and retrieval.
        """
        # Fetch real price from yfinance
        yfinance_client = YFinanceClient()
        price = await yfinance_client.get_current_price(test_yfinance_stock.symbol)

        assert price is not None

        # Store price in Redis
        await redis_client_clean.set_stock_price(
            test_yfinance_stock.id,
            test_yfinance_stock.symbol,
            price,
            StockSource.YFINANCE,
        )

        # Verify price stored correctly
        stock_info = await redis_client_clean.get_stock_info(test_yfinance_stock.id)
        assert stock_info is not None
        assert stock_info["symbol"] == test_yfinance_stock.symbol
        assert float(stock_info["price"]) == price
        # Source is stored as integer in Redis
        assert stock_info["source"] == StockSource.YFINANCE.value
        assert stock_info.get("updated_at") is not None

        print(f"✓ Price ${price:.2f} stored in Redis for {test_yfinance_stock.symbol}")


@pytest.mark.asyncio
class TestDatabaseIntegration:
    """Test database integration for historical prices."""

    async def test_bulk_insert_prices(
        self,
        db_session: AsyncSession,
        test_yfinance_stock: Stock,
    ):
        """Test bulk inserting historical prices to database.

        Verifies upsert behavior and data integrity.
        """
        # Fetch real historical prices from yfinance
        yfinance_client = YFinanceClient()
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=140)

        prices_data = await yfinance_client.get_historical_prices(
            test_yfinance_stock.symbol,
            start_date.isoformat(),
            end_date.isoformat(),
        )

        assert len(prices_data) > 0

        # Convert to DailyPriceBase schema
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

        # Bulk insert prices
        count = await DailyPriceService.bulk_insert_prices(
            db_session, test_yfinance_stock.id, prices
        )

        assert count > 0
        assert count == len(prices)

        # Verify prices in database
        stmt = select(DailyPrice).where(DailyPrice.stock_id == test_yfinance_stock.id)
        result = await db_session.execute(stmt)
        db_prices = list(result.scalars().all())

        assert len(db_prices) == len(prices)

        # Verify data integrity
        for db_price in db_prices[:5]:
            assert db_price.stock_id == test_yfinance_stock.id
            assert db_price.open > 0
            assert db_price.high >= db_price.low

        print(f"✓ Inserted {count} historical prices to database")

    async def test_upsert_duplicate_prices(
        self,
        db_session: AsyncSession,
        test_yfinance_stock: Stock,
    ):
        """Test that inserting duplicate prices updates existing records.

        Verifies ON CONFLICT DO UPDATE behavior.
        """
        # Create initial price record
        initial_price = DailyPriceBase(
            date=datetime.date.today() - datetime.timedelta(days=1),
            open=Decimal("100.00"),
            high=Decimal("105.00"),
            low=Decimal("99.00"),
            close=Decimal("102.00"),
            volume=1000000,
        )

        count1 = await DailyPriceService.bulk_insert_prices(
            db_session, test_yfinance_stock.id, [initial_price]
        )
        assert count1 == 1

        # Insert same date with different values
        updated_price = DailyPriceBase(
            date=initial_price.date,
            open=Decimal("110.00"),  # Different open
            high=Decimal("115.00"),
            low=Decimal("109.00"),
            close=Decimal("112.00"),
            volume=2000000,
        )

        count2 = await DailyPriceService.bulk_insert_prices(
            db_session, test_yfinance_stock.id, [updated_price]
        )
        assert count2 == 1  # Should update, not insert new

        # Verify price was updated
        stmt = select(DailyPrice).where(
            DailyPrice.stock_id == test_yfinance_stock.id,
            DailyPrice.date == initial_price.date,
        )
        result = await db_session.execute(stmt)
        db_price = result.scalar_one()

        assert db_price.open == Decimal("110.00")
        assert db_price.close == Decimal("112.00")
        assert db_price.volume == 2000000

        print(f"✓ Upsert correctly updated duplicate price")