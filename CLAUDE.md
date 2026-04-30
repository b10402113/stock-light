# StockLight Backend Development Guide

StockLight是一個股票到價通知服務，用戶可透過 LINE 訂閱股票價格或技術指標觸發條件，系統自動監控並推送通知。

## Compatibility Matrix

Pin to these versions or newer.

| Dependency        | Minimum | Notes                                                    |
| ----------------- | ------- | -------------------------------------------------------- |
| Python            | 3.11    | Required for `StrEnum` and `X \| Y` union syntax         |
| FastAPI           | 0.115   | `Annotated[T, Depends(...)]` is the idiomatic form       |
| Pydantic          | 2.7     | v1 APIs (`json_encoders`, `.dict()`) are removed         |
| pydantic-settings | 2.4     | Lives in a separate package since Pydantic v2            |
| SQLAlchemy        | 2.0     | Use the async API (`AsyncSession`, `async_sessionmaker`) |
| Alembic           | 1.13    | Async-aware migrations                                   |
| httpx             | 0.27    | Use `ASGITransport` for in-process tests                 |
| PyJWT             | 2.9     | Use this, not the unmaintained `python-jose`             |
| ruff              | 0.6     | Replaces black, isort, autoflake                         |

---

## Architecture Overview

### Environment

source .venv/bin/activate for any testing

### Component List

| Component      | Count | Resources       | Responsibility                 |
| -------------- | ----- | --------------- | ------------------------------ |
| Ingress/Nginx  | 1     | 0.1 CPU, 128MB  | Reverse proxy, SSL termination |
| React Frontend | 1     | 0.1 CPU, 128MB  | Static resource serving        |
| FastAPI        | 2+    | 0.25 CPU, 256MB | API request handling           |
| Postgres       | 1     | 0.5 CPU, 1GB    | Data persistence               |
| Redis          | 1     | 0.25 CPU, 512MB | Cache, Celery Broker           |
| Celery Worker  | 2     | 0.25 CPU, 256MB | Async task execution           |
| Celery Beat    | 1     | 0.1 CPU, 128MB  | Scheduled task dispatch        |

**Total: ~2 CPU, ~3GB RAM**

---

## Project Structure

Organize by domain, not by file type. Each domain is self-contained.

```
src/
├── main.py               # FastAPI entry, only mounts routers
├── config.py             # Pydantic Settings, environment variables
├── database.py           # SQLAlchemy engine/session
├── exceptions.py         # Global exception classes
├── dependencies.py       # FastAPI Depends (get_db, get_current_user)
│
├── users/                 # User domain module
│   ├── router.py         # API endpoints
│   ├── service.py        # Business logic
│   ├── schema.py         # Pydantic Request/Response
│   └── model.py          # SQLAlchemy Model
│
├── stocks/                # Stock domain module
│   ├── router.py         # API endpoints
│   ├── service.py        # Business logic (includes price update tasks)
│   ├── schema.py         # Pydantic Request/Response
│   ├── model.py          # SQLAlchemy Model
│   ├── indicators.py     # Technical indicators calculation (RSI/KD/MACD)
│   └── client.py         # Fugo API client (only stocks uses this)
│
├── subscriptions/        # Subscription domain module
│   ├── router.py         # API endpoints
│   ├── service.py        # Business logic
│   ├── schema.py         # Pydantic Request/Response
│   ├── model.py          # SQLAlchemy Model
│   ├── notifications.py  # LINE notification sending
│   ├── templates.py      # LINE Flex Message templates
│   ├── scheduler.py      # Scheduled tasks (check alerts)
│   ├── webhook.py        # LINE webhook processing
│   └── line_client.py    # LINE Messaging API client (only subscriptions uses this)
│
└── migrations/           # Alembic migrations
    ├── env.py
    ├── script.py.mako
    └── versions/
```

**Domain self-containment principle:**

- Each domain owns everything it needs (clients, helpers, tasks)
- Shared utilities go in `src/` root (`exceptions.py`, `dependencies.py`)
- No separate `core/`, `external/`, `indicators/`, `notifications/`, `tasks/`, `webhooks/` directories

