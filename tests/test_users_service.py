import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import BizException, ErrorCode
from src.users.schema import UserRegisterRequest, UserResponse
from src.users.service import UserService


class TestUserService:
    """Tests for UserService"""

    @pytest.mark.asyncio
    async def test_register_success(self, db_session: AsyncSession):
        """Test successful user registration"""
        data = UserRegisterRequest(email="test@example.com", password="password123")

        result = await UserService.register(db_session, data)

        assert isinstance(result, UserResponse)
        assert result.email == "test@example.com"
        assert result.is_active is True
        assert result.id is not None

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, db_session: AsyncSession):
        """Test registration with duplicate email raises error"""
        data = UserRegisterRequest(email="test@example.com", password="password123")

        # First registration should succeed
        await UserService.register(db_session, data)

        # Second registration with same email should fail
        with pytest.raises(BizException) as exc_info:
            await UserService.register(db_session, data)

        assert exc_info.value.error_code == ErrorCode.USER_ALREADY_EXISTS

    @pytest.mark.asyncio
    async def test_get_by_email_existing(self, db_session: AsyncSession):
        """Test getting user by email when user exists"""
        data = UserRegisterRequest(email="test@example.com", password="password123")
        await UserService.register(db_session, data)

        user = await UserService.get_by_email(db_session, "test@example.com")

        assert user is not None
        assert user.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_by_email_not_found(self, db_session: AsyncSession):
        """Test getting user by email when user doesn't exist"""
        user = await UserService.get_by_email(db_session, "nonexistent@example.com")

        assert user is None

    def test_hash_password(self):
        """Test password hashing"""
        password = "mysecurepassword123"

        hashed = UserService._hash_password(password)

        assert hashed != password
        assert hashed.startswith("$2b$")
        assert len(hashed) > 50

    def test_hash_password_different_hashes(self):
        """Test that same password produces different hashes (salt)"""
        password = "mysecurepassword123"

        hash1 = UserService._hash_password(password)
        hash2 = UserService._hash_password(password)

        assert hash1 != hash2  # Different salts
