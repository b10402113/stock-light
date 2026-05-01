# StockLight API Documentation

Version: 1.0.0
Base URL: `http://localhost:8000`

## Overview

StockLight is a stock price alert notification service. Users can subscribe to stock price or technical indicator trigger conditions via LINE, and the system automatically monitors and pushes notifications.

## Interactive Documentation

- **Swagger UI**: `/docs`
- **ReDoc**: `/redoc`
- **OpenAPI Schema**: `/openapi.json`

---

## Response Format

All API responses follow a unified format:

### Success Response

```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

### Error Response

```json
{
  "code": 1001,
  "message": "Error description",
  "data": null
}
```

---

## Users API

### Register User

Create a new user account.

**Endpoint**: `POST /users/register`

**Request Body**:

```json
{
  "email": "user@example.com",
  "password": "yourpassword"
}
```

**Request Schema**:

| Field    | Type   | Required | Constraints              | Description    |
| -------- | ------ | -------- | ------------------------ | -------------- |
| email    | string | Yes      | Valid email format       | User email     |
| password | string | Yes      | 8-128 characters         | User password  |

**Response** (201 Created):

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "email": "user@example.com",
    "is_active": true
  }
}
```

**Error Responses**:

| Status | Code | Message               |
| ------ | ---- | --------------------- |
| 400    | 1001 | User already exists   |

---

### Login

Authenticate user and get JWT access token.

**Endpoint**: `POST /users/login`

**Request Body**:

```json
{
  "email": "user@example.com",
  "password": "yourpassword"
}
```

**Request Schema**:

| Field    | Type   | Required | Constraints              | Description    |
| -------- | ------ | -------- | ------------------------ | -------------- |
| email    | string | Yes      | Valid email format       | User email     |
| password | string | Yes      | 8-128 characters         | User password  |

**Response** (200 OK):

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  }
}
```

**Error Responses**:

| Status | Code | Message               |
| ------ | ---- | --------------------- |
| 400    | 1002 | User not found        |
| 400    | 1003 | Invalid credentials   |

---

## OAuth Authentication API

### Get OAuth Authorization URL

Generate OAuth authorization URL for third-party login (Google/LINE).

**Endpoint**: `GET /auth/{provider}`

**Path Parameters**:

| Parameter | Type   | Required | Description                       |
| --------- | ------ | -------- | --------------------------------- |
| provider  | string | Yes      | OAuth provider: "google" or "line" |

**Response** (200 OK):

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
    "state": "google:abc123..."
  }
}
```

**Response Schema**:

| Field              | Type   | Description                          |
| ------------------ | ------ | ------------------------------------ |
| authorization_url  | string | URL to redirect user for authorization |
| state              | string | CSRF protection token                |

**Error Responses**:

| Status | Code | Message                    |
| ------ | ---- | -------------------------- |
| 400    | 2    | Unsupported login provider |

---

### OAuth Callback

Handle OAuth provider callback and return JWT token.

**Endpoint**: `GET /auth/{provider}/callback`

**Path Parameters**:

| Parameter | Type   | Required | Description                       |
| --------- | ------ | -------- | --------------------------------- |
| provider  | string | Yes      | OAuth provider: "google" or "line" |

**Query Parameters**:

| Parameter | Type   | Required | Description              |
| --------- | ------ | -------- | ------------------------ |
| code      | string | Yes      | Authorization code       |
| state     | string | Yes      | State token from request |

**Response** (200 OK):

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  }
}
```

**Error Responses**:

| Status | Code | Message                    |
| ------ | ---- | -------------------------- |
| 400    | 100  | Invalid state token        |
| 400    | 100  | OAuth authentication failed |
| 400    | 100  | Failed to get user info    |
| 400    | 202  | User is disabled           |

---

### OAuth Flow Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  1. Frontend calls GET /auth/{provider}                         │
│     → Returns authorization_url + state                         │
│                                                                  │
│  2. Frontend redirects user to authorization_url                │
│     → User authenticates with Google/LINE                       │
│                                                                  │
│  3. Provider redirects to GET /auth/{provider}/callback         │
│     → Backend exchanges code, creates/links user, returns JWT   │
│                                                                  │
│  4. Frontend stores JWT and uses for authenticated requests     │
└─────────────────────────────────────────────────────────────────┘
```

