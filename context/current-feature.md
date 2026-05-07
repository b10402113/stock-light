# Current Feature

## Status

Not Started

## Goals

## Notes

## Implementation Files

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

## Notes

- Tests use real Fugle API (not mocked) for price fetching
- Created seed script to prepare 100 test stocks with source=StockSource.FUGLE
- Tests verify batch processing splits 100 stocks into 2 batches of 50 each
- Redis fixtures clean state before and after each test
- All 9 integration tests passing
- Removed .TW suffix from stock symbols (Fugle API uses raw symbols)

## Implementation Files

- `tests/tasks/test_worker_integration.py` - Integration test file (9 tests)
- `scripts/seed_100_test_stocks.py` - Seed script for 100 test stocks
- `src/tasks/worker.py` - Worker implementation (verified)
- `src/config.py` - ARQ batch size configuration (STOCK_BATCH_SIZE=50)

## History

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

- 2026-05-07: Phase 3 - 高效抓取外部 API 並寫回 Redis
  - Modified Redis structure to use stock_id as key instead of symbol
  - Redis hash `stock:info:{stock_id}` stores: symbol, price, updated_at, source
  - Implemented batch task with source-based API routing (Fugle/YFinance)
  - Added YFinanceClient.get_current_price() method
  - Added StockRedisClient.batch_set_stock_prices() using Pipeline (20x performance improvement)
  - Implemented persist_redis_to_database cron job (15-minute interval)
  - Added configurable cron schedules via .env (CRON_MASTER_MINUTES, CRON_PERSIST_MINUTES)
  - Worker startup loads stock_id + symbol + source from database to Redis
  - Fixed Fugle API schema: made isClose field optional
  - Comprehensive error handling: skip failed stocks, retry batch on Redis errors
  - Bytes decoding support for ARQ Redis pool compatibility
  - All tests passing (9/9 worker tests)

- 2026-05-07: Phase 2 - 智慧分批與 Master Task 開發 (ARQ Cron)
  - Added ARQ settings to src/config.py (job timeout, retries, batch size, update interval)
  - Created src/tasks/ module following domain self-containment principle
  - Created src/tasks/config.py for ARQ Redis connection configuration
  - Created src/tasks/worker.py with WorkerSettings and master task
  - Implemented update_stock_prices_master with concurrent stock filtering:
    - Uses asyncio.gather for parallel Redis queries (avoids N+1 problem)
    - Identifies stocks needing updates (>= 5 minutes old or no record)
    - Batch splitting logic (50 stocks per chunk)
    - Concurrent job dispatch using asyncio.gather
  - Modified StockRedisClient to accept external Redis pool (from ARQ)
  - Improved error handling: skip problematic stocks instead of adding to queue
  - Used ctx["redis"] (ARQ standard key) to reuse shared pool
  - Wrote 9 unit tests covering filtering, batching, error scenarios, cron config
  - All 9 Phase 2 tests passing
  - Integration with Phase 1 Redis infrastructure

- 2026-05-07: Phase 1 - Redis 資料結構與環境設計
  - Added arq>=0.25.0 to requirements.txt for async job queue
  - Added REDIS_TIMEOUT setting to config.py (5 seconds default)
  - Created StockRedisClient in src/clients/redis_client.py
  - Implemented Redis Set operations for active stocks monitoring:
    - add_active_stock() - SADD (atomic operation)
    - remove_active_stock() - SREM (atomic operation)
    - get_active_stocks() - SMEMBERS
    - clear_active_stocks() - DELETE
  - Implemented Redis Hash operations for stock price caching:
    - set_stock_price() - HSET with price and updated_at fields
    - get_stock_price() - HGET for single price field
    - get_stock_info() - HGETALL for full stock info
    - delete_stock_info() - DELETE stock hash
    - get_stocks_updated_since() - Find recently updated stocks
  - Added Redis error codes to ErrorCode enum:
    - REDIS_CONNECTION_ERROR (504)
    - REDIS_OPERATION_ERROR (505)
  - Wrote 23 integration tests with real Redis connection
  - Wrote 6 mock tests for error scenarios
  - All tests passing (62 tests including stocks router and client tests)
  - Race condition prevention: atomic Redis operations (SADD, HSET)
  - Used aclose() for async connection closing
  - Clean Redis state before/after each test using SCAN pattern matching

