# Scheduled Reminder Subscription Spec

## Overview

Implement a new Scheduled Reminder subscription type that triggers at scheduled times regardless of technical indicator conditions. Users can set daily, weekly, or monthly reminders for their tracked stocks.

## Requirements

### Subscription Type Definition

**Scheduled Reminder (定期提醒)** - Triggered at scheduled times regardless of conditions:
- Users receive regular stock updates at configured times
- Independent of indicator conditions
- Supports Daily/Weekly/Monthly frequencies

### Database Model

> **核心硬規矩**: 主鍵一律使用 `BIGSERIAL`，禁止 NULL（業務空值用空字串或 `0`），必備 `is_deleted` 軟刪除。

#### Create `scheduled_reminders` Table

```sql
CREATE TABLE scheduled_reminders (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    stock_id BIGINT NOT NULL REFERENCES stocks(id),
    title VARCHAR(50) NOT NULL DEFAULT '',
    message VARCHAR(200) NOT NULL DEFAULT '',
    frequency_type VARCHAR(10) NOT NULL DEFAULT 'daily', -- 'daily', 'weekly', 'monthly'
    reminder_time TIME NOT NULL DEFAULT '17:00:00', -- e.g., '17:00'
    day_of_week SMALLINT NOT NULL DEFAULT 0, -- 0-6 (Mon-Sun) for weekly, 0 表示未使用
    day_of_month SMALLINT NOT NULL DEFAULT 0, -- 1-28 for monthly, 0 表示未使用
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_triggered_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT '1970-01-01 00:00:00+00',
    next_trigger_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

-- Indexes (遵循命名慣例: {table}_{column}_idx)
CREATE INDEX scheduled_reminders_user_id_idx ON scheduled_reminders(user_id);
CREATE INDEX scheduled_reminders_stock_id_idx ON scheduled_reminders(stock_id);
CREATE INDEX scheduled_reminders_is_active_idx ON scheduled_reminders(is_active);
CREATE INDEX scheduled_reminders_next_trigger_at_idx ON scheduled_reminders(next_trigger_at);
CREATE UNIQUE INDEX scheduled_reminders_user_stock_unique_key ON scheduled_reminders(user_id, stock_id, frequency_type, reminder_time, day_of_week, day_of_month)
    WHERE is_deleted = false;
```

**Fields** (遵守禁止 NULL 規矩):
- `frequency_type`: 'daily', 'weekly', or 'monthly' (預設 'daily')
- `reminder_time`: Time of day to send reminder (預設 '17:00:00')
- `day_of_week`: For weekly (0=Monday, 6=Sunday), 非週期類型時為 0
- `day_of_month`: For monthly (1-28), 非月周期類型時為 0
- `last_triggered_at`: 上次觸發時間 (預設 '1970-01-01' 作為 sentinel 值)
- `next_trigger_at`: Calculated next trigger timestamp

### Relationships

- **User → ScheduledReminder**: One-to-Many (user can have many reminders)
- **Stock → ScheduledReminder**: One-to-Many (stock can be monitored by many reminders)

### Pydantic Schemas

Create in `src/subscriptions/schema.py`:

```python
class FrequencyType(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

class ScheduledReminderCreate(BaseModel):
    stock_id: int
    title: str = Field(default="", max_length=50)
    message: str = Field(default="", max_length=200)
    frequency_type: FrequencyType = FrequencyType.DAILY
    reminder_time: str = Field(default="17:00")  # HH:MM format
    day_of_week: int = Field(default=0, ge=0, le=6)  # 0-6 for weekly
    day_of_month: int = Field(default=0, ge=0, le=28)  # 1-28 for monthly

class ScheduledReminderResponse(BaseModel):
    id: int
    stock: StockBrief
    title: str
    message: str
    frequency_type: FrequencyType
    reminder_time: str
    day_of_week: int
    day_of_month: int
    next_trigger_at: datetime
    is_active: bool
    created_at: datetime
    updated_at: datetime
```

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /subscriptions/reminders | Create scheduled reminder |
| GET | /subscriptions/reminders | List user's reminders (paginated) |
| GET | /subscriptions/reminders/{id} | Get reminder details |
| PATCH | /subscriptions/reminders/{id} | Update reminder settings |
| DELETE | /subscriptions/reminders/{id} | Soft delete reminder |

#### **POST `/subscriptions/reminders`** - Create scheduled reminder

```json
{
  "stock_id": 123,
  "title": "Weekly 2330 Reminder",
  "message": "Check 2330 weekly performance",
  "frequency_type": "weekly",
  "reminder_time": "17:00",
  "day_of_week": 2
}
```

**Response**:

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
    "title": "Weekly 2330 Reminder",
    "message": "Check 2330 weekly performance",
    "frequency_type": "weekly",
    "reminder_time": "17:00",
    "day_of_week": 2,
    "day_of_month": 0,
    "next_trigger_at": "2026-05-15T17:00:00Z",
    "is_active": true,
    "created_at": "2026-05-10T10:00:00Z",
    "updated_at": "2026-05-10T10:00:00Z"
  }
}
```

#### **GET `/subscriptions/reminders`** - List user's scheduled reminders

Keyset pagination (游標分頁，嚴禁 OFFSET)
Response includes stock details

### Service Layer

> **架構規矩**: 嚴格遵守單向依賴 router ─► service ─► model / client

Create in `src/subscriptions/service.py`:

```python
async def create_scheduled_reminder(
    db: AsyncSession,
    user_id: int,
    payload: ScheduledReminderCreate
) -> ScheduledReminder:
    # Validate quota
    await validate_subscription_quota(db, user_id)

    # Calculate next_trigger_at
    next_trigger = calculate_next_trigger_time(
        payload.frequency_type,
        payload.reminder_time,
        payload.day_of_week,
        payload.day_of_month
    )

    # Create reminder
    reminder = ScheduledReminder(
        user_id=user_id,
        stock_id=payload.stock_id,
        title=payload.title,
        message=payload.message,
        frequency_type=payload.frequency_type,
        reminder_time=payload.reminder_time,
        day_of_week=payload.day_of_week,
        day_of_month=payload.day_of_month,
        next_trigger_at=next_trigger
    )
    db.add(reminder)
    await db.commit()
    return reminder