**Cross-domain imports**: use explicit module names.

```python
from src.users import service as user_service
from src.stocks.indicators import calculate_rsi
from src.subscriptions.line_client import LineClient
```

---

## Module Layer Structure

Each business module (users/stocks/subscriptions) follows this pattern:

```
router.py ──► service.py ──► model.py
     │            │
     │            │
     ▼            ▼
  schema.py   client.py (domain-specific external API)
```

### Layer Responsibilities

| Layer   | File       | Allowed                                                                                 | Forbidden                                                                        |
| ------- | ---------- | --------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| router  | router.py  | Define API paths, call service, use Depends, validate schema, handle HTTP exceptions    | Direct DB operations, call client.py, write business logic, return model objects |
| service | service.py | Business logic, operate model (CRUD), call other services, call client.py, return model | Define API paths, handle HTTP exceptions, directly return schema                 |
| schema  | schema.py  | Define Request/Response, Pydantic validation                                            | DB queries, business logic                                                       |
| model   | model.py   | Define DB table structure, SQLAlchemy ORM                                               | Business logic, validation                                                       |
| client  | client.py  | Wrap external API calls (Fugo, LINE)                                                    | Business logic                                                                   |

---

## Cross-module Call Rules

| Caller  | Callee        | Allowed | Forbidden            |
| ------- | ------------- | ------- | -------------------- |
| router  | service       | ✅      | -                    |
| router  | model         | ❌      | Direct DB operations |
| router  | client.py     | ❌      | Direct API calls     |
| router  | other router  | ❌      | Cross-router calls   |
| service | model         | ✅      | -                    |
| service | client.py     | ✅      | -                    |
| service | other service | ✅      | One-way dependency   |
| service | router        | ❌      | Reverse dependency   |
| model   | service       | ❌      | Reverse dependency   |
| model   | client.py     | ❌      | -                    |

### Dependency Graph

```
client.py ◄─── service (✅)
model ◄─── service (✅)
service ◄─── router (✅)
          ◄─── other service (✅)
router ◄─── main.py (✅)

❌ Forbidden reverse dependencies:
model ──► service
service ──► router
router ──► client.py
```

---

## Domain-Specific Files

### stocks/indicators.py

Pure calculation functions for technical indicators.

```python
# src/stocks/indicators.py
import pandas as pd
from typing import List

def calculate_rsi(prices: List[float], period: int = 14) -> float:
    """Calculate RSI (pure calculation)"""
    df = pd.DataFrame({'close': prices})
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

# Called from stocks/service.py
async def get_stock_rsi(db: Session, symbol: str, period: int = 14) -> float:
    prices = await get_stock_prices(db, symbol, days=50)
    return calculate_rsi(prices, period)
```

### stocks/client.py

Fugo API client - only wraps API calls, no business logic.

```python
# src/stocks/client.py
import httpx

class FugoClient:
    """Fugo API client (only API encapsulation)"""

    async def get_intraday(self, symbol: str) -> dict:
        """Get real-time quotes"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.fugo.com/marketdata/v0.3/stock/intraday/{symbol}",
                params={"apiToken": settings.FUGO_API_KEY}
            )
            response.raise_for_status()
            return response.json()

# ❌ Forbidden: Including business logic in client
class BadFugoClient:
    async def check_price_alert(self, symbol: str, target: float):  # ❌
        data = await self.get_intraday(symbol)
        if data['close'] > target:  # ❌ Business logic belongs in service
            return True
```

### subscriptions/line_client.py

LINE Messaging API client.

```python
# src/subscriptions/line_client.py
import httpx

class LineClient:
    """LINE Messaging API client"""

    async def push_message(self, line_user_id: str, message: dict):
        async with httpx.AsyncClient() as client:
            await client.post(
                "https://api.line.me/v2/bot/message/push",
                headers={"Authorization": f"Bearer {settings.LINE_CHANNEL_TOKEN}"},
                json={"to": line_user_id, "messages": [message]}
            )
```

### subscriptions/scheduler.py

