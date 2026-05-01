"""Tests for stocks router endpoints."""

import pytest
from httpx import AsyncClient


class TestStocksRouter:
    """Tests for stocks router endpoints"""

    @pytest.mark.asyncio
    async def test_create_stock_success(self, client: AsyncClient):
        """Test successful stock creation"""
        response = await client.post(
            "/stocks",
            json={
                "symbol": "2330.TW",
                "name": "台積電",
                "current_price": "650.00",
                "is_active": True,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["code"] == 0
        assert data["message"] == "success"
        assert data["data"]["symbol"] == "2330.TW"
        assert data["data"]["name"] == "台積電"
        assert data["data"]["current_price"] == "650.00"
        assert data["data"]["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_stock_duplicate_symbol(self, client: AsyncClient):
        """Test creating stock with duplicate symbol"""
        # First creation
        await client.post(
            "/stocks",
            json={
                "symbol": "2330.TW",
                "name": "台積電",
            },
        )

        # Second creation with same symbol
        response = await client.post(
            "/stocks",
            json={
                "symbol": "2330.TW",
                "name": "台積電2",
            },
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_stock_invalid_symbol_format(self, client: AsyncClient):
        """Test creating stock with invalid symbol format"""
        response = await client.post(
            "/stocks",
            json={
                "symbol": "INVALID",
                "name": "Invalid Stock",
            },
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_create_stock_missing_required_fields(self, client: AsyncClient):
        """Test creating stock with missing required fields"""
        response = await client.post(
            "/stocks",
            json={"symbol": "2330.TW"},
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_stock_success(self, client: AsyncClient):
        """Test getting a single stock"""
        # Create stock first
        await client.post(
            "/stocks",
            json={
                "symbol": "2330.TW",
                "name": "台積電",
            },
        )

        # Get stock
        response = await client.get("/stocks/2330.TW")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["symbol"] == "2330.TW"
        assert data["data"]["name"] == "台積電"

    @pytest.mark.asyncio
    async def test_get_stock_not_found(self, client: AsyncClient):
        """Test getting non-existent stock"""
        response = await client.get("/stocks/9999.TW")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_stocks(self, client: AsyncClient):
        """Test listing stocks"""
        # Create multiple stocks
        await client.post(
            "/stocks",
            json={"symbol": "2330.TW", "name": "台積電"},
        )
        await client.post(
            "/stocks",
            json={"symbol": "2317.TW", "name": "鴻海"},
        )

        # List stocks
        response = await client.get("/stocks")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]["data"]) == 2
        assert data["data"]["has_more"] is False
        assert data["data"]["next_cursor"] is None

    @pytest.mark.asyncio
    async def test_list_stocks_with_pagination(self, client: AsyncClient):
        """Test listing stocks with keyset pagination"""
        # Create multiple stocks
        for i in range(5):
            await client.post(
                "/stocks",
                json={"symbol": f"{2330 + i}.TW", "name": f"股票{i}"},
            )

        # List stocks with limit
        response = await client.get("/stocks?limit=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["data"]) == 2
        assert data["data"]["has_more"] is True
        assert data["data"]["next_cursor"] is not None

        # Get next page using cursor
        cursor = data["data"]["next_cursor"]
        response2 = await client.get(f"/stocks?limit=2&cursor={cursor}")

        assert response2.status_code == 200
        data2 = response2.json()
        assert len(data2["data"]["data"]) == 2

    @pytest.mark.asyncio
    async def test_list_stocks_filter_active(self, client: AsyncClient):
        """Test listing stocks with active filter"""
        # Create stocks
        await client.post(
            "/stocks",
            json={"symbol": "2330.TW", "name": "台積電", "is_active": True},
        )
        await client.post(
            "/stocks",
            json={"symbol": "2317.TW", "name": "鴻海", "is_active": False},
        )

        # List active stocks only
        response = await client.get("/stocks?is_active=true")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["data"]) == 1
        assert data["data"]["data"][0]["symbol"] == "2330.TW"

    @pytest.mark.asyncio
    async def test_update_stock_success(self, client: AsyncClient):
        """Test updating a stock"""
        # Create stock first
        await client.post(
            "/stocks",
            json={"symbol": "2330.TW", "name": "台積電"},
        )

        # Update stock
        response = await client.patch(
            "/stocks/2330.TW",
            json={"name": "台灣積體電路", "current_price": "700.00"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["name"] == "台灣積體電路"
        assert data["data"]["current_price"] == "700.00"

    @pytest.mark.asyncio
    async def test_update_stock_not_found(self, client: AsyncClient):
        """Test updating non-existent stock"""
        response = await client.patch(
            "/stocks/9999.TW",
            json={"name": "Non-existent"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_stock_success(self, client: AsyncClient):
        """Test soft deleting a stock"""
        # Create stock first
        await client.post(
            "/stocks",
            json={"symbol": "2330.TW", "name": "台積電"},
        )

        # Delete stock
        response = await client.delete("/stocks/2330.TW")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

        # Verify stock is deleted (not found)
        get_response = await client.get("/stocks/2330.TW")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_stock_not_found(self, client: AsyncClient):
        """Test deleting non-existent stock"""
        response = await client.delete("/stocks/9999.TW")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_search_stocks_by_symbol(self, client: AsyncClient):
        """Test searching stocks by symbol"""
        # Create stocks
        await client.post(
            "/stocks",
            json={"symbol": "2330.TW", "name": "台積電"},
        )
        await client.post(
            "/stocks",
            json={"symbol": "2317.TW", "name": "鴻海"},
        )
        await client.post(
            "/stocks",
            json={"symbol": "2454.TW", "name": "聯發科"},
        )

        # Search by partial symbol
        response = await client.get("/stocks/search?q=233")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]["data"]) == 1
        assert data["data"]["data"][0]["symbol"] == "2330.TW"

    @pytest.mark.asyncio
    async def test_search_stocks_by_name(self, client: AsyncClient):
        """Test searching stocks by name"""
        # Create stocks
        await client.post(
            "/stocks",
            json={"symbol": "2330.TW", "name": "台積電"},
        )
        await client.post(
            "/stocks",
            json={"symbol": "2317.TW", "name": "鴻海"},
        )

        # Search by partial name
        response = await client.get("/stocks/search?q=台積")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]["data"]) == 1
        assert data["data"]["data"][0]["name"] == "台積電"

    @pytest.mark.asyncio
    async def test_search_stocks_case_insensitive(self, client: AsyncClient):
        """Test case-insensitive search"""
        # Create stock
        await client.post(
            "/stocks",
            json={"symbol": "2330.TW", "name": "台積電"},
        )

        # Search with lowercase
        response = await client.get("/stocks/search?q=tw")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["data"]) == 1
        assert data["data"]["data"][0]["symbol"] == "2330.TW"

    @pytest.mark.asyncio
    async def test_search_stocks_no_results(self, client: AsyncClient):
        """Test search with no matching results"""
        # Create stock
        await client.post(
            "/stocks",
            json={"symbol": "2330.TW", "name": "台積電"},
        )

        # Search with non-matching query
        response = await client.get("/stocks/search?q=AAPL")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]["data"]) == 0
        assert data["data"]["has_more"] is False

    @pytest.mark.asyncio
    async def test_search_stocks_with_pagination(self, client: AsyncClient):
        """Test search with keyset pagination"""
        # Create multiple stocks with similar symbols
        for i in range(5):
            await client.post(
                "/stocks",
                json={"symbol": f"{2330 + i}.TW", "name": f"股票{i}"},
            )

        # Search with limit
        response = await client.get("/stocks/search?q=23&limit=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["data"]) == 2
        assert data["data"]["has_more"] is True
        assert data["data"]["next_cursor"] is not None

        # Get next page
        cursor = data["data"]["next_cursor"]
        response2 = await client.get(f"/stocks/search?q=23&limit=2&cursor={cursor}")

        assert response2.status_code == 200
        data2 = response2.json()
        assert len(data2["data"]["data"]) == 2

    @pytest.mark.asyncio
    async def test_search_stocks_multiple_matches(self, client: AsyncClient):
        """Test search returning multiple matches"""
        # Create stocks
        await client.post(
            "/stocks",
            json={"symbol": "2330.TW", "name": "台積電"},
        )
        await client.post(
            "/stocks",
            json={"symbol": "2317.TW", "name": "鴻海"},
        )
        await client.post(
            "/stocks",
            json={"symbol": "2454.TW", "name": "聯發科"},
        )

        # Search that matches multiple stocks
        response = await client.get("/stocks/search?q=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["data"]) == 3
