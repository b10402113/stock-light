# Indicator Update Cron Job Refactor Spec

## Overview

Remove existing indicator calculation async tasks and rewrite with a simplified `update_indicator` cron job that runs every minute. The job queries `indicator_subscriptions` table to get all active subscriptions and calculates their indicators, storing results in `stock_indicator` table. Goal: when a user posts an indicator subscription, the corresponding stock's technical indicators should appear in `stock_indicator` shortly after.

## Requirements

### 1. Remove Existing Indicator Async Tasks
- Remove `calculate_stock_indicators` job from `src/tasks/jobs/indicator_jobs.py`
- Remove the cron job entry for `calculate_stock_indicators` from `src/tasks/worker.py`
- Remove or simplify any related task dispatch logic in subscription service if it triggers indicator calculation asynchronously

### 2. Create New `update_indicator` Cron Job
- Create new job function `update_indicator` in `src/tasks/jobs/indicator_jobs.py`
- Register as cron job in `src/tasks/worker.py` that runs every minute (`*/1`)
- Job flow:
  1. Query `indicator_subscriptions` table for all active subscriptions (where `is_deleted=False` and `is_active=True`)
  2. Extract unique stock_ids and their required indicator_keys from `condition_group`
  3. For each stock_id:
     - Check if `daily_prices` table has sufficient historical data
     - If insufficient, fetch from yfinance API (use existing YFinanceClient)
     - Calculate indicators using existing calculator functions
     - Upsert results to `stock_indicator` table
  4. Handle errors gracefully (log errors, don't stop batch processing)

### 3. Simplify Indicator Key Extraction
- Use existing `StockIndicatorService.get_required_indicator_keys()` method
- Parse `condition_group` JSONB from subscriptions to get indicator_type, period, timeframe
- Generate indicator_key using `generate_indicator_key()` function

### 4. Error Handling & Retry Logic
- Maintain existing retry tracking in Redis (REDIS_INDICATOR_RETRY_PREFIX)
- Skip stocks that exceed max retries (INDICATOR_MAX_RETRIES)
- Log individual stock failures without stopping entire batch
- Clear retry count on successful calculation

### 5. Configuration
- Update `CRON_INDICATOR_MINUTES` in `src/config.py` to `"*/1"` (every minute)
- Keep existing `INDICATOR_MAX_RETRIES` setting

## References

- @src/tasks/jobs/indicator_jobs.py - Current indicator calculation job
- @src/tasks/worker.py - Worker settings with cron jobs
- @src/stock_indicator/service.py - StockIndicatorService with get_stocks_with_indicators, get_required_indicator_keys
- @src/stock_indicator/schema.py - IndicatorType, generate_indicator_key
- @src/stock_indicator/model.py - StockIndicator model
- @src/subscriptions/model.py - IndicatorSubscription model with condition_group
- @src/config.py - CRON_INDICATOR_MINUTES setting