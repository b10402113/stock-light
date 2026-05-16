# Current Feature: Indicator Subscription Simplification

## Status

Complete

## Goals

- Create Alembic migration to remove nullable columns (indicator_type, operator, target_value) ✅
- Migrate existing single-condition subscriptions to compound_condition format ✅
- Make compound_condition required with CHECK constraint validation ✅
- Drop `uix_user_stock_single_condition` index, create new unique index on (user_id, stock_id, compound_condition) ✅
- Update model.py - remove columns, change compound_condition to required ✅
- Update schema.py - simplify schemas, rename compound_condition to condition_group ✅
- Update service.py - remove dual-mode handling logic ✅
- Update router.py - simplify validation ✅
- Update worker/indicator_jobs.py - extract conditions uniformly ✅
- Update all tests to use condition_group format ✅
- Run full test suite to verify ✅

## Notes

**Data Migration Pattern:**
- Single condition → wrapped in compound_condition: `{"logic": "and", "conditions": [{"indicator_type": "rsi", "operator": ">", "target_value": 70, "timeframe": "D", "period": 14}]}`

**Naming Convention:**
- Rename `compound_condition` → `condition_group` (semantic: always used, not "compound")

**Benefits:**
- One format for all conditions (1~N)
- Cleaner code - no branching for single vs compound
- Consistent API structure

## History

- 2026-05-16: Indicator Subscription Simplification
  - Created Alembic migration to remove nullable columns and convert data
  - Removed indicator_type, operator, target_value, timeframe, period from model
  - Made condition_group required with CHECK constraint (1-10 conditions, logic in ['and', 'or'])
  - Renamed compound_condition to condition_group in all schemas
  - Simplified IndicatorSubscriptionBase/Create/Update/Response schemas
  - Removed check_duplicate method (handled by DB unique constraint)
  - Removed dual-mode handling in service.create/update/enrich_subscription_with_stock
  - Updated StockIndicatorService.get_required_indicator_keys to only use condition_group
  - Updated 106 subscription-related tests to use condition_group format
  - Updated API documentation in api-subscription.md
  - All subscription tests passing

## History

- 2026-05-15: Indicator Data Updater
  - Added INDICATOR_UPDATE_INTERVAL_MINUTES, INDICATOR_BATCH_SIZE, INDICATOR_MAX_RETRIES config
  - Updated indicator key format to include timeframe: {TYPE}_{PARAMS}_{TIMEFRAME}
  - Enhanced calculate_stock_indicators job with yfinance API fallback for insufficient data
  - Added retry tracking in Redis for failed stocks with max retries limit
  - Added _get_min_required_days for smart data requirement calculation
  - Updated worker cron schedule to use CRON_INDICATOR_MINUTES (every 5 minutes)
  - Updated 35 tests for new indicator key format with timeframe suffix
  - All indicator tests passing

- 2026-05-15: Subscription Worker Decoupling and Stock Indicator Table
  - Created stock_indicator domain module with JSONB data storage
  - Added StockIndicator model with unique constraint on (stock_id, indicator_key)
  - Implemented indicator calculation functions (RSI, SMA, KDJ, MACD)
  - Added StockIndicatorService with upsert/query methods
  - Added calculate_stock_indicators ARQ job with cron schedule (every 5 minutes)
  - Removed worker trigger from subscription creation endpoint
  - Worker now periodically fetches active stocks with indicator subscriptions
  - 33 comprehensive tests for indicator calculations and service methods

- 2026-05-14: Indicator Subscription Timeframe and Period Fields
  - Added timeframe (VARCHAR(1), D/W) and period (SMALLINT, optional) columns to indicator_subscriptions
  - Created Alembic migration with CHECK constraints and updated unique index
  - Added Timeframe enum (D, W) to Pydantic schemas
  - Added period validation (only for RSI/SMA, range 5-200)
  - Added SMA indicator type to IndicatorType enum
  - Created GET /subscriptions/indicators/config endpoint
  - Updated Condition model for compound conditions with timeframe/period
  - Added IndicatorConfigResponse, IndicatorFieldConfig, TimeframeConfig, PeriodConfig schemas
  - Updated check_duplicate to include timeframe and period
  - Updated enrich_subscription_with_stock, create, update methods for new fields
  - Added 28 comprehensive tests (validation, unique constraints, config endpoint)
  - All 57 subscription-related tests passing

- 2026-05-14: Integration Test for prepare_subscription_data
  - Created comprehensive test suite with 11 tests for ARQ job
  - Test real yfinance API historical price fetching (100 days)
  - Test Redis active stock set population and price storage
  - Test database insertion with upsert behavior
  - Test error handling for invalid symbols and non-existent stocks
  - Fixed alembic migration dependency (scheduled_reminders -> scheduled_reminders)
  - All 11 integration tests passing

- 2026-05-13: Stock Subscription Notification Flow
  - Added automatic data availability validation before subscription creation
  - Check stock active status in Redis and historical price availability
  - Trigger ARQ job to prepare data when checks fail
  - Created prepare_subscription_data ARQ job (Redis active set, current price, 100 days history)
  - Refactored router to use FastAPI Depends for Redis client injection
  - Always use YFinance for historical prices (free API, cost optimization)
  - 14 comprehensive tests for validation logic
  - Updated API documentation with data preparation flow

- 2026-05-13: Backtest Task API
  - Created src/backtest/ domain module with schema, service, router
  - Implemented POST /stocks/{stock_id}/backtest/trigger endpoint
  - Implemented GET /tasks/{job_id} endpoint for ARQ job status
  - Created fetch_missing_daily_prices ARQ job for historical price fetching
  - Added BacktestService with check_data_coverage, calculate_missing_ranges
  - Added get_historical_prices method to YFinanceClient
  - Fixed circular import in models/__init__.py
  - Mounted new routers in main.py
  - 16 comprehensive tests for service and routers (all passing)

- 2026-05-12: DailyPrice Historical Data Table
  - Created DailyPrice model with BIGSERIAL PK, OHLCV fields, composite unique index on (stock_id, date)
  - Added OHLCV consistency validators in Pydantic schemas
  - Implemented DailyPriceService with bulk_insert (upsert), get_by_range, calculate_ma, get_latest
  - Created API endpoints: GET/POST /stocks/{stock_id}/prices, GET /stocks/{stock_id}/ma/{period}
  - Added Alembic migration for daily_prices table
  - 29 comprehensive tests covering router, service, schema validations
  - Updated API documentation in context/api/api-stock.md

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
    - TestRedActiveStocks: Setting 100 stocks as active (2 tests)
    - TestBatchSizeEnforcement: Batch splitting verification (1 test)
    - TestBatchJobExecution: Batch task execution with real API (2 tests)
    - TestWorkerPerformance: Concurrent query performance (2 tests)
  - Verified batch size limit: 100 stocks split into 2 batches of 50 each
  - Verified concurrent API calls: 10 stocks fetched in <0.3s
  - Verified concurrent Redis queries: 100 stocks in <0.01s
  - Removed .TW suffix from stock symbols (Fugle API compatibility)
  - All 9 integration tests passing
  - Redis fixtures clean state before/after each test