Scheduled task definitions for subscription alerts.

```python
# src/subscriptions/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

# Check alerts every 5 minutes (trading hours)
scheduler.add_job(
    check_alerts_task,
    "cron",
    hour="9-13",
    minute="*/5",
    timezone="Asia/Taipei"
)
```

### subscriptions/webhook.py

LINE webhook handling for user commands.

```python
# src/subscriptions/webhook.py
from fastapi import APIRouter, Request

router = APIRouter()

@router.post("/webhook/line")
async def line_webhook(request: Request):
    body = await request.json()
    # Parse user commands (subscribe, unsubscribe, list)
    await handle_webhook_event(body)
    return {"status": "ok"}
```

---

## Async Routes

### Decision Rule

| Route does this                       | Use                                                 |
| ------------------------------------- | --------------------------------------------------- |
| `await`-able non-blocking I/O         | `async def`                                         |
| Blocking I/O (no async client exists) | `def` (sync, runs in threadpool)                    |
| Mix of both                           | `async def` + `run_in_threadpool` for blocking part |
| CPU-bound work (>50 ms compute)       | Offload to worker process (Celery)                  |

### Do / Don't

```python
# DON'T — blocking call inside async route freezes the entire event loop
@router.get("/bad")
async def bad():
    time.sleep(10)            # blocks every request on this worker
    return {"ok": True}

# DO — sync route lets FastAPI run it in a threadpool
@router.get("/sync-ok")
def sync_ok():
    time.sleep(10)            # blocks one threadpool worker, not the loop
    return {"ok": True}

# DO — async route with awaitable sleep
@router.get("/async-ok")
async def async_ok():
    await asyncio.sleep(10)   # yields control, loop keeps serving requests
    return {"ok": True}

# DO — async route that has to call a sync library
from fastapi.concurrency import run_in_threadpool

@router.get("/wrap")
async def wrap():
    result = await run_in_threadpool(legacy_sync_client.fetch, "id")
    return result
```

---

## Pydantic

### Use Built-in Validators

```python
from enum import StrEnum
from pydantic import AnyUrl, BaseModel, EmailStr, Field


class MusicBand(StrEnum):
    AEROSMITH = "AEROSMITH"
    QUEEN = "QUEEN"
    ACDC = "AC/DC"


class UserCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=128)
    username: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")
    email: EmailStr
    age: int = Field(ge=18)                     # required, must be >= 18
    favorite_band: MusicBand | None = None
    website: AnyUrl | None = None
```

### Custom Serialization

Use `@field_serializer` for per-field rules.

```python
from datetime import datetime
from zoneinfo import ZoneInfo
from pydantic import BaseModel, field_serializer


class CustomModel(BaseModel):
    @field_serializer("*", when_used="json", check_fields=False)
    def _serialize_datetimes(self, value):
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=ZoneInfo("UTC"))
            return value.strftime("%Y-%m-%dT%H:%M:%S%z")
        return value
```

---

## Dependencies

### Use Annotated Form

```python
from typing import Annotated
from fastapi import Depends

PostDep = Annotated[dict, Depends(valid_post_id)]

@router.get("/posts/{post_id}")
async def get_post(post: PostDep):
    return post
```

### Validate Inside Dependencies

```python
async def valid_post_id(post_id: UUID4) -> dict:
    post = await service.get_by_id(post_id)
    if not post:
        raise PostNotFound()
    return post
```

### Chain Dependencies

```python
async def valid_owned_post(
    post: Annotated[dict, Depends(valid_post_id)],
    token_data: Annotated[dict, Depends(parse_jwt_data)],
) -> dict:
    if post["creator_id"] != token_data["user_id"]:
        raise UserNotOwner()
    return post
```

---

## Authentication — JWT

Use **PyJWT**, not `python-jose` (unmaintained).

```python
import jwt
from jwt.exceptions import InvalidTokenError

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
    except InvalidTokenError as exc:
        raise InvalidCredentials() from exc
```

---

## Database — SQLAlchemy 2.0 Async

