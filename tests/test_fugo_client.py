"""Tests for FugoClient using fugle_marketdata RestClient."""

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from fugle_marketdata import FugleAPIError

from src.clients.fugle_client import FugoClient
from src.config import settings
from src.exceptions import BizException, ErrorCode
from src.stocks.schema import HistoricalCandle, IntradayCandle, IntradayQuoteResponse


class TestFugoClient:
    """Tests for FugoClient with mocked fugle_marketdata RestClient"""

    @pytest.fixture
    def mock_stock(self):
        """Create mock stock client."""
        mock = MagicMock()
        mock.intraday = MagicMock()
        mock.historical = MagicMock()
        return mock

    @pytest.fixture
    def fugo_client(self, mock_stock):
        """Create FugoClient instance with mocked RestClient."""
        with patch("src.clients.fugle_client.RestClient") as MockRestClient:
            mock_client = MagicMock()
            mock_client.stock = mock_stock
            MockRestClient.return_value = mock_client

            client = FugoClient(
                api_key=settings.FUGO_API_KEY,
                timeout=10,
                max_retries=3,
            )
            # Ensure the mock is used
            assert client.stock == mock_stock
            return client

    @pytest.mark.asyncio
    async def test_get_intraday_quote_success(self, fugo_client: FugoClient):
        """Test successful intraday quote fetch."""
        mock_quote_data = {
            "symbol": "2330",
            "name": "台積電",
            "lastPrice": "650.00",
            "change": "5.00",
            "changePercent": "0.77",
            "openPrice": "645.00",
            "highPrice": "655.00",
            "lowPrice": "640.00",
            "previousClose": "645.00",
            "total": {"tradeVolume": 1000000, "tradeValue": 650000000},
            "isClose": False,
        }

        fugo_client.stock.intraday.quote.return_value = mock_quote_data

        result = await fugo_client.get_intraday_quote("2330")

        assert isinstance(result, IntradayQuoteResponse)
        assert result.symbol == "2330"
        assert result.name == "台積電"
        assert result.lastPrice == Decimal("650.00")
        assert result.isClose is False
        fugo_client.stock.intraday.quote.assert_called_once_with(symbol="2330")

    @pytest.mark.asyncio
    async def test_get_intraday_quote_server_error(self, fugo_client: FugoClient):
        """Test intraday quote with 500 error."""
        mock_error = FugleAPIError(
            message="Internal Server Error",
            url="https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/2330",
            status_code=500,
            params={"symbol": "2330"},
            response_text="Internal Server Error",
        )

        fugo_client.stock.intraday.quote.side_effect = mock_error

        with pytest.raises(BizException) as exc_info:
            await fugo_client.get_intraday_quote("2330")

        assert exc_info.value.error_code == ErrorCode.FUGO_API_ERROR
        assert "server error" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_get_intraday_quote_client_error(self, fugo_client: FugoClient):
        """Test intraday quote with 400 error."""
        mock_error = FugleAPIError(
            message="Bad Request",
            url="https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/2330",
            status_code=400,
            params={"symbol": "2330"},
            response_text="Bad Request",
        )

        fugo_client.stock.intraday.quote.side_effect = mock_error

        with pytest.raises(BizException) as exc_info:
            await fugo_client.get_intraday_quote("2330")

        assert exc_info.value.error_code == ErrorCode.FUGO_API_ERROR
        assert "Fugle API error" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_get_intraday_candles_success_list(self, fugo_client: FugoClient):
        """Test successful intraday candles fetch (list response)."""
        mock_candles_data = [
            {
                "date": "2026-05-05",
                "time": "2026-05-05T09:00:00",
                "open": "645.00",
                "high": "650.00",
                "low": "640.00",
                "close": "648.00",
                "volume": 100000,
            },
            {
                "date": "2026-05-05",
                "time": "2026-05-05T09:05:00",
                "open": "648.00",
                "high": "652.00",
                "low": "647.00",
                "close": "651.00",
                "volume": 120000,
            },
        ]

        fugo_client.stock.intraday.candles.return_value = mock_candles_data

        result = await fugo_client.get_intraday_candles("2330")

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(c, IntradayCandle) for c in result)
        assert result[0].open == Decimal("645.00")
        assert result[0].volume == 100000
        fugo_client.stock.intraday.candles.assert_called_once_with(symbol="2330")

    @pytest.mark.asyncio
    async def test_get_intraday_candles_success_dict(self, fugo_client: FugoClient):
        """Test successful intraday candles fetch (dict response)."""
        mock_candles_data = {
            "data": [
                {
                    "date": "2026-05-05",
                    "open": "645.00",
                    "high": "650.00",
                    "low": "640.00",
                    "close": "648.00",
                    "volume": 100000,
                },
            ]
        }

        fugo_client.stock.intraday.candles.return_value = mock_candles_data

        result = await fugo_client.get_intraday_candles("2330")

        assert len(result) == 1
        assert result[0].open == Decimal("645.00")

    @pytest.mark.asyncio
    async def test_get_intraday_candles_empty(self, fugo_client: FugoClient):
        """Test intraday candles with empty response."""
        fugo_client.stock.intraday.candles.return_value = {}

        result = await fugo_client.get_intraday_candles("2330")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_historical_candles_success(self, fugo_client: FugoClient):
        """Test successful historical candles fetch."""
        mock_candles_data = [
            {
                "date": "2026-05-01",
                "open": "640.00",
                "high": "650.00",
                "low": "635.00",
                "close": "645.00",
                "volume": 500000,
            },
            {
                "date": "2026-05-02",
                "open": "645.00",
                "high": "655.00",
                "low": "640.00",
                "close": "650.00",
                "volume": 600000,
            },
        ]

        fugo_client.stock.historical.candles.return_value = mock_candles_data

        result = await fugo_client.get_historical_candles(
            "2330", "2026-05-01", "2026-05-02"
        )

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(c, HistoricalCandle) for c in result)
        assert result[0].candle_date.strftime("%Y-%m-%d") == "2026-05-01"
        assert result[0].close == Decimal("645.00")
        fugo_client.stock.historical.candles.assert_called_once_with(
            symbol="2330", from_="2026-05-01", to="2026-05-02"
        )

    @pytest.mark.asyncio
    async def test_get_historical_candles_with_params(self, fugo_client: FugoClient):
        """Test historical candles with date parameters."""
        fugo_client.stock.historical.candles.return_value = []

        await fugo_client.get_historical_candles("2330", "2026-01-01", "2026-04-30")

        # Verify params were passed correctly (from_ not from)
        fugo_client.stock.historical.candles.assert_called_once_with(
            symbol="2330", from_="2026-01-01", to="2026-04-30"
        )

    @pytest.mark.asyncio
    async def test_client_configuration(self, fugo_client: FugoClient):
        """Test that FugoClient is configured correctly."""
        assert fugo_client.api_key == settings.FUGO_API_KEY
        assert fugo_client.timeout == 10
        assert fugo_client.max_retries == 3
        assert hasattr(fugo_client, "_client")
        assert hasattr(fugo_client, "stock")

    @pytest.mark.asyncio
    async def test_fugle_api_error_no_status_code(self, fugo_client: FugoClient):
        """Test FugleAPIError without status code (network error)."""
        mock_error = FugleAPIError(
            message="Network error",
            url="https://api.fugle.tw",
            status_code=None,
            params={},
            response_text="",
        )

        fugo_client.stock.intraday.quote.side_effect = mock_error

        with pytest.raises(BizException) as exc_info:
            await fugo_client.get_intraday_quote("2330")

        assert exc_info.value.error_code == ErrorCode.FUGO_API_ERROR
        assert "Fugle API error" in exc_info.value.message