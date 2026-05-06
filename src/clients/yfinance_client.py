"""YFinance API client - only wraps API calls, no business logic."""

from fastapi.concurrency import run_in_threadpool
import yfinance as yf

from src.exceptions import BizException, ErrorCode
from src.stocks.schema import TickerResponse


class YFinanceClient:
    """YFinance API client for stock ticker search.

    This client only wraps API calls - no business logic.
    yfinance is sync-only, so all methods use run_in_threadpool.
    """

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    async def search_tickers(
        self, query: str, max_results: int = 10
    ) -> list[TickerResponse]:
        """Search for stock tickers by symbol or company name.

        Args:
            query: Search query (symbol or company name)
            max_results: Maximum number of results to return

        Returns:
            List of TickerResponse with symbol and name

        Raises:
            BizException: On API errors
        """
        try:
            results = await run_in_threadpool(
                self._search_tickers_sync, query, max_results
            )
            return results
        except Exception as e:
            raise BizException(
                ErrorCode.YFINANCE_API_ERROR,
                f"YFinance search failed: {str(e)}",
            )

    def _search_tickers_sync(
        self, query: str, max_results: int
    ) -> list[TickerResponse]:
        """Sync implementation of ticker search."""
        search = yf.Search(query, max_results=max_results, timeout=self.timeout)
        quotes = search.quotes

        tickers = []
        for quote in quotes:
            symbol = quote.get("symbol", "")
            # yfinance uses lowercase keys: shortname, longname
            name = quote.get("shortname") or quote.get("longname", "")

            if symbol and name:
                tickers.append(TickerResponse(symbol=symbol, name=name))

        return tickers

    async def get_ticker(self, symbol: str) -> TickerResponse | None:
        """Get ticker info for a single symbol.

        Args:
            symbol: Stock symbol (e.g., "AAPL", "2330.TW")

        Returns:
            TickerResponse with symbol and name, or None if not found

        Raises:
            BizException: On API errors
        """
        try:
            result = await run_in_threadpool(self._get_ticker_sync, symbol)
            return result
        except Exception as e:
            raise BizException(
                ErrorCode.YFINANCE_API_ERROR,
                f"YFinance ticker lookup failed: {str(e)}",
            )

    def _get_ticker_sync(self, symbol: str) -> TickerResponse | None:
        """Sync implementation of single ticker lookup."""
        ticker = yf.Ticker(symbol)

        # Use info property for name (fast_info doesn't have name)
        info = ticker.info
        if not info:
            return None

        # Get name from info
        name = info.get("shortName") or info.get("longName", "")
        if not name:
            return None

        return TickerResponse(symbol=symbol, name=name)
