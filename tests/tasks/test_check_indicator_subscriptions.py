"""Tests for indicator subscription notification check functionality.

Tests the complete subscription check flow:
1. evaluate_subscription: condition evaluation logic (AND/OR)
2. build_indicator_key: key generation from subscription conditions
3. extract_indicator_value: value extraction from indicator data
4. compare_values: comparison operator logic
5. check_indicator_subscriptions: job execution with mocked Redis/DB
"""

import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from src.subscriptions.model import IndicatorSubscription
from src.subscriptions.schema import ConditionGroup, Condition, IndicatorType, Operator, LogicOperator
from src.stock_indicator.model import StockIndicator
from src.stocks.model import Stock
from src.stocks.schema import StockSource, StockMarket
from src.users.model import User
from src.tasks.jobs.subscription_jobs import (
    evaluate_subscription,
    build_indicator_key,
    extract_indicator_value,
    compare_values,
    check_indicator_subscriptions,
)


class TestBuildIndicatorKey:
    """Tests for build_indicator_key function."""

    def test_build_rsi_key_with_period(self):
        """Test building RSI indicator key with period."""
        key = build_indicator_key("rsi", "D", 14)
        assert key == "RSI_14_D"

    def test_build_rsi_key_without_period(self):
        """Test building RSI indicator key with default period."""
        key = build_indicator_key("rsi", "D", None)
        assert key == "RSI_14_D"

    def test_build_sma_key_with_period(self):
        """Test building SMA indicator key with period."""
        key = build_indicator_key("sma", "D", 20)
        assert key == "SMA_20_D"

    def test_build_sma_key_without_period(self):
        """Test building SMA indicator key with default period."""
        key = build_indicator_key("sma", "D", None)
        assert key == "SMA_20_D"

    def test_build_macd_key(self):
        """Test building MACD indicator key with default params."""
        key = build_indicator_key("macd", "D", None)
        assert key == "MACD_12_26_9_D"

    def test_build_kdj_key(self):
        """Test building KDJ indicator key with default params."""
        key = build_indicator_key("kdj", "D", None)
        assert key == "KDJ_9_3_3_D"

    def test_build_price_key_returns_none(self):
        """Test that price indicator returns None (no key needed)."""
        key = build_indicator_key("price", "D", None)
        assert key is None

    def test_build_invalid_indicator_returns_none(self):
        """Test that invalid indicator type returns None."""
        key = build_indicator_key("invalid", "D", None)
        assert key is None


class TestExtractIndicatorValue:
    """Tests for extract_indicator_value function."""

    def test_extract_rsi_value(self):
        """Test extracting RSI value from indicator data."""
        data = {"value": 65.5}
        value = extract_indicator_value("rsi", data)
        assert value == Decimal("65.5")

    def test_extract_rsi_value_none(self):
        """Test extracting RSI value when value is None."""
        data = {"value": None}
        value = extract_indicator_value("rsi", data)
        assert value is None

    def test_extract_sma_value(self):
        """Test extracting SMA value from indicator data."""
        data = {"value": 550.25}
        value = extract_indicator_value("sma", data)
        assert value == Decimal("550.25")

    def test_extract_macd_histogram(self):
        """Test extracting MACD histogram value."""
        data = {"histogram": 2.5}
        value = extract_indicator_value("macd", data)
        assert value == Decimal("2.5")

    def test_extract_kdj_k_value(self):
        """Test extracting KDJ K value."""
        data = {"k": 80.5, "d": 75.3, "j": 85.7}
        value = extract_indicator_value("kd", data)
        assert value == Decimal("80.5")

    def test_extract_kdj_k_value_none(self):
        """Test extracting KDJ K value when k is None."""
        data = {"k": None, "d": 75.3}
        value = extract_indicator_value("kd", data)
        assert value is None

    def test_extract_invalid_indicator_returns_none(self):
        """Test that invalid indicator type returns None."""
        data = {"value": 100}
        value = extract_indicator_value("invalid", data)
        assert value is None


