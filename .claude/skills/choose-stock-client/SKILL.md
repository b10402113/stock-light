---
name: choose-stock-client
description: Helps decide between FugoClient and YFinanceClient for stock market data. Use when implementing API endpoints or services that need stock data, or when user asks which client to use for stock market operations.
---

# Choose Stock Data Client

## Quick Start

When implementing stock data operations, use this decision tree:

```
Is it Taiwan stock real-time data update?
├─ YES → Use FugoClient
└─ NO → Use YFinanceClient
```

## Decision Rules

### Use FugoClient (台股即時資料)

**Trigger conditions:**
- Taiwan stock real-time quotes (當日股價、即時報價)
- Intraday OHLC candles for current trading day
- Taiwan stock symbols WITHOUT ".TW" suffix (e.g., "2330", "2317")

**Available methods:**
- `get_intraday_quote(symbol)` - Latest quote data
- `get_intraday_candles(symbol)` - Today's intraday candles
- `get_ticker(symbol)` - Ticker metadata (台股代號查詢)

**Example:**
```python
# Real-time Taiwan stock price update
from src.clients import FugoClient

fugo_client = FugoClient()
quote = await fugo_client.get_intraday_quote("2330")  # 台積電即時報價
```

### Use YFinanceClient (其他功能)

**Trigger conditions:**
- Historical price retrieval (歷史股價)
- Stock search by name/symbol (股票搜尋)
- US stock information (美股股價)
- Global stocks with suffix (e.g., "2330.TW", "AAPL")

**Available methods:**
- `search_tickers(query)` - Search stocks by name/symbol
- `get_ticker(symbol)` - Get ticker info for any symbol

**Example:**
```python
# Stock search or US stocks
from src.clients import YFinanceClient

yf_client = YFinanceClient()
tickers = await yf_client.search_tickers("Apple")  # 搜尋股票
ticker = await yf_client.get_ticker("AAPL")  # 美股資訊
```

## Workflow

When implementing a new stock data feature:

1. **Identify the use case**
   - What type of data? (real-time vs historical)
   - Which market? (Taiwan vs US/Global)
   - What operation? (search, quote, history)

2. **Apply decision matrix**

| Use Case | Market | Client | Method |
|----------|---------|---------|---------|
| 即時報價更新 | 台股 | FugoClient | `get_intraday_quote()` |
| 當日分時K線 | 台股 | FugoClient | `get_intraday_candles()` |
| 股票搜尋 | 全市場 | YFinanceClient | `search_tickers()` |
| 歷史股價 | 全市場 | YFinanceClient | (待實作) |
| 美股資訊 | 美股 | YFinanceClient | `get_ticker()` |
| 台股代號查詢 | 台股 | FugoClient | `get_ticker()` |

3. **Verify symbol format**
   - FugoClient: Use symbol WITHOUT suffix ("2330")
   - YFinanceClient: Use symbol WITH suffix for Taiwan ("2330.TW")

4. **Import and implement**
   ```python
   from src.clients import FugoClient, YFinanceClient
   # Use the chosen client based on rules above
   ```

## Common Patterns

### Pattern 1: Real-time Taiwan stock price service
```python
# src/stocks/service.py
from src.clients import FugoClient

async def update_stock_price(symbol: str) -> StockPrice:
    """Update Taiwan stock real-time price."""
    client = FugoClient()
    quote = await client.get_intraday_quote(symbol)
    # Process quote data...
```

### Pattern 2: Stock search endpoint
```python
# src/stocks/service.py
from src.clients import YFinanceClient

async def search_stocks(query: str) -> list[TickerResponse]:
    """Search stocks by name or symbol."""
    client = YFinanceClient()
    return await client.search_tickers(query)
```

### Pattern 3: Hybrid approach (fallback)
```python
# When YFinanceClient fails for Taiwan stock lookup,
# fallback to FugoClient
async def get_ticker_info(symbol: str) -> TickerResponse | None:
    yf_client = YFinanceClient()

    # Try YFinance first (supports global)
    ticker = await yf_client.get_ticker(f"{symbol}.TW")
    if ticker:
        return ticker

    # Fallback to FugoClient for Taiwan stocks
    fugo_client = FugoClient()
    return await fugo_client.get_ticker(symbol)
```

## Key Differences

| Aspect | FugoClient | YFinanceClient |
|---------|------------|----------------|
| Market | 台股專用 | 全球市場 |
| Data type | 即時資料 | 歷史/搜尋 |
| Speed | Fast (專用API) | Slower (yfinance sync) |
| Symbol format | "2330" | "2330.TW", "AAPL" |
| Async support | Native async | Threadpool wrapper |
| Cost | Paid API (Fugo) | Free (yfinance) |

## Checklist

When writing stock data code:

- [ ] Identified the use case (real-time vs historical)
- [ ] Determined the market (Taiwan vs US/Global)
- [ ] Selected the correct client using decision matrix
- [ ] Used correct symbol format (suffix handling)
- [ ] Imported client from `src.clients`
- [ ] Called appropriate method for the operation
- [ ] Handled BizException errors from client calls

## Notes

- FugoClient is for **paid real-time Taiwan stock data** - use sparingly
- YFinanceClient is for **free historical/global data** - more flexible
- Always handle BizException from both clients
- Consider rate limiting for YFinanceClient (yfinance may have limits)