### Account Binding Logic

| Scenario                           | Behavior                               |
| ---------------------------------- | -------------------------------------- |
| OAuth account exists               | Return existing user's JWT             |
| Email matches existing user        | Auto-bind OAuth to existing account    |
| No matching email                  | Create new user without password       |

---

## Stocks API

### List Stocks

Get a list of all stocks with optional filtering.

**Endpoint**: `GET /stocks`

**Query Parameters**:

| Parameter | Type    | Required | Default | Description                    |
| --------- | ------- | -------- | ------- | ------------------------------ |
| is_active | boolean | No       | -       | Filter by active status        |
| limit     | integer | No       | 100     | Maximum number of results      |
| offset    | integer | No       | 0       | Offset for pagination          |

**Response** (200 OK):

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": 1,
      "symbol": "2330.TW",
      "name": "台積電",
      "current_price": "650.00",
      "calculated_indicators": {
        "rsi_14": 65.5,
        "kd": { "k": 72.3, "d": 68.1 },
        "macd": { "macd": 12.5, "signal": 10.2, "histogram": 2.3 }
      },
      "is_active": true
    }
  ]
}
```

**Response Schema**:

| Field                 | Type             | Description                        |
| --------------------- | ---------------- | ---------------------------------- |
| id                    | integer          | Stock ID                           |
| symbol                | string           | Stock symbol (e.g., 2330.TW)       |
| name                  | string           | Stock name                         |
| current_price         | decimal \| null  | Current stock price                |
| calculated_indicators | object \| null   | Technical indicators (RSI, KD, MACD) |
| is_active             | boolean          | Whether stock is active            |

---

### Search Stocks

Search stocks by symbol or name with keyset pagination.

**Endpoint**: `GET /stocks/search`

**Query Parameters**:

| Parameter | Type    | Required | Default | Description                              |
| --------- | ------- | -------- | ------- | ---------------------------------------- |
| q         | string  | Yes      | -       | Search query (matches symbol or name)    |
| cursor    | integer | No       | -       | Pagination cursor (last ID from previous page) |
| limit     | integer | No       | 100     | Maximum number of results (1-100)        |

**Response** (200 OK):

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "data": [
      {
        "id": 1,
        "symbol": "2330.TW",
        "name": "台積電",
        "current_price": "650.00",
        "calculated_indicators": null,
        "is_active": true
      }
    ],
    "next_cursor": null,
    "has_more": false
  }
}
```

**Response Schema**:

| Field       | Type             | Description                              |
| ----------- | ---------------- | ---------------------------------------- |
| data        | array            | List of matching stocks                  |
| next_cursor | integer \| null  | Cursor for next page (null if no more)   |
| has_more    | boolean          | Whether more results exist               |

**Features**:

- Case-insensitive partial matching
- Searches both `symbol` and `name` fields (OR logic)
- Keyset pagination for efficient large result sets

**Example Searches**:

| Query   | Matches                              |
| ------- | ------------------------------------ |
| `2330`  | Stocks with "2330" in symbol or name |
| `台積`  | Stocks with "台積" in symbol or name |
| `tw`    | All stocks with ".TW" suffix         |

---

### Get Stock

Get a single stock by symbol.

**Endpoint**: `GET /stocks/{symbol}`

**Path Parameters**:

| Parameter | Type   | Required | Description               |
| --------- | ------ | -------- | ------------------------- |
| symbol    | string | Yes      | Stock symbol (e.g., 2330.TW) |

