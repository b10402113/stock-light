from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Date, ForeignKey, Index, Integer, JSON, Numeric, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.schema import UniqueConstraint

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
    daily_prices: Mapped[list["DailyPrice"]] = relationship(
        "DailyPrice", back_populates="stock", lazy="selectin", order_by="DailyPrice.date.desc()"
    )

    __table_args__ = (Index("stocks_is_active_idx", "is_active"),)


class DailyPrice(Base):
    """日K線歷史資料表"""

    __tablename__ = "daily_prices"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    stock_id: Mapped[int] = mapped_column(Integer, ForeignKey("stocks.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Relationships
    stock: Mapped["Stock"] = relationship("Stock", back_populates="daily_prices")

    __table_args__ = (
        UniqueConstraint("stock_id", "date", name="uq_daily_price_stock_date"),
        Index("idx_daily_price_stock_date", "stock_id", "date"),
    )
