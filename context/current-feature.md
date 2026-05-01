# Current Feature

## Status

Not Started

## Goals

## Notes

## History

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
