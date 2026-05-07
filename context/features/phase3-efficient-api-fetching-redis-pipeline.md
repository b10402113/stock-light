# Phase 3: 高效抓取外部 API 並寫回 Redis Spec

## Overview

Phase 3 implements the batch worker task that receives stock chunks from the master task, fetches prices from external APIs (Fugle or YFinance based on source), and updates Redis cache using Pipeline for efficiency. This phase also adds a persistence cron job that flushes Redis data to PostgreSQL every 15 minutes.

The batch task determines which API client to use by querying the database for each stock's `source` field, then uses Redis Pipeline to batch update all stock prices in a single network round-trip.

## Requirements

### R1: Redis Stock Info Schema Enhancement

- Add `source` field to Redis hash structure `stock:info:{ticker}`
- Update `set_stock_price()` to include source field in HSET operation
- Update `get_stock_info()` to return source field
- Redis hash fields after Phase 3:
  - `price`: current price (float)
  - `updated_at`: last update timestamp (int, Unix timestamp)
  - `source`: data source (int, 1=Fugle, 2=YFinance)
- Maintain backward compatibility: stocks without source field default to Fugle (1)

### R2: Batch Task Implementation - update_stock_prices_batch

- Implement `update_stock_prices_batch(ctx, batch)` in `src/tasks/worker.py`
- Logic flow:
  1. Query database to get source for each symbol in batch (single query using `SELECT symbol, source FROM stocks WHERE symbol IN (...)`)
  2. Partition batch into two groups: Fugle stocks and YFinance stocks
  3. Fetch prices concurrently using appropriate client for each group:
     - Fugle stocks: use `FugoClient.get_intraday_quote()`
     - YFinance stocks: use `run_in_threadpool` with `yf.Ticker().info`
  4. Use Redis Pipeline to batch update all stock hashes in single operation
  5. Log success/failure counts per API source

### R3: Redis Pipeline Implementation

- Add `batch_set_stock_prices()` method to `StockRedisClient`
- Use Redis Pipeline to reduce network I/O:
  - Create pipeline with `client.pipeline()`
  - Add HSET commands for each stock: `pipeline.hset(key, mapping={...})`
  - Execute all commands with single `pipeline.execute()` call
- Pipeline benefits:
  - Single network round-trip for 50 stocks (vs 50 round-trips)
  - Atomic operation guarantee
  - Reduced latency and improved throughput

### R4: Source-Based Client Routing

- Query database for source mapping:
  ```python
  from src.database import SessionFactory
  from src.stocks.model import Stock
  from src.stocks.schema import StockSource

  async with SessionFactory() as session:
      result = await session.execute(
          select(Stock.symbol, Stock.source).where(Stock.symbol.in_(batch))
      )
      source_map = {row.symbol: row.source for row in result}
  ```
- Route to appropriate client:
  - `source == StockSource.FUGLE (1)`: Use `FugoClient`
  - `source == StockSource.YFINANCE (2)`: Use `YFinanceClient`
- Handle missing stocks (not in database): skip with warning log

### R5: YFinance Price Fetching

- Add `get_current_price()` method to `YFinanceClient`:
  ```python
  async def get_current_price(self, symbol: str) -> float | None:
      """Get current price for a single symbol."""
      ticker = await run_in_threadpool(lambda: yf.Ticker(symbol))
      info = await run_in_threadpool(lambda: ticker.info)
      return info.get('currentPrice') or info.get('regularMarketPrice')
  ```
- Use `run_in_threadpool` for sync yfinance calls
- Handle API errors: return None on failure, log warning

### R6: Fugle Price Fetching

- Use existing `FugoClient.get_intraday_quote(symbol)` method
- Extract price from `IntradayQuoteResponse.lastPrice`
- Handle API errors: skip stock on failure, log warning

### R7: Persistence Cron Job - persist_redis_to_database

- Add new cron job `persist_redis_to_database` running every 15 minutes
- Logic:
  1. Fetch all active stocks from Redis
  2. For each stock, get cached price from Redis
  3. Batch update PostgreSQL `stocks` table:
     ```sql
     UPDATE stocks SET current_price = ?, updated_at = NOW()
     WHERE symbol = ?
     ```
  4. Use SQLAlchemy bulk update for efficiency
  5. Log number of stocks persisted
- Configure cron schedule:
  ```python
  cron(
      persist_redis_to_database,
      minute={0, 15, 30, 45},  # Every 15 minutes
      run_at_startup=False,
  )
  ```

