"""LevelConfig and Plan models."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, BaseWithoutAutoId


class LevelConfig(BaseWithoutAutoId):
    """等級配置表 - 定義各等級的配額與價格"""

    __tablename__ = "level_configs"

    level: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    monthly_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    yearly_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    max_subscriptions: Mapped[int] = mapped_column(Integer, nullable=False)
    max_alerts: Mapped[int] = mapped_column(Integer, nullable=False)
    features: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_purchasable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Plan(Base):
    """用戶方案表 - 記錄用戶的等級與到期日"""

    __tablename__ = "plans"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    billing_cycle: Mapped[str] = mapped_column(String(10), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship("User", lazy="selectin")

    __table_args__ = (
        Index("plans_user_id_idx", "user_id"),
        Index("plans_user_active_idx", "user_id", "is_active"),
    )