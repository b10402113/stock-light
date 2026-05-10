# Current Feature: User Level System

## Status

Complete - Implementation Done

## Goals

- Create new `src/plans/` domain module with model, schema, service, and router
- Create `level_configs` table with default pricing and quota configurations for 4 levels
- Create `plans` table to track user-level relationships with billing cycle and due dates
- Implement billing cycle logic: monthly (+1 month) and yearly (+1 year) durations
- Add API endpoints: GET `/plans/me`, GET `/plans/levels`, POST/PUT/DELETE `/plans` (admin)
- Seed existing users with Level 1 Plan records
- Remove `subscription_status` field from users table
- Update quota validation to use Plan level instead of subscription_status

## Notes

### User Levels

| Level | Name | Monthly | Yearly | Max Subscriptions | Max Alerts |
|-------|------|---------|--------|-------------------|------------|
| 1 | 普通用戶 | $0 | $0 | 10 | 10 |
| 2 | Pro用戶 | TBD | TBD | 50 | 50 |
| 3 | Pro Max用戶 | TBD | TBD | 100 | 100 |
| 4 | Admin | N/A | N/A | Unlimited | Unlimited |

**Pricing TBD:** Need actual prices for Level 2 and Level 3 (monthly/yearly)

### Key Constraints

- Only one active Plan per user at any time
- Admin level (4) is permanent, not purchasable
- Level 1 is free, auto-assigned to new users
- Plan expires → auto-downgrade to Level 1
- Price recorded at purchase time (may differ from current config)

### Migration Order

1. Create `level_configs` table → seed default data
2. Create `plans` table
3. Seed existing users with Level 1 Plans
4. Remove `subscription_status` from users table
5. Update quota validation logic

## History

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