**Response** (200 OK):

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "symbol": "2330.TW",
    "name": "台積電",
    "current_price": "650.00",
    "calculated_indicators": null,
    "is_active": true
  }
}
```

**Error Responses**:

| Status | Message                  |
| ------ | ------------------------ |
| 404    | Stock not found: {symbol} |

---

### Create Stock

Create a new stock entry.

**Endpoint**: `POST /stocks`

**Request Body**:

```json
{
  "symbol": "2330.TW",
  "name": "台積電",
  "current_price": "650.00",
  "calculated_indicators": null,
  "is_active": true
}
```

**Request Schema**:

| Field                 | Type             | Required | Constraints                     | Description               |
| --------------------- | ---------------- | -------- | ------------------------------- | ------------------------- |
| symbol                | string           | Yes      | Pattern: `^[A-Za-z0-9]+\.TW$`   | Stock symbol              |
| name                  | string           | Yes      | 1-255 characters                | Stock name                |
| current_price         | decimal \| null  | No       | 0 - 100000                      | Current price             |
| calculated_indicators | object \| null   | No       | -                               | Technical indicators      |
| is_active             | boolean          | No       | Default: true                   | Active status             |

**Response** (201 Created):

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "symbol": "2330.TW",
    "name": "台積電",
    "current_price": "650.00",
    "calculated_indicators": null,
    "is_active": true
  }
}
```

**Error Responses**:

| Status | Message                          |
| ------ | -------------------------------- |
| 409    | Stock already exists: {symbol}   |
| 422    | Validation error (invalid format) |

---

### Update Stock

Update an existing stock's information.

**Endpoint**: `PATCH /stocks/{symbol}`

**Path Parameters**:

| Parameter | Type   | Required | Description               |
| --------- | ------ | -------- | ------------------------- |
| symbol    | string | Yes      | Stock symbol              |

**Request Body**:

```json
{
  "name": "台灣積體電路製造",
  "current_price": "700.00",
  "is_active": false
}
```

**Request Schema**:

| Field                 | Type             | Required | Constraints        | Description          |
| --------------------- | ---------------- | -------- | ------------------ | -------------------- |
| name                  | string \| null   | No       | 1-255 characters   | Stock name           |
| current_price         | decimal \| null  | No       | 0 - 100000         | Current price        |
| calculated_indicators | object \| null   | No       | -                  | Technical indicators |
| is_active             | boolean \| null  | No       | -                  | Active status        |

**Response** (200 OK):

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "symbol": "2330.TW",
    "name": "台灣積體電路製造",
    "current_price": "700.00",
    "calculated_indicators": null,
    "is_active": false
  }
}
```

**Error Responses**:

| Status | Message                  |
| ------ | ------------------------ |
| 404    | Stock not found: {symbol} |

---

### Delete Stock

Soft delete a stock (marks as deleted, does not remove from database).

**Endpoint**: `DELETE /stocks/{symbol}`

**Path Parameters**:

| Parameter | Type   | Required | Description |
| --------- | ------ | -------- | ----------- |
| symbol    | string | Yes      | Stock symbol |

**Response** (200 OK):

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "symbol": "2330.TW",
    "name": "台積電",
    "current_price": "650.00",
    "calculated_indicators": null,
    "is_active": false
  }
}
```

**Error Responses**:

| Status | Message                  |
| ------ | ------------------------ |
| 404    | Stock not found: {symbol} |

**Note**: After deletion, the stock will no longer appear in list results or be accessible by symbol.

---

## Watchlists API

### List Watchlists

Get all watchlists for the authenticated user.

**Endpoint**: `GET /watchlists`

**Authentication**: Required (JWT Bearer token)

**Headers**:

| Header          | Value              | Required |
| --------------- | ------------------ | -------- |
| Authorization   | Bearer {token}     | Yes      |

