"""Watchlist models."""

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base
from src.stocks.model import Stock


class Watchlist(Base):
    """用戶自選股清單"""

    __tablename__ = "watchlists"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="My Watchlist")
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    watchlist_stocks: Mapped[list["WatchlistStock"]] = relationship(
        "WatchlistStock", back_populates="watchlist", lazy="selectin"
    )

    __table_args__ = (
        Index("watchlists_user_id_idx", "user_id"),
        Index(
            "watchlists_user_id_name_key",
            "user_id",
            "name",
            unique=True,
            postgresql_where="is_deleted = false",
        ),
    )


class WatchlistStock(Base):
    """自選股清單內的股票（關聯表）"""

    __tablename__ = "watchlist_stocks"

    watchlist_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("watchlists.id"), nullable=False
    )
    stock_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stocks.id"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    watchlist: Mapped["Watchlist"] = relationship(
        "Watchlist", back_populates="watchlist_stocks"
    )
    stock: Mapped["Stock"] = relationship("Stock", lazy="selectin")

    __table_args__ = (
        Index("watchlist_stocks_watchlist_id_idx", "watchlist_id"),
        Index("watchlist_stocks_stock_id_idx", "stock_id"),
        Index(
            "watchlist_stocks_watchlist_stock_key",
            "watchlist_id",
            "stock_id",
            unique=True,
            postgresql_where="is_deleted = false",
        ),
    )
