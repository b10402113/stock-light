"""Tests for compound_condition functionality in indicator subscriptions."""

import pytest
from httpx import AsyncClient


class TestCompoundCondition:
    """Tests for compound_condition field in IndicatorSubscription"""

    @pytest.fixture
    async def auth_headers(self, client: AsyncClient) -> dict[str, str]:
        """Create authenticated user and return headers with token"""
        await client.post(
            "/auth/register",
            json={"email": "compound_test@example.com", "password": "password123"},
        )
        login_response = await client.post(
            "/auth/login",
            json={"email": "compound_test@example.com", "password": "password123"},
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
    async def test_create_with_single_compound_condition(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test creating subscription with one additional condition (AND logic)"""
        response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "title": "Price + RSI Buy Signal",
                "message": "Trigger when price > 500 AND RSI < 30",
                "signal_type": "buy",
                "indicator_type": "price",
                "operator": ">",
                "target_value": "500.0",
                "compound_condition": {
                    "logic": "and",
                    "conditions": [
                        {"indicator_type": "rsi", "operator": "<", "target_value": "30"},
                    ],
                },
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()["data"]
        assert data["compound_condition"]["logic"] == "and"
        assert len(data["compound_condition"]["conditions"]) == 1
        assert data["compound_condition"]["conditions"][0]["indicator_type"] == "rsi"
        assert data["compound_condition"]["conditions"][0]["operator"] == "<"
        assert data["compound_condition"]["conditions"][0]["target_value"] == "30"

    @pytest.mark.asyncio
    async def test_create_with_multiple_compound_conditions(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test creating subscription with multiple additional conditions (AND logic)"""
        response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "title": "Complex Buy Signal",
                "message": "Trigger when price > 500 AND RSI < 30 AND MACD > 0",
                "signal_type": "buy",
                "indicator_type": "price",
                "operator": ">",
                "target_value": "500.0",
                "compound_condition": {
                    "logic": "and",
                    "conditions": [
                        {"indicator_type": "rsi", "operator": "<", "target_value": "30"},
                        {"indicator_type": "macd", "operator": ">", "target_value": "0"},
                    ],
                },
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()["data"]
        assert data["compound_condition"]["logic"] == "and"
        assert len(data["compound_condition"]["conditions"]) == 2
        assert data["compound_condition"]["conditions"][0]["indicator_type"] == "rsi"
        assert data["compound_condition"]["conditions"][1]["indicator_type"] == "macd"

    @pytest.mark.asyncio
    async def test_create_with_or_logic(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test creating subscription with OR logic compound condition"""
        response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "title": "Either Condition Signal",
                "message": "Trigger when RSI < 30 OR RSI > 70",
                "signal_type": "sell",
                "indicator_type": "rsi",
                "operator": "<",
                "target_value": "30.0",
                "compound_condition": {
                    "logic": "or",
                    "conditions": [
                        {"indicator_type": "rsi", "operator": ">", "target_value": "70"},
                    ],
                },
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()["data"]
        assert data["compound_condition"]["logic"] == "or"
        assert len(data["compound_condition"]["conditions"]) == 1

    @pytest.mark.asyncio
    async def test_create_without_compound_condition(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test creating subscription without compound_condition (simple condition)"""
        response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "indicator_type": "rsi",
                "operator": "<",
                "target_value": "30.0",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()["data"]
        assert data["compound_condition"] is None

    @pytest.mark.asyncio
    async def test_create_with_null_compound_condition(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test creating subscription with explicit null compound_condition"""
        response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "indicator_type": "rsi",
                "operator": "<",
                "target_value": "30.0",
                "compound_condition": None,
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()["data"]
        assert data["compound_condition"] is None

    @pytest.mark.asyncio
    async def test_get_subscription_with_compound_condition(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test retrieving subscription preserves compound_condition"""
        # Create with compound condition
        create_response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "indicator_type": "price",
                "operator": ">",
                "target_value": "500.0",
                "compound_condition": {
                    "logic": "and",
                    "conditions": [
                        {"indicator_type": "kd", "operator": "<", "target_value": "20"},
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
        assert data["compound_condition"]["logic"] == "and"
        assert data["compound_condition"]["conditions"][0]["indicator_type"] == "kd"

    @pytest.mark.asyncio
    async def test_update_compound_condition(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test updating subscription's compound_condition"""
        # Create without compound condition
        create_response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "indicator_type": "rsi",
                "operator": "<",
                "target_value": "30.0",
            },
            headers=auth_headers,
        )
        subscription_id = create_response.json()["data"]["id"]

        # Update to add compound condition
        update_response = await client.patch(
            f"/subscriptions/{subscription_id}",
            json={
                "compound_condition": {
                    "logic": "and",
                    "conditions": [
                        {"indicator_type": "macd", "operator": ">", "target_value": "0"},
                    ],
                },
            },
            headers=auth_headers,
        )

        assert update_response.status_code == 200
        data = update_response.json()["data"]
        assert data["compound_condition"]["logic"] == "and"
        assert len(data["compound_condition"]["conditions"]) == 1

    @pytest.mark.asyncio
    async def test_remove_compound_condition(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test removing compound_condition by setting to null"""
        # Create with compound condition
        create_response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "indicator_type": "price",
                "operator": ">",
                "target_value": "500.0",
                "compound_condition": {
                    "logic": "and",
                    "conditions": [
                        {"indicator_type": "rsi", "operator": "<", "target_value": "30"},
                    ],
                },
            },
            headers=auth_headers,
        )
        subscription_id = create_response.json()["data"]["id"]

        # Update to remove compound condition
        update_response = await client.patch(
            f"/subscriptions/{subscription_id}",
            json={"compound_condition": None},
            headers=auth_headers,
        )

        assert update_response.status_code == 200
        data = update_response.json()["data"]
        assert data["compound_condition"] is None

    @pytest.mark.asyncio
    async def test_list_subscriptions_with_compound_conditions(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test listing subscriptions preserves compound_condition data"""
        # Create multiple subscriptions with different compound conditions
        await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "indicator_type": "price",
                "operator": ">",
                "target_value": "500.0",
                "compound_condition": {
                    "logic": "and",
                    "conditions": [
                        {"indicator_type": "rsi", "operator": "<", "target_value": "30"},
                    ],
                },
            },
            headers=auth_headers,
        )

        await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "indicator_type": "rsi",
                "operator": ">",
                "target_value": "70.0",
                "compound_condition": None,
            },
            headers=auth_headers,
        )

        # List all subscriptions
        response = await client.get("/subscriptions", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["data"]) == 2

        # First should have compound_condition
        sub_with_condition = data["data"][0]
        assert sub_with_condition["compound_condition"]["logic"] == "and"

        # Second should have null compound_condition
        sub_without_condition = data["data"][1]
        assert sub_without_condition["compound_condition"] is None

    @pytest.mark.asyncio
    async def test_compound_condition_with_different_indicator_types(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test compound_condition with all supported indicator types"""
        response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "indicator_type": "price",
                "operator": ">",
                "target_value": "500.0",
                "compound_condition": {
                    "logic": "and",
                    "conditions": [
                        {"indicator_type": "rsi", "operator": "<", "target_value": "30"},
                        {"indicator_type": "macd", "operator": ">", "target_value": "0"},
                        {"indicator_type": "kd", "operator": "<", "target_value": "20"},
                        {"indicator_type": "price", "operator": ">=", "target_value": "480"},
                    ],
                },
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()["data"]
        conditions = data["compound_condition"]["conditions"]
        indicator_types = [c["indicator_type"] for c in conditions]
        assert "rsi" in indicator_types
        assert "macd" in indicator_types
        assert "kd" in indicator_types
        assert "price" in indicator_types

    @pytest.mark.asyncio
    async def test_compound_condition_with_all_operators(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test compound_condition with all supported operators"""
        operators = ["<", ">", "<=", ">=", "==", "!="]

        for i, op in enumerate(operators):
            response = await client.post(
                "/subscriptions",
                json={
                    "stock_id": stock_id,
                    "indicator_type": "rsi",
                    "operator": "<",
                    "target_value": str(30.0 + i),
                    "compound_condition": {
                        "logic": "and",
                        "conditions": [
                            {"indicator_type": "rsi", "operator": op, "target_value": str(50.0 + i)},
                        ],
                    },
                },
                headers=auth_headers,
            )

            assert response.status_code == 201
            data = response.json()["data"]
            assert data["compound_condition"]["conditions"][0]["operator"] == op

    @pytest.mark.asyncio
    async def test_compound_condition_preserves_decimal_values(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test compound_condition preserves decimal precision"""
        response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "indicator_type": "price",
                "operator": ">",
                "target_value": "500.1234",
                "compound_condition": {
                    "logic": "and",
                    "conditions": [
                        {"indicator_type": "rsi", "operator": "<", "target_value": "29.5678"},
                    ],
                },
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()["data"]
        # Note: target_value in conditions is stored as string in JSON
        assert data["compound_condition"]["conditions"][0]["target_value"] == "29.5678"

    @pytest.mark.asyncio
    async def test_delete_subscription_with_compound_condition(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test deleting subscription with compound_condition"""
        create_response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "indicator_type": "price",
                "operator": ">",
                "target_value": "500.0",
                "compound_condition": {
                    "logic": "and",
                    "conditions": [
                        {"indicator_type": "rsi", "operator": "<", "target_value": "30"},
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
    async def test_empty_conditions_array(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test compound_condition with empty conditions array - should be rejected"""
        response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "indicator_type": "rsi",
                "operator": "<",
                "target_value": "30.0",
                "compound_condition": {
                    "logic": "and",
                    "conditions": [],
                },
            },
            headers=auth_headers,
        )

        # Empty conditions should be rejected by validation (min_length=1)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_nested_compound_condition(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test nested compound_condition - should be rejected (Condition model doesn't support nesting)"""
        response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "indicator_type": "price",
                "operator": ">",
                "target_value": "500.0",
                "compound_condition": {
                    "logic": "and",
                    "conditions": [
                        {
                            "logic": "or",
                            "conditions": [
                                {"indicator_type": "rsi", "operator": "<", "target_value": "30"},
                                {"indicator_type": "kd", "operator": "<", "target_value": "20"},
                            ],
                        },
                        {"indicator_type": "macd", "operator": ">", "target_value": "0"},
                    ],
                },
            },
            headers=auth_headers,
        )

        # Nested compound conditions should be rejected (Condition model requires indicator_type, operator, target_value)
        assert response.status_code == 422