"""Authentication business logic."""

import bcrypt
import secrets
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import BizException, ErrorCode
from src.auth.models import OAuthAccount
from src.auth.token import create_access_token
from src.auth.schema import LoginRequest, LoginResponse, UserRegisterRequest, UserResponse
from src.auth.oauth_client import OAuthClientFactory
from src.auth.providers.base import OAuthProvider
from src.users.model import User
from src.users.service import UserService


class AuthService:
    """Authentication business logic service."""

    @staticmethod
    async def register(db: AsyncSession, data: UserRegisterRequest) -> UserResponse:
        """Register a new user.

        Args:
            db: Database session
            data: Registration request data

        Returns:
            UserResponse: Registered user info

        Raises:
            BizException: Email already registered
        """
        # Check if email exists
        existing_user = await UserService.get_by_email(db, data.email)
        if existing_user:
            raise BizException(ErrorCode.USER_ALREADY_EXISTS, "此信箱已被註冊")

        # Create new user
        user = User(
            email=data.email,
            hashed_password=AuthService._hash_password(data.password),
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        return UserResponse.model_validate(user)

    @staticmethod
    async def login(db: AsyncSession, data: LoginRequest) -> LoginResponse:
        """User login with email and password.

        Args:
            db: Database session
            data: Login request data

        Returns:
            LoginResponse: JWT access token

        Raises:
            BizException: Invalid credentials, user not found or disabled
        """
        user = await UserService.get_by_email(db, data.email)
        if not user:
            raise BizException(ErrorCode.UNAUTHORIZED, "信箱或密碼錯誤")

        if not user.is_active:
            raise BizException(ErrorCode.USER_DISABLED, "用戶已停用")

        if not AuthService._verify_password(data.password, user.hashed_password):
            raise BizException(ErrorCode.UNAUTHORIZED, "信箱或密碼錯誤")

        access_token = create_access_token(user.id)
        return LoginResponse(access_token=access_token)

    @staticmethod
    def _hash_password(password: str) -> str:
        """Hash password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            str: Hashed password
        """
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    @staticmethod
    def _verify_password(password: str, hashed_password: str) -> bool:
        """Verify password.

        Args:
            password: Plain text password
            hashed_password: Hashed password

        Returns:
            bool: Password match status
        """
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))

    @staticmethod
    def generate_oauth_state(provider: str) -> str:
        """Generate OAuth state token.

        Args:
            provider: OAuth provider name

        Returns:
            str: state token
        """
        return f"{provider}:{secrets.token_urlsafe(32)}"

    @staticmethod
    def verify_oauth_state(state: str) -> str:
        """Verify OAuth state token.

        Args:
            state: State token

        Returns:
            str: Provider name

        Raises:
            BizException: Invalid state token
        """
        try:
            provider, _ = state.split(":", 1)
            return provider
        except ValueError:
            raise BizException(ErrorCode.UNAUTHORIZED, "無效的 state token")

    @staticmethod
    async def oauth_login(
        db: AsyncSession,
        provider: str,
        code: str,
        state: str,
    ) -> LoginResponse:
        """OAuth login.

        Args:
            db: Database session
            provider: OAuth provider name
            code: Authorization code
            state: State token

        Returns:
            LoginResponse: JWT access token

        Raises:
            BizException: Login failed
        """
        # 1. Validate provider
        if provider not in (OAuthProvider.GOOGLE, OAuthProvider.LINE):
            raise BizException(ErrorCode.PARAM_ERROR, f"不支援的登入方式: {provider}")

        # 2. Verify state
        AuthService.verify_oauth_state(state)

        # 3. Exchange code for token
        try:
            client = OAuthClientFactory.get_client(provider)
            token_data = await client.exchange_token(code)
            access_token = token_data["access_token"]
        except Exception as exc:
            raise BizException(ErrorCode.UNAUTHORIZED, "OAuth 認證失敗") from exc

        # 4. Get user info from provider
        try:
            user_info = await client.get_user_info(access_token)
        except Exception as exc:
            raise BizException(ErrorCode.UNAUTHORIZED, "取得用戶資訊失敗") from exc

        # 5. Find or create user
        user = await AuthService._find_or_create_oauth_user(db, provider, user_info)

        # 6. Check user status
        if not user.is_active:
            raise BizException(ErrorCode.USER_DISABLED, "用戶已停用")

        # 7. Generate JWT
        jwt_token = create_access_token(user.id)
        return LoginResponse(access_token=jwt_token)

    @staticmethod
    async def _find_or_create_oauth_user(
        db: AsyncSession,
        provider: str,
        user_info: dict,
    ) -> User:
        """Find or create OAuth user.

        Args:
            db: Database session
            provider: OAuth provider name
            user_info: User info from OAuth provider

        Returns:
            User: User entity
        """
        provider_user_id = user_info["id"]

        # Check if OAuth account already exists
        stmt = select(OAuthAccount).where(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_user_id == provider_user_id,
            OAuthAccount.is_deleted.is_(False),
        )
        result = await db.execute(stmt)
        oauth_account = result.scalar_one_or_none()

        if oauth_account:
            # Already linked, return user
            user = await UserService.get_by_id(db, oauth_account.user_id)
            if user:
                return user

        # Check if email exists (try to link)
        email = user_info.get("email")
        user = None

        if email:
            user = await UserService.get_by_email(db, email)

        if user:
            # Link OAuth to existing account
            oauth_account = OAuthAccount(
                user_id=user.id,
                provider=provider,
                provider_user_id=provider_user_id,
                provider_email=email,
                provider_name=user_info.get("name"),
                provider_picture=user_info.get("picture"),
            )
            db.add(oauth_account)
            await db.commit()
            return user

        # Create new user
        user = User(
            email=email,
            hashed_password=None,
            is_active=True,
        )
        db.add(user)
        await db.flush()  # Get user.id

        oauth_account = OAuthAccount(
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id,
            provider_email=email,
            provider_name=user_info.get("name"),
            provider_picture=user_info.get("picture"),
        )
        db.add(oauth_account)
        await db.commit()
        await db.refresh(user)
        return user
