"""Tests for subscription indicator flow with Redis and ARQ integration.

Tests the complete user subscription flow:
1. API layer: subscription creation triggers Redis operations
2. Service layer: SubscriptionService handles Redis active set
3. ARQ Job layer: prepare_subscription_data executes correctly (mocked)
4. ARQ Job layer: update_indicator executes correctly (mocked)
5. Redis integration: active stocks, price cache, indicator data
"""

import pytest
import pytest_asyncio
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.redis_client import StockRedisClient
from src.stock_indicator.service import StockIndicatorService
from src.stocks.model import DailyPrice, Stock
from src.stocks.schema import StockSource, StockMarket
from src.subscriptions.model import IndicatorSubscription
from src.subscriptions.schema import IndicatorSubscriptionCreate, ConditionGroup, Condition
from src.subscriptions.service import SubscriptionService


class TestSubscriptionRedisIntegration:
    """Tests for Redis integration in subscription flow."""

    @pytest_asyncio.fixture
    async def seeded_stock_with_prices(self, db_session: AsyncSession) -> Stock:
        """Create a seeded stock with 100 days of historical prices."""
        stock = Stock(
            symbol="2330.TW",
            name="台積電",
            is_active=True,
            source=StockSource.FUGLE,
            market=StockMarket.TAIWAN,
        )
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        # Create 100 days of historical prices
        prices = []
        base_price = Decimal("500.00")
        for i in range(100):
            day = date.today() - timedelta(days=100 - i)
            price_offset = Decimal(str(i * 0.5))
            prices.append(
                DailyPrice(
                    stock_id=stock.id,
                    date=day,
                    open=base_price + price_offset,
                    high=base_price + price_offset + Decimal("5"),
                    low=base_price + price_offset - Decimal("5"),
                    close=base_price + price_offset + Decimal("2"),
                    volume=1000000 + i * 1000,
                )
            )

        for price in prices:
            db_session.add(price)
        await db_session.commit()

        return stock

    @pytest_asyncio.fixture
    async def seeded_inactive_stock(self, db_session: AsyncSession) -> Stock:
        """Create an inactive stock for testing activation."""
        stock = Stock(
            symbol="2330.TW",
            name="台積電",
            is_active=False,
            source=StockSource.FUGLE,
            market=StockMarket.TAIWAN,
        )
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)
        return stock

    @pytest.mark.asyncio
    async def test_subscription_activates_inactive_stock_and_adds_to_redis(
        self,
        db_session: AsyncSession,
        seeded_user,
        seeded_inactive_stock: Stock,
        redis_client: StockRedisClient,
    ):
        """Test that subscribing to inactive stock activates it and adds to Redis."""
        # Given: stock is inactive and not in Redis
        assert seeded_inactive_stock.is_active is False
        active_stocks = await redis_client.get_active_stocks()
        assert seeded_inactive_stock.id not in active_stocks

        # When: create subscription
        subscription_data = IndicatorSubscriptionCreate(
            stock_id=seeded_inactive_stock.id,
            title="RSI Buy Signal",
            message="2330 RSI below 30",
            signal_type="buy",
            condition_group=ConditionGroup(
                logic="and",
                conditions=[
                    Condition(
                        indicator_type="rsi",
                        operator="<",
                        target_value="30.0",
                        timeframe="D",
                        period=14,
                    )
                ],
            ),
        )

        subscription = await SubscriptionService.create(
            db_session,
            seeded_user.id,
            subscription_data,
            redis_client,
        )

        # Then: stock should be activated
        await db_session.refresh(seeded_inactive_stock)
        assert seeded_inactive_stock.is_active is True

        # And: stock should be in Redis active set
        active_stocks = await redis_client.get_active_stocks()
        assert seeded_inactive_stock.id in active_stocks

        # Cleanup
        await redis_client.remove_active_stock(seeded_inactive_stock.id)

    @pytest.mark.asyncio
    async def test_subscription_with_active_stock_does_not_add_to_redis(
        self,
        db_session: AsyncSession,
        seeded_user,
        seeded_stock_with_prices: Stock,
        redis_client: StockRedisClient,
    ):
        """Test that subscribing to already active stock does NOT add to Redis.

        Note: In current implementation, Redis is only updated when stock is inactive.
        """
        # Given: stock is active and not in Redis
        assert seeded_stock_with_prices.is_active is True
        await redis_client.clear_active_stocks()
        active_stocks = await redis_client.get_active_stocks()
        assert seeded_stock_with_prices.id not in active_stocks

        # When: create subscription
        subscription_data = IndicatorSubscriptionCreate(
            stock_id=seeded_stock_with_prices.id,
            title="RSI Buy Signal",
            message="2330 RSI below 30",
            signal_type="buy",
            condition_group=ConditionGroup(
                logic="and",
                conditions=[
                    Condition(
                        indicator_type="rsi",
                        operator="<",
                        target_value="30.0",
                        timeframe="D",
                        period=14,
                    )
                ],
            ),
        )

        subscription = await SubscriptionService.create(
            db_session,
            seeded_user.id,
            subscription_data,
            redis_client,
        )

        # Then: stock is NOT added to Redis (because it was already active)
        active_stocks = await redis_client.get_active_stocks()
        assert seeded_stock_with_prices.id not in active_stocks

    @pytest.mark.asyncio
    async def test_redis_price_cache_operations(
        self,
        redis_client: StockRedisClient,
    ):
        """Test Redis price cache set and get operations."""
        stock_id = 1
        symbol = "2330.TW"
        price = 550.5
        source = 1  # Fugle

        # When: set stock price
        await redis_client.set_stock_price(stock_id, symbol, price, source)

        # Then: can retrieve the price
        cached_price = await redis_client.get_stock_price(stock_id)
        assert cached_price == price

        # And: can retrieve full info
        info = await redis_client.get_stock_info(stock_id)
        assert info is not None
        assert info["symbol"] == symbol
        assert info["price"] == price
        assert info["source"] == source
        assert "updated_at" in info

        # Cleanup
        await redis_client.delete_stock_info(stock_id)

    @pytest.mark.asyncio
    async def test_redis_active_stocks_operations(
        self,
        redis_client: StockRedisClient,
    ):
        """Test Redis active stocks set operations."""
        stock_ids = [1, 2, 3]

        # When: add stocks to active set
        for stock_id in stock_ids:
            await redis_client.add_active_stock(stock_id)

        # Then: can retrieve all active stocks
        active_stocks = await redis_client.get_active_stocks()
        for stock_id in stock_ids:
            assert stock_id in active_stocks

        # When: remove a stock
        await redis_client.remove_active_stock(2)

        # Then: removed stock not in set
        active_stocks = await redis_client.get_active_stocks()
        assert 2 not in active_stocks
        assert 1 in active_stocks
        assert 3 in active_stocks

        # Cleanup
        await redis_client.clear_active_stocks()


