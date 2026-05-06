# Current Feature

## Status

Not Started

## Goals

<!-- Add feature goals here when starting a new feature -->

## Notes

<!-- Add implementation notes and constraints here -->

## History

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