"""Tests for timeframe and period fields in indicator subscriptions."""

import pytest
from httpx import AsyncClient
from decimal import Decimal

from src.subscriptions.schema import (
    Condition,
    ConditionGroup,
    IndicatorSubscriptionCreate,
    IndicatorSubscriptionUpdate,
    IndicatorType,
    LogicOperator,
    Operator,
    Timeframe,
)


class TestIndicatorConfigEndpoint:
    """Tests for GET /subscriptions/indicators/config endpoint."""

    @pytest.mark.asyncio
    async def test_get_indicator_config_success(self, client: AsyncClient):
        """Test successful retrieval of indicator configuration."""
        response = await client.get("/subscriptions/indicators/config")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "indicators" in data["data"]

        # Verify all indicator types are present
        indicators = data["data"]["indicators"]
        assert "rsi" in indicators
        assert "sma" in indicators
        assert "macd" in indicators
        assert "kd" in indicators
        assert "price" in indicators

    @pytest.mark.asyncio
    async def test_indicator_config_rsi_fields(self, client: AsyncClient):
        """Test RSI indicator configuration fields."""
        response = await client.get("/subscriptions/indicators/config")
        rsi_config = response.json()["data"]["indicators"]["rsi"]

        assert rsi_config["label"] == "RSI (Relative Strength Index)"
        assert rsi_config["timeframe"]["required"] is True
        assert rsi_config["timeframe"]["default"] == "D"
        assert rsi_config["timeframe"]["options"] == ["D", "W"]
        assert rsi_config["period"]["required"] is False
        assert rsi_config["period"]["default"] == 14
        assert rsi_config["period"]["min"] == 5
        assert rsi_config["period"]["max"] == 50
        assert rsi_config["operators"] == [">", "<", ">=", "<=", "==", "!="]

    @pytest.mark.asyncio
    async def test_indicator_config_sma_fields(self, client: AsyncClient):
        """Test SMA indicator configuration fields."""
        response = await client.get("/subscriptions/indicators/config")
        sma_config = response.json()["data"]["indicators"]["sma"]

        assert sma_config["label"] == "SMA (Simple Moving Average)"
        assert sma_config["period"]["default"] == 20
        assert sma_config["period"]["min"] == 5
        assert sma_config["period"]["max"] == 200

    @pytest.mark.asyncio
    async def test_indicator_config_macd_no_period(self, client: AsyncClient):
        """Test MACD indicator has no period field."""
        response = await client.get("/subscriptions/indicators/config")
        macd_config = response.json()["data"]["indicators"]["macd"]

        assert macd_config["label"] == "MACD"
        assert macd_config["period"] is None
        assert macd_config["note"] == "Fixed periods: 12/26/9"

    @pytest.mark.asyncio
    async def test_indicator_config_kd_no_period(self, client: AsyncClient):
        """Test KD indicator has no period field."""
        response = await client.get("/subscriptions/indicators/config")
        kd_config = response.json()["data"]["indicators"]["kd"]

        assert kd_config["label"] == "KD (Stochastic Oscillator)"
        assert kd_config["period"] is None
        assert kd_config["note"] == "Fixed period: 9"

    @pytest.mark.asyncio
    async def test_indicator_config_price_no_period(self, client: AsyncClient):
        """Test Price indicator has no period field."""
        response = await client.get("/subscriptions/indicators/config")
        price_config = response.json()["data"]["indicators"]["price"]

        assert price_config["label"] == "Price"
        assert price_config["period"] is None
        assert "note" not in price_config or price_config.get("note") is None


