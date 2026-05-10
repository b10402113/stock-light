# Indicator Subscription Enhancement Spec

## Overview

Enhance the existing IndicatorSubscription model to support frontend requirements: add title, message, signal_type fields, enrich responses with stock details, and integrate with the Plan-level quota system.

## Requirements

### Current State Analysis

**Existing IndicatorSubscription Model**:
- ✅ Basic CRUD endpoints exist
- ✅ Supports compound conditions via JSONB
- ❌ Missing: title, message, signal_type fields
- ❌ Response lacks stock details (symbol, name, price)

### Database Changes

> **核心硬規矩**: 主鍵一律使用 `BIGSERIAL`，禁止 NULL（業務空值用空字串或 `0`），必備 `is_deleted` 軟刪除。

#### Enhance `indicator_subscriptions` Table

Add new fields to existing model:

```sql
ALTER TABLE indicator_subscriptions ADD COLUMN title VARCHAR(50) NOT NULL DEFAULT '';
ALTER TABLE indicator_subscriptions ADD COLUMN message VARCHAR(200) NOT NULL DEFAULT '';
ALTER TABLE indicator_subscriptions ADD COLUMN signal_type VARCHAR(10) NOT NULL DEFAULT 'buy'; -- 'buy' or 'sell'
```

**Fields**:
- `title`: Alert title (max 50 chars, 禁止 NULL，空值用空字串)
- `message`: Alert message content (max 200 chars, 禁止 NULL，空字串)
- `signal_type`: 'buy' or 'sell' indicator (禁止 NULL，預設 'buy')

### API Endpoint Enhancement

#### **POST `/subscriptions/indicators`** - Create condition alert

Request body includes: `title`, `message`, `signal_type`
Quota validation uses Plan level (max_subscriptions)
Premium users: multiple conditions (compound_condition)
Free users: single condition limit enforced

**Response Enhancement** (following existing `Response[T]` pattern):

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "stock": {
      "id": 123,
      "symbol": "2330",
      "name": "台積電",
      "current_price": 580.5,
      "change_percent": 2.3
    },
    "subscription_type": "indicator",
    "title": "RSI Buy Signal",
    "message": "2330 RSI below 30, consider buying",
    "signal_type": "buy",
    "indicator_type": "rsi",
    "operator": "<",
    "target_value": 30,
    "compound_condition": null,
    "is_triggered": false,
    "cooldown_end_at": null,
    "is_active": true,
    "created_at": "2026-05-10T10:00:00Z",
    "updated_at": "2026-05-10T10:00:00Z"
  }
}
```

#### Unified List Endpoint

**GET `/subscriptions`** - List all subscriptions (both types):
- Response includes both indicators and reminders
- Each item has `subscription_type` field to distinguish
- Supports filtering by type: `?type=indicator` or `?type=reminder`

**Response** (following existing keyset pagination pattern):

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "data": [
      {
        "id": 1,
        "stock": {
          "id": 123,
          "symbol": "2330",
          "name": "台積電",
          "current_price": 580.5,
          "change_percent": 2.3
        },
        "subscription_type": "indicator",
        "title": "RSI Buy Signal",
        "is_active": true
      }
    ],
    "next_cursor": 2,
    "has_more": false
  }
}
```

### Keyset Pagination Implementation

> **核心硬規矩**: 列表 API 強制使用游標分頁 (Keyset Pagination)，嚴禁使用 OFFSET

**Request Schema**:

```python
class SubscriptionListRequest(BaseModel):
    """訂閱列表請求"""
    type: Optional[str] = None  # 'indicator' or 'reminder'
    cursor: Optional[int] = None
    limit: int = Field(default=20, ge=1, le=100)
```

**Query Logic** (基於主鍵 id):

```python
async def list_subscriptions(
    db: AsyncSession,
    user_id: int,
    cursor: Optional[int] = None,
    limit: int = 20
) -> list[IndicatorSubscription]:
    query = select(IndicatorSubscription).where(
        IndicatorSubscription.user_id == user_id,
        IndicatorSubscription.is_deleted == False
    )

    if cursor:
        query = query.where(IndicatorSubscription.id > cursor)

    query = query.order_by(IndicatorSubscription.id.asc()).limit(limit + 1)
    results = await db.execute(query)
    return results.scalars().all()
```

### Service Layer Changes

> **架構規矩**: 嚴格遵守單向依賴 router ─► service ─► model / client

#### `src/subscriptions/service.py`

**Cross-module Call Pattern** (顯式模組匯入):

```python
from src.plans import service as plans_service
from src.stocks import service as stocks_service
```

**Stock Details Retrieval**:
- Join with Stock model to get symbol, name
- Fetch current price from Redis cache or FugoClient
- Include change_percent calculation

```python
async def enrich_subscription_with_stock(
    db: AsyncSession,
    subscription: IndicatorSubscription
) -> SubscriptionWithStock:
    stock = await stocks_service.get_stock_by_id(db, subscription.stock_id)
    price = await stocks_service.get_current_price(subscription.stock_id)

    return SubscriptionWithStock(
        id=subscription.id,
        stock=StockBrief(
            id=stock.id,
            symbol=stock.symbol,
            name=stock.name,
            current_price=price,
            change_percent=calculate_change_percent(price, stock.prev_close)
        ),
        # ... other subscription fields
    )
```

### Plan-Level Quota Integration

| Level | Max Subscriptions (Total) | Max Conditions per Alert |
|-------|---------------------------|--------------------------|
| 1     | 10                        | 1                        |
| 2     | 50                        | 3                        |
| 3     | 100                       | Unlimited                |
| 4     | Unlimited                 | Unlimited                |

**Quota Check Logic** (service layer):

```python
async def validate_subscription_quota(db: AsyncSession, user_id: int) -> None:
    plan = await plans_service.get_active_plan(db, user_id)
    current_count = await count_user_subscriptions(db, user_id)
    max_allowed = plan.level_config.max_subscriptions

    if current_count >= max_allowed:
        raise QuotaExceededError(
            f"Quota exceeded: {current_count}/{max_allowed} subscriptions"
        )
```

### Migration Strategy

1. Add `title`, `message`, `signal_type` columns to `indicator_subscriptions` (NOT NULL with DEFAULT)
2. Update `src/subscriptions/model.py` with new fields
3. Update `src/subscriptions/schema.py` with new request/response schemas
4. Update `src/subscriptions/service.py`:
   - Enhance quota validation with Plan integration
   - Add stock details retrieval
5. Update `src/subscriptions/router.py`:
   - Enhance existing endpoints with new fields
   - Add unified list endpoint
6. Add tests for new functionality

### Frontend-Specific Response Fields

Based on [doc/frontend-spec.md](../frontend-spec.md):

**Home Page Subscription Card**:
- Stock symbol and name (e.g., "2330 台積電")
- Current price with change percentage (green/red)
- Subscription type badge (技術指標)
- Settings button (gear icon)

**Add Page Form Fields**:
- title, message, signal_type, indicator, operator, value

## References

- [doc/frontend-spec.md](../frontend-spec.md) - Frontend requirements
- [src/response.py](../../src/response.py) - Unified Response[T] format
- [src/subscriptions/schema.py](../../src/subscriptions/schema.py) - Existing keyset pagination pattern
- [src/subscriptions/model.py](../../src/subscriptions/model.py) - Current IndicatorSubscription model
- [src/subscriptions/router.py](../../src/subscriptions/router.py) - Existing API endpoints
- [indicator-subscription.md](indicator-subscription.md) - Base IndicatorSubscription spec