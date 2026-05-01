# IndicatorSubscription Spec

## Overview

Implement the IndicatorSubscription domain to allow users to subscribe to stock indicator alerts. Users can set conditions (e.g., RSI < 30, price > 100) and receive notifications when triggered.

## Requirements

### 1. Database Model

Create `IndicatorSubscription` model in `src/subscriptions/model.py`:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PK | Primary key |
| user_id | INTEGER | FK → users.id, NOT NULL | Subscription owner |
| stock_id | INTEGER | FK → stocks.id, NOT NULL | Target stock |
| indicator_type | VARCHAR(50) | NOT NULL | Type: rsi, macd, kd, price |
| operator | VARCHAR(10) | NOT NULL | Comparison: >, <, >=, <=, ==, != |
| target_value | DECIMAL(10,4) | NOT NULL | Threshold value |
| compound_condition | JSONB | NULL | For complex conditions (AND/OR logic) |
| is_triggered | BOOLEAN | DEFAULT FALSE | Whether condition was met |
| cooldown_end_at | TIMESTAMPTZ | NULL | Cooldown period for re-notifications |
| is_active | BOOLEAN | DEFAULT TRUE | Subscription status |

### 2. Relationships

- **User → IndicatorSubscription**: One-to-Many (user can have many subscriptions)
- **Stock → IndicatorSubscription**: One-to-Many (stock can be monitored by many subscriptions)
- Add back-reference on Stock model: `subscriptions: Mapped[list["IndicatorSubscription"]]`

### 3. Indexes

```sql
CREATE INDEX idx_subscriptions_user_id ON indicator_subscriptions(user_id);
CREATE INDEX idx_subscriptions_stock_id ON indicator_subscriptions(stock_id);
CREATE INDEX idx_subscriptions_is_active ON indicator_subscriptions(is_active);
CREATE INDEX idx_subscriptions_user_stock ON indicator_subscriptions(user_id, stock_id);
CREATE UNIQUE INDEX idx_subscriptions_user_indicator ON indicator_subscriptions(user_id, stock_id, indicator_type, operator, target_value) WHERE is_deleted = false;
```

### 4. Alembic Migration

Create migration file: `alembic/versions/YYYY-MM-DD_add_indicator_subscriptions.py`

- Create table with all columns
- Add all indexes
- Add foreign key constraints

### 5. Pydantic Schemas

Create `src/subscriptions/schema.py`:

- `IndicatorType(StrEnum)`: RSI, MACD, KD, PRICE
- `Operator(StrEnum)`: GT, LT, GTE, LTE, EQ, NEQ
- `IndicatorSubscriptionCreate`: Request for creating subscription
- `IndicatorSubscriptionUpdate`: Request for updating subscription
- `IndicatorSubscriptionResponse`: Response with all fields

### 6. Service Layer

Create `src/subscriptions/service.py`:

- `create_subscription(db, user_id, payload)`
- `get_subscription_by_id(db, subscription_id)`
- `get_user_subscriptions(db, user_id, cursor, limit)`
- `update_subscription(db, subscription_id, payload)`
- `delete_subscription(db, subscription_id)`
- `check_subscription_quota(db, user_id)` - Validate user quota

### 7. Router

Create `src/subscriptions/router.py`:

| Method | Path | Description |
|--------|------|-------------|
| GET | /subscriptions | List user's subscriptions (paginated) |
| POST | /subscriptions | Create new subscription |
| GET | /subscriptions/{id} | Get subscription details |
| PATCH | /subscriptions/{id} | Update subscription |
| DELETE | /subscriptions/{id} | Delete subscription |

### 8. Tests

Create `tests/test_subscriptions_router.py`:

- Test: Create subscription (success)
- Test: Create subscription (quota exceeded)
- Test: Create subscription (duplicate)
- Test: Get subscription list (pagination)
- Test: Update subscription
- Test: Delete subscription
- Test: Unauthorized access

## Notes

- Quota validation: Check `user.quota` against active subscription count
- Duplicate prevention: Same user + stock + indicator + operator + target_value
- Soft delete only, never hard delete
- Follow domain self-containment principle

## References

- @doc/database-mermaid.md - Database schema definition
- @src/watchlists/model.py - Similar pattern for user relationships
- @src/stocks/model.py - Stock model to add relationship
- @CLAUDE.md - Project conventions and architecture
