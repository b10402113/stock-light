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

    async def get_current_price(self, symbol: str) -> float | None:
        """Get current price for a single symbol.

        Args:
            symbol: Stock symbol (e.g., "AAPL", "2330.TW")

        Returns:
            Current price as float, or None if not found

        Raises:
            BizException: On API errors
        """
        try:
            ticker = await run_in_threadpool(lambda: yf.Ticker(symbol))
            info = await run_in_threadpool(lambda: ticker.info)

            # Try multiple price fields (yfinance API variations)
            price = (
                info.get("currentPrice")
                or info.get("regularMarketPrice")
                or info.get("lastPrice")
            )

            if price is None:
                return None

            return float(price)
        except Exception as e:
            raise BizException(
                ErrorCode.YFINANCE_API_ERROR,
                f"YFinance price lookup failed for {symbol}: {str(e)}",
            ) from e

    async def get_historical_prices(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> list[dict]:
        """Get historical OHLCV prices for a symbol.

        Args:
            symbol: Stock symbol (e.g., "AAPL", "2330.TW")
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            List of dicts with date, open, high, low, close, volume

        Raises:
            BizException: On API errors
        """
        try:
            ticker = await run_in_threadpool(lambda: yf.Ticker(symbol))
            hist = await run_in_threadpool(
                lambda: ticker.history(start=start_date, end=end_date, auto_adjust=False)
            )

            if hist.empty:
                return []

            # Convert DataFrame to list of dicts
            result = []
            for idx, row in hist.iterrows():
                result.append({
                    "date": idx.date(),
                    "open": float(row.get("Open", 0)),
                    "high": float(row.get("High", 0)),
                    "low": float(row.get("Low", 0)),
                    "close": float(row.get("Close", 0)),
                    "volume": int(row.get("Volume", 0)),
                })

            return result
        except Exception as e:
            raise BizException(
                ErrorCode.YFINANCE_API_ERROR,
                f"YFinance historical prices failed for {symbol}: {str(e)}",
            ) from e
