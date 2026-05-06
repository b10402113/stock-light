"""Tests for StockRedisClient with real Redis connection."""

import time
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from redis.exceptions import RedisError

from src.exceptions import BizException, ErrorCode
from src.clients.redis_client import StockRedisClient


@pytest_asyncio.fixture(scope="function")
async def redis_client():
    """Create StockRedisClient instance connected to real Redis."""
    client = StockRedisClient(
        redis_url="redis://localhost:6379/0",
        timeout=5,
    )
    yield client
    # Cleanup: close connection
    await client.close()


@pytest_asyncio.fixture(scope="function")
async def clean_redis(redis_client: StockRedisClient):
    """Ensure clean Redis state before and after each test."""
    # Get client
    client = await redis_client._get_client()

    # Clear all test keys before test
    await redis_client.clear_active_stocks()

    # Delete all stock info keys (pattern: stock:info:*)
    # Scan for keys matching pattern
    cursor = 0
    while True:
        cursor, keys = await client.scan(cursor, match="stock:info:*", count=100)
        if keys:
            await client.delete(*keys)
        if cursor == 0:
            break

    yield redis_client

    # Clear after test
    await redis_client.clear_active_stocks()

    # Delete all stock info keys
    cursor = 0
    while True:
        cursor, keys = await client.scan(cursor, match="stock:info:*", count=100)
        if keys:
            await client.delete(*keys)
        if cursor == 0:
            break


class TestStockRedisClientIntegration:
    """Integration tests with real Redis connection"""

    @pytest.mark.asyncio
    async def test_ping_success(self, redis_client: StockRedisClient):
        """Test successful Redis ping with real connection."""
        result = await redis_client.ping()
        assert result is True

    @pytest.mark.asyncio
    async def test_add_active_stock_new(self, clean_redis: StockRedisClient):
        """Test adding new stock to active list."""
        result = await clean_redis.add_active_stock("2330.TW")
        assert result is True  # New member added

        # Verify it's in the set
        stocks = await clean_redis.get_active_stocks()
        assert "2330.TW" in stocks

    @pytest.mark.asyncio
    async def test_add_active_stock_existing(self, clean_redis: StockRedisClient):
        """Test adding existing stock to active list."""
        # Add first time
        await clean_redis.add_active_stock("2330.TW")

        # Add again
        result = await clean_redis.add_active_stock("2330.TW")
        assert result is False  # Already exists

    @pytest.mark.asyncio
    async def test_add_multiple_active_stocks(self, clean_redis: StockRedisClient):
        """Test adding multiple stocks to active list."""
        await clean_redis.add_active_stock("2330.TW")
        await clean_redis.add_active_stock("2454.TW")
        await clean_redis.add_active_stock("3008.TW")

        stocks = await clean_redis.get_active_stocks()
        assert stocks == ["2330.TW", "2454.TW", "3008.TW"]  # Sorted

    @pytest.mark.asyncio
    async def test_remove_active_stock_exists(self, clean_redis: StockRedisClient):
        """Test removing existing stock from active list."""
        await clean_redis.add_active_stock("2330.TW")

        result = await clean_redis.remove_active_stock("2330.TW")
        assert result is True  # Removed

        # Verify it's gone
        stocks = await clean_redis.get_active_stocks()
        assert "2330.TW" not in stocks

    @pytest.mark.asyncio
    async def test_remove_active_stock_not_exists(self, clean_redis: StockRedisClient):
        """Test removing non-existing stock from active list."""
        result = await clean_redis.remove_active_stock("2330.TW")
        assert result is False  # Not in set

    @pytest.mark.asyncio
    async def test_get_active_stocks_empty(self, clean_redis: StockRedisClient):
        """Test getting active stocks when empty."""
        stocks = await clean_redis.get_active_stocks()
        assert stocks == []

    @pytest.mark.asyncio
    async def test_clear_active_stocks(self, clean_redis: StockRedisClient):
        """Test clearing all active stocks."""
        await clean_redis.add_active_stock("2330.TW")
        await clean_redis.add_active_stock("2454.TW")

        result = await clean_redis.clear_active_stocks()
        assert result >= 1  # At least one key deleted

        stocks = await clean_redis.get_active_stocks()
        assert stocks == []

    # Stock info operations tests

    @pytest.mark.asyncio
    async def test_set_stock_price_success(self, clean_redis: StockRedisClient):
        """Test setting stock price with real Redis."""
        result = await clean_redis.set_stock_price("2330.TW", 650.5)
        assert result is True

        # Verify price was set
        price = await clean_redis.get_stock_price("2330.TW")
        assert price == 650.5

    @pytest.mark.asyncio
    async def test_set_stock_price_update(self, clean_redis: StockRedisClient):
        """Test updating existing stock price."""
        # Set initial price
        await clean_redis.set_stock_price("2330.TW", 650.0)

        # Update price
        await clean_redis.set_stock_price("2330.TW", 655.5)

        price = await clean_redis.get_stock_price("2330.TW")
        assert price == 655.5

    @pytest.mark.asyncio
    async def test_get_stock_price_not_found(self, clean_redis: StockRedisClient):
        """Test getting non-existing stock price."""
        result = await clean_redis.get_stock_price("2330.TW")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_stock_info_found(self, clean_redis: StockRedisClient):
        """Test getting full stock info."""
        await clean_redis.set_stock_price("2330.TW", 650.5)

        result = await clean_redis.get_stock_info("2330.TW")
        assert result is not None
        assert result["price"] == 650.5
        assert "updated_at" in result
        assert isinstance(result["updated_at"], int)

    @pytest.mark.asyncio
    async def test_get_stock_info_not_found(self, clean_redis: StockRedisClient):
        """Test getting non-existing stock info."""
        result = await clean_redis.get_stock_info("2330.TW")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_stock_info_found(self, clean_redis: StockRedisClient):
        """Test deleting existing stock info."""
        await clean_redis.set_stock_price("2330.TW", 650.5)

        result = await clean_redis.delete_stock_info("2330.TW")
        assert result is True

        # Verify it's deleted
        price = await clean_redis.get_stock_price("2330.TW")
        assert price is None

    @pytest.mark.asyncio
    async def test_delete_stock_info_not_found(self, clean_redis: StockRedisClient):
        """Test deleting non-existing stock info."""
        result = await clean_redis.delete_stock_info("2330.TW")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_stocks_updated_since(self, clean_redis: StockRedisClient):
        """Test getting stocks updated within threshold."""
        # Add active stocks
        await clean_redis.add_active_stock("2330.TW")
        await clean_redis.add_active_stock("2454.TW")
        await clean_redis.add_active_stock("3008.TW")

        # Set prices with different times
        await clean_redis.set_stock_price("2330.TW", 650.0)
        await clean_redis.set_stock_price("2454.TW", 100.0)

        # Manually set old timestamp for 2454.TW
        old_time = int(time.time()) - 300  # 5 minutes ago
        client = await clean_redis._get_client()
        await client.hset("stock:info:2454.TW", mapping={"price": "100.0", "updated_at": old_time})

        # 3008.TW has no info

        # Get stocks updated within last 60 seconds
        recent_stocks = await clean_redis.get_stocks_updated_since(60)
        assert "2330.TW" in recent_stocks  # Recently updated
        assert "2454.TW" not in recent_stocks  # Old update
        assert "3008.TW" not in recent_stocks  # No info

    @pytest.mark.asyncio
    async def test_close_connection(self, redis_client: StockRedisClient):
        """Test closing Redis connection."""
        # Connect first
        await redis_client.ping()

        # Close
        await redis_client.close()
        assert redis_client._client is None


