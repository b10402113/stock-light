"""Fugle API client using fugle_marketdata SDK - only wraps API calls, no business logic."""

from fugle_marketdata import RestClient, FugleAPIError

from src.config import settings
from src.clients.base import BaseHTTPClient, get_retry_decorator
from src.exceptions import BizException, ErrorCode
from src.stocks.schema import HistoricalCandle, IntradayCandle, IntradayQuoteResponse


class FugoClient(BaseHTTPClient):
    """Fugle API client for stock market data.

    This client uses fugle_marketdata RestClient - no business logic.
    All methods raise BizException on API errors.
    """

    def __init__(
        self,
        api_key: str | None = None,
        timeout: int | None = None,
        max_retries: int | None = None,
    ):
        super().__init__(
            timeout=timeout or settings.FUGO_TIMEOUT,
            max_retries=max_retries or settings.FUGO_MAX_RETRIES,
        )
        self.api_key = api_key or settings.FUGO_API_KEY
        self._client = RestClient(api_key=self.api_key)
        self.stock = self._client.stock

    def _handle_fugle_error(self, e: FugleAPIError) -> None:
        """Convert FugleAPIError to BizException.

        Args:
            e: FugleAPIError exception

        Raises:
            BizException: Converted exception
        """
        if e.status_code and e.status_code >= 500:
            raise BizException(
                ErrorCode.FUGO_API_ERROR,
                f"Fugle API server error: {e.status_code} - {e.message}",
            )
        else:
            raise BizException(
                ErrorCode.FUGO_API_ERROR,
                f"Fugle API error: {e.message}",
            )

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
        try:
            # RestClient is synchronous, run in threadpool if needed
            data = self.stock.intraday.quote(symbol=symbol)
            return IntradayQuoteResponse(**data)
        except FugleAPIError as e:
            self._handle_fugle_error(e)

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
        try:
            data = self.stock.intraday.candles(symbol=symbol)
            # Handle different response formats
            if isinstance(data, list):
                candles = data
            elif isinstance(data, dict):
                candles = data.get("data", data.get("candles", []))
            else:
                candles = []
            return [IntradayCandle(**c) for c in candles]
        except FugleAPIError as e:
            self._handle_fugle_error(e)

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
        try:
            data = self.stock.historical.candles(
                symbol=symbol,
                from_=from_date,
                to=to_date,
            )
            # Handle different response formats
            if isinstance(data, list):
                candles = data
            elif isinstance(data, dict):
                candles = data.get("data", data.get("candles", []))
            else:
                candles = []
            return [HistoricalCandle(**c) for c in candles]
        except FugleAPIError as e:
            self._handle_fugle_error(e)