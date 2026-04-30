from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config import settings
from src.models import Base  # noqa: F401 - 匯入 Base 以便 Alembic 自動生成 migration

# 建立非同步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,  # 檢查連線是否存活
    echo=settings.DEBUG,  # 開發模式下印出 SQL
)

# Session Factory
SessionFactory = async_sessionmaker(
    engine,
    expire_on_commit=False,  # 避免物件在 commit 後失效
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Depends - 取得資料庫 session"""
    async with SessionFactory() as session:
        try:
            yield session
        finally:
            await session.close()