class TestStockRedisClientMocked:
    """Tests for error scenarios that require mocking"""

    @pytest.fixture
    def mock_redis_client(self):
        """Create StockRedisClient for mock tests."""
        return StockRedisClient(
            redis_url="redis://localhost:6379/0",
            timeout=5,
        )

    @pytest.mark.asyncio
    async def test_ping_connection_error(self, mock_redis_client: StockRedisClient):
        """Test Redis ping with connection error."""
        with patch.object(
            mock_redis_client, "_get_client", side_effect=RedisError("Connection refused")
        ):
            with pytest.raises(BizException) as exc_info:
                await mock_redis_client.ping()

            assert exc_info.value.error_code == ErrorCode.REDIS_CONNECTION_ERROR
            assert "Redis connection failed" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_add_active_stock_error(self, mock_redis_client: StockRedisClient):
        """Test adding stock with Redis error."""
        mock_redis = AsyncMock()
        mock_redis.sadd.side_effect = RedisError("SADD failed")

        with patch.object(mock_redis_client, "_get_client", return_value=mock_redis):
            with pytest.raises(BizException) as exc_info:
                await mock_redis_client.add_active_stock("2330.TW")

            assert exc_info.value.error_code == ErrorCode.REDIS_OPERATION_ERROR
            assert "Failed to add active stock" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_set_stock_price_error(self, mock_redis_client: StockRedisClient):
        """Test setting stock price with Redis error."""
        mock_redis = AsyncMock()
        mock_redis.hset.side_effect = RedisError("HSET failed")

        with patch.object(mock_redis_client, "_get_client", return_value=mock_redis):
            with pytest.raises(BizException) as exc_info:
                await mock_redis_client.set_stock_price("2330.TW", 650.5)

            assert exc_info.value.error_code == ErrorCode.REDIS_OPERATION_ERROR
            assert "Failed to set stock price" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_get_stock_price_invalid_value(self, mock_redis_client: StockRedisClient):
        """Test getting stock price with invalid cached value."""
        mock_redis = AsyncMock()
        mock_redis.hget.return_value = "invalid_price"

        with patch.object(mock_redis_client, "_get_client", return_value=mock_redis):
            with pytest.raises(BizException) as exc_info:
                await mock_redis_client.get_stock_price("2330.TW")

            assert exc_info.value.error_code == ErrorCode.REDIS_OPERATION_ERROR
            assert "Invalid cached price" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_get_stock_info_invalid_data(self, mock_redis_client: StockRedisClient):
        """Test getting stock info with invalid cached data."""
        mock_redis = AsyncMock()
        mock_redis.hgetall.return_value = {
            "price": "invalid",
            "updated_at": "1715000000",
        }

        with patch.object(mock_redis_client, "_get_client", return_value=mock_redis):
            with pytest.raises(BizException) as exc_info:
                await mock_redis_client.get_stock_info("2330.TW")

            assert exc_info.value.error_code == ErrorCode.REDIS_OPERATION_ERROR
            assert "Invalid cached data" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_close_connection_no_client(self, mock_redis_client: StockRedisClient):
        """Test closing when no connection exists."""
        mock_redis_client._client = None
        await mock_redis_client.close()
        # Should not raise error