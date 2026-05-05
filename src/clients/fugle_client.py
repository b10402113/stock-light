"""Fugo API client - only wraps API calls, no business logic."""

import httpx

from src.config import settings
from src.clients.base import BaseHTTPClient, get_retry_decorator
from src.exceptions import ErrorCode
from src.stocks.schema import HistoricalCandle, IntradayCandle, IntradayQuoteResponse


class FugoClient(BaseHTTPClient):
    """Fugo API client for stock market data.

    This client only wraps API calls - no business logic.
    All methods raise BizException on API errors.
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

    def _get_headers(self) -> dict[str, str]:
        """Get API headers with authentication."""
        return {"X-API-KEY": self.api_key}

    @get_retry_decorator(max_retries=3)
    async def get_intraday_quote(self, symbol: str) -> IntradayQuoteResponse:
        """Get latest stock information by symbol (intraday quote).

        Args:
            symbol: Stock symbol (e.g., "2330")

        Returns:
            IntradayQuoteResponse with quote data

        Raises:
            BizException: On API errors
        """
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