**Response** (200 OK):

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": 1,
      "name": "My Watchlist",
      "description": "Tech stocks",
      "is_default": true,
      "stock_count": 5,
      "created_at": "2026-05-01T10:00:00Z"
    }
  ]
}
```

**Response Schema**:

| Field        | Type             | Description                    |
| ------------ | ---------------- | ------------------------------ |
| id           | integer          | Watchlist ID                   |
| name         | string           | Watchlist name                 |
| description  | string \| null   | Watchlist description          |
| is_default   | boolean          | Whether this is the default list |
| stock_count  | integer          | Number of stocks in list       |
| created_at   | datetime         | Creation timestamp             |

---

### Create Watchlist

Create a new watchlist for the authenticated user.

**Endpoint**: `POST /watchlists`

**Authentication**: Required (JWT Bearer token)

**Request Body**:

```json
{
  "name": "Tech Stocks",
  "description": "My favorite tech companies"
}
```

**Request Schema**:

| Field        | Type             | Required | Constraints       | Description          |
| ------------ | ---------------- | -------- | ----------------- | -------------------- |
| name         | string           | Yes      | 1-100 characters  | Watchlist name       |
| description  | string \| null   | No       | Max 500 characters| Watchlist description|

**Response** (201 Created):

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "name": "Tech Stocks",
    "description": "My favorite tech companies",
    "is_default": true,
    "stock_count": 0,
    "created_at": "2026-05-01T10:00:00Z"
  }
}
```

**Note**: The first watchlist created is automatically set as default.

---

### Get Watchlist Detail

Get a single watchlist with its stocks.

**Endpoint**: `GET /watchlists/{watchlist_id}`

**Authentication**: Required (JWT Bearer token)

**Path Parameters**:

| Parameter     | Type    | Required | Description       |
| ------------ | ------- | -------- | ----------------- |
| watchlist_id | integer | Yes      | Watchlist ID      |

**Response** (200 OK):

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "name": "Tech Stocks",
    "description": "My favorite tech companies",
    "is_default": true,
    "stocks": [
      {
        "stock_id": 1,
        "symbol": "2330.TW",
        "name": "台積電",
        "current_price": "650.00",
        "notes": "Core holding",
        "sort_order": 0,
        "created_at": "2026-05-01T10:30:00Z"
      }
    ]
  }
}
```

**Response Schema**:

| Field           | Type             | Description                    |
| -------------- | ---------------- | ------------------------------ |
| id             | integer          | Watchlist ID                   |
| name           | string           | Watchlist name                 |
| description    | string \| null   | Watchlist description          |
| is_default     | boolean          | Whether this is the default list|
| stocks         | array            | List of stocks in watchlist    |

**Stock Item Schema**:

| Field          | Type             | Description                    |
| -------------  | ---------------- | ------------------------------ |
| stock_id       | integer          | Stock ID                       |
| symbol         | string           | Stock symbol                   |
| name           | string           | Stock name                     |
| current_price  | decimal \| null  | Current stock price            |
| notes          | string \| null   | User notes                     |
| sort_order     | integer          | Display order                  |
| created_at     | datetime         | Added timestamp                |

**Error Responses**:

| Status | Message                         |
| ------ | ------------------------------- |
| 404    | Watchlist not found: {id}       |

---

### Update Watchlist

Update watchlist name or description.

**Endpoint**: `PATCH /watchlists/{watchlist_id}`

**Authentication**: Required (JWT Bearer token)

**Path Parameters**:

| Parameter     | Type    | Required | Description       |
| ------------ | ------- | -------- | ----------------- |
| watchlist_id | integer | Yes      | Watchlist ID      |

**Request Body**:

```json
{
  "name": "Updated Name",
  "description": "New description"
}
```

**Request Schema**:

| Field        | Type             | Required | Constraints       | Description          |
| ------------ | ---------------- | -------- | ----------------- | -------------------- |
| name         | string \| null   | No       | 1-100 characters  | Watchlist name       |
| description  | string \| null   | No       | Max 500 characters| Watchlist description|

**Response** (200 OK):

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "name": "Updated Name",
    "description": "New description",
    "is_default": true,
    "stock_count": 5,
    "created_at": "2026-05-01T10:00:00Z"
  }
}
```

