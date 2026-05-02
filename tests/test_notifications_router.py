"""Tests for notification history router endpoints."""

import pytest
from datetime import datetime
from decimal import Decimal
from httpx import AsyncClient


class TestNotificationHistoryRouter:
    """Tests for notification history router endpoints"""

    @pytest.fixture
    async def auth_headers(self, client: AsyncClient) -> dict[str, str]:
        """Create authenticated user and return headers with token"""
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
    async def stock_id(self, client: AsyncClient) -> int:
        """Create a test stock and return its ID"""
        response = await client.post(
            "/stocks",
            json={"symbol": "2330.TW", "name": "台積電", "is_active": True},
        )
        return response.json()["data"]["id"]

    @pytest.fixture
    async def subscription_id(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ) -> int:
        """Create a test subscription and return its ID"""
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
        return response.json()["data"]["id"]

    @pytest.mark.asyncio
    async def test_list_notification_history_empty(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test listing notification history when empty"""
        response = await client.get("/notifications/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["data"] == []
        assert data["next_cursor"] is None
        assert data["has_more"] is False

    @pytest.mark.asyncio
    async def test_list_notification_history_missing_auth(
        self, client: AsyncClient
    ):
        """Test listing notification history without authentication"""
        response = await client.get("/notifications/history")
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_notification_history_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test getting non-existent notification history"""
        response = await client.get("/notifications/history/99999", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_notification_history_missing_auth(
        self, client: AsyncClient
    ):
        """Test getting notification history without authentication"""
        response = await client.get("/notifications/history/1")
        assert response.status_code == 400