def calculate_next_trigger_time(
    frequency_type: FrequencyType,
    reminder_time: str,
    day_of_week: int,
    day_of_month: int
) -> datetime:
    """Calculate next trigger timestamp based on frequency settings."""
    now = datetime.now(timezone.utc)
    time_parts = datetime.strptime(reminder_time, "%H:%M")

    if frequency_type == FrequencyType.DAILY:
        next_date = now.date() + timedelta(days=1)
        return datetime.combine(next_date, time_parts.time(), tzinfo=timezone.utc)

    elif frequency_type == FrequencyType.WEEKLY:
        # Find next occurrence of day_of_week
        days_ahead = (day_of_week - now.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7  # Move to next week
        next_date = now.date() + timedelta(days=days_ahead)
        return datetime.combine(next_date, time_parts.time(), tzinfo=timezone.utc)

    elif frequency_type == FrequencyType.MONTHLY:
        # Find next occurrence of day_of_month
        next_month = now.month
        next_year = now.year
        if now.day >= day_of_month:
            next_month += 1
            if next_month > 12:
                next_month = 1
                next_year += 1
        next_date = date(next_year, next_month, day_of_month)
        return datetime.combine(next_date, time_parts.time(), tzinfo=timezone.utc)
```

### Scheduler Integration

#### `src/subscriptions/scheduler.py`

Add scheduled reminder processing:

```python
async def process_scheduled_reminders():
    """Process all scheduled reminders that are due."""
    now = datetime.now(timezone.utc)
    due_reminders = await get_due_reminders(now)

    for reminder in due_reminders:
        # Fetch latest stock data via stocks_service
        stock_data = await stocks_service.get_stock_price(reminder.stock_id)

        # Send LINE notification
        await send_reminder_notification(reminder, stock_data)

        # Update next_trigger_at
        await update_next_trigger_time(reminder)

async def get_due_reminders(now: datetime) -> list[ScheduledReminder]:
    """Get reminders where next_trigger_at <= now and is_active."""
    query = select(ScheduledReminder).where(
        ScheduledReminder.next_trigger_at <= now,
        ScheduledReminder.is_active == True,
        ScheduledReminder.is_deleted == False
    )
    results = await db.execute(query)
    return results.scalars().all()

async def update_next_trigger_time(reminder: ScheduledReminder):
    """Update reminder's next_trigger_at and last_triggered_at."""
    reminder.last_triggered_at = datetime.now(timezone.utc)
    reminder.next_trigger_at = calculate_next_trigger_time(
        reminder.frequency_type,
        reminder.reminder_time,
        reminder.day_of_week,
        reminder.day_of_month
    )
    await db.commit()
```

**Trigger Calculation**:
- Daily: `next_trigger_at = today + 1 day at reminder_time`
- Weekly: `next_trigger_at = next day_of_week at reminder_time`
- Monthly: `next_trigger_at = next day_of_month at reminder_time`

### Router Layer

> **Router 權責**: 定義路徑、呼叫 Service 層、使用 Depends、Schema 驗證、處理 HTTP 畩常

```python
@router.post("/subscriptions/reminders", response_model=Response[ScheduledReminderResponse])
async def create_reminder(
    payload: ScheduledReminderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Response[ScheduledReminderResponse]:
    """建立定期提醒訂閱"""
    reminder = await service.create_scheduled_reminder(db, current_user.id, payload)
    enriched = await service.enrich_reminder_with_stock(db, reminder)
    return Response(data=enriched)

@router.get("/subscriptions/reminders", response_model=Response[ScheduledReminderListResponse])
async def list_reminders(
    request: ReminderListRequest = Depends(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Response[ScheduledReminderListResponse]:
    """列出用戶的定期提醒"""
    reminders = await service.list_scheduled_reminders(
        db, current_user.id, request.cursor, request.limit
    )
    return Response(data=ScheduledReminderListResponse.from_models(reminders))
```

### Migration Strategy

1. Create Alembic migration for `scheduled_reminders` table
2. Create `ScheduledReminder` model in `src/subscriptions/model.py`
3. Add reminder schemas to `src/subscriptions/schema.py`
4. Add reminder service methods to `src/subscriptions/service.py`
5. Add reminder endpoints to `src/subscriptions/router.py`
6. Add reminder processing to `src/subscriptions/scheduler.py`
7. Add tests for reminder functionality

### Frontend-Specific Fields

Based on [doc/frontend-spec.md](../frontend-spec.md):

**Home Page Subscription Card**:
- Subscription type badge (定期提醒)
- Next trigger time display
- Frequency indicator (每日/每週/每月)

**Add Page Form Fields**:
- title, message
- frequency_type selector
- reminder_time picker
- day_of_week selector (for weekly)
- day_of_month selector (for monthly)

## References

- [doc/frontend-spec.md](../frontend-spec.md) - Frontend requirements
- [indicator-subscription.md](indicator-subscription.md) - Existing IndicatorSubscription spec
- [indicator-subscription-enhancement.md](indicator-subscription-enhancement.md) - Enhancement spec
- [src/response.py](../../src/response.py) - Unified Response[T] format
- [src/subscriptions/scheduler.py](../../src/subscriptions/scheduler.py) - Existing scheduler pattern
- [doc/rules/database.md](../rules/database.md) - Database design rules