## Subscriptions API

### List Subscriptions

Get all indicator subscriptions for the authenticated user with keyset pagination. Responses include enriched stock details (symbol, name, price).

**Endpoint**: `GET /subscriptions`

**Authentication**: Required (JWT Bearer token)

**Headers**:

| Header        | Value          | Required |
| ------------- | -------------- | -------- |
| Authorization | Bearer {token} | Yes      |

**Query Parameters**:

| Parameter | Type    | Required | Default | Description                                    |
| --------- | ------- | -------- | ------- | ---------------------------------------------- |
| cursor    | integer | No       | -       | Pagination cursor (last ID from previous page) |
| limit     | integer | No       | 20      | Items per page (1-100)                         |

**Response** (200 OK):

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
          "symbol": "2330.TW",
          "name": "台積電",
          "current_price": 580.5,
          "change_percent": null
        },
        "subscription_type": "indicator",
        "title": "RSI Buy Signal",
        "message": "2330 RSI below 30, consider buying",
        "signal_type": "buy",
        "indicator_type": "rsi",
        "operator": "<",
        "target_value": "30.0000",
        "compound_condition": null,
        "is_triggered": false,
        "cooldown_end_at": null,
        "is_active": true,
        "created_at": "2026-05-01T10:00:00Z",
        "updated_at": "2026-05-01T10:00:00Z"
      }
    ],
    "next_cursor": null,
    "has_more": false
  }
}
```

**Response Schema**:

| Field       | Type            | Description                            |
| ----------- | --------------- | -------------------------------------- |
| data        | array           | List of subscriptions                  |
| next_cursor | integer \| null | Cursor for next page (null if no more) |
| has_more    | boolean         | Whether more results exist             |

**Subscription Schema**:

| Field              | Type             | Description                              |
| ------------------ | ---------------- | ---------------------------------------- |
| id                 | integer          | Subscription ID                          |
| stock              | object           | Stock details (id, symbol, name, price)  |
| subscription_type  | string           | Always "indicator"                       |
| title              | string           | Alert title (max 50 chars)               |
| message            | string           | Alert message content (max 200 chars)    |
| signal_type        | string           | Signal type: "buy" or "sell"             |
| indicator_type     | string           | Indicator type: rsi, macd, kd, price     |
| operator           | string           | Comparison: >, <, >=, <=, ==, !=         |
| target_value       | decimal          | Target threshold value                   |
| compound_condition | object \| null   | Complex AND/OR conditions                |
| is_triggered       | boolean          | Whether condition was triggered          |
| cooldown_end_at    | datetime \| null | Cooldown period end time                 |
| is_active          | boolean          | Subscription active status               |
| created_at         | datetime         | Creation timestamp                       |
| updated_at         | datetime         | Last update timestamp                    |

**Stock Schema**:

| Field          | Type            | Description                         |
| -------------- | --------------- | ----------------------------------- |
| id             | integer         | Stock ID                            |
| symbol         | string          | Stock symbol (e.g., "2330.TW")      |
| name           | string          | Stock name (e.g., "台積電")         |
| current_price  | decimal \| null | Current price from Redis cache      |
| change_percent | decimal \| null | Price change percentage (if available) |

---

### Create Subscription

Create a new indicator subscription. Quota is validated against the user's Plan level.

**Endpoint**: `POST /subscriptions`

**Authentication**: Required (JWT Bearer token)

**Request Body**:

```json
{
  "stock_id": 1,
  "title": "RSI Buy Signal",
  "message": "2330 RSI below 30, consider buying",
  "signal_type": "buy",
  "indicator_type": "rsi",
  "operator": "<",
  "target_value": "30.0",
  "compound_condition": null
}
```

**Request Schema**:

| Field              | Type           | Required | Default | Constraints                 | Description                 |
| ------------------ | -------------- | -------- | ------- | --------------------------- | --------------------------- |
| stock_id           | integer        | Yes      | -       | Must reference active stock | Target stock ID             |
| title              | string         | No       | ""      | max_length: 50              | Alert title                 |
| message            | string         | No       | ""      | max_length: 200             | Alert message content       |
| signal_type        | string         | No       | "buy"   | Enum: buy, sell             | Signal type                 |
| indicator_type     | string         | Yes      | -       | Enum: rsi, macd, kd, price  | Type of indicator           |
| operator           | string         | Yes      | -       | Enum: >, <, >=, <=, ==, !=  | Comparison operator         |
| target_value       | decimal        | Yes      | -       | >= 0                        | Target threshold value      |
| compound_condition | object \| null | No       | null    | -                           | Complex conditions (AND/OR) |

**Signal Types**:

| Value | Description             |
| ----- | ----------------------- |
| buy   | Buy signal indicator    |
| sell  | Sell signal indicator   |

**Indicator Types**:

| Value | Description                           |
| ----- | ------------------------------------- |
| rsi   | Relative Strength Index               |
| macd  | Moving Average Convergence Divergence |
| kd    | Stochastic Oscillator                 |
| price | Stock price                           |

**Operators**:

| Value | Description           |
| ----- | --------------------- |
| >     | Greater than          |
| <     | Less than             |
| >=    | Greater than or equal |
| <=    | Less than or equal    |
| ==    | Equal to              |
| !=    | Not equal to          |

**Response** (201 Created):

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "stock": {
      "id": 123,
      "symbol": "2330.TW",
      "name": "台積電",
      "current_price": 580.5,
      "change_percent": null
    },
    "subscription_type": "indicator",
    "title": "RSI Buy Signal",
    "message": "2330 RSI below 30, consider buying",
    "signal_type": "buy",
    "indicator_type": "rsi",
    "operator": "<",
    "target_value": "30.0000",
    "compound_condition": null,
    "is_triggered": false,
    "cooldown_end_at": null,
    "is_active": true,
    "created_at": "2026-05-01T10:00:00Z",
    "updated_at": "2026-05-01T10:00:00Z"
  }
}
```

