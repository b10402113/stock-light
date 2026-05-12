"""Stock business logic (CRUD only)."""

from datetime import date
from decimal import Decimal

from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.stocks.model import DailyPrice, Stock
from src.stocks.schema import DailyPriceBase, DailyPriceBulkCreate, StockCreate, StockUpdate


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


class DailyPriceService:
    """日K線業務邏輯"""

    @staticmethod
    async def bulk_insert_prices(
        db: AsyncSession,
        stock_id: int,
        prices: list[DailyPriceBase],
    ) -> int:
        """批量插入價格資料（upsert 模式，避免重複）.

        Args:
            db: 資料庫會話
            stock_id: 股票 ID
            prices: 價格列表

        Returns:
            int: 插入/更新的記錄數
        """
        values = [
            {
                "stock_id": stock_id,
                "date": p.date,
                "open": p.open,
                "high": p.high,
                "low": p.low,
                "close": p.close,
                "volume": p.volume,
            }
            for p in prices
        ]

        stmt = insert(DailyPrice).values(values)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_daily_price_stock_date",
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
            },
        )

        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

    @staticmethod
    async def get_prices_by_range(
        db: AsyncSession,
        stock_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
        cursor: date | None = None,
        limit: int = 100,
        descending: bool = True,
    ) -> tuple[list[DailyPrice], date | None]:
        """根據日期範圍取得價格資料 (Keyset Pagination).

        Args:
            db: 資料庫會話
            stock_id: 股票 ID
            start_date: 開始日期（包含）
            end_date: 結束日期（包含）
            cursor: 分頁游標（上一頁最後一筆的日期）
            limit: 最大返回數量
            descending: 是否按日期降序排列

        Returns:
            tuple[list[DailyPrice], date | None]: 價格列表和下一頁游標
        """
        stmt = select(DailyPrice).where(
            DailyPrice.stock_id == stock_id,
            DailyPrice.is_deleted.is_(False),
        )

        if start_date:
            stmt = stmt.where(DailyPrice.date >= start_date)

        if end_date:
            stmt = stmt.where(DailyPrice.date <= end_date)

        if cursor:
            if descending:
                stmt = stmt.where(DailyPrice.date < cursor)
            else:
                stmt = stmt.where(DailyPrice.date > cursor)

        if descending:
            stmt = stmt.order_by(DailyPrice.date.desc())
        else:
            stmt = stmt.order_by(DailyPrice.date.asc())

        stmt = stmt.limit(limit)

        result = await db.execute(stmt)
        prices = list(result.scalars().all())

        next_cursor = None
        if len(prices) == limit:
            next_cursor = prices[-1].date

        return prices, next_cursor

    @staticmethod
    async def calculate_ma(
        db: AsyncSession,
        stock_id: int,
        period: int,
        as_of_date: date | None = None,
    ) -> tuple[Decimal | None, int]:
        """計算移動平均值.

        Args:
            db: 資料庫會話
            stock_id: 股票 ID
            period: 移動平均期數
            as_of_date: 計算日期（若未提供則使用最新日期）

        Returns:
            tuple[Decimal | None, int]: 移動平均值和實際數據點數
        """
        if as_of_date:
            stmt = select(DailyPrice.close).where(
                DailyPrice.stock_id == stock_id,
                DailyPrice.date <= as_of_date,
                DailyPrice.is_deleted.is_(False),
            ).order_by(DailyPrice.date.desc()).limit(period)
        else:
            stmt = select(DailyPrice.close).where(
                DailyPrice.stock_id == stock_id,
                DailyPrice.is_deleted.is_(False),
            ).order_by(DailyPrice.date.desc()).limit(period)

        result = await db.execute(stmt)
        closes = [row[0] for row in result.fetchall()]

        if not closes:
            return None, 0

        data_points = len(closes)
        if data_points < period:
            return None, data_points

        avg = sum(closes) / period
        return avg, data_points

    @staticmethod
    async def get_latest_prices(
        db: AsyncSession,
        stock_id: int,
        n: int = 30,
    ) -> list[DailyPrice]:
        """取得最近 N 天的價格資料.

        Args:
            db: 資料庫會話
            stock_id: 股票 ID
            n: 天數

        Returns:
            list[DailyPrice]: 價格列表（按日期降序）
        """
        stmt = select(DailyPrice).where(
            DailyPrice.stock_id == stock_id,
            DailyPrice.is_deleted.is_(False),
        ).order_by(DailyPrice.date.desc()).limit(n)

        result = await db.execute(stmt)
        return list(result.scalars().all())
