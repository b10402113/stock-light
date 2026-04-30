import pytest
from httpx import AsyncClient


class TestUsersRouter:
    """Tests for users router endpoints"""

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        """Test successful registration via API"""
        response = await client.post(
            "/users/register",
            json={"email": "test@example.com", "password": "password123"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["code"] == 0
        assert data["message"] == "success"
        assert data["data"]["email"] == "test@example.com"
        assert data["data"]["is_active"] is True
        assert "hashed_password" not in data["data"]

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient):
        """Test registration with duplicate email"""
        # First registration
        await client.post(
            "/users/register",
            json={"email": "test@example.com", "password": "password123"},
        )

        # Second registration with same email
        response = await client.post(
            "/users/register",
            json={"email": "test@example.com", "password": "password456"},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["code"] == 201  # USER_ALREADY_EXISTS error code

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        """Test registration with invalid email format"""
        response = await client.post(
            "/users/register",
            json={"email": "invalid-email", "password": "password123"},
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_short_password(self, client: AsyncClient):
        """Test registration with password too short"""
        response = await client.post(
            "/users/register",
            json={"email": "test@example.com", "password": "short"},
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_missing_fields(self, client: AsyncClient):
        """Test registration with missing required fields"""
        response = await client.post(
            "/users/register",
            json={"email": "test@example.com"},
        )

        assert response.status_code == 422  # Validation error