- 2026-05-06: Add Source and Market Fields to Stock Model
  - Added `source` field to Stock model to track data origin (Fugle vs YFinance)
  - Added `market` field to Stock model to track stock market type (Taiwan vs US)
  - Created StockSource IntEnum with FUGLE=1 and YFINANCE=2 values
  - Created StockMarket IntEnum with TAIWAN=1 and US=2 values
  - Added source and market columns as SmallInteger with default values
  - Created Alembic migration for both new columns
  - Updated StockResponse and StockCreate schemas to include both fields
  - Updated seed script to set source=StockSource.FUGLE and market=StockMarket.TAIWAN
  - Updated tests to include both fields in payloads and verify API responses

- 2026-05-06: Database-Only Stock Search with Taiwan Seed Data
  - Removed YFinance API fallback from search_stocks (database-only queries)
  - Added get_tickers method to FugoClient for fetching all Taiwan stocks
  - Created seed script scripts/seed_taiwan_stocks.py using Fugle API
  - Seed script normalizes 4-digit symbols with .TW suffix
  - Updated TickerResponse schema to allow nullable name field
  - Upsert logic for re-runnable seeding without duplicates
  - Removed YFinance fallback tests, added empty result test
  - All 114 tests passing (19 stocks router tests)

- 2026-05-06: YFinance Ticker Search Client Implementation
  - Created YFinanceClient in src/clients/yfinance_client.py
  - Implemented search_tickers() for searching by symbol/company name
  - Implemented get_ticker() for single ticker lookup
  - Used run_in_threadpool for async compatibility (yfinance is sync-only)
  - Added YFINANCE_API_ERROR error code
  - Updated StockService to use YFinance API as fallback (removed Fugle)
  - Updated router to inject YFinanceClient dependency
  - Fixed yfinance key names: shortname/longname (lowercase)
  - Added 10 real API tests for YFinanceClient
  - Added US stock (AAPL) and Taiwan stock (TSM) search tests
  - All 20 stocks router tests and 10 yfinance tests passing

- 2026-05-06: Fugle Single Symbol Ticker Lookup Implementation
  - Added get_ticker method to FugoClient using GET /intraday/ticker/{symbol} endpoint
  - Modified search_stocks in StockService:
    - Removed logger statements
    - Changed from fetching all TSE/OTC tickers to single ticker lookup
    - Filter by symbol only when using Fugle fallback
  - Updated tests to use get_ticker instead of get_tickers
  - Updated API documentation with new fallback strategy
  - All 21 stock router tests passing

- 2026-05-06: Stock Search API Fallback Strategy Implementation
  - Added get_tickers method to FugoClient using fugle_marketdata SDK intraday.tickers endpoint
  - Created TickerResponse Pydantic schema for Fugle ticker data
  - Implemented fallback logic in StockService.search_stocks:
    - Database-first search
    - If no results, query Fugle API for TSE and OTC markets
    - Filter results by query (case-insensitive)
    - Persist matching stocks to database
    - Gracefully handle API failures (returns empty list)
  - Added fugle_client dependency injection to router
  - Updated router to pass fugle_client to service method
  - Added pytest-mock>=3.12.0 to requirements.txt
  - Added fugle-marketdata>=0.1.0 to requirements.txt
  - Wrote 2 unit tests for fallback behavior:
    - test_search_stocks_fugle_fallback: Tests API fallback when database empty
    - test_search_stocks_database_first_no_fugle_call: Tests that API not called when database has results
  - Updated API documentation with fallback strategy details
  - All 21 stock router tests passing

- 2026-05-05: Fugo API Client Implementation
  - Created FugoClient class in src/stocks/client.py
  - Implemented async methods: get_intraday_quote, get_intraday_candles, get_historical_candles
  - Added Pydantic response models: IntradayQuoteResponse, IntradayCandle, HistoricalCandle
  - Configured via Settings: FUGO_BASE_URL, FUGO_TIMEOUT (10s), FUGO_MAX_RETRIES (3)
  - Retry logic with tenacity: exponential backoff with jitter, retry on 5xx errors
  - Raise BizException (FUGO_API_ERROR) on API errors, no retry on 4xx
  - Added tenacity>=8.0.0 to requirements.txt
  - Wrote 10 unit tests with mocked httpx responses
  - All 105 tests passing

- 2026-05-02: NotificationHistory API Implementation
  - Created NotificationHistory model in subscriptions module
  - Added relationships to User and IndicatorSubscription models
  - Implemented NotificationHistoryService with CRUD operations
  - Added API endpoints: GET /notifications/history, GET /notifications/history/{id}
  - Used keyset pagination on triggered_at DESC
  - Created Alembic migration with 5 indexes for query optimization
  - Wrote 15 unit tests (11 service + 4 router tests)
  - All 96 tests passing