```python
# src/database.py
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

engine = create_async_engine(str(settings.DATABASE_URL), pool_pre_ping=True)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)

async def get_db() -> AsyncSession:
    async with SessionFactory() as session:
        yield session
```

### Table Naming

- `lower_case_snake`
- Singular tables: `user`, `stock`, `subscription`
- Group with prefix: `payment_account`, `payment_bill`
- `_at` suffix for `datetime`, `_date` suffix for `date`
- Same FK column name everywhere (`user_id`, not mixing with `profile_id`)

### Index Naming Convention

```python
POSTGRES_INDEXES_NAMING_CONVENTION = {
    "ix": "%(column_0_label)s_idx",
    "uq": "%(table_name)s_%(column_0_name)s_key",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}
```

---

## Index Design Principles

### Index Decision Table

| Scenario            | Index?       | Type      | SQL Example                                                                       |
| ------------------- | ------------ | --------- | --------------------------------------------------------------------------------- |
| Primary key         | ✅ auto      | B-tree    | `id SERIAL PRIMARY KEY`                                                           |
| Foreign key         | ✅ must      | B-tree    | `CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id)`                |
| WHERE single column | ✅ must      | B-tree    | `CREATE INDEX idx_users_line_user_id ON users(line_user_id)`                      |
| WHERE multiple AND  | ✅ must      | Composite | `CREATE INDEX idx_subscriptions_user_symbol ON subscriptions(user_id, symbol)`    |
| ORDER BY with LIMIT | ⚠️ if needed | B-tree    | `CREATE INDEX idx_stock_prices_date_desc ON stock_prices(symbol, date DESC)`      |
| LIKE '%keyword%'    | ❌           | -         | Use full-text search instead                                                      |
| LIKE 'keyword%'     | ✅           | B-tree    | Can use regular index                                                             |
| JSONB query         | ✅ if needed | GIN       | `CREATE INDEX idx_subscriptions_condition ON subscriptions USING GIN (condition)` |

### Composite Index Rules

**Rule 1: Leftmost Prefix**

```sql
-- Index: (a, b, c)
WHERE a = ?                  -- ✅ uses index
WHERE a = ? AND b = ?        -- ✅ uses index
WHERE b = ?                  -- ❌ cannot use index
```

**Rule 2: High Selectivity First**

```sql
-- ✅ Good: user_id has high selectivity
CREATE INDEX idx_sub_user_symbol ON subscriptions(user_id, symbol);

-- ❌ Bad: symbol has many duplicates
CREATE INDEX idx_sub_symbol_user ON subscriptions(symbol, user_id);
```

**Rule 3: Covering Index**

```sql
-- Query
SELECT symbol, close FROM stock_prices
WHERE symbol = '2330.TW' ORDER BY date DESC LIMIT 1;

-- Covering index (avoids table lookup)
CREATE INDEX idx_sp_symbol_date_close ON stock_prices(symbol, date DESC, close);
```

---

## Large Table Strategies

### Large Table Prediction

| Table             | Est. Volume | Large? | Reason                                    |
| ----------------- | ----------- | ------ | ----------------------------------------- |
| users             | < 10,000    | ❌     | Hundreds of users                         |
| stocks            | ~ 2,500     | ❌     | Total Taiwan stocks                       |
| stock_prices      | High risk   | ✅     | 2500 × 200 days × 12 mo ≈ 6M rows/year    |
| notification_logs | High risk   | ✅     | Daily notifications × 365 ≈ millions/year |

### stock_prices Strategies

- [x] Must use composite index
- [x] Must limit query time range (`WHERE date >= ?`)
- [x] Forbidden `SELECT *`, only select needed columns
- [x] Periodically clean data older than 200 days

### notification_logs Strategies

- [x] Must have time index
- [x] Archive logs older than 90 days to cold storage
- [x] Use soft delete, not hard delete
- [x] Use batch insert for writes

---

## Pagination Specification

### Keyset Pagination (Required)

