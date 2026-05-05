"""Tests for FugoClient."""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.exceptions import BizException, ErrorCode
from src.stocks.client import FugoClient
from src.stocks.schema import HistoricalCandle, IntradayCandle, IntradayQuoteResponse


class TestFugoClient:
    """Tests for FugoClient with mocked httpx"""

    @pytest.fixture
    def fugo_client(self):
        """Create FugoClient instance for testing."""
        return FugoClient(
            api_key="test-api-key",
            base_url="https://api.fugle.tw/marketdata/v1.0/stock",
            timeout=10,
            max_retries=3,
        )

    @pytest.mark.asyncio
    async def test_get_intraday_quote_success(self, fugo_client: FugoClient):
        """Test successful intraday quote fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
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

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await fugo_client.get_intraday_quote("2330")

            assert isinstance(result, IntradayQuoteResponse)
            assert result.symbol == "2330"
            assert result.name == "台積電"
            assert result.lastPrice == Decimal("650.00")
            assert result.isClose is False
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_intraday_quote_server_error(self, fugo_client: FugoClient):
        """Test intraday quote with 500 error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            with pytest.raises(BizException) as exc_info:
                await fugo_client.get_intraday_quote("2330")

            assert exc_info.value.error_code == ErrorCode.FUGO_API_ERROR
            assert "server error" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_get_intraday_quote_client_error(self, fugo_client: FugoClient):
        """Test intraday quote with 400 error (no retry)."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            with pytest.raises(BizException) as exc_info:
                await fugo_client.get_intraday_quote("2330")

            assert exc_info.value.error_code == ErrorCode.FUGO_API_ERROR
            assert "client error" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_get_intraday_candles_success_list(self, fugo_client: FugoClient):
        """Test successful intraday candles fetch (list response)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
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

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await fugo_client.get_intraday_candles("2330")

            assert isinstance(result, list)
            assert len(result) == 2
            assert all(isinstance(c, IntradayCandle) for c in result)
            assert result[0].open == Decimal("645.00")
            assert result[0].volume == 100000

    @pytest.mark.asyncio
    async def test_get_intraday_candles_success_dict(self, fugo_client: FugoClient):
        """Test successful intraday candles fetch (dict response)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
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

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await fugo_client.get_intraday_candles("2330")

            assert len(result) == 1
            assert result[0].open == Decimal("645.00")

    @pytest.mark.asyncio
    async def test_get_intraday_candles_empty(self, fugo_client: FugoClient):
        """Test intraday candles with empty response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await fugo_client.get_intraday_candles("2330")

            assert result == []

    @pytest.mark.asyncio
    async def test_get_historical_candles_success(self, fugo_client: FugoClient):
        """Test successful historical candles fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
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

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await fugo_client.get_historical_candles(
                "2330", "2026-05-01", "2026-05-02"
            )

            assert isinstance(result, list)
            assert len(result) == 2
            assert all(isinstance(c, HistoricalCandle) for c in result)
            assert result[0].candle_date.strftime("%Y-%m-%d") == "2026-05-01"
            assert result[0].close == Decimal("645.00")

    @pytest.mark.asyncio
    async def test_get_historical_candles_with_params(self, fugo_client: FugoClient):
        """Test historical candles with date parameters."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            await fugo_client.get_historical_candles("2330", "2026-01-01", "2026-04-30")

            # Verify params were passed
            call_args = mock_get.call_args
            assert "params" in call_args.kwargs
            assert call_args.kwargs["params"]["from"] == "2026-01-01"
            assert call_args.kwargs["params"]["to"] == "2026-04-30"

    @pytest.mark.asyncio
    async def test_headers_include_api_key(self, fugo_client: FugoClient):
        """Test that API key is included in headers."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "symbol": "2330",
            "name": "台積電",
            "isClose": False,
        }

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            await fugo_client.get_intraday_quote("2330")

            call_args = mock_get.call_args
            assert "headers" in call_args.kwargs
            assert call_args.kwargs["headers"]["X-API-KEY"] == "test-api-key"

    @pytest.mark.asyncio
    async def test_client_configuration(self, fugo_client: FugoClient):
        """Test that FugoClient is configured correctly."""
        assert fugo_client.api_key == "test-api-key"
        assert fugo_client.base_url == "https://api.fugle.tw/marketdata/v1.0/stock"
        assert fugo_client.timeout == 10
        assert fugo_client.max_retries == 3