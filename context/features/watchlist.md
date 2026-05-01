# WatchList Spec

## Overview

Implement a WatchList feature that allows users to manage their personal stock watchlists. Users can create watchlists, add/remove stocks, and perform full CRUD operations on their watchlist entries.

## Requirements

### Database Tables

#### watchlists Table
- `id`: SERIAL PRIMARY KEY
- `user_id`: INTEGER FK -> users.id (required)
- `name`: VARCHAR(100) (required, default: "My Watchlist")
- `description`: VARCHAR(500) (optional)
- `is_default`: BOOLEAN (default: false)
- Standard columns: `created_at`, `updated_at`, `is_deleted`

**Indexes:**
- `watchlists_user_id_idx` on `user_id`
- `watchlists_user_id_name_key` unique on `(user_id, name)` where `is_deleted = false`

#### watchlist_stocks Table (Junction)
- `id`: SERIAL PRIMARY KEY
- `watchlist_id`: INTEGER FK -> watchlists.id (required)
- `stock_id`: INTEGER FK -> stocks.id (required)
- `notes`: VARCHAR(500) (optional, user notes about this stock)
- `sort_order`: INTEGER (default: 0, for custom ordering)
- Standard columns: `created_at`, `updated_at`, `is_deleted`

**Indexes:**
- `watchlist_stocks_watchlist_id_idx` on `watchlist_id`
- `watchlist_stocks_stock_id_idx` on `stock_id`
- `watchlist_stocks_watchlist_stock_key` unique on `(watchlist_id, stock_id)` where `is_deleted = false`

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/watchlists` | List all user's watchlists |
| POST | `/watchlists` | Create a new watchlist |
| GET | `/watchlists/{watchlist_id}` | Get watchlist details with stocks |
| PATCH | `/watchlists/{watchlist_id}` | Update watchlist name/description |
| DELETE | `/watchlists/{watchlist_id}` | Delete a watchlist (soft delete) |
| POST | `/watchlists/{watchlist_id}/stocks` | Add stock to watchlist |
| DELETE | `/watchlists/{watchlist_id}/stocks/{stock_id}` | Remove stock from watchlist |
| PATCH | `/watchlists/{watchlist_id}/stocks/{stock_id}` | Update stock notes/sort_order |

### Business Logic

1. **Authorization**: User can only access their own watchlists
2. **Default Watchlist**: First watchlist created is auto-set as default
3. **Quota Check**: Optional - enforce max stocks per watchlist based on user quota
4. **Duplicate Prevention**: Cannot add same stock to same watchlist twice
5. **Stock Validation**: Stock must exist and be active (`is_active = true`)

### Module Structure

Follow domain-driven structure per CLAUDE.md:

```
src/watchlists/
├── router.py      # API endpoints
├── service.py     # Business logic
├── schema.py      # Pydantic schemas
├── model.py       # SQLAlchemy models
```

### Schemas

```python
# Request
class WatchlistCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)

class WatchlistUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)

class WatchlistStockAdd(BaseModel):
    stock_id: int
    notes: str | None = Field(None, max_length=500)

class WatchlistStockUpdate(BaseModel):
    notes: str | None = Field(None, max_length=500)
    sort_order: int | None = None

# Response
class WatchlistResponse(BaseModel):
    id: int
    name: str
    description: str | None
    is_default: bool
    stock_count: int
    created_at: datetime

class WatchlistDetailResponse(BaseModel):
    id: int
    name: str
    description: str | None
    is_default: bool
    stocks: list[WatchlistStockItem]

class WatchlistStockItem(BaseModel):
    stock_id: int
    symbol: str
    name: str
    current_price: Decimal | None
    notes: str | None
    sort_order: int
    added_at: datetime
```

## References

- @CLAUDE.md - Architecture, naming conventions, module structure
- @src/stocks/model.py - Stock model reference
- @src/users/model.py - User model reference
- @src/models/base.py - Base model with common columns
