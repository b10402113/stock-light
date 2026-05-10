from decimal import Decimal

from sqlalchemy import Boolean, Index, JSON, Numeric, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class Stock(Base):
    """股票資料表"""

    __tablename__ = "stocks"

    symbol: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    current_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    calculated_indicators: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    market: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)

    # Relationships
    subscriptions: Mapped[list["IndicatorSubscription"]] = relationship(
        "IndicatorSubscription", back_populates="stock", lazy="selectin"
    )
    reminders: Mapped[list["ScheduledReminder"]] = relationship(
        "ScheduledReminder", back_populates="stock", lazy="selectin"
    )

    __table_args__ = (Index("stocks_is_active_idx", "is_active"),)