**Error Responses**:

| Status | Message                               |
| ------ | ------------------------------------- |
| 400    | Stock not found or inactive: {id}     |
| 400    | Duplicate subscription already exists |
| 403    | Subscription quota exceeded: used X/Y |
| 409    | Subscription already exists           |

---

### Get Subscription

Get a single subscription by ID with enriched stock details.

**Endpoint**: `GET /subscriptions/{subscription_id}`

**Authentication**: Required (JWT Bearer token)

**Path Parameters**:

| Parameter       | Type    | Required | Description     |
| --------------- | ------- | -------- | --------------- |
| subscription_id | integer | Yes      | Subscription ID |

**Response** (200 OK):

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "stock": {
      "id": 123,
      "symbol": "2330.TW",
      "name": "台積電",
      "current_price": 580.5,
      "change_percent": null
    },
    "subscription_type": "indicator",
    "title": "RSI Buy Signal",
    "message": "2330 RSI below 30, consider buying",
    "signal_type": "buy",
    "indicator_type": "rsi",
    "operator": "<",
    "target_value": "30.0000",
    "compound_condition": null,
    "is_triggered": false,
    "cooldown_end_at": null,
    "is_active": true,
    "created_at": "2026-05-01T10:00:00Z",
    "updated_at": "2026-05-01T10:00:00Z"
  }
}
```

**Error Responses**:

| Status | Message                      |
| ------ | ---------------------------- |
| 404    | Subscription not found: {id} |

---

### Update Subscription

Update subscription title, message, signal_type, indicator type, operator, target value, or active status.

**Endpoint**: `PATCH /subscriptions/{subscription_id}`

**Authentication**: Required (JWT Bearer token)

**Path Parameters**:

| Parameter       | Type    | Required | Description     |
| --------------- | ------- | -------- | --------------- |
| subscription_id | integer | Yes      | Subscription ID |

**Request Body**:

```json
{
  "title": "Updated Title",
  "message": "Updated message",
  "signal_type": "sell",
  "indicator_type": "price",
  "operator": ">",
  "target_value": "700.0",
  "is_active": false
}
```

**Request Schema**:

| Field              | Type            | Required | Constraints                | Description         |
| ------------------ | --------------- | -------- | -------------------------- | ------------------- |
| title              | string \| null  | No       | max_length: 50             | Alert title         |
| message            | string \| null  | No       | max_length: 200            | Alert message       |
| signal_type        | string \| null  | No       | Enum: buy, sell            | Signal type         |
| indicator_type     | string \| null  | No       | Enum: rsi, macd, kd, price | Type of indicator   |
| operator           | string \| null  | No       | Enum: >, <, >=, <=, ==, != | Comparison operator |
| target_value       | decimal \| null | No       | >= 0                       | Target value        |
| compound_condition | object \| null  | No       | -                          | Complex conditions  |
| is_active          | boolean \| null | No       | -                          | Active status       |

**Response** (200 OK):

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "stock": {
      "id": 123,
      "symbol": "2330.TW",
      "name": "台積電",
      "current_price": 580.5,
      "change_percent": null
    },
    "subscription_type": "indicator",
    "title": "Updated Title",
    "message": "Updated message",
    "signal_type": "sell",
    "indicator_type": "price",
    "operator": ">",
    "target_value": "700.0000",
    "compound_condition": null,
    "is_triggered": false,
    "cooldown_end_at": null,
    "is_active": false,
    "created_at": "2026-05-01T10:00:00Z",
    "updated_at": "2026-05-01T11:00:00Z"
  }
}
```