class TestPrepareSubscriptionDataJobMocked:
    """Tests for prepare_subscription_data ARQ job with mocked dependencies."""

    @pytest_asyncio.fixture
    async def seeded_stock_for_job(self, db_session: AsyncSession) -> Stock:
        """Create a stock for job testing."""
        stock = Stock(
            symbol="2330.TW",
            name="台積電",
            is_active=True,
            source=StockSource.YFINANCE,
            market=StockMarket.TAIWAN,
        )
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)
        return stock

    @pytest.mark.asyncio
    async def test_prepare_subscription_data_job_adds_to_redis(
        self,
        seeded_stock_for_job: Stock,
        redis_client: StockRedisClient,
    ):
        """Test that prepare_subscription_data job adds stock to Redis."""
        # Mock the database session to return our test stock
        with patch("src.tasks.jobs.subscription_jobs.SessionFactory") as mock_session_factory:
            # Create mock session context manager
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_factory.return_value = mock_session

            # Mock StockService.get_by_id to return our stock
            with patch("src.tasks.jobs.subscription_jobs.StockService.get_by_id") as mock_get_stock:
                mock_get_stock.return_value = seeded_stock_for_job

                # Import and run the job
                from src.tasks.jobs.subscription_jobs import prepare_subscription_data

                ctx = {"redis": redis_client._client}

                result = await prepare_subscription_data(ctx, seeded_stock_for_job.id)

        # Then: stock should be added to Redis active set
        active_stocks = await redis_client.get_active_stocks()
        assert seeded_stock_for_job.id in active_stocks
        assert result["added_to_redis"] is True

        # Cleanup
        await redis_client.remove_active_stock(seeded_stock_for_job.id)
        await redis_client.delete_stock_info(seeded_stock_for_job.id)

    @pytest.mark.asyncio
    async def test_prepare_subscription_data_job_returns_correct_structure(
        self,
        seeded_stock_for_job: Stock,
        redis_client: StockRedisClient,
    ):
        """Test that prepare_subscription_data returns correct result dict."""
        # Mock the database session
        with patch("src.tasks.jobs.subscription_jobs.SessionFactory") as mock_session_factory:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_factory.return_value = mock_session

            with patch("src.tasks.jobs.subscription_jobs.StockService.get_by_id") as mock_get_stock:
                mock_get_stock.return_value = seeded_stock_for_job

                from src.tasks.jobs.subscription_jobs import prepare_subscription_data

                ctx = {"redis": redis_client._client}

                result = await prepare_subscription_data(ctx, seeded_stock_for_job.id)

        # Then: result should have expected structure
        assert "stock_id" in result
        assert "added_to_redis" in result
        assert "current_price_fetched" in result
        assert "historical_prices_count" in result
        assert "success" in result
        assert "error" in result

        assert result["stock_id"] == seeded_stock_for_job.id

        # Cleanup
        await redis_client.remove_active_stock(seeded_stock_for_job.id)


