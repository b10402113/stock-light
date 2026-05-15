"""StockIndicator model for storing calculated technical indicator values."""

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class StockIndicator(Base):
    """股票指標計算結果表 - 使用 JSONB 儲存各類技術指標數值"""

    __tablename__ = "stock_indicator"

    stock_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("stocks.id"), nullable=False
    )
    indicator_key: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    data: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    stock: Mapped["Stock"] = relationship("Stock", lazy="selectin")

    __table_args__ = (
        UniqueConstraint(
            "stock_id",
            "indicator_key",
            name="uq_stock_indicator_stock_key"
        ),
        Index("idx_stock_indicator_stock_id", "stock_id"),
        Index("idx_stock_indicator_key", "indicator_key"),
    )