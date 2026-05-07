"""Update script to set first 100 stocks as active for ARQ worker testing.

This script:
1. Fetches first 100 stocks from database
2. Updates their is_active status to True
"""

import asyncio
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, update

from src.database import SessionFactory
from src.models import Stock
from src.users.model import User  # noqa: F401 - Required for model relationships
from src.subscriptions.model import IndicatorSubscription  # noqa: F401 - Required for model relationships


async def set_100_stocks_active():
    """Set first 100 stocks in database as active."""
    print("Updating first 100 stocks to active status...")

    async with SessionFactory() as session:
        # Get first 100 stocks
        result = await session.execute(
            select(Stock.id).limit(10)
        )
        stock_ids = [row[0] for row in result.all()]

        print(f"Found {len(stock_ids)} stocks to update")

        if stock_ids:
            # Update is_active to True
            await session.execute(
                update(Stock)
                .where(Stock.id.in_(stock_ids))
                .values(is_active=True)
            )
            await session.commit()
            print(f"Updated {len(stock_ids)} stocks to active status")

        # Verify total active stocks
        result = await session.execute(
            select(Stock).where(Stock.is_active == True)
        )
        active_stocks = result.scalars().all()
        print(f"Total active stocks in database: {len(active_stocks)}")

        return len(active_stocks)


if __name__ == "__main__":
    try:
        count = asyncio.run(set_100_stocks_active())
        print(f"\nSuccess! {count} active stocks ready for testing")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)