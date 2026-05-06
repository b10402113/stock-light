"""Stock business logic (CRUD only)."""

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.stocks.model import Stock
from src.stocks.schema import StockCreate, StockUpdate


class StockService:
    """股票業務邏輯"""

    @staticmethod
    async def get_by_symbol(db: AsyncSession, symbol: str) -> Stock | None:
        """根據股票代碼取得股票.

        Args:
            db: 資料庫會話
            symbol: 股票代碼

        Returns:
            Stock | None: 股票實體或 None
        """
        stmt = select(Stock).where(
            Stock.symbol == symbol,
            Stock.is_deleted.is_(False),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_id(db: AsyncSession, stock_id: int) -> Stock | None:
        """根據 ID 取得股票.

        Args:
            db: 資料庫會話
            stock_id: 股票 ID

        Returns:
            Stock | None: 股票實體或 None
        """
        stmt = select(Stock).where(
            Stock.id == stock_id,
            Stock.is_deleted.is_(False),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_stocks(
        db: AsyncSession,
        is_active: bool | None = None,
        cursor: int | None = None,
        limit: int = 100,
    ) -> tuple[list[Stock], int | None]:
        """取得股票列表 (Keyset Pagination).

        Args:
            db: 資料庫會話
            is_active: 是否只取活躍股票
            cursor: 分頁游標 (上一頁最後一筆的 ID)
            limit: 最大返回數量

        Returns:
            tuple[list[Stock], int | None]: 股票列表和下一頁游標
        """
        stmt = select(Stock).where(Stock.is_deleted.is_(False))

        if is_active is not None:
            stmt = stmt.where(Stock.is_active == is_active)

        if cursor:
            stmt = stmt.where(Stock.id > cursor)

        stmt = stmt.order_by(Stock.id.asc()).limit(limit)
        result = await db.execute(stmt)
        stocks = list(result.scalars().all())

        next_cursor = None
        if len(stocks) == limit:
            next_cursor = stocks[-1].id

        return stocks, next_cursor

    @staticmethod
    async def search_stocks(
        db: AsyncSession,
        query: str,
        cursor: int | None = None,
        limit: int = 100,
    ) -> tuple[list[Stock], int | None]:
        """搜索股票 (Keyset Pagination) - Database only.

        Args:
            db: 資料庫會話
            query: 搜索關鍵字 (匹配 symbol 或 name)
            cursor: 分頁游標 (上一頁最後一筆的 ID)
            limit: 最大返回數量

        Returns:
            tuple[list[Stock], int | None]: 股票列表和下一頁游標
        """
        pattern = f"%{query}%"
        stmt = select(Stock).where(
            Stock.is_deleted.is_(False),
            or_(
                Stock.symbol.ilike(pattern),
                Stock.name.ilike(pattern),
            ),
        )

        if cursor:
            stmt = stmt.where(Stock.id > cursor)

        stmt = stmt.order_by(Stock.id.asc()).limit(limit)
        result = await db.execute(stmt)
        stocks = list(result.scalars().all())

        next_cursor = None
        if len(stocks) == limit:
            next_cursor = stocks[-1].id

        return stocks, next_cursor

    @staticmethod
    async def create(db: AsyncSession, data: StockCreate) -> Stock:
        """創建股票.

        Args:
            db: 資料庫會話
            data: 股票創建數據

        Returns:
            Stock: 創建後的股票實體
        """
        stock = Stock(
            symbol=data.symbol,
            name=data.name,
            current_price=data.current_price,
            calculated_indicators=data.calculated_indicators,
            is_active=data.is_active,
        )
        db.add(stock)
        await db.commit()
        await db.refresh(stock)
        return stock

    @staticmethod
    async def update(db: AsyncSession, stock: Stock, data: StockUpdate) -> Stock:
        """更新股票.

        Args:
            db: 資料庫會話
            stock: 股票實體
            data: 股票更新數據

        Returns:
            Stock: 更新後的股票實體
        """
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(stock, key, value)

        await db.commit()
        await db.refresh(stock)
        return stock

    @staticmethod
    async def soft_delete(db: AsyncSession, stock: Stock) -> Stock:
        """軟刪除股票.

        Args:
            db: 資料庫會話
            stock: 股票實體

        Returns:
            Stock: 軟刪除後的股票實體
        """
        stock.soft_delete()
        await db.commit()
        await db.refresh(stock)
        return stock
