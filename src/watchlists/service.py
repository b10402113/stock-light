"""Watchlist business logic."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.stocks.model import Stock
from src.watchlists.model import Watchlist, WatchlistStock
from src.watchlists.schema import (
    WatchlistCreate,
    WatchlistStockAdd,
    WatchlistStockUpdate,
    WatchlistUpdate,
)


class WatchlistService:
    """自選股清單業務邏輯"""

    @staticmethod
    async def get_by_id(db: AsyncSession, watchlist_id: int) -> Watchlist | None:
        """根據 ID 取得自選股清單.

        Args:
            db: 資料庫會話
            watchlist_id: 清單 ID

        Returns:
            Watchlist | None: 清單實體或 None
        """
        stmt = (
            select(Watchlist)
            .where(
                Watchlist.id == watchlist_id,
                Watchlist.is_deleted.is_(False),
            )
            .options(selectinload(Watchlist.watchlist_stocks))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_watchlists(
        db: AsyncSession, user_id: int
    ) -> list[Watchlist]:
        """取得用戶所有自選股清單.

        Args:
            db: 資料庫會話
            user_id: 用戶 ID

        Returns:
            list[Watchlist]: 清單列表
        """
        stmt = (
            select(Watchlist)
            .where(
                Watchlist.user_id == user_id,
                Watchlist.is_deleted.is_(False),
            )
            .order_by(Watchlist.is_default.desc(), Watchlist.created_at.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def create(db: AsyncSession, user_id: int, data: WatchlistCreate) -> Watchlist:
        """創建自選股清單.

        Args:
            db: 資料庫會話
            user_id: 用戶 ID
            data: 清單創建數據

        Returns:
            Watchlist: 創建後的清單實體
        """
        # Check if this is the user's first watchlist
        existing_count = await db.scalar(
            select(func.count())
            .select_from(Watchlist)
            .where(
                Watchlist.user_id == user_id,
                Watchlist.is_deleted.is_(False),
            )
        )
        is_first = existing_count == 0

        watchlist = Watchlist(
            user_id=user_id,
            name=data.name,
            description=data.description,
            is_default=is_first,
        )
        db.add(watchlist)
        await db.commit()
        await db.refresh(watchlist)
        return watchlist

    @staticmethod
    async def update(
        db: AsyncSession, watchlist: Watchlist, data: WatchlistUpdate
    ) -> Watchlist:
        """更新自選股清單.

        Args:
            db: 資料庫會話
            watchlist: 清單實體
            data: 清單更新數據

        Returns:
            Watchlist: 更新後的清單實體
        """
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(watchlist, key, value)

        await db.commit()
        await db.refresh(watchlist)
        return watchlist

    @staticmethod
    async def soft_delete(db: AsyncSession, watchlist: Watchlist) -> Watchlist:
        """軟刪除自選股清單.

        Args:
            db: 資料庫會話
            watchlist: 清單實體

        Returns:
            Watchlist: 軟刪除後的清單實體
        """
        watchlist.soft_delete()
        await db.commit()
        await db.refresh(watchlist)
        return watchlist

    @staticmethod
    async def get_watchlist_stock(
        db: AsyncSession, watchlist_id: int, stock_id: int
    ) -> WatchlistStock | None:
        """取得清單內的特定股票.

        Args:
            db: 資料庫會話
            watchlist_id: 清單 ID
            stock_id: 股票 ID

        Returns:
            WatchlistStock | None: 股票實體或 None
        """
        stmt = select(WatchlistStock).where(
            WatchlistStock.watchlist_id == watchlist_id,
            WatchlistStock.stock_id == stock_id,
            WatchlistStock.is_deleted.is_(False),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def add_stock(
        db: AsyncSession, watchlist_id: int, data: WatchlistStockAdd
    ) -> WatchlistStock:
        """添加股票到清單.

        Args:
            db: 資料庫會話
            watchlist_id: 清單 ID
            data: 股票添加數據

        Returns:
            WatchlistStock: 添加後的股票實體

        Raises:
            ValueError: 股票不存在或未啟用
        """
        # Verify stock exists and is active
        stock = await db.get(Stock, data.stock_id)
        if not stock or stock.is_deleted or not stock.is_active:
            raise ValueError(f"Stock not found or inactive: {data.stock_id}")

        # Get max sort_order for this watchlist
        max_order = await db.scalar(
            select(func.coalesce(func.max(WatchlistStock.sort_order), -1)).where(
                WatchlistStock.watchlist_id == watchlist_id,
                WatchlistStock.is_deleted.is_(False),
            )
        )

        watchlist_stock = WatchlistStock(
            watchlist_id=watchlist_id,
            stock_id=data.stock_id,
            notes=data.notes,
            sort_order=max_order + 1,
        )
        db.add(watchlist_stock)
        await db.commit()
        await db.refresh(watchlist_stock)
        return watchlist_stock

    @staticmethod
    async def update_stock(
        db: AsyncSession,
        watchlist_stock: WatchlistStock,
        data: WatchlistStockUpdate,
    ) -> WatchlistStock:
        """更新清單內股票.

        Args:
            db: 資料庫會話
            watchlist_stock: 股票實體
            data: 股票更新數據

        Returns:
            WatchlistStock: 更新後的股票實體
        """
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(watchlist_stock, key, value)

        await db.commit()
        await db.refresh(watchlist_stock)
        return watchlist_stock

    @staticmethod
    async def remove_stock(
        db: AsyncSession, watchlist_stock: WatchlistStock
    ) -> WatchlistStock:
        """從清單移除股票.

        Args:
            db: 資料庫會話
            watchlist_stock: 股票實體

        Returns:
            WatchlistStock: 移除後的股票實體
        """
        watchlist_stock.soft_delete()
        await db.commit()
        await db.refresh(watchlist_stock)
        return watchlist_stock

    @staticmethod
    async def get_stock_count(db: AsyncSession, watchlist_id: int) -> int:
        """取得清單內股票數量.

        Args:
            db: 資料庫會話
            watchlist_id: 清單 ID

        Returns:
            int: 股票數量
        """
        count = await db.scalar(
            select(func.count())
            .select_from(WatchlistStock)
            .where(
                WatchlistStock.watchlist_id == watchlist_id,
                WatchlistStock.is_deleted.is_(False),
            )
        )
        return count or 0
