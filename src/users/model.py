from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class User(Base):
    """用戶資料表"""

    __tablename__ = "users"

    email: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    line_user_id: Mapped[str | None] = mapped_column(
        String(50), unique=True, nullable=True, index=True
    )
