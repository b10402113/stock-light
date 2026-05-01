"""Stock business logic (CRUD only)."""

from sqlalchemy import select
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
        limit: int = 100,
        offset: int = 0,
    ) -> list[Stock]:
        """取得股票列表.

        Args:
            db: 資料庫會話
            is_active: 是否只取活躍股票
            limit: 最大返回數量
            offset: 偏移量

        Returns:
            list[Stock]: 股票列表
        """
        stmt = select(Stock).where(Stock.is_deleted.is_(False))

        if is_active is not None:
            stmt = stmt.where(Stock.is_active == is_active)

        stmt = stmt.order_by(Stock.symbol).limit(limit).offset(offset)
        result = await db.execute(stmt)
        return list(result.scalars().all())

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
