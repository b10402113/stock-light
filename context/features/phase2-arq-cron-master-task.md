# Phase 2: 智慧分批與 Master Task 開發 (ARQ Cron) Spec

## Overview

Phase 2 implements the master scheduling task that determines which stocks need price updates and dispatches batch jobs to worker tasks. This phase builds on the Redis infrastructure from Phase 1 and introduces ARQ cron scheduling for automated stock price monitoring.

The master task runs every minute, identifies stocks that haven been updated in the last 5 minutes, splits them into batches of 50 stocks, and dispatches update jobs to ARQ workers.

## Requirements

### R1: ARQ Cron Setup

- Configure ARQ worker with cron job running every minute (`* * * * *`)
- Create master task function `update_stock_prices_master` as the cron entry point
- Register cron job in ARQ's `cron_jobs` configuration
- Ensure worker can be started with `arq src.tasks.worker.WorkerSettings.run`

### R2: Stock Update Filtering Logic

- Fetch active stocks list from Redis using `stocks:active` key (from Phase 1)
- For each stock symbol in active list:
  - Retrieve stock info from Redis hash `stock:{symbol}` using `get_stock_info()`
  - Check `updated_at` field from hash
  - Calculate elapsed time: `current_time - updated_at`
  - If elapsed time >= 300 seconds (5 minutes) OR no Redis record exists, add to "to-update list"
- Return list of stock symbols requiring price updates

### R3: Batch Chunking Logic

- Split to-update list into chunks of maximum 50 stocks per chunk
- Use `enqueue_job()` to dispatch each chunk to sub-task `update_stock_prices_batch`
- Pass chunk as list parameter: `enqueue_job('update_stock_prices_batch', chunk)`
- Log number of chunks dispatched and total stocks to update

### R4: Task Module Structure

- Create `src/tasks/` directory for ARQ task definitions
- Create `src/tasks/worker.py` for WorkerSettings and task functions
- Create `src/tasks/config.py` for ARQ configuration (Redis connection, job settings)
- Follow domain self-containment: tasks module owns its configuration and worker setup

### R5: Error Handling

- Handle Redis connection failures gracefully (log error, skip this run)
- Handle empty active stocks list (no dispatch needed)
- Handle enqueue failures with retry logic (ARQ built-in retry)
- Use BizException with appropriate error codes for task failures

### R6: Configuration Settings

- Add ARQ settings to `src/config.py`:
  - `ARQ_REDIS_HOST` (default: localhost)
  - `ARQ_REDIS_PORT` (default: 6379)
  - `ARQ_REDIS_DB` (default: 0)
  - `ARQ_JOB_TIMEOUT` (default: 300 seconds)
  - `ARQ_MAX_TRIES` (default: 3)
  - `STOCK_UPDATE_INTERVAL` (default: 300 seconds)
  - `STOCK_BATCH_SIZE` (default: 50)

### R7: Integration with Phase 1

- Import `StockRedisClient` from `src/clients/redis_client.py`
- Use existing methods: `get_active_stocks()`, `get_stock_info()`
- Maintain Redis key naming convention from Phase 1:
  - Active stocks: `stocks:active`
  - Stock hash: `stock:{symbol}`
  - Hash fields: `price`, `updated_at`

## Implementation Files

- `src/tasks/__init__.py` - Module initialization
- `src/tasks/config.py` - ARQ Redis connection and job settings
- `src/tasks/worker.py` - WorkerSettings class with cron and task functions
- `src/config.py` - Add ARQ-related settings
- `tests/tasks/test_worker.py` - Unit tests for master task logic

## References

- @context/current-feature.md - Phase 1 implementation history
- @src/clients/redis_client.py - StockRedisClient from Phase 1
- @CLAUDE.md - Domain self-containment principle, task module structure
- https://arq.readthedocs.io/ - ARQ documentation for cron and job enqueue