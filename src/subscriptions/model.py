"""IndicatorSubscription and NotificationHistory models."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, text
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
    notification_histories: Mapped[list["NotificationHistory"]] = relationship(
        "NotificationHistory", back_populates="indicator_subscription", lazy="selectin"
    )

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


class NotificationHistory(Base):
    """通知歷史表 - 記錄每次通知發送的狀態"""

    __tablename__ = "notification_histories"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    indicator_subscription_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("indicator_subscriptions.id"), nullable=False
    )
    triggered_value: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    send_status: Mapped[str] = mapped_column(String(20), nullable=False)
    line_message_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", lazy="selectin")
    indicator_subscription: Mapped["IndicatorSubscription"] = relationship(
        "IndicatorSubscription", back_populates="notification_histories", lazy="selectin"
    )

    __table_args__ = (
        Index("notification_histories_user_id_idx", "user_id"),
        Index("notification_histories_indicator_subscription_id_idx", "indicator_subscription_id"),
        Index("notification_histories_triggered_at_idx", "triggered_at"),
        Index("notification_histories_send_status_idx", "send_status"),
        Index("notification_histories_user_triggered_idx", "user_id", text("triggered_at DESC")),
    )