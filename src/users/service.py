"""User business logic (CRUD only)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.users.model import User


class UserService:
    """用戶業務邏輯"""

    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> User | None:
        """根據信箱取得用戶.

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
        """根據 ID 取得用戶.

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
    async def get_by_line_user_id(db: AsyncSession, line_user_id: str) -> User | None:
        """根據 LINE User ID 取得用戶.

        Args:
            db: 資料庫會話
            line_user_id: LINE User ID

        Returns:
            User | None: 用戶實體或 None
        """
        stmt = select(User).where(
            User.line_user_id == line_user_id,
            User.is_deleted.is_(False),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def update_email(db: AsyncSession, user: User, email: str) -> User:
        """更新用戶信箱.

        Args:
            db: 資料庫會話
            user: 用戶實體
            email: 新信箱

        Returns:
            User: 更新後的用戶實體
        """
        user.email = email
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def update_password(db: AsyncSession, user: User, hashed_password: str) -> User:
        """更新用戶密碼.

        Args:
            db: 資料庫會話
            user: 用戶實體
            hashed_password: 雜湊後的密碼

        Returns:
            User: 更新後的用戶實體
        """
        user.hashed_password = hashed_password
        await db.commit()
        await db.refresh(user)
        return user