**Error Responses**:

| Status | Message                         |
| ------ | ------------------------------- |
| 404    | Watchlist not found: {id}       |

---

### Delete Watchlist

Soft delete a watchlist.

**Endpoint**: `DELETE /watchlists/{watchlist_id}`

**Authentication**: Required (JWT Bearer token)

**Path Parameters**:

| Parameter     | Type    | Required | Description       |
| ------------ | ------- | -------- | ----------------- |
| watchlist_id | integer | Yes      | Watchlist ID      |

**Response** (200 OK):

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "name": "Deleted Watchlist",
    "description": null,
    "is_default": false,
    "stock_count": 0,
    "created_at": "2026-05-01T10:00:00Z"
  }
}
```

**Error Responses**:

| Status | Message                         |
| ------ | ------------------------------- |
| 404    | Watchlist not found: {id}       |

---

### Add Stock to Watchlist

Add a stock to a watchlist.

**Endpoint**: `POST /watchlists/{watchlist_id}/stocks`

**Authentication**: Required (JWT Bearer token)

**Path Parameters**:

| Parameter     | Type    | Required | Description       |
| ------------ | ------- | -------- | ----------------- |
| watchlist_id | integer | Yes      | Watchlist ID      |

**Request Body**:

```json
{
  "stock_id": 1,
  "notes": "Buying opportunity at 600"
}
```

**Request Schema**:

| Field     | Type             | Required | Constraints          | Description    |
| --------- | ---------------- | -------- | -------------------- | -------------- |
| stock_id  | integer          | Yes      | Must be > 0          | Stock ID       |
| notes     | string \| null   | No       | Max 500 characters   | User notes     |

**Response** (201 Created):

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "watchlist_id": 1,
    "stock_id": 1,
    "symbol": "2330.TW",
    "name": "台積電",
    "current_price": "650.00",
    "notes": "Buying opportunity at 600",
    "sort_order": 0,
    "created_at": "2026-05-01T10:30:00Z"
  }
}
```

**Error Responses**:

| Status | Message                              |
| ------ | ------------------------------------ |
| 400    | Stock not found or inactive: {id}    |
| 404    | Watchlist not found: {id}            |
| 409    | Stock already in watchlist: {id}     |

---

### Remove Stock from Watchlist

Remove a stock from a watchlist.

**Endpoint**: `DELETE /watchlists/{watchlist_id}/stocks/{stock_id}`

**Authentication**: Required (JWT Bearer token)

**Path Parameters**:

| Parameter     | Type    | Required | Description       |
| ------------ | ------- | -------- | ----------------- |
| watchlist_id | integer | Yes      | Watchlist ID      |
| stock_id     | integer | Yes      | Stock ID          |

**Response** (200 OK):

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "watchlist_id": 1,
    "stock_id": 1,
    "symbol": "2330.TW",
    "name": "台積電",
    "current_price": "650.00",
    "notes": null,
    "sort_order": 0,
    "created_at": "2026-05-01T10:30:00Z"
  }
}
```

**Error Responses**:

| Status | Message                              |
| ------ | ------------------------------------ |
| 404    | Watchlist not found: {id}            |
| 404    | Stock not found in watchlist: {id}   |

---

### Update Stock in Watchlist

Update notes or sort order for a stock in watchlist.

**Endpoint**: `PATCH /watchlists/{watchlist_id}/stocks/{stock_id}`

**Authentication**: Required (JWT Bearer token)

**Path Parameters**:

| Parameter     | Type    | Required | Description       |
| ------------ | ------- | -------- | ----------------- |
| watchlist_id | integer | Yes      | Watchlist ID      |
| stock_id     | integer | Yes      | Stock ID          |

**Request Body**:

```json
{
  "notes": "Updated notes",
  "sort_order": 5
}
```

**Request Schema**:

| Field       | Type             | Required | Constraints     | Description    |
| ----------- | ---------------- | -------- | -------------- | -------------- |
| notes       | string \| null   | No       | Max 500 chars   | User notes     |
| sort_order  | integer \| null  | No       | Must be >= 0    | Display order  |

**Response** (200 OK):

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "watchlist_id": 1,
    "stock_id": 1,
    "symbol": "2330.TW",
    "name": "台積電",
    "current_price": "650.00",
    "notes": "Updated notes",
    "sort_order": 5,
    "created_at": "2026-05-01T10:30:00Z"
  }
}
```