### R8: Error Handling

- Handle database query failures: log error, skip entire batch
- Handle API failures per stock: skip stock, continue with others
- Handle Redis Pipeline failures: log error, raise exception (job retry)
- Use BizException with appropriate error codes:
  - `ErrorCode.DATABASE_ERROR` for database issues
  - `ErrorCode.FUGLE_API_ERROR` for Fugle failures
  - `ErrorCode.YFINANCE_API_ERROR` for YFinance failures
  - `ErrorCode.REDIS_OPERATION_ERROR` for Redis failures

### R9: Configuration Settings

- Add to `src/config.py`:
  - `REDIS_PERSIST_INTERVAL`: Persistence cron interval (default: 900 seconds = 15 minutes)
  - `STOCK_API_TIMEOUT`: Timeout for external API calls (default: 10 seconds)
  - `STOCK_API_MAX_RETRIES`: Max retries for API calls (default: 3)

### R10: Integration with Phase 1 & Phase 2

- Import `StockRedisClient` from Phase 1
- Import `FugoClient` and `YFinanceClient` from `src/clients/`
- Receive batch parameter from master task (Phase 2)
- Maintain Redis key naming conventions:
  - Active stocks: `stocks:active`
  - Stock hash: `stock:info:{symbol}`
  - Hash fields: `price`, `updated_at`, `source`

## Implementation Files

- `src/tasks/worker.py` - Implement `update_stock_prices_batch` and `persist_redis_to_database`
- `src/clients/redis_client.py` - Add `batch_set_stock_prices()` method
- `src/clients/yfinance_client.py` - Add `get_current_price()` method
- `src/config.py` - Add persistence and API timeout settings
- `src/tasks/config.py` - Add WorkerSettings for new cron job
- `tests/tasks/test_worker_batch.py` - Unit tests for batch task
- `tests/tasks/test_persistence.py` - Unit tests for persistence cron
- `tests/clients/test_redis_pipeline.py` - Tests for Pipeline operations

## Design Considerations

### Why Query Database for Source?

- Database is authoritative source for stock metadata
- Source field is set during stock creation/seeding
- Redis is cache layer, should not be authoritative for metadata
- Query cost is acceptable (single batched query for 50 symbols)

### Why Redis Pipeline?

- Without Pipeline: 50 stocks × 2 network round-trips = 100 RTTs
- With Pipeline: 1 network round-trip for all 50 stocks
- Estimated time savings: ~100ms → ~5ms (20x improvement)

### Why 15-Minute Persistence?

- Redis is volatile cache, need durability for price data
- 15-minute interval balances:
  - Write load on PostgreSQL (4 writes/hour per stock vs continuous)
  - Data freshness (max 15-minute data loss on Redis crash)
  - Query performance (Redis serves hot data, PostgreSQL serves historical)

### Why Skip Failed Stocks Instead of Retry?

- Batch task already has ARQ retry mechanism
- Individual stock failures should not block entire batch
- Problematic stocks will be retried in next master task cycle
- Avalanche prevention: don't retry problematic stocks indefinitely

## Testing Strategy

### Unit Tests for Batch Task

- Mock database query: return predefined source mapping
- Mock FugleClient: return fake prices for Fugle stocks
- Mock YFinanceClient: return fake prices for YFinance stocks
- Mock Redis Pipeline: verify correct HSET commands
- Test error scenarios: API failure, database failure, missing stock

### Unit Tests for Persistence Cron

- Mock Redis: return fake stock prices
- Mock database session: verify correct UPDATE calls
- Test empty cache scenario
- Test partial failures scenario

### Unit Tests for Redis Pipeline

- Test `batch_set_stock_prices()` with mock Redis
- Verify pipeline.execute() called exactly once
- Verify correct HSET mapping for each stock

## References

- @context/current-feature.md - Phase 1 & Phase 2 implementation history
- @src/tasks/worker.py - Master task from Phase 2
- @src/clients/redis_client.py - StockRedisClient from Phase 1
- @src/clients/fugle_client.py - FugoClient for Taiwan stocks
- @src/clients/yfinance_client.py - YFinanceClient for US stocks
- @src/stocks/model.py - Stock model with source field
- @src/stocks/schema.py - StockSource enum definition
- @CLAUDE.md - Domain self-containment principle, error handling guidelines
- https://arq.readthedocs.io/ - ARQ cron and job documentation
- https://redis.readthedocs.io/ - Redis Pipeline documentation