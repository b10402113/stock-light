"""Redis client for stock data caching.

Provides atomic operations for active stock list and price caching to prevent race conditions.
"""

import time
from typing import Optional

import redis.asyncio as redis
from redis.asyncio import Redis
from redis.exceptions import RedisError

from src.config import settings
from src.exceptions import BizException, ErrorCode


class StockRedisClient:
    """Redis client for stock data caching with atomic operations.

    Data structures:
    - Active stocks list: Redis Set (key: stocks:active)
    - Stock price cache: Redis Hash (key: stock:info:{ticker})

    Fields in stock info hash:
    - price: current price (float)
    - updated_at: last update timestamp (int, Unix timestamp)
    """

    ACTIVE_STOCKS_KEY = "stocks:active"
    STOCK_INFO_KEY_PREFIX = "stock:info:"

    def __init__(self, redis_url: str = None, timeout: int = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self.timeout = timeout or settings.REDIS_TIMEOUT
        self._client: Optional[Redis] = None

    async def _get_client(self) -> Redis:
        """Get or create Redis connection."""
        if self._client is None:
            self._client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=self.timeout,
                socket_connect_timeout=self.timeout,
            )
        return self._client

    async def close(self):
        """Close Redis connection."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def ping(self) -> bool:
        """Check Redis connection."""
        try:
            client = await self._get_client()
            return await client.ping()
        except RedisError as exc:
            raise BizException(
                ErrorCode.REDIS_CONNECTION_ERROR,
                f"Redis connection failed: {exc}",
            ) from exc

    # Active stocks operations (Redis Set)

    async def add_active_stock(self, symbol: str) -> bool:
        """Add stock to active monitoring list.

        Uses SADD (atomic operation) to prevent race conditions.

        Args:
            symbol: Stock symbol (e.g., '2330.TW')

        Returns:
            True if added (new member), False if already exists
        """
        try:
            client = await self._get_client()
            result = await client.sadd(self.ACTIVE_STOCKS_KEY, symbol)
            return result == 1
        except RedisError as exc:
            raise BizException(
                ErrorCode.REDIS_OPERATION_ERROR,
                f"Failed to add active stock {symbol}: {exc}",
            ) from exc

    async def remove_active_stock(self, symbol: str) -> bool:
        """Remove stock from active monitoring list.

        Uses SREM (atomic operation).

        Args:
            symbol: Stock symbol

        Returns:
            True if removed, False if not in set
        """
        try:
            client = await self._get_client()
            result = await client.srem(self.ACTIVE_STOCKS_KEY, symbol)
            return result == 1
        except RedisError as exc:
            raise BizException(
                ErrorCode.REDIS_OPERATION_ERROR,
                f"Failed to remove active stock {symbol}: {exc}",
            ) from exc

    async def get_active_stocks(self) -> list[str]:
        """Get all active stocks being monitored.

        Uses SMEMBERS to retrieve the full set.

        Returns:
            List of stock symbols
        """
        try:
            client = await self._get_client()
            members = await client.smembers(self.ACTIVE_STOCKS_KEY)
            return sorted(list(members))
        except RedisError as exc:
            raise BizException(
                ErrorCode.REDIS_OPERATION_ERROR,
                f"Failed to get active stocks: {exc}",
            ) from exc

    async def clear_active_stocks(self) -> int:
        """Clear all active stocks from monitoring list.

        Returns:
            Number of members removed
        """
        try:
            client = await self._get_client()
            return await client.delete(self.ACTIVE_STOCKS_KEY)
        except RedisError as exc:
            raise BizException(
                ErrorCode.REDIS_OPERATION_ERROR,
                f"Failed to clear active stocks: {exc}",
            ) from exc

    # Stock info operations (Redis Hash)

    def _stock_info_key(self, symbol: str) -> str:
        """Generate stock info hash key."""
        return f"{self.STOCK_INFO_KEY_PREFIX}{symbol}"

    async def set_stock_price(self, symbol: str, price: float) -> bool:
        """Update stock price in cache.

        Uses HSET (atomic operation) to update price and timestamp.

        Args:
            symbol: Stock symbol
            price: Current price

        Returns:
            True if successful
        """
        try:
            client = await self._get_client()
            key = self._stock_info_key(symbol)
            timestamp = int(time.time())

            # HSET is atomic - updates both fields in single operation
            await client.hset(key, mapping={"price": str(price), "updated_at": timestamp})
            return True
        except RedisError as exc:
            raise BizException(
                ErrorCode.REDIS_OPERATION_ERROR,
                f"Failed to set stock price for {symbol}: {exc}",
            ) from exc

    async def get_stock_price(self, symbol: str) -> Optional[float]:
        """Get cached stock price.

        Args:
            symbol: Stock symbol

        Returns:
            Cached price or None if not found
        """
        try:
            client = await self._get_client()
            key = self._stock_info_key(symbol)
            price_str = await client.hget(key, "price")

            if price_str is None:
                return None

            return float(price_str)
        except RedisError as exc:
            raise BizException(
                ErrorCode.REDIS_OPERATION_ERROR,
                f"Failed to get stock price for {symbol}: {exc}",
            ) from exc
        except ValueError as exc:
            raise BizException(
                ErrorCode.REDIS_OPERATION_ERROR,
                f"Invalid cached price for {symbol}: {exc}",
            ) from exc

    async def get_stock_info(self, symbol: str) -> Optional[dict]:
        """Get full stock info from cache.

        Args:
            symbol: Stock symbol

        Returns:
            Dict with 'price' and 'updated_at' or None if not found
        """
        try:
            client = await self._get_client()
            key = self._stock_info_key(symbol)
            info = await client.hgetall(key)

            if not info:
                return None

            # Convert types
            return {
                "price": float(info["price"]),
                "updated_at": int(info["updated_at"]),
            }
        except RedisError as exc:
            raise BizException(
                ErrorCode.REDIS_OPERATION_ERROR,
                f"Failed to get stock info for {symbol}: {exc}",
            ) from exc
        except (ValueError, KeyError) as exc:
            raise BizException(
                ErrorCode.REDIS_OPERATION_ERROR,
                f"Invalid cached data for {symbol}: {exc}",
            ) from exc

    async def delete_stock_info(self, symbol: str) -> bool:
        """Delete stock info from cache.

        Args:
            symbol: Stock symbol

        Returns:
            True if deleted, False if not found
        """
        try:
            client = await self._get_client()
            key = self._stock_info_key(symbol)
            result = await client.delete(key)
            return result == 1
        except RedisError as exc:
            raise BizException(
                ErrorCode.REDIS_OPERATION_ERROR,
                f"Failed to delete stock info for {symbol}: {exc}",
            ) from exc

    async def get_stocks_updated_since(self, threshold_seconds: int) -> list[str]:
        """Get stocks updated within threshold.

        Useful for finding recently updated stock prices.

        Args:
            threshold_seconds: Only return stocks updated within this many seconds

        Returns:
            List of stock symbols updated recently
        """
        try:
            active_stocks = await self.get_active_stocks()
            recent_stocks = []
            cutoff_time = int(time.time()) - threshold_seconds

            for symbol in active_stocks:
                info = await self.get_stock_info(symbol)
                if info and info["updated_at"] >= cutoff_time:
                    recent_stocks.append(symbol)

            return recent_stocks
        except RedisError as exc:
            raise BizException(
                ErrorCode.REDIS_OPERATION_ERROR,
                f"Failed to get recently updated stocks: {exc}",
            ) from exc