**Error Responses**:

| Status | Message                              |
| ------ | ------------------------------------ |
| 404    | Watchlist not found: {id}            |
| 404    | Stock not found in watchlist: {id}   |

---

## Subscriptions API

### List Subscriptions

Get all indicator subscriptions for the authenticated user with keyset pagination.

**Endpoint**: `GET /subscriptions`

**Authentication**: Required (JWT Bearer token)

**Headers**:

| Header          | Value              | Required |
| --------------- | ------------------ | -------- |
| Authorization   | Bearer {token}     | Yes      |

**Query Parameters**:

| Parameter | Type    | Required | Default | Description                              |
| --------- | ------- | -------- | ------- | ---------------------------------------- |
| cursor    | integer | No       | -       | Pagination cursor (last ID from previous page) |
| limit     | integer | No       | 20      | Items per page (1-100)                   |

**Response** (200 OK):

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "data": [
      {
        "id": 1,
        "user_id": 1,
        "stock_id": 1,
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

| Field               | Type             | Description                              |
| ------------------- | ---------------- | ---------------------------------------- |
| data                | array            | List of subscriptions                    |
| next_cursor         | integer \| null  | Cursor for next page (null if no more)   |
| has_more            | boolean          | Whether more results exist               |

**Subscription Schema**:

| Field               | Type             | Description                              |
| ------------------- | ---------------- | ---------------------------------------- |
| id                  | integer          | Subscription ID                          |
| user_id             | integer          | Owner user ID                            |
| stock_id            | integer          | Target stock ID                          |
| indicator_type      | string           | Indicator type: rsi, macd, kd, price     |
| operator            | string           | Comparison: >, <, >=, <=, ==, !=         |
| target_value        | decimal          | Target threshold value                   |
| compound_condition  | object \| null   | Complex AND/OR conditions                |
| is_triggered        | boolean          | Whether condition was triggered          |
| cooldown_end_at     | datetime \| null | Cooldown period end time                 |
| is_active           | boolean          | Subscription active status               |
| created_at          | datetime         | Creation timestamp                       |
| updated_at          | datetime         | Last update timestamp                    |

---

### Create Subscription

Create a new indicator subscription.

**Endpoint**: `POST /subscriptions`

**Authentication**: Required (JWT Bearer token)

**Request Body**:

```json
{
  "stock_id": 1,
  "indicator_type": "rsi",
  "operator": "<",
  "target_value": "30.0",
  "compound_condition": null
}
```

**Request Schema**:

| Field               | Type             | Required | Constraints                    | Description                    |
| ------------------- | ---------------- | -------- | ------------------------------ | ------------------------------ |
| stock_id            | integer          | Yes      | Must reference active stock    | Target stock ID                |
| indicator_type      | string           | Yes      | Enum: rsi, macd, kd, price     | Type of indicator              |
| operator            | string           | Yes      | Enum: >, <, >=, <=, ==, !=     | Comparison operator            |
| target_value        | decimal          | Yes      | >= 0                           | Target threshold value         |
| compound_condition  | object \| null   | No       | -                              | Complex conditions (AND/OR)    |

**Indicator Types**:

| Value  | Description                |
| ------ | -------------------------- |
| rsi    | Relative Strength Index    |
| macd   | Moving Average Convergence Divergence |
| kd     | Stochastic Oscillator      |
| price  | Stock price                |

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
    "user_id": 1,
    "stock_id": 1,
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

| Status | Message                                        |
| ------ | ---------------------------------------------- |
| 400    | Stock not found or inactive: {id}              |
| 400    | Duplicate subscription already exists          |
| 403    | Subscription quota exceeded: used X/Y          |

---

### Get Subscription

Get a single subscription by ID.

**Endpoint**: `GET /subscriptions/{subscription_id}`

**Authentication**: Required (JWT Bearer token)

**Path Parameters**:

| Parameter        | Type    | Required | Description       |
| --------------- | ------- | -------- | ----------------- |
| subscription_id | integer | Yes      | Subscription ID   |

**Response** (200 OK):

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "user_id": 1,
    "stock_id": 1,
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

| Status | Message                            |
| ------ | ---------------------------------- |
| 404    | Subscription not found: {id}       |

---

### Update Subscription

Update subscription indicator type, operator, target value, or active status.

**Endpoint**: `PATCH /subscriptions/{subscription_id}`

**Authentication**: Required (JWT Bearer token)

**Path Parameters**:

| Parameter        | Type    | Required | Description       |
| --------------- | ------- | -------- | ----------------- |
| subscription_id | integer | Yes      | Subscription ID   |

**Request Body**:

```json
{
  "indicator_type": "price",
  "operator": ">",
  "target_value": "700.0",
  "is_active": false
}
```

**Request Schema**:

| Field               | Type             | Required | Constraints                    | Description          |
| ------------------- | ---------------- | -------- | ------------------------------ | -------------------- |
| indicator_type      | string \| null   | No       | Enum: rsi, macd, kd, price     | Type of indicator    |
| operator            | string \| null   | No       | Enum: >, <, >=, <=, ==, !=     | Comparison operator  |
| target_value        | decimal \| null  | No       | >= 0                           | Target value         |
| compound_condition  | object \| null   | No       | -                              | Complex conditions   |
| is_active           | boolean \| null  | No       | -                              | Active status        |

**Response** (200 OK):

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "user_id": 1,
    "stock_id": 1,
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

| Status | Message                            |
| ------ | ---------------------------------- |
| 404    | Subscription not found: {id}       |

---

### Delete Subscription

Soft delete a subscription.

**Endpoint**: `DELETE /subscriptions/{subscription_id}`

**Authentication**: Required (JWT Bearer token)

**Path Parameters**:

| Parameter        | Type    | Required | Description       |
| --------------- | ------- | -------- | ----------------- |
| subscription_id | integer | Yes      | Subscription ID   |

**Response** (200 OK):

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "user_id": 1,
    "stock_id": 1,
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

| Status | Message                            |
| ------ | ---------------------------------- |
| 404    | Subscription not found: {id}       |

**Note**: After deletion, the subscription will no longer appear in list results or be accessible by ID.

---

## Changelog

### v1.4.0 (2026-05-02)

- Added Stock Search API
- Search stocks by symbol or name
- Case-insensitive partial matching
- Keyset pagination support
- GET /stocks/search endpoint

### v1.3.0 (2026-05-01)

- Added Subscriptions API
- Create, list, get, update, delete indicator subscriptions
- Support for RSI, MACD, KD, and Price indicators
- Comparison operators: >, <, >=, <=, ==, !=
- Keyset pagination for subscription list
- Quota validation per user
- Duplicate prevention
- Compound condition support for complex alerts

### v1.2.0 (2026-05-01)

- Added Watchlists API
- Create, list, get, update, delete watchlists
- Add, remove, update stocks in watchlists
- First watchlist auto-set as default
- Authorization: users can only access their own watchlists

### v1.1.0 (2026-05-01)

- Added Stocks API
- List stocks with filtering
- Get single stock by symbol
- Create new stock entries
- Update stock information
- Soft delete stocks

### v1.0.0 (2026-04-30)

- Initial API release
- User registration endpoint
- User login endpoint with JWT authentication
- Google OAuth 2.0 login
- LINE Login integration
- Auto account binding for OAuth users
