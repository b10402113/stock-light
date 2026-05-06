"""Seed Taiwan stocks from Fugle API."""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.clients.fugle_client import FugoClient
from src.config import settings
from src.models.base import Base
from src.stocks.model import Stock
from src.stocks.schema import StockSource, StockMarket
from src.users.model import User
from src.subscriptions.model import IndicatorSubscription


def normalize_symbol(symbol: str) -> str:
    """Normalize symbol to .TW format for Taiwan stocks."""
    # If symbol is a 4-digit number (Taiwan stock), add .TW suffix
    if symbol.isdigit() and len(symbol) == 4:
        return f"{symbol}.TW"
    # If already has .TW suffix, return as-is
    if symbol.endswith(".TW"):
        return symbol
    # Otherwise return as-is (for other formats)
    return symbol


async def seed_taiwan_stocks():
    """Fetch all Taiwan stocks from Fugle API and populate database."""
    engine = create_async_engine(str(settings.DATABASE_URL), echo=True)
    SessionFactory = async_sessionmaker(engine, expire_on_commit=False)

    fugle_client = FugoClient()

    async with SessionFactory() as session:
        try:
            print("Fetching Taiwan stocks from Fugle API...")
            tickers = await fugle_client.get_tickers()
            print(f"Found {len(tickers)} stocks")

            stocks_created = 0
            stocks_updated = 0

            for ticker in tickers:
                # Normalize symbol format (add .TW suffix for Taiwan stocks)
                symbol = normalize_symbol(ticker.symbol)

                # Use symbol as name if name is not provided
                name = ticker.name or ticker.symbol

                # Check if stock already exists (by symbol)
                existing_stmt = select(Stock).where(Stock.symbol == symbol)
                existing_result = await session.execute(existing_stmt)
                existing_stock = existing_result.scalar_one_or_none()

                if existing_stock is None:
                    # Create new stock
                    stock = Stock(
                        symbol=symbol,
                        name=name,
                        current_price=None,
                        calculated_indicators=None,
                        is_active=False,
                        source=StockSource.FUGLE,
                        market=StockMarket.TAIWAN,
                    )
                    session.add(stock)
                    stocks_created += 1
                else:
                    # Update all fields for existing stock
                    existing_stock.name = name
                    existing_stock.current_price = None
                    existing_stock.calculated_indicators = None
                    existing_stock.is_active = False
                    existing_stock.source = StockSource.FUGLE
                    existing_stock.market = StockMarket.TAIWAN
                    stocks_updated += 1

            await session.commit()
            print(f"\n✅ Seed completed!")
            print(f"   Created: {stocks_created} stocks")
            print(f"   Updated: {stocks_updated} stocks")

        except Exception as e:
            await session.rollback()
            print(f"\n❌ Error seeding database: {e}")
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    print("=" * 50)
    print("Taiwan Stocks Seed Script")
    print("=" * 50)
    asyncio.run(seed_taiwan_stocks())