**Error Responses**:

| Status | Message                      |
| ------ | ---------------------------- |
| 404    | Subscription not found: {id} |

---

### Delete Subscription

Soft delete a subscription.

**Endpoint**: `DELETE /subscriptions/{subscription_id}`

**Authentication**: Required (JWT Bearer token)

**Path Parameters**:

| Parameter       | Type    | Required | Description     |
| --------------- | ------- | -------- | --------------- |
| subscription_id | integer | Yes      | Subscription ID |

**Response** (200 OK):

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "stock": {
      "id": 123,
      "symbol": "2330.TW",
      "name": "台積電",
      "current_price": 580.5,
      "change_percent": null
    },
    "subscription_type": "indicator",
    "title": "RSI Buy Signal",
    "message": "2330 RSI below 30",
    "signal_type": "buy",
    "indicator_type": "rsi",
    "operator": "<",
    "target_value": "30.0000",
    "compound_condition": null,
    "is_triggered": false,
    "cooldown_end_at": null,
    "is_active": true,
    "created_at": "2026-05-01T10:00:00Z",
    "updated_at": "2026-05-01T12:00:00Z"
  }
}
```

**Error Responses**:

| Status | Message                      |
| ------ | ---------------------------- |
| 404    | Subscription not found: {id} |

**Note**: After deletion, the subscription will no longer appear in list results or be accessible by ID.

---

### Quota Limits by Plan Level

Subscription quota is validated against the user's active Plan level:

| Level | Name    | Max Subscriptions | Max Conditions per Alert |
| ----- | ------- | ----------------- | ------------------------ |
| 1     | Regular | 10                | 1                        |
| 2     | Pro     | 50                | 3                        |
| 3     | Pro Max | 100               | Unlimited                |
| 4     | Admin   | Unlimited (-1)     | Unlimited                |

---

## Scheduled Reminders API

Scheduled reminders trigger at configured times regardless of indicator conditions. Supports daily, weekly, and monthly frequencies.

### List Scheduled Reminders

Get all scheduled reminders for the authenticated user with keyset pagination.

**Endpoint**: `GET /subscriptions/reminders`

**Authentication**: Required (JWT Bearer token)

**Query Parameters**:

| Parameter | Type    | Required | Default | Description                                    |
| --------- | ------- | -------- | ------- | ---------------------------------------------- |
| cursor    | integer | No       | -       | Pagination cursor (last ID from previous page) |
| limit     | integer | No       | 20      | Items per page (1-100)                         |

**Response** (200 OK):

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
          "symbol": "2330.TW",
          "name": "台積電",
          "current_price": 580.5,
          "change_percent": null
        },
        "subscription_type": "reminder",
        "title": "Daily 2330 Reminder",
        "message": "Check daily performance",
        "frequency_type": "daily",
        "reminder_time": "17:00",
        "day_of_week": 0,
        "day_of_month": 0,
        "next_trigger_at": "2026-05-11T17:00:00Z",
        "is_active": true,
        "created_at": "2026-05-10T10:00:00Z",
        "updated_at": "2026-05-10T10:00:00Z"
      }
    ],
    "next_cursor": null,
    "has_more": false
  }
}
```

---

### Create Scheduled Reminder

Create a new scheduled reminder. Quota is validated against the user's Plan level (combined with indicator subscriptions).

**Endpoint**: `POST /subscriptions/reminders`

**Authentication**: Required (JWT Bearer token)

**Request Body**:

```json
{
  "stock_id": 1,
  "title": "Weekly 2330 Reminder",
  "message": "Check weekly performance",
  "frequency_type": "weekly",
  "reminder_time": "17:00",
  "day_of_week": 2
}
```