```python
# ❌ Wrong: Using OFFSET
@router.get("/subscriptions")
async def list_subscriptions(
    db: Session = Depends(get_db),
    page: int = 1,
    page_size: int = 20,
):
    offset = (page - 1) * page_size
    subscriptions = db.query(Subscription).offset(offset).limit(page_size).all()
    return subscriptions

# ✅ Correct: Using Keyset
@router.get("/subscriptions")
async def list_subscriptions(
    db: Annotated[Session, Depends(get_db)],
    cursor: Optional[int] = None,
    limit: int = 20,
):
    query = db.query(Subscription).order_by(Subscription.id.asc())

    if cursor:
        query = query.filter(Subscription.id > cursor)

    subscriptions = query.limit(limit).all()

    next_cursor = None
    if len(subscriptions) == limit:
        next_cursor = subscriptions[-1].id

    return {
        "data": subscriptions,
        "next_cursor": next_cursor,
        "has_more": next_cursor is not None,
    }
```

### Paginated Response Schema

```python
from pydantic import BaseModel
from typing import Generic, TypeVar, Optional, List

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    next_cursor: Optional[int] = None
    has_more: bool = False

    class Config:
        from_attributes = True
```

---

## Common Column Conventions

### Required Columns

```sql
CREATE TABLE example (
    id SERIAL PRIMARY KEY,              -- Primary key (auto-increment)
    created_at TIMESTAMPTZ DEFAULT NOW(), -- Created time (required)
    updated_at TIMESTAMPTZ DEFAULT NOW(), -- Updated time (required)
    is_deleted BOOLEAN DEFAULT FALSE    -- Soft delete marker (required)
);
```

### Column Types

| Purpose       | Name        | Type             | Default | Notes                 |
| ------------- | ----------- | ---------------- | ------- | --------------------- |
| Primary key   | id          | SERIAL/BIGSERIAL | auto    | All tables            |
| Foreign key   | {table}\_id | INTEGER/BIGINT   | -       | e.g., user_id         |
| Created time  | created_at  | TIMESTAMPTZ      | NOW()   | Timezone-aware        |
| Updated time  | updated_at  | TIMESTAMPTZ      | NOW()   | Trigger update        |
| Soft delete   | is_deleted  | BOOLEAN          | FALSE   | Forbidden hard delete |
| Active status | is_active   | BOOLEAN          | TRUE    | Business state        |
| Price/Amount  | price       | DECIMAL(10,2)    | -       | Exact calculation     |
| Percentage    | rate        | DECIMAL(5,4)     | -       | 0.1234 = 12.34%       |
| JSON data     | metadata    | JSONB            | {}      | Structured JSON       |

### updated_at Trigger

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

### Soft Delete Implementation

```python
# model.py
from sqlalchemy import Boolean, Column, DateTime, Integer
from datetime import datetime

class BaseModel:
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

    def soft_delete(self):
        self.is_deleted = True
        self.updated_at = datetime.utcnow()

# service.py - Always filter soft deleted records
def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(
        User.id == user_id,
        User.is_deleted == False
    ).first()
```

---

## Background Tasks

| Use BackgroundTasks when...     | Use Celery when...                    |
| ------------------------------- | ------------------------------------- |
| Task is < 1 second              | Task takes seconds to minutes         |
| Failure can be silently dropped | Need retries, dead-letter, visibility |
| Task is in-process              | CPU-heavy or needs separate pool      |
| No scheduling needed            | Need cron, ETA, or rate limiting      |

```python
from fastapi import BackgroundTasks

@router.post("/signup")
async def signup(data: SignupIn, bg: BackgroundTasks):
    user = await service.create_user(data)
    bg.add_task(send_welcome_email, user.email)   # fire-and-forget
    return user
```

> BackgroundTasks run after response is sent, in the same worker process.
> If worker dies, task is lost. No retry. Don't use for critical tasks.

---

## Testing

### Async Client

```python
import pytest
from httpx import AsyncClient, ASGITransport

from src.main import app

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_create_post(client: AsyncClient):
    resp = await client.post("/posts", json={"title": "hi"})
    assert resp.status_code == 201
```

### Override Dependencies

