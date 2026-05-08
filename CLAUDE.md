# 專案規範

## Project Overview

StockLight是一個股票到價通知服務，用戶可透過 LINE 訂閱股票價格或技術指標觸發條件，系統自動監控並推送通知。

## Project Structure

Organize by domain, not by file type. Each domain is self-contained.

```
src/
├── main.py               # FastAPI entry, only mounts routers
├── config.py             # Pydantic Settings, environment variables
├── database.py           # SQLAlchemy engine/session
├── exceptions.py         # Global exception classes
├── dependencies.py       # FastAPI Depends (get_db, get_current_user)
├── admin/                # React management system
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

## Core

- **技術棧**: Python 3.11+, FastAPI 0.115+, SQLAlchemy 2.0 (Async), Pydantic 2.7+, PostgreSQL, Redis, Celery。
- **架構原則**: 採領域驅動 (Domain-driven) 完全獨立。嚴格遵守單向調用層級：`router` ➔ `service` ➔ `model` / `client`。嚴禁反向依賴與跨 Router 調用。
- **資料庫硬原則**:
  - 主鍵一律使用自增 BIGINT (`BIGSERIAL`)，禁止使用 UUID（影響索引效能）。
  - 禁止使用 NULL，業務空值請用空字串或 `0` 代替。
  - 嚴禁硬刪除，必須使用 `is_deleted` 軟刪除並搭配 `updated_at` Trigger。
  - 列表 API 強制使用 Keyset Pagination (游標分頁)，嚴禁使用 `OFFSET`。
- **非同步開發**: I/O 密集型一律用 `async def`；阻塞型操作使用 `def` 或 `run_in_threadpool`；耗時大於 50ms 或需重試的任務一律交由 Celery 處理，禁用 `BackgroundTasks` 處理關鍵任務。
- **代碼風格**: 全面使用 `ruff` 進行格式化與靜態檢查；依賴注入統一使用最新標準 `Annotated[T, Depends(...)]`。

## Run the application

```bash
# 進入虛擬環境
source .venv/bin/activate

# run application
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# run seeds
uv run scripts/seed_data.py

```

### Testing

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_users.py

# Run with coverage report
uv run pytest --cov=src --cov-report=html
```

## 詳細文檔

- 架構與模組開發規範: 見 `docs/rules/architecture.md` (含跨模組限制、目錄結構、Anti-patterns)
- 數據庫設計與遷移: 見 `docs/rules/database.md` (含索引策略、大表處理、Alembic 規範)
- API 與資料驗證規範: 見 `docs/rules/api-spec.md` (含 Pydantic 驗證、游標分頁實作、JWT 認證)
- 背景任務與非同步決策: 見 `docs/rules/async-tasks.md` (含 Celery vs BackgroundTasks 決策表)
- 測試規範: 見 `docs/rules/testing.md` (含 AsyncClient 測試與 Dependencies 覆寫)
