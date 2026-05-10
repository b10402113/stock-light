# Current Feature: Scheduled Reminder Subscription

## Status

Complete

## Goals

- Create `scheduled_reminders` database table with proper model (BIGSERIAL, no NULL, soft delete)
- Add `FrequencyType` enum (daily/weekly/monthly) and Pydantic schemas
- Implement API endpoints: POST/GET/PATCH/DELETE `/subscriptions/reminders`
- Implement service layer with `calculate_next_trigger_time` function
- Add scheduler integration for processing due reminders
- Integrate with Plan-level quota validation
- Add tests for reminder functionality

## Notes

**Subscription Type**: Scheduled Reminder triggers at scheduled times regardless of indicator conditions.

**Database Design**:
- `frequency_type`: 'daily', 'weekly', 'monthly' (預設 'daily')
- `reminder_time`: Time of day (預設 '17:00:00')
- `day_of_week`: 0-6 for weekly, 0 for non-weekly
- `day_of_month`: 1-28 for monthly, 0 for non-monthly
- `last_triggered_at`: 上次觸發時間 (預設 '1970-01-01' as sentinel)
- `next_trigger_at`: Calculated next trigger timestamp
- Unique constraint on (user_id, stock_id, frequency_type, reminder_time, day_of_week, day_of_month)

**Architecture**:
- Domain module in `src/subscriptions/` (existing)
- Scheduler processing in `subscriptions/scheduler.py`
- Follow strict dependency: router ─► service ─► model/client
- Keyset pagination (游標分頁, no OFFSET)

**Trigger Calculation**:
- Daily: tomorrow at reminder_time
- Weekly: next day_of_week at reminder_time
- Monthly: next day_of_month at reminder_time

**Frontend Integration**:
- Subscription type badge (定期提醒)
- Next trigger time display
- Frequency indicator (每日/每週/每月)

## History

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