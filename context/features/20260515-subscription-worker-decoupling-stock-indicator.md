# Subscription Worker Decoupling and Stock Indicator Table Spec

## Overview

Decouple the stock subscription creation flow from worker processing. When a user subscribes to a stock with indicator conditions, the system should only persist the subscription data without immediately triggering worker tasks. The worker will periodically fetch active stocks with indicator subscriptions and calculate/store indicator values in a new `stock_indicator` table using JSONB for flexible data storage.

## Requirements

### 1. Subscription Flow Modification
- Remove worker trigger from subscription creation endpoint
- Store subscription data with stock's `is_active` status and indicator condition details
- Mark subscribed stocks as `is_active=True` when creating indicator subscriptions
- Decouple subscription creation from immediate data fetching

### 2. Stock Indicator Table Creation
- Create `stock_indicator` table with JSONB data storage
- Schema:
  ```sql
  CREATE TABLE stock_indicator (
      id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
      stock_id BIGINT NOT NULL,
      indicator_key VARCHAR(50) NOT NULL, -- e.g., 'MACD_12_26_9', 'KDJ_9_3_3', 'RSI_14'
      data JSONB NOT NULL DEFAULT '{}',   -- stores {"k": 80, "d": 75, "j": 85} or {"value": 70}
      updated_at BIGINT NOT NULL DEFAULT 0,
      CONSTRAINT fk_stock_indicator_stock FOREIGN KEY (stock_id) REFERENCES stocks(id)
  );
  ```
- Add unique constraint on `(stock_id, indicator_key)` to prevent duplicates
- Add indexes for efficient querying:
  - Index on `stock_id` for stock-based lookups
  - Index on `indicator_key` for type-based filtering
  - GIN index on `data` for JSONB queries

### 3. Worker Periodic Processing
- Update ARQ worker to periodically fetch stocks where:
  - `is_active=True`
  - Has at least one indicator subscription
- Calculate indicators for fetched stocks (RSI, KDJ, MACD, etc.)
- Store calculated values in `stock_indicator` table with appropriate `indicator_key`
- Handle multiple indicator configurations (different periods, parameters)

### 4. Indicator Key Design
- Standardize indicator key format: `{TYPE}_{PARAMETERS}`
  - RSI: `RSI_{period}` (e.g., `RSI_14`)
  - SMA: `SMA_{period}` (e.g., `SMA_20`)
  - KDJ: `KDJ_{k_period}_{d_period}_{j_period}` (e.g., `KDJ_9_3_3`)
  - MACD: `MACD_{fast}_{slow}_{signal}` (e.g., `MACD_12_26_9`)
- Indicator key parsing logic to extract type and parameters

### 5. JSONB Data Structure
- Each indicator type has specific JSON structure:
  - RSI: `{"value": 70.5}`
  - SMA: `{"value": 150.25}`
  - KDJ: `{"k": 80, "d": 75, "j": 85}`
  - MACD: `{"macd": 0.5, "signal": 0.3, "histogram": 0.2}`
- Standardized schema validation for JSONB data

### 6. Database Model and Service
- Create `StockIndicator` SQLAlchemy model
- Implement `StockIndicatorService` with:
  - `upsert_indicator(stock_id, indicator_key, data)` - insert or update indicator
  - `get_by_stock(stock_id)` - get all indicators for a stock
  - `get_by_type(indicator_key)` - get all stocks with specific indicator type
  - `delete_outdated(stock_ids, before_timestamp)` - cleanup old entries

### 7. Alembic Migration
- Create migration for `stock_indicator` table
- Add foreign key constraint with `stocks.id`
- Add unique constraint and indexes
- Follow project's database conventions (BIGINT, no NULL)

## References

- @src/subscriptions/router.py - Subscription creation endpoint
- @src/subscriptions/service.py - Subscription business logic
- @src/subscriptions/model.py - Subscription model
- @src/tasks/jobs/subscription_jobs.py - Worker job definitions
- @src/stocks/indicators.py - Indicator calculation functions
- @src/stocks/model.py - Stock model with is_active field
- @doc/rules/database.md - Database design principles