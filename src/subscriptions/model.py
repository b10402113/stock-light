"""IndicatorSubscription, ScheduledReminder, and NotificationHistory models."""

from datetime import datetime, time, timezone
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, SmallInteger, String, Time, text
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
    title: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    message: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    signal_type: Mapped[str] = mapped_column(String(10), nullable=False, default="buy")
    indicator_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    operator: Mapped[str | None] = mapped_column(String(10), nullable=True)
    target_value: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
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
        Index(
            "idx_indicator_subs_on_stock_active",
            "stock_id",
            postgresql_where="(is_active = true AND is_deleted = false)"
        ),
        Index(
            "idx_indicator_subs_on_user",
            "user_id",
            postgresql_where="(is_deleted = false)"
        ),
        Index(
            "uix_user_stock_single_condition",
            "user_id",
            "stock_id",
            "indicator_type",
            "operator",
            "target_value",
            unique=True,
            postgresql_where="(is_deleted = false AND compound_condition IS NULL)"
        ),
    )


class ScheduledReminder(Base):
    """定期提醒表 - 用戶設定定期股票更新提醒"""

    __tablename__ = "scheduled_reminders"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    stock_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stocks.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    message: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    frequency_type: Mapped[str] = mapped_column(String(10), nullable=False, default="daily")
    reminder_time: Mapped[time] = mapped_column(Time, nullable=False, default=time(17, 0))
    day_of_week: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    day_of_month: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime(1970, 1, 1, tzinfo=timezone.utc)
    )
    next_trigger_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user: Mapped["User"] = relationship("User", lazy="selectin")
    stock: Mapped["Stock"] = relationship("Stock", back_populates="reminders", lazy="selectin")

    __table_args__ = (
        Index("scheduled_reminders_user_id_idx", "user_id"),
        Index("scheduled_reminders_stock_id_idx", "stock_id"),
        Index("scheduled_reminders_is_active_idx", "is_active"),
        Index("scheduled_reminders_next_trigger_at_idx", "next_trigger_at"),
        Index(
            "scheduled_reminders_user_stock_unique_key",
            "user_id",
            "stock_id",
            "frequency_type",
            "reminder_time",
            "day_of_week",
            "day_of_month",
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