class TestCompareValues:
    """Tests for compare_values function."""

    def test_compare_greater_than(self):
        """Test > operator."""
        assert compare_values(Decimal("70"), ">", Decimal("60")) is True
        assert compare_values(Decimal("50"), ">", Decimal("60")) is False

    def test_compare_less_than(self):
        """Test < operator."""
        assert compare_values(Decimal("50"), "<", Decimal("60")) is True
        assert compare_values(Decimal("70"), "<", Decimal("60")) is False

    def test_compare_greater_equal(self):
        """Test >= operator."""
        assert compare_values(Decimal("70"), ">=", Decimal("70")) is True
        assert compare_values(Decimal("60"), ">=", Decimal("70")) is False

    def test_compare_less_equal(self):
        """Test <= operator."""
        assert compare_values(Decimal("60"), "<=", Decimal("60")) is True
        assert compare_values(Decimal("70"), "<=", Decimal("60")) is False

    def test_compare_equal(self):
        """Test == operator."""
        assert compare_values(Decimal("60"), "==", Decimal("60")) is True
        assert compare_values(Decimal("60.1"), "==", Decimal("60")) is False

    def test_compare_not_equal(self):
        """Test != operator."""
        assert compare_values(Decimal("60"), "!=", Decimal("70")) is True
        assert compare_values(Decimal("60"), "!=", Decimal("60")) is False

    def test_invalid_operator_returns_false(self):
        """Test that invalid operator returns False."""
        assert compare_values(Decimal("60"), "invalid", Decimal("50")) is False


