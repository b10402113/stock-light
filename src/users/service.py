from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import BizException, ErrorCode
from src.users.model import User
from src.users.schema import UserRegisterRequest, UserResponse


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
    def _hash_password(password: str) -> str:
        """
        使用 bcrypt 雜湊密碼

        Args:
            password: 明文密碼

        Returns:
            str: 雜湊後的密碼
        """
        import bcrypt

        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
