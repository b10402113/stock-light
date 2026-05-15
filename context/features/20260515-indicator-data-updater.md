# Indicator Data Updater Spec

## Overview

The Indicator Data Updater is a scheduled worker that maintains up-to-date technical indicator values for stocks with active subscriptions. It operates independently of user subscription conditions, focusing solely on preparing indicator data for stocks that users are currently watching.

The worker follows a decoupled architecture: subscription creation only persists data, while this worker runs on schedule to batch process all active stocks with indicator subscriptions, enabling efficient resource management and consistent data availability.

## Requirements

### 1. Scheduled Worker Setup

- Create ARQ cron job `update_indicator_data` with configurable interval (default: every 5 minutes)
- Add `INDICATOR_UPDATE_INTERVAL_MINUTES` to config.py (default: 5)
- Worker retrieves stocks with active indicator subscriptions from `indicator_subscriptions` table
- Query returns list of unique `(stock_id, indicator_key)` combinations where:
  - `is_deleted=False`
  - Stock has at least one active indicator subscription
  - Example output: `['2330:RSI_5_D', '2330:RSI_14_D', '2330:MACD_12_26_9_D']`

### 2. Redis Queue Integration

- Push processing tasks to Redis queue for batch distribution
- Use existing Redis infrastructure from `src/redis_client/`
- Batch size configurable via `INDICATOR_BATCH_SIZE` (default: 50 stocks)
- Queue structure: `{stock_id}:{indicator_key}` items

### 3. Data Fetching Strategy

- Check `daily_prices` table for available historical data
- If sufficient data exists (at least required period days):
  - Use existing `daily_prices` records for calculation
- If insufficient data:
  - Call `YFinanceClient.get_historical_prices()` to fetch missing data
  - Upsert to `daily_prices` table via `DailyPriceService.bulk_insert()`
- Required periods vary by indicator:
  - RSI: needs `period` days (e.g., RSI_14 needs 14+ days)
  - SMA: needs `period` days (e.g., SMA_20 needs 20+ days)
  - KDJ: needs `n` days (e.g., KDJ_9_3_3 needs 9+ days)
  - MACD: needs `slow_period` days (e.g., MACD_12_26_9 needs 26+ days)

### 4. Indicator Calculation

- Use existing calculation functions from `src/stocks/indicators.py`
- Calculate all indicators for a stock in single pass (optimization)
- Indicator key parsing: `{TYPE}_{PARAMS}_{TIMEFRAME}`
  - Example: `RSI_14_D` → type=RSI, period=14, timeframe=DAILY
  - Example: `MACD_12_26_9_D` → type=MACD, fast=12, slow=26, signal=9, timeframe=DAILY
- Calculate based on timeframe:
  - `D` (DAILY): use daily_prices data
  - `W` (WEEKLY): aggregate daily to weekly or fetch weekly data

### 5. Database Updates

- Upsert results to `stock_indicator` table (being created in current feature)
- Use `StockIndicatorService.upsert()` method
- Update `updated_at` with BIGINT Unix timestamp (never NULL)
- JSONB data structure by indicator type:
  - RSI: `{"value": 70.5}`
  - SMA: `{"value": 150.25}`
  - KDJ: `{"k": 80, "d": 75, "j": 85}`
  - MACD: `{"macd": 0.5, "signal": 0.3, "histogram": 0.2}`
- Handle concurrent updates safely (upsert logic)

### 6. Error Handling

- Log errors for individual stock failures without stopping batch
- Track failed stocks in Redis with retry count
- Max retries configurable via `INDICATOR_MAX_RETRIES` (default: 3)
- Send alert to monitoring system on persistent failures
- Graceful handling of yfinance API timeouts

### 7. Performance Optimization

- Batch database queries (fetch daily_prices for multiple stocks)
- Parallel indicator calculations with asyncio.gather
- Cache recently fetched price data (Redis TTL: 5 minutes)
- Connection pooling for yfinance API calls

## Technical Specifications

### Worker Entry Point

```python
# src/tasks/jobs/indicator_jobs.py

async def update_indicator_data(ctx: Dict) -> None:
    """
    Cron job to update technical indicators for stocks with active subscriptions.

    Flow:
    1. Query active (stock_id, indicator_key) pairs
    2. Batch by stock_id to minimize API calls
    3. Fetch historical prices (daily_prices or yfinance)
    4. Calculate indicators
    5. Upsert to stock_indicator table
    """
```

### Database Query

```sql
-- Get unique stock + indicator combinations with active subscriptions
SELECT DISTINCT
    s.symbol,
    is.indicator_key,
    is.timeframe,
    is.indicator_type,
    is.period  -- nullable for non-period indicators
FROM indicator_subscriptions is
JOIN stocks s ON s.id = is.stock_id
WHERE is.is_deleted = FALSE
  AND s.is_deleted = FALSE
ORDER BY s.symbol, is.indicator_key;
```

### Indicator Key Format

Standard format: `{INDICATOR_TYPE}_{PARAMETERS}_{TIMEFRAME}`

- RSI: `RSI_{period}_{timeframe}` (e.g., `RSI_14_D`)
- SMA: `SMA_{period}_{timeframe}` (e.g., `SMA_20_D`)
- KDJ: `KDJ_{n}_{m}_{t}_{timeframe}` (e.g., `KDJ_9_3_3_D`)
- MACD: `MACD_{fast}_{slow}_{signal}_{timeframe}` (e.g., `MACD_12_26_9_D`)

Timeframe codes:
- `D` = DAILY
- `W` = WEEKLY

## References

- @src/stocks/indicators.py - Existing indicator calculation functions
- @src/clients/yfinance_client.py - YFinance API client for historical prices
- @src/tasks/jobs/subscription_jobs.py - Existing ARQ job structure reference
- @src/redis_client/ - Redis infrastructure
- @doc/rules/database.md - BIGINT timestamp requirements, no NULL policy
- @doc/rules/async-tasks.md - ARQ worker conventions
- @context/features/20260515-subscription-worker-decoupling-stock-indicator.md - Related ongoing work for stock_indicator table