class TestUpdateIndicatorJobMocked:
    """Tests for update_indicator ARQ job with mocked dependencies."""

    @pytest_asyncio.fixture
    async def seeded_subscription_with_prices(
        self,
        db_session: AsyncSession,
        seeded_user,
    ) -> tuple[Stock, IndicatorSubscription]:
        """Create stock with prices and subscription for indicator testing."""
        # Create stock
        stock = Stock(
            symbol="2330.TW",
            name="台積電",
            is_active=True,
            source=StockSource.YFINANCE,
            market=StockMarket.TAIWAN,
        )
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        # Create 50 days of historical prices (enough for RSI_14)
        prices = []
        base_price = Decimal("500.00")
        for i in range(50):
            day = date.today() - timedelta(days=50 - i)
            variation = Decimal(str(10 * (i % 10 - 5)))
            prices.append(
                DailyPrice(
                    stock_id=stock.id,
                    date=day,
                    open=base_price + variation,
                    high=base_price + variation + Decimal("5"),
                    low=base_price + variation - Decimal("5"),
                    close=base_price + variation,
                    volume=1000000,
                )
            )

        for price in prices:
            db_session.add(price)
        await db_session.commit()

        # Create subscription with RSI indicator
        subscription = IndicatorSubscription(
            user_id=seeded_user.id,
            stock_id=stock.id,
            title="RSI Test",
            message="RSI signal",
            signal_type="buy",
            condition_group={
                "logic": "and",
                "conditions": [
                    {
                        "indicator_type": "rsi",
                        "operator": "<",
                        "target_value": "30.0",
                        "timeframe": "D",
                        "period": 14,
                    }
                ],
            },
            is_active=True,
        )
        db_session.add(subscription)
        await db_session.commit()
        await db_session.refresh(subscription)

        return stock, subscription

    @pytest.mark.asyncio
    async def test_update_indicator_creates_indicator_data(
        self,
        db_session: AsyncSession,
        seeded_subscription_with_prices: tuple[Stock, IndicatorSubscription],
        redis_client: StockRedisClient,
    ):
        """Test that update_indicator job creates indicator records."""
        stock, subscription = seeded_subscription_with_prices

        # Mock SessionFactory to use our test session
        with patch("src.tasks.jobs.indicator_jobs.SessionFactory") as mock_session_factory:
            # Make SessionFactory return our test db_session wrapped as context manager
            async def mock_context():
                yield db_session

            mock_session_factory.return_value = mock_context()

            from src.tasks.jobs.indicator_jobs import update_indicator

            ctx = {"redis": redis_client._client}

            # When: run update_indicator job
            result = await update_indicator(ctx)

        # Then: job should succeed
        assert result["success"] is True
        assert result["stocks_processed"] >= 1
        assert result["indicators_calculated"] >= 1

        # And: indicator should be stored in database
        indicators = await StockIndicatorService.get_by_stock(db_session, stock.id)
        assert len(indicators) > 0

        # Find RSI indicator
        rsi_indicator = None
        for ind in indicators:
            if "RSI" in ind.indicator_key:
                rsi_indicator = ind
                break

        assert rsi_indicator is not None
        assert "value" in rsi_indicator.data
        # RSI should be between 0 and 100
        rsi_value = rsi_indicator.data["value"]
        assert 0 <= rsi_value <= 100

    @pytest.mark.asyncio
    async def test_update_indicator_gets_required_keys_from_subscriptions(
        self,
        db_session: AsyncSession,
        seeded_subscription_with_prices: tuple[Stock, IndicatorSubscription],
    ):
        """Test that job correctly determines required indicators from subscriptions."""
        stock, subscription = seeded_subscription_with_prices

        # When: get required indicator keys
        required_keys = await StockIndicatorService.get_required_indicator_keys(
            db_session, stock.id
        )

        # Then: should include RSI_14_D
        assert len(required_keys) > 0
        assert any("RSI" in key for key in required_keys)

    @pytest.mark.asyncio
    async def test_update_indicator_skips_stocks_without_subscriptions(
        self,
        db_session: AsyncSession,
        seeded_stock_with_prices: Stock,
        redis_client: StockRedisClient,
    ):
        """Test that job skips stocks without indicator subscriptions."""
        # Mock SessionFactory
        with patch("src.tasks.jobs.indicator_jobs.SessionFactory") as mock_session_factory:
            async def mock_context():
                yield db_session

            mock_session_factory.return_value = mock_context()

            from src.tasks.jobs.indicator_jobs import update_indicator

            ctx = {"redis": redis_client._client}

            # When: run job (no subscriptions exist for seeded_stock_with_prices)
            result = await update_indicator(ctx)

        # Then: should skip the stock
        assert result["stocks_processed"] == 0


