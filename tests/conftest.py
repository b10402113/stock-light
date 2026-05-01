import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from src.main import app
from src.database import get_db
from src.models.base import Base
from src.users.model import User  # noqa: F401 - Ensure model is registered with Base
from src.stocks.model import Stock  # noqa: F401 - Ensure model is registered with Base
from src.watchlists.model import Watchlist, WatchlistStock  # noqa: F401 - Ensure model is registered with Base
from src.subscriptions.model import IndicatorSubscription  # noqa: F401 - Ensure model is registered with Base


# Session-scoped container (sync)
@pytest.fixture(scope="session")
def postgres_container():
    """Start PostgreSQL container for testing session."""
    container = PostgresContainer("postgres:15")
    container.start()
    yield container
    container.stop()


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Build async URL (sync fixture)
@pytest.fixture(scope="session")
def test_database_url(postgres_container: PostgresContainer) -> str:
    """Get async PostgreSQL connection URL from container."""
    sync_url = postgres_container.get_connection_url()
    async_url = sync_url.replace("+psycopg2", "+asyncpg")
    return async_url


# Create engine and tables (function-scoped for pytest-asyncio compatibility)
@pytest_asyncio.fixture(scope="function")
async def test_engine(test_database_url: str):
    """Create test engine and set up database."""
    engine = create_async_engine(test_database_url, echo=False)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    session_factory = async_sessionmaker(
        test_engine,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession, test_engine) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with database override."""
    session_factory = async_sessionmaker(
        test_engine,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async def _get_test_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _get_test_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()