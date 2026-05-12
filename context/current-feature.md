# Current Feature: DailyPrice Historical Data Table

## Status

Complete

## Goals

- Create DailyPrice model with OHLCV fields (open, high, low, close, volume)
- Add composite unique index on (stock_id, date) to prevent duplicates
- Define Pydantic schemas for create/response with pagination support
- Add service methods: bulk_insert, get_by_range, calculate_ma, get_latest
- Create API endpoints: GET/POST /stocks/{stock_id}/prices, GET /stocks/{stock_id}/ma/{period}
- Create Alembic migration with proper indexes
- Add comprehensive tests for model, service, API, and edge cases

## Notes

### Database Design

- Primary key: BIGSERIAL (project convention, avoid UUID for performance)
- Foreign key: stock_id → stocks.id (Integer)
- Date field: Date type, nullable=False
- OHLCV: Numeric(10, 2), Volume: BigInteger
- Composite unique index idx_daily_price_stock_date on (stock_id, date)
- No NULL values, no soft delete (historical data is immutable)

### Data Source

- **Phase 1**: Manual/admin upload via API only (no yfinance integration yet)
- POST /stocks/{stock_id}/prices endpoint for bulk insert (admin only)
- yfinance integration deferred to future iteration

### Performance

- Expected volume: 100 stocks × 365 days × 5 years ≈ 182,500 rows
- Composite index covers stock_id + date range queries
- Redis caching for frequently calculated indicators (200MA)

### Data Quality

- Validate OHLCV consistency: high >= low, high >= open/close, low <= open/close
- Handle missing data: weekends, holidays, suspended trading
- No adjusted prices initially (future consideration for stock splits/dividends)

### Backtesting Support

- Ensure data completeness for accurate backtesting
- Efficient date range queries via composite index

## History

- 2026-05-12: DailyPrice Historical Data Table
  - Created DailyPrice model in src/stocks/model.py with BIGSERIAL PK, OHLCV fields, BigInteger volume
  - Added composite unique constraint uq_daily_price_stock_date on (stock_id, date)
  - Added composite index idx_daily_price_stock_date for efficient range queries
  - Added Stock.daily_prices relationship with lazy="selectin" and order_by date desc
  - Defined Pydantic schemas: DailyPriceBase, DailyPriceCreate, DailyPriceBulkCreate, DailyPriceResponse, DailyPriceListResponse, MovingAverageResponse
  - Added OHLCV consistency validators (high >= open/close, low <= open/close, high >= low)
  - Added DailyPriceService with bulk_insert_prices (upsert mode), get_prices_by_range (keyset pagination), calculate_ma, get_latest_prices
  - Created API endpoints: GET/POST /stocks/{stock_id}/prices, GET /stocks/{stock_id}/ma/{period}
  - Created Alembic migration 2026-05-12_create_daily_prices_table.py
  - Added 29 comprehensive tests covering router, service, and schema validations
  - Updated API documentation in context/api/api-stock.md
  - Fixed datetime import convention (use datetime.date/datetime.datetime with prefix)
  - All stock-related tests pass (48/48)

- 2026-05-10: Compound Condition Model Fix
  - Changed indicator_type, operator, target_value to nullable=True in model.py
  - Removed redundant indexes (is_active_idx, user_id_idx, stock_id_idx)
  - Added optimized partial indexes for actual query patterns
  - Updated unique constraint to only apply to single conditions (compound_condition IS NULL)
  - Added model_validator to ensure at least one condition is provided
  - Updated service.py to handle nullable single condition fields
  - Created database migration for nullable changes and index restructuring
  - All compound condition tests (15/15) pass
  - Migration preserves existing data with no loss

- 2026-05-10: Compound Condition Schema
  - Added LogicOperator enum (AND="and", OR="or") to schema.py
  - Defined Condition model with indicator_type, operator, target_value fields
  - Defined CompoundCondition model with logic, conditions list and max 10 validator
  - Updated IndicatorSubscriptionBase, Update, Response to use Optional[CompoundCondition]
  - Added compound condition schema documentation to api-subscription.md
  - Updated service layer to serialize/deserialize CompoundCondition for JSONB storage
  - Updated existing tests to use lowercase logic values ("and"/"or")
  - Added validation tests for empty conditions and nested compound conditions

- 2026-05-10: Scheduled Reminder Subscription
  - Created scheduled_reminders table with FrequencyType enum (daily/weekly/monthly)
  - Added ScheduledReminder model with proper constraints (BIGSERIAL, no NULL, soft delete)
  - Implemented ScheduledReminderService with calculate_next_trigger_time logic
  - Added API endpoints: POST/GET/PATCH/DELETE /subscriptions/reminders
  - Integrated with Plan-level quota validation (combined with indicator subscriptions)
  - Added reminder_jobs.py for processing due reminders via ARQ cron
  - Added CRON_REMINDER_MINUTES config for schedule control
  - Updated router ordering (literal routes before path parameters)
  - Added 20 tests covering all endpoints and service logic
  - Updated API documentation with Scheduled Reminders section

- 2026-05-10: Indicator Subscription Enhancement
  - Added title, message, signal_type fields to IndicatorSubscription model
  - Database migration with NOT NULL DEFAULT constraints (VARCHAR 50, 200, 10)
  - Updated schemas with StockBrief for enriched responses
  - Added SignalType enum (buy, sell)
  - Integrated Plan-level quota validation (max_subscriptions per level)
  - Enriched API responses with stock details (symbol, name, price from Redis)
  - Updated router to use enrich_subscription_with_stock for all responses
  - Updated test fixtures with LevelConfig and Plan seeding
  - Updated API documentation with new fields and quota limits table

- 2026-05-10: Add User Level System
  - Created src/plans/ domain module (model, schema, service, router)
  - Added LevelConfig model for pricing and quota configuration (4 levels)
  - Added Plan model for user-level relationships with billing cycles
  - Created database migration with level_configs and plans tables
  - Seeded default level configs and existing users with Level 1 plans
  - Added API endpoints: GET /plans/levels, GET /plans/me, POST/PUT/DELETE /plans (admin)
  - Added BaseWithoutAutoId for models with custom primary keys
  - Levels: Regular (free), Pro ($99/mo), Pro Max ($199/mo), Admin (unlimited)

- 2026-05-10: Add Health Check Endpoint
  - Added public /health endpoint (no authentication required)
  - Check PostgreSQL connection with SELECT 1
  - Check Redis connection using StockRedisClient.ping()
  - Return HTTP 200 if healthy, HTTP 503 if unhealthy
  - Response includes status, version, description, uptime, and component details
  - Added API documentation for health endpoint

- 2026-05-09: Enable CORS on Backend for Frontend Connection
  - Added CORSMiddleware to FastAPI app in src/main.py
  - Positioned after app creation, before router registration
  - Used settings.cors_origins_list (localhost:3000, localhost:5173)
  - Enabled credentials for authentication cookies/headers
  - Allowed standard HTTP methods (GET, POST, PUT, DELETE, OPTIONS, PATCH)
  - Allowed headers (Authorization, Content-Type, Accept, Origin, X-Requested-With)
  - Production origins configurable via CORS_ORIGINS env var

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