class TestSubscriptionFlowEndToEnd:
    """End-to-end tests for complete subscription flow via API."""

    @pytest.fixture
    async def auth_headers(self, client: AsyncClient) -> dict[str, str]:
        """Create authenticated user and return headers."""
        await client.post(
            "/auth/register",
            json={"email": "test@example.com", "password": "password123"},
        )
        login_response = await client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    async def stock_id(self, client: AsyncClient, auth_headers: dict) -> int:
        """Create test stock."""
        response = await client.post(
            "/stocks",
            json={"symbol": "2330.TW", "name": "台積電", "is_active": False},
            headers=auth_headers,
        )
        return response.json()["data"]["id"]

    @pytest.mark.asyncio
    async def test_full_subscription_flow_with_inactive_stock(
        self,
        client: AsyncClient,
        auth_headers: dict,
        stock_id: int,
        redis_client: StockRedisClient,
    ):
        """Test complete subscription flow: create inactive stock -> subscribe -> check Redis."""
        # Given: stock is inactive
        stock_response = await client.get(f"/stocks/{stock_id}", headers=auth_headers)
        assert stock_response.json()["data"]["is_active"] is False

        # Clear Redis first
        await redis_client.clear_active_stocks()

        # When: create subscription via API
        response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "title": "RSI Buy Signal",
                "message": "2330 RSI below 30",
                "signal_type": "buy",
                "condition_group": {
                    "logic": "and",
                    "conditions": [
                        {
                            "indicator_type": "rsi",
                            "operator": "<",
                            "target_value": "30.0",
                            "timeframe": "D",
                            "period": 14,
                        }
                    ],
                },
            },
            headers=auth_headers,
        )

        # Then: subscription created successfully
        assert response.status_code == 201
        data = response.json()["data"]
        subscription_id = data["id"]

        # And: stock should be activated
        stock_response = await client.get(f"/stocks/{stock_id}", headers=auth_headers)
        assert stock_response.json()["data"]["is_active"] is True

        # And: stock should be in Redis active set
        active_stocks = await redis_client.get_active_stocks()
        assert stock_id in active_stocks

        # Cleanup
        await redis_client.remove_active_stock(stock_id)


