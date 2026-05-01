# Current Feature: StockTable Implementation

## Status

In Progress

## Goals

- [x] Create SQLAlchemy Stock model in `src/stocks/model.py`
- [x] Create Alembic migration for stocks table
- [x] Add basic CRUD service methods in `src/stocks/service.py`
- [x] Add API endpoints in `src/stocks/router.py`
- [x] Add Pydantic schemas in `src/stocks/schema.py`
- [x] Write unit tests for stocks domain
- [x] Register Stock model in `src/models/__init__.py`

## Notes

### Database Schema (from database-mermaid.md)

```mermaid
StockTable {
    string id PK
    string symbol UK "股票代碼 (ex: 2330.TW)"
    string name
    float current_price
    jsonb calculated_indicators
    boolean is_active
    timestamp updated_at
}
```

### Model Design

Following project conventions:

| Field                | Type              | Notes                                      |
| -------------------- | ----------------- | ------------------------------------------ |
| id                   | Integer (from Base) | Primary key, auto-increment              |
| symbol               | String(20)        | Unique, indexed. e.g., "2330.TW"           |
| name                 | String(255)       | Stock name in Chinese                      |
| current_price        | DECIMAL(10,2)     | Use DECIMAL for exact calculation          |
| calculated_indicators| JSONB             | Store RSI, KD, MACD etc. as JSON           |
| is_active            | Boolean           | Business state (tradable/suspended)        |
| created_at           | DateTime (from Base) | Auto-set on creation                    |
| updated_at           | DateTime (from Base) | Auto-update on modification             |
| is_deleted           | Boolean (from Base) | Soft delete marker                      |

### JSONB Structure for calculated_indicators

```json
{
  "rsi_14": 65.5,
  "kd": {
    "k": 72.3,
    "d": 68.1
  },
  "macd": {
    "macd": 12.5,
    "signal": 10.2,
    "histogram": 2.3
  },
  "updated_at": "2026-05-01T10:30:00Z"
}
```

### Indexes

| Index Name              | Columns      | Type    | Purpose                          |
| ----------------------- | ------------ | ------- | -------------------------------- |
| stocks_symbol_idx       | symbol       | Unique  | Fast lookup by stock symbol      |
| stocks_is_active_idx    | is_active    | B-tree  | Filter active stocks             |

### API Endpoints (Initial)

| Method | Path               | Description                    |
| ------ | ------------------ | ------------------------------ |
| GET    | /stocks            | List all active stocks         |
| GET    | /stocks/{symbol}   | Get stock by symbol            |
| POST   | /stocks            | Create new stock (admin)       |
| PATCH  | /stocks/{symbol}   | Update stock info              |
| DELETE | /stocks/{symbol}   | Soft delete stock              |

### Related Tables (Future Features)

- `HistoricalPriceTable` - Stock price history (stock_id FK)
- `WatchListStockTable` - Watch list membership (stock_id FK)
- `IndicatorSubscriptionTable` - User subscriptions (stock_id FK)

### File Checklist

**model.py:**
- [ ] Import Base from src.models.base
- [ ] Define Stock class with all columns
- [ ] Add __tablename__ = "stocks"
- [ ] Use Mapped[] type hints

**migration:**
- [ ] Create `migrations/versions/2026-05-01_create_stocks_table.py`
- [ ] Include all columns and indexes
- [ ] Implement upgrade() and downgrade()

**service.py:**
- [ ] get_stock_by_symbol(db, symbol) -> Stock | None
- [ ] get_stocks(db, is_active: bool = True) -> list[Stock]
- [ ] create_stock(db, data: StockCreate) -> Stock
- [ ] update_stock(db, symbol, data: StockUpdate) -> Stock
- [ ] soft_delete_stock(db, symbol) -> bool

**schema.py:**
- [ ] StockResponse - Response model
- [ ] StockCreate - Request for creating
- [ ] StockUpdate - Request for updating
- [ ] StockListResponse - Paginated list

**router.py:**
- [ ] GET /stocks - List stocks
- [ ] GET /stocks/{symbol} - Get single stock
- [ ] POST /stocks - Create stock
- [ ] PATCH /stocks/{symbol} - Update stock
- [ ] DELETE /stocks/{symbol} - Soft delete

### Constraints

- Symbol format: Taiwan stocks use `{code}.TW` (e.g., "2330.TW")
- Price precision: 2 decimal places
- Soft delete required (no hard delete)

## History

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
