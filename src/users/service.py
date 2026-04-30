import bcrypt
import jwt
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.exceptions import BizException, ErrorCode
from src.users.model import User
from src.users.schema import (
    LoginRequest,
    LoginResponse,
    UserRegisterRequest,
    UserResponse,
)


class UserService:
    """用戶業務邏輯"""

    @staticmethod
    async def register(db: AsyncSession, data: UserRegisterRequest) -> UserResponse:
        """
        註冊新用戶

        Args:
            db: 資料庫會話
            data: 註冊請求資料

        Returns:
            UserResponse: 註冊成功的用戶資訊

        Raises:
            BizException: 信箱已被註冊
        """
        # 檢查信箱是否已存在
        existing_user = await UserService.get_by_email(db, data.email)
        if existing_user:
            raise BizException(ErrorCode.USER_ALREADY_EXISTS, "此信箱已被註冊")

        # 建立新用戶
        user = User(
            email=data.email,
            hashed_password=UserService._hash_password(data.password),
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        return UserResponse.model_validate(user)

    @staticmethod
    async def login(db: AsyncSession, data: LoginRequest) -> LoginResponse:
        """
        用戶登入

        Args:
            db: 資料庫會話
            data: 登入請求資料

        Returns:
            LoginResponse: JWT 存取權杖

        Raises:
            BizException: 憑證無效、用戶不存在或已停用
        """
        user = await UserService.get_by_email(db, data.email)
        if not user:
            raise BizException(ErrorCode.UNAUTHORIZED, "信箱或密碼錯誤")

        if not user.is_active:
            raise BizException(ErrorCode.USER_DISABLED, "用戶已停用")

        if not UserService._verify_password(data.password, user.hashed_password):
            raise BizException(ErrorCode.UNAUTHORIZED, "信箱或密碼錯誤")

        access_token = UserService._create_access_token(user.id)
        return LoginResponse(access_token=access_token)

    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> User | None:
        """
        根據信箱取得用戶

        Args:
            db: 資料庫會話
            email: 用戶信箱

        Returns:
            User | None: 用戶實體或 None
        """
        stmt = select(User).where(User.email == email, User.is_deleted.is_(False))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: int) -> User | None:
        """
        根據 ID 取得用戶

        Args:
            db: 資料庫會話
            user_id: 用戶 ID

        Returns:
            User | None: 用戶實體或 None
        """
        stmt = select(User).where(User.id == user_id, User.is_deleted.is_(False))
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def _hash_password(password: str) -> str:
        """
        使用 bcrypt 雜湊密碼

        Args:
            password: 明文密碼

        Returns:
            str: 雜湊後的密碼
        """
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    @staticmethod
    def _verify_password(password: str, hashed_password: str) -> bool:
        """
        驗證密碼

        Args:
            password: 明文密碼
            hashed_password: 雜湊後的密碼

        Returns:
            bool: 密碼是否匹配
        """
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))

    @staticmethod
    def _create_access_token(user_id: int) -> str:
        """
        建立 JWT 存取權杖

        Args:
            user_id: 用戶 ID

        Returns:
            str: JWT 權杖
        """
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )
        payload = {"user_id": user_id, "exp": expire}
        return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)
