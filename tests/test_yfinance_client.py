"""Tests for YFinanceClient with real API calls."""

import pytest

from src.clients.yfinance_client import YFinanceClient
from src.stocks.schema import TickerResponse


class TestYFinanceClient:
    """Tests for YFinanceClient with real yfinance API"""

    @pytest.fixture
    def yfinance_client(self):
        """Create YFinanceClient instance for testing."""
        return YFinanceClient(timeout=30)

    @pytest.mark.asyncio
    async def test_search_tickers_apple(self, yfinance_client: YFinanceClient):
        """Test ticker search for Apple."""
        results = await yfinance_client.search_tickers("Apple", max_results=10)

        print(f"\nSearch 'Apple' results: {results}")

        assert len(results) > 0
        assert all(isinstance(r, TickerResponse) for r in results)
        # Should find AAPL
        apple_results = [r for r in results if "AAPL" in r.symbol]
        assert len(apple_results) > 0

    @pytest.mark.asyncio
    async def test_search_tickers_taiwan_stock(self, yfinance_client: YFinanceClient):
        """Test ticker search for Taiwan stock (2330 TSMC)."""
        results = await yfinance_client.search_tickers("TSMC", max_results=10)

        print(f"\nSearch 'TSMC' results: {results}")

        assert len(results) > 0
        # Should find TSM (Taiwan Semiconductor)
        tsmc_results = [r for r in results if "TSM" in r.symbol or "2330" in r.symbol]
        assert len(tsmc_results) > 0

    @pytest.mark.asyncio
    async def test_search_tickers_microsoft(self, yfinance_client: YFinanceClient):
        """Test ticker search for Microsoft."""
        results = await yfinance_client.search_tickers("Microsoft", max_results=5)

        print(f"\nSearch 'Microsoft' results: {results}")

        assert len(results) > 0
        # Should find MSFT
        msft_results = [r for r in results if r.symbol == "MSFT"]
        assert len(msft_results) > 0

    @pytest.mark.asyncio
    async def test_search_tickers_google(self, yfinance_client: YFinanceClient):
        """Test ticker search for Google."""
        results = await yfinance_client.search_tickers("Google", max_results=10)

        print(f"\nSearch 'Google' results: {results}")

        assert len(results) > 0
        # Should find GOOG or GOOGL
        google_results = [r for r in results if r.symbol in ("GOOG", "GOOGL")]
        assert len(google_results) > 0

    @pytest.mark.asyncio
    async def test_get_ticker_aapl(self, yfinance_client: YFinanceClient):
        """Test single ticker lookup for AAPL."""
        result = await yfinance_client.get_ticker("AAPL")

        print(f"\nGet ticker 'AAPL': {result}")

        assert result is not None
        assert isinstance(result, TickerResponse)
        assert result.symbol == "AAPL"
        assert result.name is not None
        assert "Apple" in result.name

    @pytest.mark.asyncio
    async def test_get_ticker_msft(self, yfinance_client: YFinanceClient):
        """Test single ticker lookup for MSFT."""
        result = await yfinance_client.get_ticker("MSFT")

        print(f"\nGet ticker 'MSFT': {result}")

        assert result is not None
        assert isinstance(result, TickerResponse)
        assert result.symbol == "MSFT"
        assert result.name is not None
        assert "Microsoft" in result.name

    @pytest.mark.asyncio
    async def test_get_ticker_tsm_taiwan(self, yfinance_client: YFinanceClient):
        """Test single ticker lookup for TSM (TSMC ADR)."""
        result = await yfinance_client.get_ticker("TSM")

        print(f"\nGet ticker 'TSM': {result}")

        assert result is not None
        assert isinstance(result, TickerResponse)
        assert result.symbol == "TSM"
        assert result.name is not None

    @pytest.mark.asyncio
    async def test_get_ticker_invalid_symbol(self, yfinance_client: YFinanceClient):
        """Test ticker lookup for invalid symbol."""
        result = await yfinance_client.get_ticker("INVALIDTICKER123")

        print(f"\nGet ticker 'INVALIDTICKER123': {result}")

        # Invalid ticker should return None
        assert result is None

    @pytest.mark.asyncio
    async def test_search_tickers_partial_symbol(self, yfinance_client: YFinanceClient):
        """Test ticker search with partial symbol."""
        results = await yfinance_client.search_tickers("AA", max_results=10)

        print(f"\nSearch 'AA' results: {results}")

        assert len(results) > 0
        # Should find stocks starting with AA
        aa_results = [r for r in results if r.symbol.startswith("AA")]
        assert len(aa_results) > 0

    def test_client_configuration(self, yfinance_client: YFinanceClient):
        """Test that YFinanceClient is configured correctly."""
        assert yfinance_client.timeout == 30
