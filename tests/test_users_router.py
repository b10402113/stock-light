import pytest
from httpx import AsyncClient


class TestAuthRouter:
    """Tests for auth router endpoints"""

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        """Test successful registration via API"""
        response = await client.post(
            "/auth/register",
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
            "/auth/register",
            json={"email": "test@example.com", "password": "password123"},
        )

        # Second registration with same email
        response = await client.post(
            "/auth/register",
            json={"email": "test@example.com", "password": "password456"},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["code"] == 201  # USER_ALREADY_EXISTS error code

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        """Test registration with invalid email format"""
        response = await client.post(
            "/auth/register",
            json={"email": "invalid-email", "password": "password123"},
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_short_password(self, client: AsyncClient):
        """Test registration with password too short"""
        response = await client.post(
            "/auth/register",
            json={"email": "test@example.com", "password": "short"},
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_missing_fields(self, client: AsyncClient):
        """Test registration with missing required fields"""
        response = await client.post(
            "/auth/register",
            json={"email": "test@example.com"},
        )

        assert response.status_code == 422  # Validation error


class TestLoginRouter:
    """Tests for login endpoint"""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient):
        """Test successful login"""
        # Register user first
        await client.post(
            "/auth/register",
            json={"email": "test@example.com", "password": "password123"},
        )

        # Login
        response = await client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["message"] == "success"
        assert data["data"]["access_token"] is not None
        assert len(data["data"]["access_token"]) > 0
        assert data["data"]["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient):
        """Test login with wrong password"""
        # Register user
        await client.post(
            "/auth/register",
            json={"email": "test@example.com", "password": "password123"},
        )

        # Login with wrong password
        response = await client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "wrongpassword"},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["code"] == 100  # UNAUTHORIZED error code

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with nonexistent user"""
        response = await client.post(
            "/auth/login",
            json={"email": "nonexistent@example.com", "password": "password123"},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["code"] == 100  # UNAUTHORIZED error code

    @pytest.mark.asyncio
    async def test_login_invalid_email(self, client: AsyncClient):
        """Test login with invalid email format"""
        response = await client.post(
            "/auth/login",
            json={"email": "invalid-email", "password": "password123"},
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_login_short_password(self, client: AsyncClient):
        """Test login with password too short"""
        response = await client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "short"},
        )

        assert response.status_code == 422  # Validation error


class TestUsersRouter:
    """Tests for users router endpoints"""

    @pytest.mark.asyncio
    async def test_get_current_user(self, client: AsyncClient):
        """Test getting current user info"""
        # Register and login
        await client.post(
            "/auth/register",
            json={"email": "test@example.com", "password": "password123"},
        )
        login_response = await client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        # Get current user
        response = await client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["email"] == "test@example.com"
        assert data["data"]["is_active"] is True

    @pytest.mark.asyncio
    async def test_get_current_user_without_token(self, client: AsyncClient):
        """Test getting current user without token"""
        response = await client.get("/users/me")

        assert response.status_code == 400
        data = response.json()
        assert data["code"] == 100  # UNAUTHORIZED error code
