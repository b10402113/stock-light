"""Seed script to create 100 test stocks for ARQ worker testing.

This script:
1. Fetches Taiwan stocks from Fugle API
2. Selects 100 active stocks (TSE market)
3. Seeds them to database with source=StockSource.FUGLE
"""

import asyncio
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from src.clients.fugle_client import FugoClient
from src.database import SessionFactory
from src.models import Stock
from src.users.model import User  # noqa: F401 - Required for model relationships
from src.subscriptions.model import IndicatorSubscription  # noqa: F401 - Required for model relationships
from src.stocks.schema import StockSource, StockMarket


async def seed_100_test_stocks():
    """Seed 100 test stocks from Fugle API."""
    print("Fetching Taiwan stocks from Fugle API...")

    # Use Fugle API to get all Taiwan stocks
    fugle_client = FugoClient()
    tickers = await fugle_client.get_tickers()

    print(f"Found {len(tickers)} Taiwan stocks from Fugle API")

    # Filter TSE stocks (typically 4-digit symbols)
    # TSE stocks are more actively traded and have real price data
    tse_tickers = [
        t for t in tickers
        if t.symbol and len(t.symbol) == 4 and t.name
    ]

    print(f"Filtered {len(tse_tickers)} TSE stocks (4-digit symbols)")

    # Select first 100 stocks
    selected_tickers = tse_tickers[:100]

    if len(selected_tickers) < 100:
        print(f"Warning: Only {len(selected_tickers)} TSE stocks available")
        print("Adding more stocks from remaining tickers...")
        # Add more from remaining tickers if needed
        remaining = [t for t in tickers if t not in selected_tickers and t.name]
        needed = 100 - len(selected_tickers)
        selected_tickers.extend(remaining[:needed])

    print(f"Selected {len(selected_tickers)} stocks for seeding")

    # Seed to database
    async with SessionFactory() as session:
        # Check existing stocks to avoid duplicates
        result = await session.execute(select(Stock.symbol))
        existing_symbols = set(row[0] for row in result.all())

        new_stocks = []
        for ticker in selected_tickers:
            symbol = ticker.symbol

            if symbol not in existing_symbols:
                stock = Stock(
                    symbol=symbol,
                    name=ticker.name,
                    current_price=None,
                    calculated_indicators=None,
                    is_active=True,  # Set as active for testing
                    source=StockSource.FUGLE,
                    market=StockMarket.TAIWAN,
                )
                new_stocks.append(stock)

        if new_stocks:
            session.add_all(new_stocks)
            await session.commit()
            print(f"Seeded {len(new_stocks)} new stocks to database")
        else:
            print("No new stocks to seed (all already exist)")

        # Verify total active stocks
        result = await session.execute(
            select(Stock).where(Stock.is_active == True)
        )
        active_stocks = result.scalars().all()
        print(f"Total active stocks in database: {len(active_stocks)}")

        return len(active_stocks)


if __name__ == "__main__":
    try:
        count = asyncio.run(seed_100_test_stocks())
        print(f"\nSuccess! {count} active stocks ready for testing")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)