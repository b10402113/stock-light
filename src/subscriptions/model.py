"""IndicatorSubscription model."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class IndicatorSubscription(Base):
    """指標訂閱表 - 用戶訂閱股票指標觸發條件"""

    __tablename__ = "indicator_subscriptions"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    stock_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stocks.id"), nullable=False
    )
    indicator_type: Mapped[str] = mapped_column(String(50), nullable=False)
    operator: Mapped[str] = mapped_column(String(10), nullable=False)
    target_value: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    compound_condition: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_triggered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cooldown_end_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", lazy="selectin")
    stock: Mapped["Stock"] = relationship("Stock", back_populates="subscriptions", lazy="selectin")

    __table_args__ = (
        Index("indicator_subscriptions_user_id_idx", "user_id"),
        Index("indicator_subscriptions_stock_id_idx", "stock_id"),
        Index("indicator_subscriptions_is_active_idx", "is_active"),
        Index("indicator_subscriptions_user_stock_idx", "user_id", "stock_id"),
        Index(
            "indicator_subscriptions_user_indicator_key",
            "user_id",
            "stock_id",
            "indicator_type",
            "operator",
            "target_value",
            unique=True,
            postgresql_where="is_deleted = false",
        ),
    )