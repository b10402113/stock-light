"""Tests for watchlists router endpoints."""

import pytest
from httpx import AsyncClient


class TestWatchlistsRouter:
    """Tests for watchlists router endpoints"""

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
    async def test_create_watchlist_success(self, client: AsyncClient, auth_headers: dict):
        """Test successful watchlist creation"""
        response = await client.post(
            "/watchlists",
            json={"name": "My First Watchlist", "description": "Test description"},
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["name"] == "My First Watchlist"
        assert data["data"]["description"] == "Test description"
        assert data["data"]["is_default"] is True
        assert data["data"]["stock_count"] == 0

    @pytest.mark.asyncio
    async def test_create_watchlist_missing_auth(self, client: AsyncClient):
        """Test creating watchlist without authentication"""
        response = await client.post(
            "/watchlists",
            json={"name": "Test Watchlist"},
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_watchlist_missing_name(self, client: AsyncClient, auth_headers: dict):
        """Test creating watchlist without required name"""
        response = await client.post(
            "/watchlists",
            json={},
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_watchlists(self, client: AsyncClient, auth_headers: dict):
        """Test listing user's watchlists"""
        # Create multiple watchlists
        await client.post(
            "/watchlists",
            json={"name": "Watchlist 1"},
            headers=auth_headers,
        )
        await client.post(
            "/watchlists",
            json={"name": "Watchlist 2"},
            headers=auth_headers,
        )

        response = await client.get("/watchlists", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]) == 2

    @pytest.mark.asyncio
    async def test_get_watchlist_success(self, client: AsyncClient, auth_headers: dict):
        """Test getting a single watchlist"""
        # Create watchlist
        create_response = await client.post(
            "/watchlists",
            json={"name": "Test Watchlist"},
            headers=auth_headers,
        )
        watchlist_id = create_response.json()["data"]["id"]

        response = await client.get(f"/watchlists/{watchlist_id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "Test Watchlist"

    @pytest.mark.asyncio
    async def test_get_watchlist_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test getting non-existent watchlist"""
        response = await client.get("/watchlists/999", headers=auth_headers)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_watchlist_success(self, client: AsyncClient, auth_headers: dict):
        """Test updating a watchlist"""
        # Create watchlist
        create_response = await client.post(
            "/watchlists",
            json={"name": "Original Name"},
            headers=auth_headers,
        )
        watchlist_id = create_response.json()["data"]["id"]

        # Update watchlist
        response = await client.patch(
            f"/watchlists/{watchlist_id}",
            json={"name": "Updated Name", "description": "New description"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "Updated Name"
        assert data["data"]["description"] == "New description"

    @pytest.mark.asyncio
    async def test_delete_watchlist_success(self, client: AsyncClient, auth_headers: dict):
        """Test soft deleting a watchlist"""
        # Create watchlist
        create_response = await client.post(
            "/watchlists",
            json={"name": "To Be Deleted"},
            headers=auth_headers,
        )
        watchlist_id = create_response.json()["data"]["id"]

        # Delete watchlist
        response = await client.delete(f"/watchlists/{watchlist_id}", headers=auth_headers)

        assert response.status_code == 200

        # Verify watchlist is deleted (not found)
        get_response = await client.get(f"/watchlists/{watchlist_id}", headers=auth_headers)
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_add_stock_to_watchlist_success(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test adding a stock to watchlist"""
        # Create watchlist
        create_response = await client.post(
            "/watchlists",
            json={"name": "My Watchlist"},
            headers=auth_headers,
        )
        watchlist_id = create_response.json()["data"]["id"]

        # Add stock
        response = await client.post(
            f"/watchlists/{watchlist_id}/stocks",
            json={"stock_id": stock_id, "notes": "Good stock"},
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["data"]["stock_id"] == stock_id
        assert data["data"]["symbol"] == "2330.TW"
        assert data["data"]["notes"] == "Good stock"

    @pytest.mark.asyncio
    async def test_add_stock_to_watchlist_duplicate(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test adding duplicate stock to watchlist"""
        # Create watchlist
        create_response = await client.post(
            "/watchlists",
            json={"name": "My Watchlist"},
            headers=auth_headers,
        )
        watchlist_id = create_response.json()["data"]["id"]

        # Add stock first time
        await client.post(
            f"/watchlists/{watchlist_id}/stocks",
            json={"stock_id": stock_id},
            headers=auth_headers,
        )

        # Try to add same stock again
        response = await client.post(
            f"/watchlists/{watchlist_id}/stocks",
            json={"stock_id": stock_id},
            headers=auth_headers,
        )

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_add_stock_invalid_stock(self, client: AsyncClient, auth_headers: dict):
        """Test adding non-existent stock to watchlist"""
        # Create watchlist
        create_response = await client.post(
            "/watchlists",
            json={"name": "My Watchlist"},
            headers=auth_headers,
        )
        watchlist_id = create_response.json()["data"]["id"]

        # Try to add invalid stock
        response = await client.post(
            f"/watchlists/{watchlist_id}/stocks",
            json={"stock_id": 999},
            headers=auth_headers,
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_remove_stock_from_watchlist(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test removing stock from watchlist"""
        # Create watchlist
        create_response = await client.post(
            "/watchlists",
            json={"name": "My Watchlist"},
            headers=auth_headers,
        )
        watchlist_id = create_response.json()["data"]["id"]

        # Add stock
        await client.post(
            f"/watchlists/{watchlist_id}/stocks",
            json={"stock_id": stock_id},
            headers=auth_headers,
        )

        # Remove stock
        response = await client.delete(
            f"/watchlists/{watchlist_id}/stocks/{stock_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200

        # Verify stock is removed from watchlist detail
        detail_response = await client.get(f"/watchlists/{watchlist_id}", headers=auth_headers)
        assert len(detail_response.json()["data"]["stocks"]) == 0

    @pytest.mark.asyncio
    async def test_update_stock_in_watchlist(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test updating stock notes and sort order in watchlist"""
        # Create watchlist
        create_response = await client.post(
            "/watchlists",
            json={"name": "My Watchlist"},
            headers=auth_headers,
        )
        watchlist_id = create_response.json()["data"]["id"]

        # Add stock
        await client.post(
            f"/watchlists/{watchlist_id}/stocks",
            json={"stock_id": stock_id, "notes": "Original notes"},
            headers=auth_headers,
        )

        # Update stock
        response = await client.patch(
            f"/watchlists/{watchlist_id}/stocks/{stock_id}",
            json={"notes": "Updated notes", "sort_order": 5},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["notes"] == "Updated notes"
        assert data["data"]["sort_order"] == 5
