"""資料庫種子腳本 - 建立測試資料"""

import asyncio
import random
import sys
from decimal import Decimal
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.auth.models import OAuthAccount
from src.config import settings
from src.models.base import Base
from src.stocks.model import Stock
from src.subscriptions.model import IndicatorSubscription, NotificationHistory
from src.users.model import User
from src.watchlists.model import Watchlist, WatchlistStock


# 台灣股票列表 (熱門股票)
STOCKS_DATA = [
    ("2330", "台積電", Decimal(850.00)),
    ("2317", "鴻海", Decimal(145.50)),
    ("2454", "聯發科", Decimal(1180.00)),
    ("2308", "台達電", Decimal(320.00)),
    ("2412", "中華電", Decimal(125.00)),
    ("2303", "聯電", Decimal(48.50)),
    ("2382", "廣達", Decimal(85.00)),
    ("2376", "技嘉", Decimal(42.00)),
    ("3037", "欣興", Decimal(95.00)),
    ("2603", "長榮", Decimal(120.00)),
    ("2615", "萬海", Decimal(45.00)),
    ("2609", "陽明", Decimal(35.00)),
    ("2881", "富邦金", Decimal(85.00)),
    ("2882", "國泰金", Decimal(62.00)),
    ("2891", "中信金", Decimal(24.00)),
    ("2884", "玉山金", Decimal(28.00)),
    ("2886", "兆豐金", Decimal(35.00)),
    ("2002", "中鋼", Decimal(25.00)),
    ("1101", "台泥", Decimal(42.00)),
    ("1216", "統一", Decimal(52.00)),
]

# 使用者資料
USERS_DATA = [
    ("user1@example.com", "測試使用者1"),
    ("user2@example.com", "測試使用者2"),
    ("user3@example.com", "測試使用者3"),
    ("user4@example.com", "測試使用者4"),
    ("user5@example.com", "測試使用者5"),
]


async def seed_database():
    """填充資料庫"""
    engine = create_async_engine(str(settings.DATABASE_URL), echo=True)
    SessionFactory = async_sessionmaker(engine, expire_on_commit=False)

    async with SessionFactory() as session:
        try:
            # 1. 建立股票
            print("正在建立股票...")
            stocks = []
            for symbol, name, price in STOCKS_DATA:
                stock = Stock(
                    symbol=symbol,
                    name=name,
                    current_price=price,
                    is_active=True,
                )
                session.add(stock)
                stocks.append(stock)

            await session.flush()  # 取得 stock IDs
            print(f"已建立 {len(stocks)} 檔股票")

            # 2. 建立使用者
            print("正在建立使用者...")
            users = []
            for email, display_name in USERS_DATA:
                user = User(
                    email=email,
                    display_name=display_name,
                    is_active=True,
                    quota=10,
                    subscription_status="free",
                )
                session.add(user)
                users.append(user)

            await session.flush()  # 取得 user IDs
            print(f"已建立 {len(users)} 位使用者")

            # 3. 為每位使用者建立 watchlist 並加入隨機股票
            print("正在建立自選股清單...")
            for user in users:
                # 建立預設 watchlist
                watchlist = Watchlist(
                    user_id=user.id,
                    name="我的自選股",
                    description=f"{user.display_name} 的預設自選股清單",
                    is_default=True,
                )
                session.add(watchlist)
                await session.flush()

                # 隨機選擇 3 檔股票
                selected_stocks = random.sample(stocks, 3)
                for idx, stock in enumerate(selected_stocks):
                    watchlist_stock = WatchlistStock(
                        watchlist_id=watchlist.id,
                        stock_id=stock.id,
                        notes=f"隨機加入的股票 #{idx + 1}",
                        sort_order=idx,
                    )
                    session.add(watchlist_stock)

                print(f"已為 {user.display_name} 建立自選股清單，包含 3 檔股票")

            await session.commit()
            print("\n✅ 資料庫填充完成！")

        except Exception as e:
            await session.rollback()
            print(f"\n❌ 填充資料庫時發生錯誤: {e}")
            raise
        finally:
            await engine.dispose()


async def clear_all_data():
    """清除所有測試資料"""
    engine = create_async_engine(str(settings.DATABASE_URL), echo=True)
    SessionFactory = async_sessionmaker(engine, expire_on_commit=False)

    async with SessionFactory() as session:
        try:
            # 按依賴順序刪除（子表 → 父表）
            print("正在刪除 notification_histories...")
            result = await session.execute(delete(NotificationHistory))
            print(f"已刪除 {result.rowcount} notification_histories")

            print("正在刪除 indicator_subscriptions...")
            result = await session.execute(delete(IndicatorSubscription))
            print(f"已刪除 {result.rowcount} indicator_subscriptions")

            print("正在刪除 watchlist_stocks...")
            result = await session.execute(delete(WatchlistStock))
            print(f"已刪除 {result.rowcount} watchlist_stocks")

            print("正在刪除 watchlists...")
            result = await session.execute(delete(Watchlist))
            print(f"已刪除 {result.rowcount} watchlists")

            print("正在刪除 oauth_accounts...")
            result = await session.execute(delete(OAuthAccount))
            print(f"已刪除 {result.rowcount} oauth_accounts")

            print("正在刪除 stocks...")
            result = await session.execute(delete(Stock))
            print(f"已刪除 {result.rowcount} stocks")

            print("正在刪除 users...")
            result = await session.execute(delete(User))
            print(f"已刪除 {result.rowcount} users")

            await session.commit()
            print("✅ 所有資料已清除")

        except Exception as e:
            await session.rollback()
            print(f"❌ 清除資料時發生錯誤: {e}")
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    import sys

    print("=" * 50)
    print("StockLight 資料庫種子腳本")
    print("=" * 50)

    action = sys.argv[1] if len(sys.argv) > 1 else "seed"

    if action == "seed":
        asyncio.run(seed_database())
    elif action == "clear":
        asyncio.run(clear_all_data())
    else:
        print(f"未知的動作: {action}")
        print("使用方式: python scripts/seed_data.py [seed|clear]")