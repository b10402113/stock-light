import pytest
from httpx import AsyncClient

from src.auth.dependencies import get_current_user_id, get_current_user
from src.auth.schema import UserRegisterRequest
from src.auth.service import AuthService


class TestJWTDependencies:
    """Tests for JWT dependencies"""

    @pytest.mark.asyncio
    async def test_get_current_user_id_valid_token(self, client: AsyncClient):
        """Test extracting user_id from valid token"""
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

        # Manually test dependency function
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
        from src.exceptions import BizException, ErrorCode

        with pytest.raises(BizException) as exc_info:
            await get_current_user_id(authorization=None)

        assert exc_info.value.error_code == ErrorCode.UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_current_user_id_invalid_format(self):
        """Test extracting user_id with invalid header format"""
        from src.exceptions import BizException, ErrorCode

        with pytest.raises(BizException) as exc_info:
            await get_current_user_id(authorization="InvalidFormat")

        assert exc_info.value.error_code == ErrorCode.TOKEN_INVALID

    @pytest.mark.asyncio
    async def test_get_current_user_id_invalid_token(self):
        """Test extracting user_id with invalid token"""
        from src.exceptions import BizException, ErrorCode

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
            "/auth/register",
            json={"email": "test@example.com", "password": "password123"},
        )

        # Login to get token
        login_response = await client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        # Use token to access protected endpoint
        response = await client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_current_user_success(self, db_session):
        """Test loading full user entity from valid token"""

        # Register user directly in database
        data = UserRegisterRequest(email="test@example.com", password="password123")
        user_response = await AuthService.register(db_session, data)

        # Create token
        from src.auth.token import create_access_token

        token = create_access_token(user_response.id)

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
        from src.exceptions import BizException, ErrorCode
        from src.users.service import UserService

        # Register user
        data = UserRegisterRequest(email="test@example.com", password="password123")
        user_response = await AuthService.register(db_session, data)

        # Disable user
        user = await UserService.get_by_id(db_session, user_response.id)
        user.is_active = False
        await db_session.commit()

        # Create token
        from src.auth.token import create_access_token

        token = create_access_token(user_response.id)

        # Test get_current_user dependency
        user_id = await get_current_user_id(authorization=f"Bearer {token}")

        with pytest.raises(BizException) as exc_info:
            await get_current_user(user_id=user_id, db=db_session)

        assert exc_info.value.error_code == ErrorCode.USER_DISABLED

    @pytest.mark.asyncio
    async def test_get_current_user_not_found(self, db_session):
        """Test loading nonexistent user raises error"""
        from src.exceptions import BizException, ErrorCode

        # Create token for nonexistent user_id
        from src.auth.token import create_access_token

        token = create_access_token(999)

        # Test get_current_user dependency
        user_id = await get_current_user_id(authorization=f"Bearer {token}")

        with pytest.raises(BizException) as exc_info:
            await get_current_user(user_id=user_id, db=db_session)

        assert exc_info.value.error_code == ErrorCode.USER_NOT_FOUND
