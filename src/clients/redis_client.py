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
    - Stock price cache: Redis Hash (key: stock:info:{stock_id})

    Fields in stock info hash:
    - symbol: stock symbol (string, e.g., "006208")
    - price: current price (float)
    - updated_at: last update timestamp (int, Unix timestamp)
    - source: data source (int, 1=Fugle, 2=YFinance, default=1)
    """

    ACTIVE_STOCKS_KEY = "stocks:active"
    STOCK_INFO_KEY_PREFIX = "stock:info:"

    def __init__(self, redis_url: str = None, timeout: int = None, pool: Redis = None):
        """Initialize Redis client.

        Args:
            redis_url: Redis connection URL (used if pool not provided)
            timeout: Connection timeout in seconds
            pool: External Redis connection pool (e.g., from ARQ)
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self.timeout = timeout or settings.REDIS_TIMEOUT
        self._client: Optional[Redis] = pool
        self._external_pool = pool is not None  # Track if pool is externally provided

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
        """Close Redis connection.

        Only closes connections created internally. External pools are not closed.
        """
        if self._client and not self._external_pool:
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

    async def add_active_stock(self, stock_id: int) -> bool:
        """Add stock to active monitoring list.

        Uses SADD (atomic operation) to prevent race conditions.

        Args:
            stock_id: Stock primary key ID

        Returns:
            True if added (new member), False if already exists
        """
        try:
            client = await self._get_client()
            result = await client.sadd(self.ACTIVE_STOCKS_KEY, str(stock_id))
            return result == 1
        except RedisError as exc:
            raise BizException(
                ErrorCode.REDIS_OPERATION_ERROR,
                f"Failed to add active stock {stock_id}: {exc}",
            ) from exc

    async def remove_active_stock(self, stock_id: int) -> bool:
        """Remove stock from active monitoring list.

        Uses SREM (atomic operation).

        Args:
            stock_id: Stock primary key ID

        Returns:
            True if removed, False if not in set
        """
        try:
            client = await self._get_client()
            result = await client.srem(self.ACTIVE_STOCKS_KEY, str(stock_id))
            return result == 1
        except RedisError as exc:
            raise BizException(
                ErrorCode.REDIS_OPERATION_ERROR,
                f"Failed to remove active stock {stock_id}: {exc}",
            ) from exc

    async def get_active_stocks(self) -> list[int]:
        """Get all active stocks being monitored.

        Uses SMEMBERS to retrieve the full set.

        Returns:
            List of stock IDs (decoded from bytes if needed)
        """
        try:
            client = await self._get_client()
            members = await client.smembers(self.ACTIVE_STOCKS_KEY)

            # Decode bytes to integers if needed (ARQ pool doesn't use decode_responses)
            decoded_members = []
            for member in members:
                if isinstance(member, bytes):
                    decoded_members.append(int(member.decode("utf-8")))
                else:
                    decoded_members.append(int(member))

            return sorted(decoded_members)
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

    def _stock_info_key(self, stock_id: int) -> str:
        """Generate stock info hash key.

        Args:
            stock_id: Stock primary key ID

        Returns:
            Redis key string (e.g., "stock:info:123")
        """
        return f"{self.STOCK_INFO_KEY_PREFIX}{stock_id}"

    async def set_stock_price(
        self, stock_id: int, symbol: str, price: float, source: int = 1
    ) -> bool:
        """Update stock price in cache.

        Uses HSET (atomic operation) to update all fields.

        Args:
            stock_id: Stock primary key ID
            symbol: Stock symbol (e.g., '006208')
            price: Current price
            source: Data source (1=Fugle, 2=YFinance, default=1)

        Returns:
            True if successful
        """
        try:
            client = await self._get_client()
            key = self._stock_info_key(stock_id)
            timestamp = int(time.time())

            # HSET is atomic - updates all fields in single operation
            await client.hset(
                key,
                mapping={
                    "symbol": symbol,
                    "price": str(price),
                    "updated_at": timestamp,
                    "source": str(source),
                },
            )
            return True
        except RedisError as exc:
            raise BizException(
                ErrorCode.REDIS_OPERATION_ERROR,
                f"Failed to set stock price for stock_id {stock_id}: {exc}",
            ) from exc

    async def get_stock_price(self, stock_id: int) -> Optional[float]:
        """Get cached stock price.

        Args:
            stock_id: Stock primary key ID

        Returns:
            Cached price or None if not found
        """
        try:
            client = await self._get_client()
            key = self._stock_info_key(stock_id)
            price_str = await client.hget(key, "price")

            if price_str is None:
                return None

            # Decode bytes to string if needed (ARQ pool doesn't use decode_responses)
            if isinstance(price_str, bytes):
                price_str = price_str.decode("utf-8")

            return float(price_str)
        except RedisError as exc:
            raise BizException(
                ErrorCode.REDIS_OPERATION_ERROR,
                f"Failed to get stock price for stock_id {stock_id}: {exc}",
            ) from exc
        except ValueError as exc:
            raise BizException(
                ErrorCode.REDIS_OPERATION_ERROR,
                f"Invalid cached price for stock_id {stock_id}: {exc}",
            ) from exc

    async def get_stock_info(self, stock_id: int) -> Optional[dict]:
        """Get full stock info from cache.

        Args:
            stock_id: Stock primary key ID

        Returns:
            Dict with 'symbol', 'price', 'updated_at', and 'source' or None if not found
            - Returns None if price/updated_at missing (incomplete cache)
            - Source defaults to 1 (Fugle) for backward compatibility
        """
        try:
            client = await self._get_client()
            key = self._stock_info_key(stock_id)
            info = await client.hgetall(key)

            if not info:
                return None

            # Decode bytes to strings if needed (ARQ pool doesn't use decode_responses)
            decoded_info = {}
            for k, v in info.items():
                # Decode key
                key_str = k.decode("utf-8") if isinstance(k, bytes) else k
                # Decode value
                val_str = v.decode("utf-8") if isinstance(v, bytes) else v
                decoded_info[key_str] = val_str

            # Check if essential fields exist (price and updated_at)
            if "price" not in decoded_info or "updated_at" not in decoded_info:
                # Incomplete cache - return None to trigger update
                # But preserve symbol and source if available for batch task routing
                if "symbol" in decoded_info and "source" in decoded_info:
                    # Return dict with only symbol/source (special case for startup)
                    return {
                        "symbol": decoded_info["symbol"],
                        "source": int(decoded_info["source"]),
                        "incomplete": True,
                    }
                return None

            # Convert types with backward compatibility for missing source field
            return {
                "symbol": decoded_info.get("symbol", ""),
                "price": float(decoded_info["price"]),
                "updated_at": int(decoded_info["updated_at"]),
                "source": int(decoded_info.get("source", "1")),  # Default to Fugle (1) if missing
            }
        except RedisError as exc:
            raise BizException(
                ErrorCode.REDIS_OPERATION_ERROR,
                f"Failed to get stock info for stock_id {stock_id}: {exc}",
            ) from exc
        except (ValueError, KeyError) as exc:
            raise BizException(
                ErrorCode.REDIS_OPERATION_ERROR,
                f"Invalid cached data for stock_id {stock_id}: {exc}",
            ) from exc

    async def delete_stock_info(self, stock_id: int) -> bool:
        """Delete stock info from cache.

        Args:
            stock_id: Stock primary key ID

        Returns:
            True if deleted, False if not found
        """
        try:
            client = await self._get_client()
            key = self._stock_info_key(stock_id)
            result = await client.delete(key)
            return result == 1
        except RedisError as exc:
            raise BizException(
                ErrorCode.REDIS_OPERATION_ERROR,
                f"Failed to delete stock info for stock_id {stock_id}: {exc}",
            ) from exc

    async def get_stocks_updated_since(
        self, stock_ids: list[int], threshold_seconds: int
    ) -> list[int]:
        """Get stocks updated within threshold.

        Useful for finding recently updated stock prices.

        Args:
            stock_ids: List of stock IDs to check
            threshold_seconds: Only return stocks updated within this many seconds

        Returns:
            List of stock IDs updated recently
        """
        try:
            recent_stock_ids = []
            cutoff_time = int(time.time()) - threshold_seconds

            for stock_id in stock_ids:
                info = await self.get_stock_info(stock_id)
                if info and not info.get("incomplete") and info["updated_at"] >= cutoff_time:
                    recent_stock_ids.append(stock_id)

            return recent_stock_ids
        except RedisError as exc:
            raise BizException(
                ErrorCode.REDIS_OPERATION_ERROR,
                f"Failed to get recently updated stocks: {exc}",
            ) from exc

    async def batch_set_stock_prices(
        self, stock_data: list[tuple[int, str, float, int]]
    ) -> int:
        """Batch update multiple stock prices using Redis Pipeline.

        Reduces network I/O by executing all HSET commands in single round-trip.

        Args:
            stock_data: List of tuples (stock_id, symbol, price, source)
                - stock_id: Stock primary key ID
                - symbol: Stock symbol (e.g., '006208')
                - price: Current price
                - source: Data source (1=Fugle, 2=YFinance)

        Returns:
            Number of stocks successfully updated

        Raises:
            BizException: On Redis operation errors
        """
        try:
            client = await self._get_client()
            timestamp = int(time.time())

            # Create pipeline for batch operations
            pipeline = client.pipeline()

            for stock_id, symbol, price, source in stock_data:
                key = self._stock_info_key(stock_id)
                # Add HSET command to pipeline (no execution yet)
                pipeline.hset(
                    key,
                    mapping={
                        "symbol": symbol,
                        "price": str(price),
                        "updated_at": timestamp,
                        "source": str(source),
                    },
                )

            # Execute all commands in single network round-trip
            results = await pipeline.execute()

            # Return count of successful updates
            return len(results)
        except RedisError as exc:
            raise BizException(
                ErrorCode.REDIS_OPERATION_ERROR,
                f"Failed to batch set stock prices: {exc}",
            ) from exc