class TestEvaluateSubscription:
    """Tests for evaluate_subscription function."""

    @pytest_asyncio.fixture
    async def seeded_user(self, db_session: AsyncSession) -> User:
        """Create a seeded user."""
        user = User(
            line_user_id="test_user_123",
            display_name="Test User",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    @pytest_asyncio.fixture
    async def seeded_stock(self, db_session: AsyncSession) -> Stock:
        """Create a seeded stock."""
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
        return stock

    @pytest_asyncio.fixture
    async def seeded_subscription(
        self,
        db_session: AsyncSession,
        seeded_user: User,
        seeded_stock: Stock,
    ) -> IndicatorSubscription:
        """Create a seeded indicator subscription with single condition."""
        subscription = IndicatorSubscription(
            user_id=seeded_user.id,
            stock_id=seeded_stock.id,
            title="RSI > 70",
            message="RSI exceeds 70",
            signal_type="buy",
            condition_group={
                "logic": "and",
                "conditions": [
                    {
                        "indicator_type": "rsi",
                        "operator": ">",
                        "target_value": "70",
                        "timeframe": "D",
                        "period": 14,
                    }
                ],
            },
            is_active=True,
            is_triggered=False,
        )
        db_session.add(subscription)
        await db_session.commit()
        await db_session.refresh(subscription)
        return subscription

    @pytest.mark.asyncio
    async def test_evaluate_single_condition_and_triggered(
        self,
        seeded_subscription: IndicatorSubscription,
    ):
        """Test single condition (AND logic) when triggered."""
        indicators = {"RSI_14_D": {"value": 75.5}}

        triggered, value = await evaluate_subscription(seeded_subscription, indicators)

        assert triggered is True
        assert value == Decimal("75.5")

    @pytest.mark.asyncio
    async def test_evaluate_single_condition_and_not_triggered(
        self,
        seeded_subscription: IndicatorSubscription,
    ):
        """Test single condition (AND logic) when not triggered."""
        indicators = {"RSI_14_D": {"value": 65.0}}

        triggered, value = await evaluate_subscription(seeded_subscription, indicators)

        assert triggered is False
        assert value is None

    @pytest.mark.asyncio
    async def test_evaluate_multiple_conditions_and_all_pass(
        self,
        db_session: AsyncSession,
        seeded_user: User,
        seeded_stock: Stock,
    ):
        """Test multiple conditions (AND logic) all passing."""
        subscription = IndicatorSubscription(
            user_id=seeded_user.id,
            stock_id=seeded_stock.id,
            title="RSI > 70 AND SMA > 500",
            message="Both conditions met",
            signal_type="buy",
            condition_group={
                "logic": "and",
                "conditions": [
                    {
                        "indicator_type": "rsi",
                        "operator": ">",
                        "target_value": "70",
                        "timeframe": "D",
                        "period": 14,
                    },
                    {
                        "indicator_type": "sma",
                        "operator": ">",
                        "target_value": "500",
                        "timeframe": "D",
                        "period": 20,
                    },
                ],
            },
            is_active=True,
        )
        db_session.add(subscription)
        await db_session.commit()

        indicators = {
            "RSI_14_D": {"value": 75.0},
            "SMA_20_D": {"value": 520.0},
        }

        triggered, value = await evaluate_subscription(subscription, indicators)

        assert triggered is True
        assert value == Decimal("75.0")

    @pytest.mark.asyncio
    async def test_evaluate_multiple_conditions_and_one_fails(
        self,
        db_session: AsyncSession,
        seeded_user: User,
        seeded_stock: Stock,
    ):
        """Test multiple conditions (AND logic) one failing."""
        subscription = IndicatorSubscription(
            user_id=seeded_user.id,
            stock_id=seeded_stock.id,
            title="RSI > 70 AND SMA > 500",
            message="Both conditions met",
            signal_type="buy",
            condition_group={
                "logic": "and",
                "conditions": [
                    {
                        "indicator_type": "rsi",
                        "operator": ">",
                        "target_value": "70",
                        "timeframe": "D",
                        "period": 14,
                    },
                    {
                        "indicator_type": "sma",
                        "operator": ">",
                        "target_value": "500",
                        "timeframe": "D",
                        "period": 20,
                    },
                ],
            },
            is_active=True,
        )
        db_session.add(subscription)
        await db_session.commit()

        indicators = {
            "RSI_14_D": {"value": 75.0},
            "SMA_20_D": {"value": 480.0},  # Fails
        }

        triggered, value = await evaluate_subscription(subscription, indicators)

        assert triggered is False
        assert value is None

    @pytest.mark.asyncio
    async def test_evaluate_multiple_conditions_or_one_passes(
        self,
        db_session: AsyncSession,
        seeded_user: User,
        seeded_stock: Stock,
    ):
        """Test multiple conditions (OR logic) one passing."""
        subscription = IndicatorSubscription(
            user_id=seeded_user.id,
            stock_id=seeded_stock.id,
            title="RSI > 70 OR SMA > 500",
            message="Either condition met",
            signal_type="buy",
            condition_group={
                "logic": "or",
                "conditions": [
                    {
                        "indicator_type": "rsi",
                        "operator": ">",
                        "target_value": "70",
                        "timeframe": "D",
                        "period": 14,
                    },
                    {
                        "indicator_type": "sma",
                        "operator": ">",
                        "target_value": "500",
                        "timeframe": "D",
                        "period": 20,
                    },
                ],
            },
            is_active=True,
        )
        db_session.add(subscription)
        await db_session.commit()

        indicators = {
            "RSI_14_D": {"value": 75.0},
            "SMA_20_D": {"value": 480.0},
        }

        triggered, value = await evaluate_subscription(subscription, indicators)

        assert triggered is True
        assert value == Decimal("75.0")

    @pytest.mark.asyncio
    async def test_evaluate_multiple_conditions_or_all_fail(
        self,
        db_session: AsyncSession,
        seeded_user: User,
        seeded_stock: Stock,
    ):
        """Test multiple conditions (OR logic) all failing."""
        subscription = IndicatorSubscription(
            user_id=seeded_user.id,
            stock_id=seeded_stock.id,
            title="RSI > 70 OR SMA > 500",
            message="Either condition met",
            signal_type="buy",
            condition_group={
                "logic": "or",
                "conditions": [
                    {
                        "indicator_type": "rsi",
                        "operator": ">",
                        "target_value": "70",
                        "timeframe": "D",
                        "period": 14,
                    },
                    {
                        "indicator_type": "sma",
                        "operator": ">",
                        "target_value": "500",
                        "timeframe": "D",
                        "period": 20,
                    },
                ],
            },
            is_active=True,
        )
        db_session.add(subscription)
        await db_session.commit()

        indicators = {
            "RSI_14_D": {"value": 60.0},
            "SMA_20_D": {"value": 480.0},
        }

        triggered, value = await evaluate_subscription(subscription, indicators)

        assert triggered is False
        assert value is None

    @pytest.mark.asyncio
    async def test_evaluate_missing_indicator_data(
        self,
        seeded_subscription: IndicatorSubscription,
    ):
        """Test evaluation when indicator data is missing."""
        indicators = {}  # No indicator data

        triggered, value = await evaluate_subscription(seeded_subscription, indicators)

        assert triggered is False
        assert value is None

    @pytest.mark.asyncio
    async def test_evaluate_boundary_values(
        self,
        db_session: AsyncSession,
        seeded_user: User,
        seeded_stock: Stock,
    ):
        """Test evaluation with boundary values (0, 100)."""
        # Test RSI = 0
        subscription_low = IndicatorSubscription(
            user_id=seeded_user.id,
            stock_id=seeded_stock.id,
            title="RSI < 10",
            message="RSI below 10",
            signal_type="buy",
            condition_group={
                "logic": "and",
                "conditions": [
                    {
                        "indicator_type": "rsi",
                        "operator": "<",
                        "target_value": "10",
                        "timeframe": "D",
                        "period": 14,
                    }
                ],
            },
            is_active=True,
        )
        db_session.add(subscription_low)
        await db_session.commit()

        indicators = {"RSI_14_D": {"value": 0.0}}
        triggered, value = await evaluate_subscription(subscription_low, indicators)
        assert triggered is True
        assert value == Decimal("0")

        # Test RSI = 100
        subscription_high = IndicatorSubscription(
            user_id=seeded_user.id,
            stock_id=seeded_stock.id,
            title="RSI > 90",
            message="RSI above 90",
            signal_type="sell",
            condition_group={
                "logic": "and",
                "conditions": [
                    {
                        "indicator_type": "rsi",
                        "operator": ">",
                        "target_value": "90",
                        "timeframe": "D",
                        "period": 14,
                    }
                ],
            },
            is_active=True,
        )
        db_session.add(subscription_high)
        await db_session.commit()

        indicators = {"RSI_14_D": {"value": 100.0}}
        triggered, value = await evaluate_subscription(subscription_high, indicators)
        assert triggered is True
        assert value == Decimal("100")


class TestCheckIndicatorSubscriptionsJob:
    """Tests for check_indicator_subscriptions ARQ job."""

    @pytest_asyncio.fixture
    async def seeded_user(self, db_session: AsyncSession) -> User:
        """Create a seeded user."""
        user = User(
            line_user_id="test_user_456",
            display_name="Test User",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    @pytest_asyncio.fixture
    async def seeded_stock(self, db_session: AsyncSession) -> Stock:
        """Create a seeded stock."""
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
        return stock

    @pytest_asyncio.fixture
    async def seeded_indicator(
        self,
        db_session: AsyncSession,
        seeded_stock: Stock,
    ) -> StockIndicator:
        """Create seeded indicator data."""
        indicator = StockIndicator(
            stock_id=seeded_stock.id,
            indicator_key="RSI_14_D",
            data={"value": 75.0},
        )
        db_session.add(indicator)
        await db_session.commit()
        await db_session.refresh(indicator)
        return indicator

    @pytest_asyncio.fixture
    async def seeded_subscription(
        self,
        db_session: AsyncSession,
        seeded_user: User,
        seeded_stock: Stock,
    ) -> IndicatorSubscription:
        """Create seeded subscription."""
        subscription = IndicatorSubscription(
            user_id=seeded_user.id,
            stock_id=seeded_stock.id,
            title="RSI > 70",
            message="RSI exceeds 70",
            signal_type="buy",
            condition_group={
                "logic": "and",
                "conditions": [
                    {
                        "indicator_type": "rsi",
                        "operator": ">",
                        "target_value": "70",
                        "timeframe": "D",
                        "period": 14,
                    }
                ],
            },
            is_active=True,
            is_triggered=False,
        )
        db_session.add(subscription)
        await db_session.commit()
        await db_session.refresh(subscription)
        return subscription

    @pytest.mark.asyncio
    async def test_job_empty_updated_stocks(self):
        """Test job with no updated stocks in Redis."""
        mock_redis = AsyncMock()
        mock_redis.smembers = AsyncMock(return_value=set())

        ctx = {"redis": mock_redis}

        result = await check_indicator_subscriptions(ctx)

        assert result["success"] is True
        assert result["stocks_checked"] == 0
        assert result["subscriptions_evaluated"] == 0
        mock_redis.smembers.assert_called_once_with("indicator:updated:last_minute")

    @pytest.mark.asyncio
    async def test_job_with_updated_stocks_and_triggered_subscription(
        self,
        db_session: AsyncSession,
        seeded_subscription: IndicatorSubscription,
        seeded_indicator: StockIndicator,
        seeded_stock: Stock,
        seeded_user: User,
    ):
        """Test job with updated stocks and triggered subscription."""
        mock_redis = AsyncMock()
        mock_redis.smembers = AsyncMock(
            return_value={str(seeded_stock.id).encode()}
        )
        mock_redis.delete = AsyncMock()

        ctx = {"redis": mock_redis}

        with patch("src.tasks.jobs.subscription_jobs.SessionFactory") as mock_session_factory:
            mock_session_factory.return_value.__aenter__.return_value = db_session

            result = await check_indicator_subscriptions(ctx)

        assert result["success"] is True
        assert result["stocks_checked"] == 1
        assert result["subscriptions_evaluated"] == 1
        assert result["conditions_triggered"] == 1
        assert result["notifications_sent"] == 1

        # Verify notification was recorded
        await db_session.refresh(seeded_subscription)
        assert seeded_subscription.is_triggered is True
        assert seeded_subscription.cooldown_end_at is not None

    @pytest.mark.asyncio
    async def test_job_subscription_in_cooldown(
        self,
        db_session: AsyncSession,
        seeded_user: User,
        seeded_stock: Stock,
        seeded_indicator: StockIndicator,
    ):
        """Test job skips subscription in cooldown period."""
        # Create subscription with cooldown
        subscription = IndicatorSubscription(
            user_id=seeded_user.id,
            stock_id=seeded_stock.id,
            title="RSI > 70",
            message="RSI exceeds 70",
            signal_type="buy",
            condition_group={
                "logic": "and",
                "conditions": [
                    {
                        "indicator_type": "rsi",
                        "operator": ">",
                        "target_value": "70",
                        "timeframe": "D",
                        "period": 14,
                    }
                ],
            },
            is_active=True,
            is_triggered=True,
            cooldown_end_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db_session.add(subscription)
        await db_session.commit()

        mock_redis = AsyncMock()
        mock_redis.smembers = AsyncMock(
            return_value={str(seeded_stock.id).encode()}
        )
        mock_redis.delete = AsyncMock()

        ctx = {"redis": mock_redis}

        with patch("src.tasks.jobs.subscription_jobs.SessionFactory") as mock_session_factory:
            mock_session_factory.return_value.__aenter__.return_value = db_session

            result = await check_indicator_subscriptions(ctx)

        assert result["success"] is True
        assert result["subscriptions_evaluated"] == 0  # Skipped due to cooldown
        assert result["notifications_sent"] == 0

    @pytest.mark.asyncio
    async def test_job_subscription_not_active(
        self,
        db_session: AsyncSession,
        seeded_user: User,
        seeded_stock: Stock,
        seeded_indicator: StockIndicator,
    ):
        """Test job skips inactive subscription."""
        subscription = IndicatorSubscription(
            user_id=seeded_user.id,
            stock_id=seeded_stock.id,
            title="RSI > 70",
            message="RSI exceeds 70",
            signal_type="buy",
            condition_group={
                "logic": "and",
                "conditions": [
                    {
                        "indicator_type": "rsi",
                        "operator": ">",
                        "target_value": "70",
                        "timeframe": "D",
                        "period": 14,
                    }
                ],
            },
            is_active=False,  # Inactive
            is_triggered=False,
        )
        db_session.add(subscription)
        await db_session.commit()

        mock_redis = AsyncMock()
        mock_redis.smembers = AsyncMock(
            return_value={str(seeded_stock.id).encode()}
        )
        mock_redis.delete = AsyncMock()

        ctx = {"redis": mock_redis}

        with patch("src.tasks.jobs.subscription_jobs.SessionFactory") as mock_session_factory:
            mock_session_factory.return_value.__aenter__.return_value = db_session

            result = await check_indicator_subscriptions(ctx)

        assert result["success"] is True
        assert result["subscriptions_evaluated"] == 0
        assert result["notifications_sent"] == 0

    @pytest.mark.asyncio
    async def test_job_handles_error_gracefully(
        self,
        db_session: AsyncSession,
        seeded_subscription: IndicatorSubscription,
        seeded_indicator: StockIndicator,
        seeded_stock: Stock,
    ):
        """Test job handles errors gracefully and continues."""
        mock_redis = AsyncMock()
        mock_redis.smembers = AsyncMock(
            return_value={str(seeded_stock.id).encode()}
        )
        mock_redis.delete = AsyncMock()

        ctx = {"redis": mock_redis}

        # Mock SessionFactory to raise error
        with patch("src.tasks.jobs.subscription_jobs.SessionFactory") as mock_session_factory:
            mock_session_factory.return_value.__aenter__.side_effect = Exception("DB error")

            result = await check_indicator_subscriptions(ctx)

        assert result["success"] is False
        assert len(result["errors"]) > 0
        assert "DB error" in result["errors"][0]