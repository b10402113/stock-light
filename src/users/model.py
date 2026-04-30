from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class User(Base):
    """用戶資料表"""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