**Request Schema**:

| Field          | Type    | Required | Default  | Constraints                     | Description                   |
| -------------- | ------- | -------- | -------- | ------------------------------- | ----------------------------- |
| stock_id       | integer | Yes      | -        | Must reference active stock     | Target stock ID               |
| title          | string  | No       | ""       | max_length: 50                  | Reminder title                |
| message        | string  | No       | ""       | max_length: 200                 | Reminder message content      |
| frequency_type | string  | No       | "daily"  | Enum: daily, weekly, monthly    | Frequency type                |
| reminder_time  | string  | No       | "17:00"  | Format: HH:MM                   | Time of day to send reminder  |
| day_of_week    | integer | No       | 0        | 0-6 (Mon-Sun), only for weekly  | Day of week for weekly        |
| day_of_month   | integer | No       | 0        | 1-28, only for monthly          | Day of month for monthly      |

**Frequency Types**:

| Value    | Description                  |
| -------- | ---------------------------- |
| daily    | Triggers daily at set time   |
| weekly   | Triggers weekly on set day   |
| monthly  | Triggers monthly on set date |

**Response** (201 Created):

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "stock": {
      "id": 123,
      "symbol": "2330.TW",
      "name": "台積電",
      "current_price": 580.5,
      "change_percent": null
    },
    "subscription_type": "reminder",
    "title": "Weekly 2330 Reminder",
    "message": "Check weekly performance",
    "frequency_type": "weekly",
    "reminder_time": "17:00",
    "day_of_week": 2,
    "day_of_month": 0,
    "next_trigger_at": "2026-05-14T17:00:00Z",
    "is_active": true,
    "created_at": "2026-05-10T10:00:00Z",
    "updated_at": "2026-05-10T10:00:00Z"
  }
}
```

**Error Responses**:

| Status | Message                               |
| ------ | ------------------------------------- |
| 400    | Stock not found or inactive: {id}     |
| 400    | Duplicate reminder already exists     |
| 403    | Subscription quota exceeded: used X/Y |
| 409    | Reminder already exists               |

---

### Get Scheduled Reminder

Get a single scheduled reminder by ID.

**Endpoint**: `GET /subscriptions/reminders/{reminder_id}`

**Authentication**: Required (JWT Bearer token)

**Path Parameters**:

| Parameter    | Type    | Required | Description  |
| ------------ | ------- | -------- | ------------ |
| reminder_id  | integer | Yes      | Reminder ID  |

**Response** (200 OK):

Same as Create response.

**Error Responses**:

| Status | Message                   |
| ------ | ------------------------- |
| 404    | Reminder not found: {id}  |

---

### Update Scheduled Reminder

Update reminder title, message, frequency settings, or active status.

**Endpoint**: `PATCH /subscriptions/reminders/{reminder_id}`

**Authentication**: Required (JWT Bearer token)

**Request Body**:

```json
{
  "title": "Updated Reminder",
  "frequency_type": "monthly",
  "reminder_time": "18:00",
  "day_of_month": 15
}
```

**Request Schema**:

| Field          | Type            | Required | Constraints                     | Description                   |
| -------------- | --------------- | -------- | ------------------------------- | ----------------------------- |
| title          | string \| null  | No       | max_length: 50                  | Reminder title                |
| message        | string \| null  | No       | max_length: 200                 | Reminder message              |
| frequency_type | string \| null  | No       | Enum: daily, weekly, monthly    | Frequency type                |
| reminder_time  | string \| null  | No       | Format: HH:MM                   | Time of day                   |
| day_of_week    | integer \| null | No       | 0-6 (Mon-Sun)                   | Day of week for weekly        |
| day_of_month   | integer \| null | No       | 1-28                            | Day of month for monthly      |
| is_active      | boolean \| null | No       | -                               | Active status                 |

**Note**: If frequency settings are updated, `next_trigger_at` is automatically recalculated.

**Response** (200 OK):

Same as Create response.

---

### Delete Scheduled Reminder

Soft delete a scheduled reminder.

**Endpoint**: `DELETE /subscriptions/reminders/{reminder_id}`

**Authentication**: Required (JWT Bearer token)

**Response** (200 OK):

Same as Create response.

**Error Responses**:

| Status | Message                   |
| ------ | ------------------------- |
| 404    | Reminder not found: {id}  |

---