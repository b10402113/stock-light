# Indicator Subscription Enhancement

## Status

Complete

## Goals

- Add title, message, signal_type fields to IndicatorSubscription model
- Enrich API responses with stock details (symbol, name, price, change_percent)
- Integrate quota validation with Plan-level limits
- Implement unified list endpoint for all subscription types
- Apply keyset pagination for list queries (no OFFSET)
- Create database migration for new fields (NOT NULL with DEFAULT)
- Update schemas, service, and router for new functionality

## Notes

### Database Constraints
- Primary key: BIGSERIAL (auto-increment)
- No NULL allowed - use empty string or 0 for business empty values
- Soft delete required: is_deleted + updated_at trigger
- New fields: title (VARCHAR 50), message (VARCHAR 200), signal_type ('buy'|'sell')

### Quota Limits by Level
- Level 1 (Regular): 10 subscriptions, 1 condition per alert
- Level 2 (Pro): 50 subscriptions, 3 conditions per alert
- Level 3 (Pro Max): 100 subscriptions, unlimited conditions
- Level 4 (Admin): Unlimited

### Cross-module Dependencies
- stocks_service: get stock details and current price
- plans_service: check user quota limits
- Strict layering: router → service → model/client

### Response Format
- Follow existing Response[T] pattern
- Stock nested in response with brief info
- Unified list endpoint distinguishes by subscription_type field

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