```python
from src.auth.dependencies import parse_jwt_data
from src.main import app

def fake_user():
    return {"user_id": "00000000-0000-0000-0000-000000000001"}

@pytest.fixture(autouse=True)
def _override_auth():
    app.dependency_overrides[parse_jwt_data] = fake_user
    yield
    app.dependency_overrides.clear()
```

---

## Migrations (Alembic)

- Migrations must be static and reversible
- Use async template: `alembic init -t async migrations`
- Descriptive filenames:
  ```ini
  # alembic.ini
  file_template = %%(year)d-%%(month).2d-%%(day).2d_%%(slug)s
  ```
  → `2026-04-14_add_post_content_idx.py`

---

## API Documentation

### Hide Docs Outside Selected Envs

```python
from fastapi import FastAPI
from src.config import settings

SHOW_DOCS_IN = {"local", "staging"}
app_kwargs = {"title": "StockLight API"}
if settings.ENVIRONMENT not in SHOW_DOCS_IN:
    app_kwargs["openapi_url"] = None

app = FastAPI(**app_kwargs)
```

### Document Endpoints

```python
@router.post(
    "/subscriptions",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create subscription",
    description="Creates a stock alert subscription.",
    tags=["subscriptions"],
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Validation error"},
        status.HTTP_409_CONFLICT:    {"model": ErrorResponse, "description": "Already subscribed"},
    },
)
async def create_subscription(payload: SubscriptionCreate) -> SubscriptionResponse: ...
```

---

## Naming Conventions

| Item         | Convention                 | Example                                 |
| ------------ | -------------------------- | --------------------------------------- |
| API path     | RESTful, lowercase, plural | `/users`, `/subscriptions`              |
| Function     | snake_case, verb prefix    | `get_user_by_id`, `create_subscription` |
| Class        | PascalCase                 | `UserResponse`, `FugoClient`            |
| Variable     | snake_case                 | `user_id`, `stock_prices`               |
| Schema class | `{Action}Request/Response` | `UserCreateRequest`, `UserResponse`     |
| Model class  | Singular noun              | `User`, `Subscription`                  |
| Table name   | Plural noun                | `users`, `subscriptions`                |

---

## Linting

```shell
ruff check --fix src
ruff format src
```

---

## Checklist for AI Agents

### When Adding Code

**router.py:**

- [ ] Only calls service?
- [ ] Uses Depends?
- [ ] Returns schema?
- [ ] No direct DB operations?
- [ ] No calls to client.py?

**service.py:**

- [ ] Contains business logic?
- [ ] Operates model?
- [ ] Can call client.py?
- [ ] Can call other services?
- [ ] No HTTPException?

**schema.py:**

- [ ] Only Pydantic validation?
- [ ] No DB queries?
- [ ] No business logic?

**model.py:**

- [ ] Only SQLAlchemy definition?
- [ ] No business logic methods?

**Cross-module calls:**

- [ ] service → service is one-way?
- [ ] No reverse dependencies?

### When Creating Tables

- [ ] Table name uses plural form
- [ ] Primary key named `id`, type SERIAL or BIGSERIAL
- [ ] Includes `created_at TIMESTAMPTZ`
- [ ] Includes `updated_at TIMESTAMPTZ`
- [ ] Includes `is_deleted BOOLEAN`
- [ ] Foreign keys named `{table}_id`
- [ ] Created corresponding `updated_at` trigger
- [ ] Added indexes based on query patterns
- [ ] Added indexes on foreign keys
- [ ] Added indexes on time-range queries
- [ ] Large tables use BIGSERIAL
- [ ] Prices use DECIMAL(10,2), not FLOAT
- [ ] JSON data uses JSONB, not JSON

---

## Anti-patterns

