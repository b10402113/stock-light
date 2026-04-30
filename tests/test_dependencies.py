import pytest
from httpx import AsyncClient

from src.dependencies import get_current_user_id, get_current_user
from src.exceptions import BizException, ErrorCode
from src.users.schema import UserRegisterRequest
from src.users.service import UserService


class TestJWTDependencies:
    """Tests for JWT dependencies"""

    @pytest.mark.asyncio
    async def test_get_current_user_id_valid_token(self, client: AsyncClient):
        """Test extracting user_id from valid token"""
        # Register user
        await client.post(
            "/users/register",
            json={"email": "test@example.com", "password": "password123"},
        )

        # Login to get token
        login_response = await client.post(
            "/users/login",
            json={"email": "test@example.com", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        # Manually test the dependency function
        from src.main import app
        from src.database import get_db
        from tests.conftest import get_test_db

        app.dependency_overrides[get_db] = get_test_db

        user_id = await get_current_user_id(authorization=f"Bearer {token}")

        app.dependency_overrides.clear()

        assert user_id is not None
        assert isinstance(user_id, int)

    @pytest.mark.asyncio
    async def test_get_current_user_id_missing_header(self):
        """Test extracting user_id with missing Authorization header"""
        with pytest.raises(BizException) as exc_info:
            await get_current_user_id(authorization=None)

        assert exc_info.value.error_code == ErrorCode.UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_current_user_id_invalid_format(self):
        """Test extracting user_id with invalid header format"""
        with pytest.raises(BizException) as exc_info:
            await get_current_user_id(authorization="InvalidFormat")

        assert exc_info.value.error_code == ErrorCode.TOKEN_INVALID

    @pytest.mark.asyncio
    async def test_get_current_user_id_invalid_token(self):
        """Test extracting user_id with invalid token"""
        with pytest.raises(BizException) as exc_info:
            await get_current_user_id(authorization="Bearer invalidtoken")

        assert exc_info.value.error_code == ErrorCode.TOKEN_INVALID


class TestProtectedEndpoints:
    """Tests for protected endpoints using JWT dependencies"""

    @pytest.mark.asyncio
    async def test_protected_endpoint_with_valid_token(
        self, client: AsyncClient, db_session
    ):
        """Test accessing protected endpoint with valid token"""
        # Register user
        await client.post(
            "/users/register",
            json={"email": "test@example.com", "password": "password123"},
        )

        # Login to get token
        login_response = await client.post(
            "/users/login",
            json={"email": "test@example.com", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        # Use token to access protected endpoint (if one exists)
        # For now, we verify the token works by decoding it
        import jwt
        from src.config import settings

        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])

        assert "user_id" in payload
        assert "exp" in payload

    @pytest.mark.asyncio
    async def test_protected_endpoint_without_token(self, client: AsyncClient):
        """Test accessing protected endpoint without token"""
        # This would fail in a real protected endpoint
        # For now, we verify that missing token raises appropriate error
        with pytest.raises(BizException) as exc_info:
            await get_current_user_id(authorization=None)

        assert exc_info.value.error_code == ErrorCode.UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_current_user_success(self, db_session):
        """Test loading full user entity from valid token"""
        # Register user directly in database
        data = UserRegisterRequest(email="test@example.com", password="password123")
        user_response = await UserService.register(db_session, data)

        # Create token
        token = UserService._create_access_token(user_response.id)

        # Test get_current_user dependency
        user_id = await get_current_user_id(authorization=f"Bearer {token}")
        user = await get_current_user(user_id=user_id, db=db_session)

        assert user is not None
        assert user.id == user_response.id
        assert user.email == "test@example.com"
        assert user.is_active is True

    @pytest.mark.asyncio
    async def test_get_current_user_disabled(self, db_session):
        """Test loading disabled user raises error"""
        # Register user
        data = UserRegisterRequest(email="test@example.com", password="password123")
        user_response = await UserService.register(db_session, data)

        # Disable user
        user = await UserService.get_by_id(db_session, user_response.id)
        user.is_active = False
        await db_session.commit()

        # Create token
        token = UserService._create_access_token(user_response.id)

        # Test get_current_user dependency
        user_id = await get_current_user_id(authorization=f"Bearer {token}")

        with pytest.raises(BizException) as exc_info:
            await get_current_user(user_id=user_id, db=db_session)

        assert exc_info.value.error_code == ErrorCode.USER_DISABLED

    @pytest.mark.asyncio
    async def test_get_current_user_not_found(self, db_session):
        """Test loading nonexistent user raises error"""
        # Create token for nonexistent user_id
        token = UserService._create_access_token(999)

        # Test get_current_user dependency
        user_id = await get_current_user_id(authorization=f"Bearer {token}")

        with pytest.raises(BizException) as exc_info:
            await get_current_user(user_id=user_id, db=db_session)

        assert exc_info.value.error_code == ErrorCode.USER_NOT_FOUND
