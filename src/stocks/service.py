"""Stock business logic (CRUD only)."""

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.fugle_client import FugoClient
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
        fugle_client: FugoClient | None = None,
    ) -> tuple[list[Stock], int | None]:
        """搜索股票 (Keyset Pagination) - Database first, Fugle API fallback.

        Args:
            db: 資料庫會話
            query: 搜索關鍵字 (匹配 symbol 或 name)
            cursor: 分頁游標 (上一頁最後一筆的 ID)
            limit: 最大返回數量
            fugle_client: Fugle API client (optional, for fallback)

        Returns:
            tuple[list[Stock], int | None]: 股票列表和下一頁游標
        """
        # First, search database
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

        # If no results found in database and fugle_client is provided, fallback to Fugle API
        if len(stocks) == 0 and fugle_client is not None:
            try:
                # Extract symbol from query (remove .TW suffix if present)
                symbol_query = query.upper()
                if symbol_query.endswith(".TW"):
                    symbol_query = symbol_query[:-3]

                # Query single ticker from Fugle API
                ticker = await fugle_client.get_ticker(symbol_query)

                if ticker is not None:
                    # Check if query matches ticker symbol (case-insensitive)
                    if query.lower() in ticker.symbol.lower():
                        # Add .TW suffix for database storage
                        symbol = ticker.symbol
                        if not symbol.endswith(".TW"):
                            symbol = f"{symbol}.TW"

                        # Check if stock already exists (to avoid duplicates)
                        existing_stmt = select(Stock).where(Stock.symbol == symbol)
                        existing_result = await db.execute(existing_stmt)
                        existing_stock = existing_result.scalar_one_or_none()

                        if existing_stock is None:
                            # Create new stock
                            stock = Stock(
                                symbol=symbol,
                                name=ticker.name,
                                current_price=None,
                                calculated_indicators=None,
                                is_active=True,
                            )
                            db.add(stock)
                            await db.commit()

                        # Re-query to get the newly created stock
                        stmt = (
                            select(Stock)
                            .where(
                                Stock.is_deleted.is_(False),
                                Stock.symbol == symbol,
                            )
                            .order_by(Stock.id.asc())
                            .limit(limit)
                        )
                        result = await db.execute(stmt)
                        stocks = list(result.scalars().all())

            except Exception:
                # If Fugle API fails, just return empty list
                pass

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
