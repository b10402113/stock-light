## Watchlists API

### List Watchlists

Get all watchlists for the authenticated user.

**Endpoint**: `GET /watchlists`

**Authentication**: Required (JWT Bearer token)

**Headers**:

| Header        | Value          | Required |
| ------------- | -------------- | -------- |
| Authorization | Bearer {token} | Yes      |

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

| Field       | Type           | Description                      |
| ----------- | -------------- | -------------------------------- |
| id          | integer        | Watchlist ID                     |
| name        | string         | Watchlist name                   |
| description | string \| null | Watchlist description            |
| is_default  | boolean        | Whether this is the default list |
| stock_count | integer        | Number of stocks in list         |
| created_at  | datetime       | Creation timestamp               |

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

| Field       | Type           | Required | Constraints        | Description           |
| ----------- | -------------- | -------- | ------------------ | --------------------- |
| name        | string         | Yes      | 1-100 characters   | Watchlist name        |
| description | string \| null | No       | Max 500 characters | Watchlist description |

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

| Parameter    | Type    | Required | Description  |
| ------------ | ------- | -------- | ------------ |
| watchlist_id | integer | Yes      | Watchlist ID |

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

| Field       | Type           | Description                      |
| ----------- | -------------- | -------------------------------- |
| id          | integer        | Watchlist ID                     |
| name        | string         | Watchlist name                   |
| description | string \| null | Watchlist description            |
| is_default  | boolean        | Whether this is the default list |
| stocks      | array          | List of stocks in watchlist      |

**Stock Item Schema**:

| Field         | Type            | Description         |
| ------------- | --------------- | ------------------- |
| stock_id      | integer         | Stock ID            |
| symbol        | string          | Stock symbol        |
| name          | string          | Stock name          |
| current_price | decimal \| null | Current stock price |
| notes         | string \| null  | User notes          |
| sort_order    | integer         | Display order       |
| created_at    | datetime        | Added timestamp     |

**Error Responses**:

| Status | Message                   |
| ------ | ------------------------- |
| 404    | Watchlist not found: {id} |

---

### Update Watchlist

Update watchlist name or description.

**Endpoint**: `PATCH /watchlists/{watchlist_id}`

**Authentication**: Required (JWT Bearer token)

**Path Parameters**:

| Parameter    | Type    | Required | Description  |
| ------------ | ------- | -------- | ------------ |
| watchlist_id | integer | Yes      | Watchlist ID |

**Request Body**:

```json
{
  "name": "Updated Name",
  "description": "New description"
}
```

**Request Schema**:

| Field       | Type           | Required | Constraints        | Description           |
| ----------- | -------------- | -------- | ------------------ | --------------------- |
| name        | string \| null | No       | 1-100 characters   | Watchlist name        |
| description | string \| null | No       | Max 500 characters | Watchlist description |

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

| Status | Message                   |
| ------ | ------------------------- |
| 404    | Watchlist not found: {id} |

---

### Delete Watchlist

Soft delete a watchlist.

**Endpoint**: `DELETE /watchlists/{watchlist_id}`

**Authentication**: Required (JWT Bearer token)

**Path Parameters**:

| Parameter    | Type    | Required | Description  |
| ------------ | ------- | -------- | ------------ |
| watchlist_id | integer | Yes      | Watchlist ID |

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

| Status | Message                   |
| ------ | ------------------------- |
| 404    | Watchlist not found: {id} |

---

### Add Stock to Watchlist

Add a stock to a watchlist.

**Endpoint**: `POST /watchlists/{watchlist_id}/stocks`

**Authentication**: Required (JWT Bearer token)

**Path Parameters**:

| Parameter    | Type    | Required | Description  |
| ------------ | ------- | -------- | ------------ |
| watchlist_id | integer | Yes      | Watchlist ID |

**Request Body**:

```json
{
  "stock_id": 1,
  "notes": "Buying opportunity at 600"
}
```

**Request Schema**:

| Field    | Type           | Required | Constraints        | Description |
| -------- | -------------- | -------- | ------------------ | ----------- |
| stock_id | integer        | Yes      | Must be > 0        | Stock ID    |
| notes    | string \| null | No       | Max 500 characters | User notes  |

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

| Status | Message                           |
| ------ | --------------------------------- |
| 400    | Stock not found or inactive: {id} |
| 404    | Watchlist not found: {id}         |
| 409    | Stock already in watchlist: {id}  |

---

### Remove Stock from Watchlist

Remove a stock from a watchlist.

**Endpoint**: `DELETE /watchlists/{watchlist_id}/stocks/{stock_id}`

**Authentication**: Required (JWT Bearer token)

**Path Parameters**:

| Parameter    | Type    | Required | Description  |
| ------------ | ------- | -------- | ------------ |
| watchlist_id | integer | Yes      | Watchlist ID |
| stock_id     | integer | Yes      | Stock ID     |

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

| Status | Message                            |
| ------ | ---------------------------------- |
| 404    | Watchlist not found: {id}          |
| 404    | Stock not found in watchlist: {id} |

---

### Update Stock in Watchlist

Update notes or sort order for a stock in watchlist.

**Endpoint**: `PATCH /watchlists/{watchlist_id}/stocks/{stock_id}`

**Authentication**: Required (JWT Bearer token)

**Path Parameters**:

| Parameter    | Type    | Required | Description  |
| ------------ | ------- | -------- | ------------ |
| watchlist_id | integer | Yes      | Watchlist ID |
| stock_id     | integer | Yes      | Stock ID     |

**Request Body**:

```json
{
  "notes": "Updated notes",
  "sort_order": 5
}
```

**Request Schema**:

| Field      | Type            | Required | Constraints   | Description   |
| ---------- | --------------- | -------- | ------------- | ------------- |
| notes      | string \| null  | No       | Max 500 chars | User notes    |
| sort_order | integer \| null | No       | Must be >= 0  | Display order |

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

| Status | Message                            |
| ------ | ---------------------------------- |
| 404    | Watchlist not found: {id}          |
| 404    | Stock not found in watchlist: {id} |

---