| Anti-pattern                                                                       | Why it's wrong                                       | Fix                                                                                                                   |
| ---------------------------------------------------------------------------------- | ---------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `requests.get(...)` inside `async def`                                             | Blocks the event loop. `requests` is sync.           | Use `httpx.AsyncClient` or `await run_in_threadpool(requests.get, ...)`.                                              |
| `time.sleep` / `open()` / sync DB driver inside `async def`                        | Same — blocks the loop.                              | Use the async equivalent (`asyncio.sleep`, `aiofiles`, async driver).                                                 |
| `from jose import jwt`                                                             | `python-jose` is unmaintained.                       | `import jwt` (PyJWT).                                                                                                 |
| `from async_asgi_testclient import TestClient`                                     | Unmaintained.                                        | `httpx.AsyncClient` + `ASGITransport`.                                                                                |
| `model_config = ConfigDict(json_encoders={...})`                                   | Deprecated in Pydantic v2.                           | `@field_serializer` or `Annotated[T, PlainSerializer(...)]`.                                                          |
| `Field(ge=18, default=None)`                                                       | Constraint contradicts the default.                  | Pick required or optional, not both.                                                                                  |
| `def get_user(id: int = Depends(...))` (default-arg form)                          | Legacy; gotchas with default values.                 | `user: Annotated[User, Depends(...)]`.                                                                                |
| Catching `Exception` around a route's body                                         | Hides bugs and turns 500s into silent 200s.          | Catch the specific exception class; raise `HTTPException` with a meaningful status.                                   |
| `BackgroundTasks` for anything you'd page on                                       | No retry, dies with the worker.                      | Use Celery.                                                                                                           |
| Calling a sync ORM session inside `async def`                                      | Blocks the loop, may deadlock the pool.              | Use `AsyncSession`.                                                                                                   |
| Returning a Pydantic model and _also_ setting `response_model=` to that same class | Model gets constructed twice (validate + serialize). | Either return a `dict`/ORM row and let `response_model` validate, or drop `response_model` and trust the return type. |
| Importing across domains via deep paths (`from src.users.service.user import ...`) | Tight coupling, hard to refactor.                    | `from src.users import service as user_service`.                                                                      |
| Reusing one `BaseSettings` for the whole app                                       | Hard to reason about, every domain reads every var.  | One `BaseSettings` per domain.                                                                                        |
| Mocking the database in integration tests                                          | Mock/prod divergence eventually fires in prod.       | Use a real DB (testcontainers, ephemeral schema) and `dependency_overrides` for auth/external services.               |
| Using OFFSET for pagination on large tables                                        | Scans all preceding rows, O(n) performance.          | Use keyset pagination (`WHERE id > cursor LIMIT n`).                                                                  |
| Hard delete instead of soft delete                                                 | Cannot recover data, breaks audit trails.            | Use `is_deleted` flag and filter in queries.                                                                          |
| Model methods containing business logic                                            | Violates layer separation.                           | Move logic to service layer.                                                                                          |

---

## Quick Reference

| Scenario                          | Solution                                       |
| --------------------------------- | ---------------------------------------------- |
| Non-blocking I/O                  | `async def` route with `await`                 |
| Blocking I/O (no async client)    | `def` route (sync, runs in threadpool)         |
| Sync library inside async route   | `await run_in_threadpool(fn, *args)`           |
| CPU-intensive work                | Celery worker process                          |
| Request validation against DB     | Dependency that loads + validates + returns    |
| Reuse validation across routes    | Chain dependencies                             |
| Inject dependency in modern style | `Annotated[T, Depends(...)]`                   |
| Per-request dep caching           | Default behavior — same `Depends(x)` runs once |
| Per-domain config                 | One `BaseSettings` subclass per domain         |
| Custom datetime serialization     | `@field_serializer`                            |
| Fire-and-forget short task        | `BackgroundTasks`                              |
| Reliable / scheduled / heavy task | Celery                                         |
| JWT decode                        | `PyJWT` (`import jwt`)                         |
| Async DB                          | SQLAlchemy 2.0 async (`AsyncSession`)          |
| HTTP test client                  | `httpx.AsyncClient` + `ASGITransport`          |
| Swap dep in tests                 | `app.dependency_overrides[dep] = fake`         |
| Lint + format                     | `ruff check --fix` + `ruff format`             |
| Pagination                        | Keyset (`WHERE id > cursor LIMIT n`)           |