- 2026-05-02: Stock Search API Implementation
  - Added GET /stocks/search endpoint with query parameter `q`
  - Case-insensitive partial matching on symbol and name using PostgreSQL ILIKE
  - Add search_stocks method to StockService
  - Write 6 unit tests for search functionality
  - Update API documentation with search endpoint details
  - All 82 tests passing

- 2026-05-01: IndicatorSubscription Implementation
  - Created SQLAlchemy IndicatorSubscription model with User/Stock relationships
  - Added JSONB compound_condition field for complex alert conditions
  - Created Alembic migration with partial unique constraint for duplicate prevention
  - Implemented SubscriptionService with CRUD operations and quota validation
  - Added REST endpoints: GET/POST /subscriptions, GET/PATCH/DELETE /subscriptions/{id}
  - Created Pydantic schemas with IndicatorType and Operator enums
  - Wrote 15 unit tests using PostgreSQL testcontainers
  - Updated API documentation with Subscriptions API section
  - Migrated tests from SQLite to PostgreSQL with testcontainers

- 2026-05-01: WatchList Implementation
  - Created SQLAlchemy models: Watchlist, WatchlistStock (junction table)
  - Added Alembic migration with proper indexes and partial unique constraints
  - Implemented WatchlistService with full CRUD operations
  - Added REST endpoints: GET/POST /watchlists, GET/PATCH/DELETE /watchlists/{id}
  - Added stock management: POST/DELETE/PATCH /watchlists/{id}/stocks/{stock_id}
  - Created Pydantic schemas: WatchlistCreate, WatchlistUpdate, WatchlistStockAdd, WatchlistStockUpdate
  - Wrote 13 unit tests for watchlists router
  - Updated API documentation with Watchlists API section
  - All 59 tests passing

- 2026-05-01: StockTable Implementation
  - Created SQLAlchemy Stock model with symbol, name, current_price, calculated_indicators
  - Added Alembic migration with unique index on symbol and index on is_active
  - Implemented StockService with CRUD operations and soft delete
  - Added REST endpoints: GET /stocks, GET /stocks/{symbol}, POST /stocks, PATCH /stocks/{symbol}, DELETE /stocks/{symbol}
  - Created Pydantic schemas: StockResponse, StockCreate, StockUpdate
  - Wrote 12 unit tests for stocks router
  - Updated API documentation with Stocks API section
  - All 46 tests passing

- 2026-04-30: Users & Auth Tables Update
  - Added display_name, picture_url, quota, subscription_status to users table
  - Added access_token, refresh_token, expires_at to oauth_accounts table
  - Created migration: 2026-04-30_update_users_oauth_tables.py
  - All tests passing (34/34)

- 2026-04-30: Auth Domain Refactor
  - Created new `src/auth/` domain for authentication logic
  - Separated OAuth providers into `auth/providers/` (google.py, line.py)
  - Moved JWT utilities to `auth/token.py`
  - Moved auth dependencies to `auth/dependencies.py`
  - Moved auth schemas to `auth/schema.py`
  - Moved auth business logic to `auth/service.py`
  - Moved auth endpoints to `auth/router.py` (`/auth/register`, `/auth/login`, `/auth/{provider}`)
  - Simplified `users/` domain to focus on CRUD operations only
  - Updated API endpoints: `/users/register` → `/auth/register`, `/users/login` → `/auth/login`
  - All tests passing (34/34)

- 2026-04-30: OAuth 2.0 Login with Google and LINE
  - Implemented OAuth 2.0 authorization code flow
  - Added oauth_accounts table for third-party account linking
  - Modified users table: email and hashed_password now nullable
  - Created OAuthClient for provider API interactions
  - Implemented auto account binding by email
  - Added GET /auth/{provider} and GET /auth/{provider}/callback endpoints

- 2026-04-30: Backend Login with JWT
  - Implemented POST /users/login endpoint
  - Added JWT token generation using PyJWT
  - Created authentication dependencies (get_current_user_id, get_current_user)
  - Added LoginRequest and LoginResponse schemas
  - Added comprehensive tests (34 passing)

- 2026-04-30: Backend Account Registration
  - Implemented user registration endpoint POST /users/register
  - Added email validation and uniqueness check
  - Implemented bcrypt password hashing
  - Created User model and Alembic migration
  - Added unit tests (11 passing)