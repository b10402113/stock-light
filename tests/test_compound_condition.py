"""Tests for condition_group functionality in indicator subscriptions."""

import pytest
from httpx import AsyncClient


class TestConditionGroup:
    """Tests for condition_group field in IndicatorSubscription"""

    @pytest.fixture
    async def auth_headers(self, client: AsyncClient) -> dict[str, str]:
        """Create authenticated user and return headers with token"""
        await client.post(
            "/auth/register",
            json={"email": "condition_test@example.com", "password": "password123"},
        )
        login_response = await client.post(
            "/auth/login",
            json={"email": "condition_test@example.com", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    async def stock_id(self, client: AsyncClient) -> int:
        """Create a test stock and return its ID"""
        response = await client.post(
            "/stocks",
            json={"symbol": "2330.TW", "name": "台積電", "is_active": True},
        )
        return response.json()["data"]["id"]

    @pytest.mark.asyncio
    async def test_create_with_single_condition(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test creating subscription with one condition in condition_group"""
        response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "title": "RSI Buy Signal",
                "message": "Trigger when RSI < 30",
                "signal_type": "buy",
                "condition_group": {
                    "logic": "and",
                    "conditions": [
                        {"indicator_type": "rsi", "operator": "<", "target_value": "30", "timeframe": "D", "period": 14},
                    ],
                },
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()["data"]
        assert data["condition_group"]["logic"] == "and"
        assert len(data["condition_group"]["conditions"]) == 1
        assert data["condition_group"]["conditions"][0]["indicator_type"] == "rsi"
        assert data["condition_group"]["conditions"][0]["operator"] == "<"
        assert data["condition_group"]["conditions"][0]["target_value"] == "30"

    @pytest.mark.asyncio
    async def test_create_with_multiple_conditions(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test creating subscription with multiple conditions (AND logic)"""
        response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "title": "Complex Buy Signal",
                "message": "Trigger when price > 500 AND RSI < 30 AND MACD > 0",
                "signal_type": "buy",
                "condition_group": {
                    "logic": "and",
                    "conditions": [
                        {"indicator_type": "price", "operator": ">", "target_value": "500", "timeframe": "D"},
                        {"indicator_type": "rsi", "operator": "<", "target_value": "30", "timeframe": "D", "period": 14},
                        {"indicator_type": "macd", "operator": ">", "target_value": "0", "timeframe": "D"},
                    ],
                },
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()["data"]
        assert data["condition_group"]["logic"] == "and"
        assert len(data["condition_group"]["conditions"]) == 3
        assert data["condition_group"]["conditions"][0]["indicator_type"] == "price"
        assert data["condition_group"]["conditions"][1]["indicator_type"] == "rsi"
        assert data["condition_group"]["conditions"][2]["indicator_type"] == "macd"

    @pytest.mark.asyncio
    async def test_create_with_or_logic(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test creating subscription with OR logic condition_group"""
        response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "title": "Either Condition Signal",
                "message": "Trigger when RSI < 30 OR RSI > 70",
                "signal_type": "sell",
                "condition_group": {
                    "logic": "or",
                    "conditions": [
                        {"indicator_type": "rsi", "operator": "<", "target_value": "30", "timeframe": "D", "period": 14},
                        {"indicator_type": "rsi", "operator": ">", "target_value": "70", "timeframe": "D", "period": 14},
                    ],
                },
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()["data"]
        assert data["condition_group"]["logic"] == "or"
        assert len(data["condition_group"]["conditions"]) == 2

    @pytest.mark.asyncio
    async def test_get_subscription_with_condition_group(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test retrieving subscription preserves condition_group"""
        # Create with condition_group
        create_response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "title": "Price + KD Signal",
                "message": "Trigger when price > 500 AND KD < 20",
                "signal_type": "buy",
                "condition_group": {
                    "logic": "and",
                    "conditions": [
                        {"indicator_type": "price", "operator": ">", "target_value": "500", "timeframe": "D"},
                        {"indicator_type": "kd", "operator": "<", "target_value": "20", "timeframe": "D"},
                    ],
                },
            },
            headers=auth_headers,
        )
        subscription_id = create_response.json()["data"]["id"]

        # Get by ID
        get_response = await client.get(
            f"/subscriptions/{subscription_id}",
            headers=auth_headers,
        )

        assert get_response.status_code == 200
        data = get_response.json()["data"]
        assert data["condition_group"]["logic"] == "and"
        assert data["condition_group"]["conditions"][0]["indicator_type"] == "price"
        assert data["condition_group"]["conditions"][1]["indicator_type"] == "kd"

    @pytest.mark.asyncio
    async def test_update_condition_group(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test updating subscription's condition_group"""
        # Create with single condition
        create_response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "title": "RSI Signal",
                "message": "Trigger when RSI < 30",
                "signal_type": "buy",
                "condition_group": {
                    "logic": "and",
                    "conditions": [
                        {"indicator_type": "rsi", "operator": "<", "target_value": "30", "timeframe": "D", "period": 14},
                    ],
                },
            },
            headers=auth_headers,
        )
        subscription_id = create_response.json()["data"]["id"]

        # Update to add more conditions
        update_response = await client.patch(
            f"/subscriptions/{subscription_id}",
            json={
                "condition_group": {
                    "logic": "and",
                    "conditions": [
                        {"indicator_type": "rsi", "operator": "<", "target_value": "30", "timeframe": "D", "period": 14},
                        {"indicator_type": "macd", "operator": ">", "target_value": "0", "timeframe": "D"},
                    ],
                },
            },
            headers=auth_headers,
        )

        assert update_response.status_code == 200
        data = update_response.json()["data"]
        assert data["condition_group"]["logic"] == "and"
        assert len(data["condition_group"]["conditions"]) == 2

    @pytest.mark.asyncio
    async def test_list_subscriptions_with_condition_groups(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test listing subscriptions preserves condition_group data"""
        # Create multiple subscriptions
        await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "title": "Complex Signal",
                "message": "Multi-condition",
                "signal_type": "buy",
                "condition_group": {
                    "logic": "and",
                    "conditions": [
                        {"indicator_type": "price", "operator": ">", "target_value": "500", "timeframe": "D"},
                        {"indicator_type": "rsi", "operator": "<", "target_value": "30", "timeframe": "D", "period": 14},
                    ],
                },
            },
            headers=auth_headers,
        )

        await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "title": "Simple Signal",
                "message": "Single condition",
                "signal_type": "sell",
                "condition_group": {
                    "logic": "and",
                    "conditions": [
                        {"indicator_type": "rsi", "operator": ">", "target_value": "70", "timeframe": "D", "period": 14},
                    ],
                },
            },
            headers=auth_headers,
        )

        # List all subscriptions
        response = await client.get("/subscriptions", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["data"]) == 2

        # Both should have condition_group
        for sub in data["data"]:
            assert sub["condition_group"]["logic"] == "and"
            assert len(sub["condition_group"]["conditions"]) >= 1

    @pytest.mark.asyncio
    async def test_condition_group_with_different_indicator_types(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test condition_group with all supported indicator types"""
        response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "title": "All Indicators",
                "message": "Test all indicator types",
                "signal_type": "buy",
                "condition_group": {
                    "logic": "and",
                    "conditions": [
                        {"indicator_type": "price", "operator": ">", "target_value": "500", "timeframe": "D"},
                        {"indicator_type": "rsi", "operator": "<", "target_value": "30", "timeframe": "D", "period": 14},
                        {"indicator_type": "sma", "operator": "<", "target_value": "480", "timeframe": "D", "period": 20},
                        {"indicator_type": "macd", "operator": ">", "target_value": "0", "timeframe": "D"},
                        {"indicator_type": "kd", "operator": "<", "target_value": "20", "timeframe": "D"},
                    ],
                },
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()["data"]
        conditions = data["condition_group"]["conditions"]
        indicator_types = [c["indicator_type"] for c in conditions]
        assert "price" in indicator_types
        assert "rsi" in indicator_types
        assert "sma" in indicator_types
        assert "macd" in indicator_types
        assert "kd" in indicator_types

    @pytest.mark.asyncio
    async def test_condition_group_with_all_operators(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test condition_group with all supported operators"""
        operators = ["<", ">", "<=", ">=", "==", "!="]

        for op in operators:
            response = await client.post(
                "/subscriptions",
                json={
                    "stock_id": stock_id,
                    "title": f"Test {op}",
                    "message": f"Test operator {op}",
                    "signal_type": "buy",
                    "condition_group": {
                        "logic": "and",
                        "conditions": [
                            {"indicator_type": "rsi", "operator": op, "target_value": "50", "timeframe": "D", "period": 14},
                        ],
                    },
                },
                headers=auth_headers,
            )

            assert response.status_code == 201
            data = response.json()["data"]
            assert data["condition_group"]["conditions"][0]["operator"] == op

    @pytest.mark.asyncio
    async def test_condition_group_preserves_decimal_values(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test condition_group preserves decimal precision"""
        response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "title": "Decimal Test",
                "message": "Test decimal precision",
                "signal_type": "buy",
                "condition_group": {
                    "logic": "and",
                    "conditions": [
                        {"indicator_type": "rsi", "operator": "<", "target_value": "29.5678", "timeframe": "D", "period": 14},
                    ],
                },
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()["data"]
        assert str(data["condition_group"]["conditions"][0]["target_value"]) == "29.5678"

    @pytest.mark.asyncio
    async def test_delete_subscription_with_condition_group(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test deleting subscription with condition_group"""
        create_response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "title": "To Delete",
                "message": "Will be deleted",
                "signal_type": "buy",
                "condition_group": {
                    "logic": "and",
                    "conditions": [
                        {"indicator_type": "rsi", "operator": "<", "target_value": "30", "timeframe": "D", "period": 14},
                    ],
                },
            },
            headers=auth_headers,
        )
        subscription_id = create_response.json()["data"]["id"]

        # Delete
        delete_response = await client.delete(
            f"/subscriptions/{subscription_id}",
            headers=auth_headers,
        )

        assert delete_response.status_code == 200
        # Verify deleted
        get_response = await client.get(
            f"/subscriptions/{subscription_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_empty_conditions_array_rejected(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test condition_group with empty conditions array - should be rejected"""
        response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "title": "Empty Conditions",
                "message": "Should be rejected",
                "signal_type": "buy",
                "condition_group": {
                    "logic": "and",
                    "conditions": [],
                },
            },
            headers=auth_headers,
        )

        # Empty conditions should be rejected by validation (min_length=1)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_nested_condition_rejected(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test nested condition structure - should be rejected"""
        response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "title": "Nested",
                "message": "Should be rejected",
                "signal_type": "buy",
                "condition_group": {
                    "logic": "and",
                    "conditions": [
                        {
                            "logic": "or",
                            "conditions": [
                                {"indicator_type": "rsi", "operator": "<", "target_value": "30"},
                                {"indicator_type": "kd", "operator": "<", "target_value": "20"},
                            ],
                        },
                    ],
                },
            },
            headers=auth_headers,
        )

        # Nested conditions should be rejected (Condition model requires indicator_type, operator, target_value)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_condition_group_rejected(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test missing condition_group - should be rejected"""
        response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "title": "No Conditions",
                "message": "Should be rejected",
                "signal_type": "buy",
            },
            headers=auth_headers,
        )

        # condition_group is required
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_max_conditions_limit(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test max 10 conditions limit"""
        conditions = [
            {"indicator_type": "price", "operator": ">", "target_value": str(500 + i), "timeframe": "D"}
            for i in range(11)
        ]

        response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "title": "Too Many Conditions",
                "message": "Should be rejected",
                "signal_type": "buy",
                "condition_group": {
                    "logic": "and",
                    "conditions": conditions,
                },
            },
            headers=auth_headers,
        )

        # More than 10 conditions should be rejected
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_period_validation_for_rsi_sma(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test period field validation for RSI/SMA"""
        # RSI with valid period
        response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "title": "RSI with period",
                "message": "RSI period 14",
                "signal_type": "buy",
                "condition_group": {
                    "logic": "and",
                    "conditions": [
                        {"indicator_type": "rsi", "operator": "<", "target_value": "30", "timeframe": "D", "period": 14},
                    ],
                },
            },
            headers=auth_headers,
        )
        assert response.status_code == 201

        # SMA with valid period
        response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "title": "SMA with period",
                "message": "SMA period 20",
                "signal_type": "buy",
                "condition_group": {
                    "logic": "and",
                    "conditions": [
                        {"indicator_type": "sma", "operator": ">", "target_value": "500", "timeframe": "D", "period": 20},
                    ],
                },
            },
            headers=auth_headers,
        )
        assert response.status_code == 201

        # MACD with period should be rejected
        response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "title": "MACD with period",
                "message": "Should be rejected",
                "signal_type": "buy",
                "condition_group": {
                    "logic": "and",
                    "conditions": [
                        {"indicator_type": "macd", "operator": ">", "target_value": "0", "timeframe": "D", "period": 14},
                    ],
                },
            },
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_timeframe_validation(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test timeframe field validation (D or W)"""
        # Daily timeframe
        response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "title": "Daily",
                "message": "Daily timeframe",
                "signal_type": "buy",
                "condition_group": {
                    "logic": "and",
                    "conditions": [
                        {"indicator_type": "rsi", "operator": "<", "target_value": "30", "timeframe": "D", "period": 14},
                    ],
                },
            },
            headers=auth_headers,
        )
        assert response.status_code == 201

        # Weekly timeframe
        response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "title": "Weekly",
                "message": "Weekly timeframe",
                "signal_type": "buy",
                "condition_group": {
                    "logic": "and",
                    "conditions": [
                        {"indicator_type": "rsi", "operator": "<", "target_value": "30", "timeframe": "W", "period": 14},
                    ],
                },
            },
            headers=auth_headers,
        )
        assert response.status_code == 201

        # Invalid timeframe should be rejected
        response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "title": "Invalid Timeframe",
                "message": "Should be rejected",
                "signal_type": "buy",
                "condition_group": {
                    "logic": "and",
                    "conditions": [
                        {"indicator_type": "rsi", "operator": "<", "target_value": "30", "timeframe": "M", "period": 14},
                    ],
                },
            },
            headers=auth_headers,
        )
        assert response.status_code == 422