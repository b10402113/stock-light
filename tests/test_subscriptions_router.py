"""Tests for subscriptions router endpoints."""

import pytest
from httpx import AsyncClient


class TestSubscriptionsRouter:
    """Tests for subscriptions router endpoints"""

    @pytest.fixture
    async def auth_headers(self, client: AsyncClient) -> dict[str, str]:
        """Create authenticated user and return headers with token"""
        # Register user
        await client.post(
            "/auth/register",
            json={"email": "test@example.com", "password": "password123"},
        )

        # Login to get token
        login_response = await client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "password123"},
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
    async def test_create_subscription_success(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test successful subscription creation"""
        response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "title": "RSI Buy Signal",
                "message": "2330 RSI below 30",
                "signal_type": "buy",
                "indicator_type": "rsi",
                "operator": "<",
                "target_value": "30.0",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["stock"]["id"] == stock_id
        assert data["data"]["stock"]["symbol"] == "2330.TW"
        assert data["data"]["stock"]["name"] == "台積電"
        assert data["data"]["subscription_type"] == "indicator"
        assert data["data"]["title"] == "RSI Buy Signal"
        assert data["data"]["message"] == "2330 RSI below 30"
        assert data["data"]["signal_type"] == "buy"
        assert data["data"]["indicator_type"] == "rsi"
        assert data["data"]["operator"] == "<"
        assert data["data"]["target_value"] == "30.0000"
        assert data["data"]["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_subscription_missing_auth(self, client: AsyncClient, stock_id: int):
        """Test creating subscription without authentication"""
        response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "indicator_type": "rsi",
                "operator": "<",
                "target_value": "30.0",
            },
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_subscription_invalid_indicator_type(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test creating subscription with invalid indicator type"""
        response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "indicator_type": "invalid_type",
                "operator": "<",
                "target_value": "30.0",
            },
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_subscription_invalid_operator(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test creating subscription with invalid operator"""
        response = await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "indicator_type": "rsi",
                "operator": "invalid",
                "target_value": "30.0",
            },
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_subscription_invalid_stock(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test creating subscription with non-existent stock"""
        response = await client.post(
            "/subscriptions",
            json={
                "stock_id": 999,
                "indicator_type": "rsi",
                "operator": "<",
                "target_value": "30.0",
            },
            headers=auth_headers,
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_subscription_duplicate(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test creating duplicate subscription"""
        # Create first subscription
        await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "indicator_type": "rsi",
                "operator": "<",
                "target_value": "30.0",
            },
            headers=auth_headers,
        )

        # Try to create duplicate
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

        # Should fail due to unique constraint (indicator, operator, value)
        assert response.status_code == 400 or response.status_code == 409

    @pytest.mark.asyncio
    async def test_list_subscriptions(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test listing user's subscriptions"""
        # Create multiple subscriptions
        await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "indicator_type": "rsi",
                "operator": "<",
                "target_value": "30.0",
            },
            headers=auth_headers,
        )
        await client.post(
            "/subscriptions",
            json={
                "stock_id": stock_id,
                "indicator_type": "price",
                "operator": ">",
                "target_value": "500.0",
            },
            headers=auth_headers,
        )

        response = await client.get("/subscriptions", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]["data"]) == 2
        assert data["data"]["has_more"] is False
        # Check stock details are included
        assert data["data"]["data"][0]["stock"]["symbol"] == "2330.TW"

    @pytest.mark.asyncio
    async def test_list_subscriptions_pagination(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test subscription list pagination"""
        # Create 5 subscriptions (different indicators to avoid duplicate)
        indicators = ["rsi", "macd", "kd", "price", "rsi"]
        operators = ["<", ">", ">=", "<=", "=="]
        for i in range(5):
            await client.post(
                "/subscriptions",
                json={
                    "stock_id": stock_id,
                    "indicator_type": indicators[i],
                    "operator": operators[i],
                    "target_value": str(30.0 + i),
                },
                headers=auth_headers,
            )

        # Get first page (limit 2)
        response = await client.get("/subscriptions?limit=2", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["data"]) == 2
        assert data["data"]["has_more"] is True
        next_cursor = data["data"]["next_cursor"]

        # Get second page
        response2 = await client.get(
            f"/subscriptions?limit=2&cursor={next_cursor}",
            headers=auth_headers,
        )

        assert response2.status_code == 200
        data2 = response2.json()
        assert len(data2["data"]["data"]) == 2

    @pytest.mark.asyncio
    async def test_get_subscription_success(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test getting a single subscription"""
        # Create subscription
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

        response = await client.get(
            f"/subscriptions/{subscription_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["indicator_type"] == "rsi"
        assert data["data"]["stock"]["id"] == stock_id

    @pytest.mark.asyncio
    async def test_get_subscription_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test getting non-existent subscription"""
        response = await client.get("/subscriptions/999", headers=auth_headers)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_subscription_success(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test updating a subscription"""
        # Create subscription
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

        # Update subscription
        response = await client.patch(
            f"/subscriptions/{subscription_id}",
            json={"title": "Updated Title", "target_value": "25.0", "is_active": False},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["title"] == "Updated Title"
        assert data["data"]["target_value"] == "25.0000"
        assert data["data"]["is_active"] is False

    @pytest.mark.asyncio
    async def test_delete_subscription_success(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test soft deleting a subscription"""
        # Create subscription
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

        # Delete subscription
        response = await client.delete(
            f"/subscriptions/{subscription_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200

        # Verify subscription is deleted (not found)
        get_response = await client.get(
            f"/subscriptions/{subscription_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_subscription_with_compound_condition(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test creating subscription with compound condition"""
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
                    ],
                },
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["data"]["compound_condition"]["logic"] == "and"

    @pytest.mark.asyncio
    async def test_create_different_indicator_types(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test creating subscriptions with different indicator types"""
        indicator_types = ["rsi", "macd", "kd", "price"]

        for indicator_type in indicator_types:
            response = await client.post(
                "/subscriptions",
                json={
                    "stock_id": stock_id,
                    "indicator_type": indicator_type,
                    "operator": ">",
                    "target_value": "50.0",
                },
                headers=auth_headers,
            )

            assert response.status_code == 201
            assert response.json()["data"]["indicator_type"] == indicator_type

    @pytest.mark.asyncio
    async def test_create_different_operators(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test creating subscriptions with different operators"""
        operators = [">", "<", ">=", "<=", "==", "!="]

        for i, operator in enumerate(operators):
            response = await client.post(
                "/subscriptions",
                json={
                    "stock_id": stock_id,
                    "indicator_type": "rsi",
                    "operator": operator,
                    "target_value": str(50.0 + i),  # Different values to avoid duplicate
                },
                headers=auth_headers,
            )

            assert response.status_code == 201
            assert response.json()["data"]["operator"] == operator