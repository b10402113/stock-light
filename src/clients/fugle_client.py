"""Fugo API client - only wraps API calls, no business logic."""

import asyncio
import httpx
from aiolimiter import AsyncLimiter

from src.config import settings
from src.clients.base import BaseHTTPClient, get_retry_decorator
from src.exceptions import ErrorCode
from src.stocks.schema import HistoricalCandle, IntradayCandle, IntradayQuoteResponse, TickerResponse


class FugoClient(BaseHTTPClient):
    """Fugo API client for stock market data with rate limiting.

    This client only wraps API calls - no business logic.
    All methods raise BizException on API errors.

    Rate limiting:
    - Time window: Max 50 requests per minute (Fugle API limit)
    - Concurrency: Max 10 concurrent requests (configurable)
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: int | None = None,
        max_retries: int | None = None,
    ):
        super().__init__(
            timeout=timeout or settings.FUGO_TIMEOUT,
            max_retries=max_retries or settings.FUGO_MAX_RETRIES,
        )
        self.api_key = api_key or settings.FUGO_API_KEY
        self.base_url = base_url or settings.FUGO_BASE_URL

        # Rate limiter: 每分鐘最多 50 個請求（時間窗口）
        self.rate_limiter = AsyncLimiter(
            max_rate=settings.FUGLE_RATE_LIMIT,  # 50 requests
            time_period=60  # 60 seconds
        )

        # Semaphore: 同時最多 10 個並發請求
        self.semaphore = asyncio.Semaphore(settings.FUGLE_MAX_CONCURRENT_REQUESTS)

    def _get_headers(self) -> dict[str, str]:
        """Get API headers with authentication."""
        return {"X-API-KEY": self.api_key}

    @get_retry_decorator(max_retries=3)
    async def get_intraday_quote(self, symbol: str) -> IntradayQuoteResponse:
        """Get latest stock information by symbol (intraday quote) with rate limiting.

        Args:
            symbol: Stock symbol (e.g., "2330")

        Returns:
            IntradayQuoteResponse with quote data

        Raises:
            BizException: On API errors
        """
        # Apply rate limiting (time window + concurrency)
        async with self.rate_limiter:  # 時間窗口限制：每分鐘最多 50 個請求
            async with self.semaphore:  # 並發數限制：同時最多 10 個請求
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    url = f"{self.base_url}/intraday/quote/{symbol}"
                    response = await client.get(url, headers=self._get_headers())

                    if response.status_code != 200:
                        self._handle_error(response, "Fugo API", ErrorCode.FUGO_API_ERROR)

                    return IntradayQuoteResponse(**response.json())

    @get_retry_decorator(max_retries=3)
    async def get_intraday_candles(self, symbol: str) -> list[IntradayCandle]:
        """Get intraday OHLC candles for current trading day.

        Args:
            symbol: Stock symbol (e.g., "2330")

        Returns:
            List of IntradayCandle

        Raises:
            BizException: On API errors
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.base_url}/intraday/candles/{symbol}"
            response = await client.get(url, headers=self._get_headers())

            if response.status_code != 200:
                self._handle_error(response, "Fugo API", ErrorCode.FUGO_API_ERROR)

            data = response.json()
            # Handle different response formats
            if isinstance(data, list):
                candles = data
            elif isinstance(data, dict):
                candles = data.get("data", data.get("candles", []))
            else:
                candles = []

            return [IntradayCandle(**c) for c in candles]

    @get_retry_decorator(max_retries=3)
    async def get_historical_candles(
        self,
        symbol: str,
        from_date: str,
        to_date: str,
    ) -> list[HistoricalCandle]:
        """Get historical OHLC candles.

        Args:
            symbol: Stock symbol (e.g., "2330")
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)

        Returns:
            List of HistoricalCandle

        Raises:
            BizException: On API errors
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.base_url}/historical/candles/{symbol}"
            params = {"from": from_date, "to": to_date}
            response = await client.get(
                url,
                headers=self._get_headers(),
                params=params,
            )

            if response.status_code != 200:
                self._handle_error(response, "Fugo API", ErrorCode.FUGO_API_ERROR)

            data = response.json()
            # Handle different response formats
            if isinstance(data, list):
                candles = data
            elif isinstance(data, dict):
                candles = data.get("data", data.get("candles", []))
            else:
                candles = []

            return [HistoricalCandle(**c) for c in candles]

    @get_retry_decorator(max_retries=3)
    async def get_ticker(self, symbol: str) -> TickerResponse | None:
        """Get ticker metadata for a single symbol.

        Args:
            symbol: Stock symbol (e.g., "2330")

        Returns:
            TickerResponse with symbol and name, or None if not found

        Raises:
            BizException: On API errors (except 404)
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.base_url}/intraday/ticker/{symbol}"
            response = await client.get(url, headers=self._get_headers())

            if response.status_code == 404:
                return None

            if response.status_code != 200:
                self._handle_error(response, "Fugo API", ErrorCode.FUGO_API_ERROR)

            return TickerResponse(**response.json())

    @get_retry_decorator(max_retries=3)
    async def get_tickers(self) -> list[TickerResponse]:
        """Get all Taiwan stock tickers.

        Returns:
            List of TickerResponse with all Taiwan stocks (TSE + OTC)

        Raises:
            BizException: On API errors
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.base_url}/intraday/tickers"
            response = await client.get(url, headers=self._get_headers())

            if response.status_code != 200:
                self._handle_error(response, "Fugo API", ErrorCode.FUGO_API_ERROR)

            data = response.json()
            # Handle different response formats
            if isinstance(data, list):
                tickers = data
            elif isinstance(data, dict):
                tickers = data.get("data", [])
            else:
                tickers = []

            return [TickerResponse(**t) for t in tickers]