class TestTimeframePeriodValidation:
    """Tests for timeframe and period field validation in schemas."""

    def test_timeframe_default_is_day(self):
        """Test that timeframe defaults to 'D' in Condition."""
        condition = Condition(
            indicator_type=IndicatorType.RSI,
            operator=Operator.GT,
            target_value=Decimal("70"),
        )
        assert condition.timeframe == Timeframe.D

    def test_timeframe_week_valid(self):
        """Test that timeframe 'W' is valid in Condition."""
        condition = Condition(
            indicator_type=IndicatorType.RSI,
            operator=Operator.GT,
            target_value=Decimal("70"),
            timeframe=Timeframe.W,
        )
        assert condition.timeframe == Timeframe.W

    def test_period_valid_for_rsi(self):
        """Test that period is valid for RSI indicator."""
        condition = Condition(
            indicator_type=IndicatorType.RSI,
            operator=Operator.GT,
            target_value=Decimal("70"),
            period=14,
        )
        assert condition.period == 14

    def test_period_valid_for_sma(self):
        """Test that period is valid for SMA indicator."""
        condition = Condition(
            indicator_type=IndicatorType.SMA,
            operator=Operator.GT,
            target_value=Decimal("100"),
            period=20,
        )
        assert condition.period == 20

    def test_period_invalid_for_macd(self):
        """Test that period is not allowed for MACD."""
        with pytest.raises(ValueError, match="period is not applicable for macd"):
            Condition(
                indicator_type=IndicatorType.MACD,
                operator=Operator.GT,
                target_value=Decimal("0"),
                period=12,
            )

    def test_period_invalid_for_kd(self):
        """Test that period is not allowed for KD."""
        with pytest.raises(ValueError, match="period is not applicable for kd"):
            Condition(
                indicator_type=IndicatorType.KD,
                operator=Operator.GT,
                target_value=Decimal("80"),
                period=9,
            )

    def test_period_invalid_for_price(self):
        """Test that period is not allowed for Price."""
        with pytest.raises(ValueError, match="period is not applicable for price"):
            Condition(
                indicator_type=IndicatorType.PRICE,
                operator=Operator.GT,
                target_value=Decimal("100"),
                period=10,
            )

    def test_period_out_of_range_min(self):
        """Test that period below minimum is rejected."""
        with pytest.raises(ValueError):
            Condition(
                indicator_type=IndicatorType.RSI,
                operator=Operator.GT,
                target_value=Decimal("70"),
                period=4,  # Below min of 5
            )

    def test_period_out_of_range_max(self):
        """Test that period above maximum is rejected."""
        with pytest.raises(ValueError):
            Condition(
                indicator_type=IndicatorType.SMA,
                operator=Operator.GT,
                target_value=Decimal("100"),
                period=201,  # Above max of 200
            )

    def test_period_optional_for_rsi(self):
        """Test that period is optional for RSI (defaults to None)."""
        condition = Condition(
            indicator_type=IndicatorType.RSI,
            operator=Operator.GT,
            target_value=Decimal("70"),
        )
        assert condition.period is None

    def test_condition_group_with_single_condition(self):
        """Test ConditionGroup with single condition."""
        data = IndicatorSubscriptionCreate(
            stock_id=1,
            condition_group=ConditionGroup(
                logic=LogicOperator.AND,
                conditions=[
                    Condition(
                        indicator_type=IndicatorType.RSI,
                        operator=Operator.GT,
                        target_value=Decimal("70"),
                    ),
                ],
            ),
        )
        assert data.condition_group.logic == LogicOperator.AND
        assert len(data.condition_group.conditions) == 1


class TestConditionTimeframePeriod:
    """Tests for timeframe and period in Condition model."""

    def test_condition_with_timeframe(self):
        """Test Condition with timeframe field."""
        condition = Condition(
            indicator_type=IndicatorType.RSI,
            operator=Operator.GT,
            target_value=Decimal("70"),
            timeframe=Timeframe.W,
        )
        assert condition.timeframe == Timeframe.W

    def test_condition_with_period(self):
        """Test Condition with period field."""
        condition = Condition(
            indicator_type=IndicatorType.RSI,
            operator=Operator.GT,
            target_value=Decimal("70"),
            period=7,
        )
        assert condition.period == 7

    def test_condition_period_invalid_for_macd(self):
        """Test that Condition rejects period for MACD."""
        with pytest.raises(ValueError, match="period is not applicable for macd"):
            Condition(
                indicator_type=IndicatorType.MACD,
                operator=Operator.GT,
                target_value=Decimal("0"),
                period=12,
            )

    def test_condition_group_with_timeframe_period(self):
        """Test ConditionGroup with timeframe/period in conditions."""
        condition_group = ConditionGroup(
            logic=LogicOperator.AND,
            conditions=[
                Condition(
                    indicator_type=IndicatorType.RSI,
                    operator=Operator.GT,
                    target_value=Decimal("70"),
                    timeframe=Timeframe.W,
                    period=14,
                ),
                Condition(
                    indicator_type=IndicatorType.SMA,
                    operator=Operator.LT,
                    target_value=Decimal("100"),
                    timeframe=Timeframe.D,
                    period=50,
                ),
            ],
        )
        assert condition_group.conditions[0].timeframe == Timeframe.W
        assert condition_group.conditions[0].period == 14
        assert condition_group.conditions[1].timeframe == Timeframe.D
        assert condition_group.conditions[1].period == 50


