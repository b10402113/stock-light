from decimal import Decimal

from sqlalchemy import Boolean, Index, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

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
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (Index("stocks_is_active_idx", "is_active"),)
