import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import BizException, ErrorCode
from src.auth.schema import (
    LoginRequest,
    LoginResponse,
    UserRegisterRequest,
    UserResponse,
)
from src.auth.service import AuthService
from src.auth.token import create_access_token


class TestAuthService:
    """Tests for AuthService"""

    @pytest.mark.asyncio
    async def test_register_success(self, db_session: AsyncSession):
        """Test successful user registration"""
        data = UserRegisterRequest(email="test@example.com", password="password123")

        result = await AuthService.register(db_session, data)

        assert isinstance(result, UserResponse)
        assert result.email == "test@example.com"
        assert result.is_active is True
        assert result.id is not None

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, db_session: AsyncSession):
        """Test registration with duplicate email raises error"""
        data = UserRegisterRequest(email="test@example.com", password="password123")

        # First registration should succeed
        await AuthService.register(db_session, data)

        # Second registration with same email should fail
        with pytest.raises(BizException) as exc_info:
            await AuthService.register(db_session, data)

        assert exc_info.value.error_code == ErrorCode.USER_ALREADY_EXISTS

    def test_hash_password(self):
        """Test password hashing"""
        password = "mysecurepassword123"

        hashed = AuthService._hash_password(password)

        assert hashed != password
        assert hashed.startswith("$2b$")
        assert len(hashed) > 50

    def test_hash_password_different_hashes(self):
        """Test that same password produces different hashes (salt)"""
        password = "mysecurepassword123"

        hash1 = AuthService._hash_password(password)
        hash2 = AuthService._hash_password(password)

        assert hash1 != hash2  # Different salts

    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        password = "password123"
        hashed = AuthService._hash_password(password)

        assert AuthService._verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        password = "password123"
        hashed = AuthService._hash_password(password)

        assert AuthService._verify_password("wrongpassword", hashed) is False

    @pytest.mark.asyncio
    async def test_login_success(self, db_session: AsyncSession):
        """Test successful login"""
        # Register user first
        register_data = UserRegisterRequest(
            email="test@example.com", password="password123"
        )
        await AuthService.register(db_session, register_data)

        # Login
        login_data = LoginRequest(email="test@example.com", password="password123")
        result = await AuthService.login(db_session, login_data)

        assert isinstance(result, LoginResponse)
        assert result.access_token is not None
        assert len(result.access_token) > 0
        assert result.token_type == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, db_session: AsyncSession):
        """Test login with wrong password"""
        # Register user first
        register_data = UserRegisterRequest(
            email="test@example.com", password="password123"
        )
        await AuthService.register(db_session, register_data)

        # Login with wrong password
        login_data = LoginRequest(email="test@example.com", password="wrongpassword")

        with pytest.raises(BizException) as exc_info:
            await AuthService.login(db_session, login_data)

        assert exc_info.value.error_code == ErrorCode.UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, db_session: AsyncSession):
        """Test login with nonexistent user"""
        login_data = LoginRequest(
            email="nonexistent@example.com", password="password123"
        )

        with pytest.raises(BizException) as exc_info:
            await AuthService.login(db_session, login_data)

        assert exc_info.value.error_code == ErrorCode.UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_login_disabled_user(self, db_session: AsyncSession):
        """Test login with disabled user"""
        # Register user
        from src.users.service import UserService

        register_data = UserRegisterRequest(
            email="test@example.com", password="password123"
        )
        await AuthService.register(db_session, register_data)

        # Disable user
        user = await UserService.get_by_email(db_session, "test@example.com")
        user.is_active = False
        await db_session.commit()

        # Try to login
        login_data = LoginRequest(email="test@example.com", password="password123")

        with pytest.raises(BizException) as exc_info:
            await AuthService.login(db_session, login_data)

        assert exc_info.value.error_code == ErrorCode.USER_DISABLED

    def test_create_access_token(self):
        """Test JWT token creation"""
        user_id = 1

        token = create_access_token(user_id)

        assert token is not None
        assert len(token) > 0
        # JWT tokens have 3 parts separated by dots
        assert len(token.split(".")) == 3

    def test_generate_oauth_state(self):
        """Test OAuth state generation"""
        state = AuthService.generate_oauth_state("google")

        assert state.startswith("google:")
        assert len(state.split(":")) == 2
        assert len(state.split(":")[1]) > 20

    def test_verify_oauth_state(self):
        """Test OAuth state verification"""
        state = AuthService.generate_oauth_state("line")

        provider = AuthService.verify_oauth_state(state)

        assert provider == "line"

    def test_verify_oauth_state_invalid(self):
        """Test OAuth state verification with invalid state"""
        with pytest.raises(BizException) as exc_info:
            AuthService.verify_oauth_state("invalid-state")

        assert exc_info.value.error_code == ErrorCode.UNAUTHORIZED