class TestSubscriptionRouterTimeframePeriod:
    """Tests for timeframe and period in subscription router endpoints."""

    @pytest.fixture
    async def auth_headers(self, client: AsyncClient) -> dict[str, str]:
        """Create authenticated user and return headers with token."""
        await client.post(
            "/auth/register",
            json={"email": "test_tp@example.com", "password": "password123"},
        )
        login_response = await client.post(
            "/auth/login",
            json={"email": "test_tp@example.com", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    async def stock_id(self, client: AsyncClient, auth_headers: dict) -> int:
        """Create a test stock and return its ID."""
        response = await client.post(
            "/stocks",
            json={"symbol": "2330TP.TW", "name": "台積電TP", "is_active": True},
            headers=auth_headers,
        )
        assert response.status_code == 201, f"Failed to create stock: {response.json()}"
        return response.json()["data"]["id"]

    @pytest.mark.asyncio
    async def test_create_with_timeframe(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test creating subscription with timeframe."""
        response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "condition_group": {
                    "logic": "and",
                    "conditions": [
                        {"indicator_type": "rsi", "operator": "<", "target_value": "30.0", "timeframe": "W"}
                    ],
                },
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["data"]["condition_group"]["conditions"][0]["timeframe"] == "W"

    @pytest.mark.asyncio
    async def test_create_with_period(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test creating subscription with period."""
        response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "condition_group": {
                    "logic": "and",
                    "conditions": [
                        {"indicator_type": "rsi", "operator": "<", "target_value": "30.0", "period": 7}
                    ],
                },
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["data"]["condition_group"]["conditions"][0]["period"] == 7

    @pytest.mark.asyncio
    async def test_create_with_timeframe_and_period(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test creating subscription with both timeframe and period."""
        response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "condition_group": {
                    "logic": "and",
                    "conditions": [
                        {"indicator_type": "sma", "operator": ">", "target_value": "100.0", "timeframe": "D", "period": 50}
                    ],
                },
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["data"]["condition_group"]["conditions"][0]["timeframe"] == "D"
        assert data["data"]["condition_group"]["conditions"][0]["period"] == 50

    @pytest.mark.asyncio
    async def test_create_invalid_period_for_macd(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test that period is rejected for MACD."""
        response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "condition_group": {
                    "logic": "and",
                    "conditions": [
                        {"indicator_type": "macd", "operator": ">", "target_value": "0.0", "period": 12}
                    ],
                },
            },
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_timeframe_and_period(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test updating subscription timeframe and period."""
        # Create subscription
        create_response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "condition_group": {
                    "logic": "and",
                    "conditions": [
                        {"indicator_type": "rsi", "operator": "<", "target_value": "30.0"}
                    ],
                },
            },
            headers=auth_headers,
        )
        subscription_id = create_response.json()["data"]["id"]

        # Update timeframe and period
        response = await client.patch(
            f"/subscriptions/{subscription_id}",
            json={
                "condition_group": {
                    "logic": "and",
                    "conditions": [
                        {"indicator_type": "rsi", "operator": "<", "target_value": "30.0", "timeframe": "W", "period": 21}
                    ],
                },
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["condition_group"]["conditions"][0]["timeframe"] == "W"
        assert data["data"]["condition_group"]["conditions"][0]["period"] == 21

    @pytest.mark.asyncio
    async def test_unique_constraint_with_different_timeframe(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test that same condition with different timeframe is allowed."""
        # Create first subscription with D timeframe
        response1 = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "condition_group": {
                    "logic": "and",
                    "conditions": [
                        {"indicator_type": "rsi", "operator": "<", "target_value": "30.0", "timeframe": "D"}
                    ],
                },
            },
            headers=auth_headers,
        )
        assert response1.status_code == 201

        # Create second subscription with W timeframe (should be allowed)
        response2 = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "condition_group": {
                    "logic": "and",
                    "conditions": [
                        {"indicator_type": "rsi", "operator": "<", "target_value": "30.0", "timeframe": "W"}
                    ],
                },
            },
            headers=auth_headers,
        )
        assert response2.status_code == 201

    @pytest.mark.asyncio
    async def test_unique_constraint_with_different_period(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test that same condition with different period is allowed."""
        # Create first subscription with period 14
        response1 = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "condition_group": {
                    "logic": "and",
                    "conditions": [
                        {"indicator_type": "rsi", "operator": "<", "target_value": "30.0", "period": 14}
                    ],
                },
            },
            headers=auth_headers,
        )
        assert response1.status_code == 201

        # Create second subscription with period 7 (should be allowed)
        response2 = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "condition_group": {
                    "logic": "and",
                    "conditions": [
                        {"indicator_type": "rsi", "operator": "<", "target_value": "30.0", "period": 7}
                    ],
                },
            },
            headers=auth_headers,
        )
        assert response2.status_code == 201

    @pytest.mark.asyncio
    async def test_condition_group_with_timeframe_period(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test creating subscription with condition_group containing timeframe/period."""
        response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "condition_group": {
                    "logic": "and",
                    "conditions": [
                        {
                            "indicator_type": "rsi",
                            "operator": "<",
                            "target_value": "30",
                            "timeframe": "D",
                            "period": 14,
                        },
                        {
                            "indicator_type": "sma",
                            "operator": ">",
                            "target_value": "100",
                            "timeframe": "W",
                            "period": 50,
                        },
                    ],
                },
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        conditions = data["data"]["condition_group"]["conditions"]
        assert conditions[0]["timeframe"] == "D"
        assert conditions[0]["period"] == 14
        assert conditions[1]["timeframe"] == "W"
        assert conditions[1]["period"] == 50