class TestIndicatorCalculationEdgeCases:
    """Tests for edge cases in indicator calculation."""

    @pytest_asyncio.fixture
    async def stock_with_insufficient_data(self, db_session: AsyncSession) -> Stock:
        """Create stock with only 5 days of data (insufficient for RSI_14)."""
        stock = Stock(
            symbol="2330.TW",
            name="台積電",
            is_active=True,
            source=StockSource.YFINANCE,
            market=StockMarket.TAIWAN,
        )
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        # Only 5 days of prices
        for i in range(5):
            day = date.today() - timedelta(days=5 - i)
            db_session.add(
                DailyPrice(
                    stock_id=stock.id,
                    date=day,
                    open=Decimal("500"),
                    high=Decimal("505"),
                    low=Decimal("495"),
                    close=Decimal("500"),
                    volume=1000000,
                )
            )
        await db_session.commit()

        return stock

    @pytest_asyncio.fixture
    async def subscription_for_insufficient_stock(
        self,
        db_session: AsyncSession,
        seeded_user,
        stock_with_insufficient_data: Stock,
    ) -> IndicatorSubscription:
        """Create subscription for stock with insufficient data."""
        subscription = IndicatorSubscription(
            user_id=seeded_user.id,
            stock_id=stock_with_insufficient_data.id,
            title="RSI Test",
            message="RSI signal",
            signal_type="buy",
            condition_group={
                "logic": "and",
                "conditions": [
                    {
                        "indicator_type": "rsi",
                        "operator": "<",
                        "target_value": "30.0",
                        "timeframe": "D",
                        "period": 14,
                    }
                ],
            },
            is_active=True,
        )
        db_session.add(subscription)
        await db_session.commit()
        await db_session.refresh(subscription)
        return subscription

    @pytest.mark.asyncio
    async def test_insufficient_data_returns_correct_min_days(
        self,
        db_session: AsyncSession,
        seeded_user,
        stock_with_insufficient_data: Stock,
        subscription_for_insufficient_stock: IndicatorSubscription,
    ):
        """Test that insufficient data is correctly identified."""
        # When: check minimum required days
        from src.tasks.jobs.indicator_jobs import _get_min_required_days

        required_keys = await StockIndicatorService.get_required_indicator_keys(
            db_session, stock_with_insufficient_data.id
        )
        min_days = _get_min_required_days(required_keys)

        # Then: should require at least 15 days (RSI_14 needs 14+1)
        assert min_days >= 15

        # And: stock has less than required
        prices = await StockIndicatorService.get_stocks_with_indicators(db_session)
        assert stock_with_insufficient_data.id in prices  # Stock has subscription


class TestTriggerDataPreparation:
    """Tests for triggering ARQ data preparation job."""

    @pytest.mark.asyncio
    async def test_trigger_data_preparation_calls_enqueue_job(
        self,
        seeded_stock_with_prices: Stock,
    ):
        """Test that trigger_data_preparation calls ARQ enqueue_job."""
        with patch("arq.create_pool") as mock_create_pool:
            mock_pool = AsyncMock()
            mock_pool.enqueue_job = AsyncMock(return_value=MagicMock(job_id="test-job-123"))
            mock_pool.close = AsyncMock()
            mock_create_pool.return_value = mock_pool

            # When: trigger data preparation
            await SubscriptionService.trigger_data_preparation(seeded_stock_with_prices.id)

            # Then: enqueue_job should be called with correct job name
            mock_pool.enqueue_job.assert_called_once_with(
                "prepare_subscription_data",
                seeded_stock_with_prices.id,
            )
            mock_pool.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_data_preparation_handles_error_gracefully(
        self,
        seeded_stock_with_prices: Stock,
    ):
        """Test that trigger_data_preparation doesn't raise on error."""
        with patch("arq.create_pool") as mock_create_pool:
            mock_create_pool.side_effect = Exception("Redis connection failed")

            # When: trigger data preparation (should not raise)
            await SubscriptionService.trigger_data_preparation(seeded_stock_with_prices.id)

            # Then: no exception raised, error logged internally