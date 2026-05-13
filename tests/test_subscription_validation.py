"""Tests for subscription validation and data preparation flow."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

from src.subscriptions.schema import (
    IndicatorSubscriptionCreate,
    IndicatorType,
    Operator,
    SignalType,
    CompoundCondition,
    Condition,
    LogicOperator,
)
from src.subscriptions.service import SubscriptionService
from src.stocks.model import Stock, DailyPrice
from datetime import date


class TestExtractIndicatorTypes:
    """Test extract_indicator_types method."""

    def test_single_condition(self):
        """Test extracting indicator type from single condition."""
        data = IndicatorSubscriptionCreate(
            stock_id=1,
            indicator_type=IndicatorType.RSI,
            operator=Operator.GT,
            target_value=Decimal("70"),
        )

        result = SubscriptionService.extract_indicator_types(data)
        assert result == ["rsi"]

    def test_single_condition_price(self):
        """Test that price indicator is filtered out."""
        data = IndicatorSubscriptionCreate(
            stock_id=1,
            indicator_type=IndicatorType.PRICE,
            operator=Operator.GT,
            target_value=Decimal("100"),
        )

        result = SubscriptionService.extract_indicator_types(data)
        assert result == []  # Price doesn't need indicator calculation

    def test_compound_condition(self):
        """Test extracting indicator types from compound condition."""
        data = IndicatorSubscriptionCreate(
            stock_id=1,
            compound_condition=CompoundCondition(
                logic=LogicOperator.AND,
                conditions=[
                    Condition(indicator_type=IndicatorType.RSI, operator=Operator.GT, target_value=Decimal("70")),
                    Condition(indicator_type=IndicatorType.MACD, operator=Operator.LT, target_value=Decimal("0")),
                ],
            ),
        )

        result = SubscriptionService.extract_indicator_types(data)
        assert set(result) == {"rsi", "macd"}  # Should extract both

    def test_compound_condition_with_duplicates(self):
        """Test that duplicate indicator types are removed."""
        data = IndicatorSubscriptionCreate(
            stock_id=1,
            compound_condition=CompoundCondition(
                logic=LogicOperator.OR,
                conditions=[
                    Condition(indicator_type=IndicatorType.RSI, operator=Operator.GT, target_value=Decimal("70")),
                    Condition(indicator_type=IndicatorType.RSI, operator=Operator.LT, target_value=Decimal("30")),
                ],
            ),
        )

        result = SubscriptionService.extract_indicator_types(data)
        assert result == ["rsi"]  # Should deduplicate

    def test_mixed_single_and_compound(self):
        """Test extracting from both single and compound conditions."""
        data = IndicatorSubscriptionCreate(
            stock_id=1,
            indicator_type=IndicatorType.KD,
            operator=Operator.GT,
            target_value=Decimal("80"),
            compound_condition=CompoundCondition(
                logic=LogicOperator.AND,
                conditions=[
                    Condition(indicator_type=IndicatorType.RSI, operator=Operator.GT, target_value=Decimal("70")),
                ],
            ),
        )

        result = SubscriptionService.extract_indicator_types(data)
        assert set(result) == {"kd", "rsi"}  # Should extract from both


class TestCheckStockDataAvailability:
    """Test check_stock_data_availability method."""

    @pytest.mark.asyncio
    async def test_stock_not_in_redis_no_data(self, db_session, redis_client):
        """Test when stock is not active in Redis and has no historical data."""
        stock_id = 1
        indicator_types = ["rsi", "macd"]

        # Clear Redis active stocks
        await redis_client.clear_active_stocks()

        is_active, has_data = await SubscriptionService.check_stock_data_availability(
            db_session, stock_id, indicator_types, redis_client
        )

        assert is_active is False
        assert has_data is False

    @pytest.mark.asyncio
    async def test_stock_in_redis_no_data(self, db_session, redis_client, seeded_stock):
        """Test when stock is active in Redis but has insufficient historical data."""
        # Add stock to Redis active set
        await redis_client.add_active_stock(seeded_stock.id)

        # Ensure no daily prices
        # ( seeded_stock fixture should not create daily prices )

        is_active, has_data = await SubscriptionService.check_stock_data_availability(
            db_session, seeded_stock.id, ["rsi"], redis_client
        )

        assert is_active is True
        assert has_data is False

    @pytest.mark.asyncio
    async def test_stock_in_redis_with_data(self, db_session, redis_client, seeded_stock_with_prices):
        """Test when stock is active in Redis and has sufficient historical data."""
        stock = seeded_stock_with_prices

        # Add stock to Redis active set
        await redis_client.add_active_stock(stock.id)

        is_active, has_data = await SubscriptionService.check_stock_data_availability(
            db_session, stock.id, ["rsi"], redis_client
        )

        assert is_active is True
        assert has_data is True  # Should have >= 30 days of data

    @pytest.mark.asyncio
    async def test_no_indicator_types(self, db_session):
        """Test when no indicator types provided (e.g., price-only subscription)."""
        stock_id = 1

        is_active, has_data = await SubscriptionService.check_stock_data_availability(
            db_session, stock_id, [], None
        )

        assert is_active is False
        assert has_data is False  # No check performed when empty list


class TestTriggerDataPreparation:
    """Test trigger_data_preparation method."""

    @pytest.mark.asyncio
    async def test_enqueue_job_success(self):
        """Test successful job enqueueing."""
        stock_id = 1

        # Mock ARQ pool
        mock_pool = AsyncMock()
        mock_job = MagicMock()
        mock_job.job_id = "test-job-id"
        mock_pool.enqueue_job.return_value = mock_job

        with patch('arq.create_pool', return_value=mock_pool):
            await SubscriptionService.trigger_data_preparation(stock_id)

            mock_pool.enqueue_job.assert_called_once_with("prepare_subscription_data", stock_id)
            mock_pool.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_enqueue_job_failure(self):
        """Test handling when job enqueueing fails."""
        stock_id = 1

        # Mock ARQ pool that returns None
        mock_pool = AsyncMock()
        mock_pool.enqueue_job.return_value = None

        with patch('arq.create_pool', return_value=mock_pool):
            await SubscriptionService.trigger_data_preparation(stock_id)

            # Should not raise exception
            mock_pool.enqueue_job.assert_called_once()


class TestSubscriptionCreateWithValidation:
    """Test subscription create method with data validation integration."""

    @pytest.mark.asyncio
    async def test_create_triggers_data_preparation(
        self, db_session, seeded_user, seeded_stock, redis_client
    ):
        """Test that subscription creation triggers data preparation when needed."""
        # Ensure stock is not in Redis active set
        await redis_client.clear_active_stocks()

        data = IndicatorSubscriptionCreate(
            stock_id=seeded_stock.id,
            indicator_type=IndicatorType.RSI,
            operator=Operator.GT,
            target_value=Decimal("70"),
        )

        # Mock trigger_data_preparation to avoid actually enqueueing job
        with patch.object(
            SubscriptionService, 'trigger_data_preparation', new_callable=AsyncMock
        ) as mock_trigger:
            subscription = await SubscriptionService.create(
                db_session, seeded_user.id, data, redis_client
            )

            # Verify subscription was created
            assert subscription.id is not None
            assert subscription.stock_id == seeded_stock.id

            # Verify data preparation was triggered
            mock_trigger.assert_called_once_with(seeded_stock.id)

    @pytest.mark.asyncio
    async def test_create_no_trigger_when_data_ready(
        self, db_session, seeded_user, seeded_stock_with_prices, redis_client
    ):
        """Test that data preparation is not triggered when stock has data."""
        stock = seeded_stock_with_prices

        # Add stock to Redis active set
        await redis_client.add_active_stock(stock.id)

        data = IndicatorSubscriptionCreate(
            stock_id=stock.id,
            indicator_type=IndicatorType.RSI,
            operator=Operator.GT,
            target_value=Decimal("70"),
        )

        # Mock StockRedisClient to use test redis_client
        with patch('src.subscriptions.service.StockRedisClient', return_value=redis_client):
            # Mock trigger_data_preparation
            with patch.object(
                SubscriptionService, 'trigger_data_preparation', new_callable=AsyncMock
            ) as mock_trigger:
                subscription = await SubscriptionService.create(
                    db_session, seeded_user.id, data, redis_client
                )

                # Verify subscription was created
                assert subscription.id is not None

                # Verify data preparation was NOT triggered (data already ready)
                mock_trigger.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_price_subscription_no_trigger(
        self, db_session, seeded_user, seeded_stock, redis_client
    ):
        """Test that price-only subscription doesn't trigger data preparation."""
        data = IndicatorSubscriptionCreate(
            stock_id=seeded_stock.id,
            indicator_type=IndicatorType.PRICE,
            operator=Operator.GT,
            target_value=Decimal("100"),
        )

        # Mock trigger_data_preparation
        with patch.object(
            SubscriptionService, 'trigger_data_preparation', new_callable=AsyncMock
        ) as mock_trigger:
            subscription = await SubscriptionService.create(
                db_session, seeded_user.id, data, redis_client
            )

            # Verify subscription was created
            assert subscription.id is not None

            # Verify data preparation was NOT triggered (price doesn't need indicators)
            mock_trigger.assert_not_called()