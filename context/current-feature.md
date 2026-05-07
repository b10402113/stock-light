# Current Feature: Split ARQ Workers by Task Type

## Status

Not Started

## Goals

- Separate API-intensive batch jobs from fast system scheduling tasks
- Prevent API rate limiting issues by isolating API worker with `max_jobs=1`
- Allow system tasks to run concurrently without being blocked by slow API calls
- Master task dispatches batch jobs to dedicated `api_queue`
- Two distinct worker classes: `DefaultWorkerSettings` and `ApiWorkerSettings`

## Notes

### Current Problem
- Current `WorkerSettings` has `max_jobs=1` to prevent 429 rate limit errors
- This single setting blocks ALL tasks (including fast system tasks like `persist_redis_to_database`)
- System tasks run quickly but must wait for slow API batch jobs to complete

### Solution Architecture
- **Default Worker**: Monitors default queue `arq:queue`, handles cron scheduling and fast system tasks
  - `max_jobs=10` (high concurrency for non-blocking tasks)
  - Functions: `update_stock_prices_master`, `persist_redis_to_database`, `sync_active_stocks_to_redis`
  - Contains all `cron_jobs`

- **API Worker**: Monitors dedicated `api_queue`, only handles API batch jobs
  - `max_jobs=1` (serial execution to respect rate limits)
  - Functions: `update_stock_prices_batch`
  - No cron jobs (passive, receives jobs from master task)

### Implementation Steps

1. **Modify Master Task**: Add `_queue_name="api_queue"` to `enqueue_job` call
   ```python
   # In update_stock_prices_master, Step 4
   enqueue_tasks = [
       redis_pool.enqueue_job(
           "update_stock_prices_batch",
           batch,
           _queue_name="api_queue"  # Dispatch to API queue
       )
       for batch in batches
   ]
   ```

2. **Split WorkerSettings into Two Classes**:
   ```python
   class DefaultWorkerSettings:
       """Fast system tasks and cron scheduling."""
       functions = [
           update_stock_prices_master,
           persist_redis_to_database,
           sync_active_stocks_to_redis,
       ]
       max_jobs = 10  # High concurrency for fast tasks
       cron_jobs = [...]  # All cron scheduling

   class ApiWorkerSettings:
       """API batch jobs with rate limiting."""
       queue_name = "api_queue"  # Dedicated queue
       functions = [update_stock_prices_batch]
       max_jobs = 1  # Serial execution
       # No cron_jobs
   ```

3. **Deployment**: Run two worker processes
   ```bash
   arq src.tasks.worker.DefaultWorkerSettings  # System worker
   arq src.tasks.worker.ApiWorkerSettings      # API worker
   ```

## Implementation Files

- [src/tasks/worker.py](src/tasks/worker.py) - Split WorkerSettings, modify master task

## History

- 2026-05-07: Fix Fugle API Rate Limit Exceeded (429 Error)
  - Root cause: asyncio.gather simultaneously sends all batch requests (50 concurrent)
  - Added WorkerSettings.max_jobs = 1 (prevent multi-batch concurrency)
  - Added aiolimiter>=1.0.0 to requirements.txt for time window rate limiting
  - Added FUGLE_RATE_LIMIT=50 and FUGLE_MAX_CONCURRENT_REQUESTS=10 to config.py
  - Modified FugoClient with:
    - AsyncLimiter (50 requests per 60 seconds - time window limit)
    - asyncio.Semaphore (10 concurrent requests)
    - Applied dual rate limiting in get_intraday_quote()
  - Expected behavior:
    - Batch 1 executes with 50 requests throttled (5-10s execution time)
    - Batch 2 waits due to max_jobs=1
    - No 429 errors (rate limit respected)
  - All 9 integration tests passing

- 2026-05-07: Phase - Test ARQ Worker Batch Processing Integration
  - Created integration tests for tasks/worker.py with real Fugle API calls
  - Created seed script scripts/seed_100_test_stocks.py (102 stocks seeded)
  - Test suite covers 5 test classes with 9 tests:
    - TestRealFugleAPICalls: Real API price fetching (2 tests)
    - TestRedisActiveStocks: Setting 100 stocks as active (2 tests)
    - TestBatchSizeEnforcement: Batch splitting verification (1 test)
    - TestBatchJobExecution: Batch task execution with real API (2 tests)
    - TestWorkerPerformance: Concurrent query performance (2 tests)
  - Verified batch size limit: 100 stocks split into 2 batches of 50 each
  - Verified concurrent API calls: 10 stocks fetched in <0.3s
  - Verified concurrent Redis queries: 100 stocks in <0.01s
  - Removed .TW suffix from stock symbols (Fugle API compatibility)
  - All 9 integration tests passing
  - Redis fixtures clean state before/after each test