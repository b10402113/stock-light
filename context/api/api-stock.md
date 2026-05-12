## Stocks API

### List Stocks

Get a list of all stocks with optional filtering.

**Endpoint**: `GET /stocks`

**Query Parameters**:

| Parameter | Type    | Required | Default | Description               |
| --------- | ------- | -------- | ------- | ------------------------- |
| is_active | boolean | No       | -       | Filter by active status   |
| limit     | integer | No       | 100     | Maximum number of results |
| offset    | integer | No       | 0       | Offset for pagination     |

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

| Field                 | Type            | Description                          |
| --------------------- | --------------- | ------------------------------------ |
| id                    | integer         | Stock ID                             |
| symbol                | string          | Stock symbol (e.g., 2330.TW)         |
| name                  | string          | Stock name                           |
| current_price         | decimal \| null | Current stock price                  |
| calculated_indicators | object \| null  | Technical indicators (RSI, KD, MACD) |
| is_active             | boolean         | Whether stock is active              |

---

### Search Stocks

Search stocks by symbol or name with keyset pagination. Implements a database-first fallback strategy: searches the local database first, and if no results are found, queries the Fugle API for a single ticker by symbol lookup.

**Endpoint**: `GET /stocks/search`

**Query Parameters**:

| Parameter | Type    | Required | Default | Description                                    |
| --------- | ------- | -------- | ------- | ---------------------------------------------- |
| q         | string  | Yes      | -       | Search query (matches symbol or name)          |
| cursor    | integer | No       | -       | Pagination cursor (last ID from previous page) |
| limit     | integer | No       | 100     | Maximum number of results (1-100)              |

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

| Field       | Type            | Description                            |
| ----------- | --------------- | -------------------------------------- |
| data        | array           | List of matching stocks                |
| next_cursor | integer \| null | Cursor for next page (null if no more) |
| has_more    | boolean         | Whether more results exist             |

**Features**:

- Case-insensitive partial matching
- Searches both `symbol` and `name` fields in database (OR logic)
- Keyset pagination for efficient large result sets
- **Fallback Strategy**: Database-first with single ticker lookup
  - First searches local database
  - If no results found, queries Fugle API for single ticker by symbol
  - Automatically persists new stock data to database
  - More efficient than fetching all market tickers
  - Gracefully handles API failures (returns empty results on error)

**Example Searches**:

| Query  | Matches                              |
| ------ | ------------------------------------ |
| `2330` | Stocks with "2330" in symbol or name |
| `台積` | Stocks with "台積" in symbol or name |
| `tw`   | All stocks with ".TW" suffix         |

**Fallback Behavior Examples**:

- **Database has results**: Returns immediately, no Fugle API call
- **Database empty, Fugle has ticker**: Fetches single ticker by symbol, saves to database, returns results
- **Ticker not found or API failure**: Returns empty result set

---

### Get Stock

Get a single stock by symbol.

**Endpoint**: `GET /stocks/{symbol}`

**Path Parameters**:

| Parameter | Type   | Required | Description                  |
| --------- | ------ | -------- | ---------------------------- |
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

| Status | Message                   |
| ------ | ------------------------- |
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

| Field                 | Type            | Required | Constraints                   | Description          |
| --------------------- | --------------- | -------- | ----------------------------- | -------------------- |
| symbol                | string          | Yes      | Pattern: `^[A-Za-z0-9]+\.TW$` | Stock symbol         |
| name                  | string          | Yes      | 1-255 characters              | Stock name           |
| current_price         | decimal \| null | No       | 0 - 100000                    | Current price        |
| calculated_indicators | object \| null  | No       | -                             | Technical indicators |
| is_active             | boolean         | No       | Default: true                 | Active status        |

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

| Status | Message                           |
| ------ | --------------------------------- |
| 409    | Stock already exists: {symbol}    |
| 422    | Validation error (invalid format) |

---

### Update Stock

Update an existing stock's information.

**Endpoint**: `PATCH /stocks/{symbol}`

**Path Parameters**:

| Parameter | Type   | Required | Description  |
| --------- | ------ | -------- | ------------ |
| symbol    | string | Yes      | Stock symbol |

**Request Body**:

```json
{
  "name": "台灣積體電路製造",
  "current_price": "700.00",
  "is_active": false
}
```

**Request Schema**:

| Field                 | Type            | Required | Constraints      | Description          |
| --------------------- | --------------- | -------- | ---------------- | -------------------- |
| name                  | string \| null  | No       | 1-255 characters | Stock name           |
| current_price         | decimal \| null | No       | 0 - 100000       | Current price        |
| calculated_indicators | object \| null  | No       | -                | Technical indicators |
| is_active             | boolean \| null | No       | -                | Active status        |

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

| Status | Message                   |
| ------ | ------------------------- |
| 404    | Stock not found: {symbol} |

---

### Delete Stock

Soft delete a stock (marks as deleted, does not remove from database).

**Endpoint**: `DELETE /stocks/{symbol}`

**Path Parameters**:

| Parameter | Type   | Required | Description  |
| --------- | ------ | -------- | ------------ |
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

| Status | Message                   |
| ------ | ------------------------- |
| 404    | Stock not found: {symbol} |

**Note**: After deletion, the stock will no longer appear in list results or be accessible by symbol.

---

## Daily Price Endpoints

### List Daily Prices

Get historical daily OHLCV (Open, High, Low, Close, Volume) prices for a stock with keyset pagination.

**Endpoint**: `GET /stocks/{stock_id}/prices`

**Path Parameters**:

| Parameter | Type    | Required | Description |
| --------- | ------- | -------- | ----------- |
| stock_id  | integer | Yes      | Stock ID    |

**Query Parameters**:

| Parameter  | Type    | Required | Default | Description                                          |
| ---------- | ------- | -------- | ------- | ---------------------------------------------------- |
| start_date | date    | No       | -       | Start date (inclusive, format: YYYY-MM-DD)           |
| end_date   | date    | No       | -       | End date (inclusive, format: YYYY-MM-DD)             |
| cursor     | date    | No       | -       | Pagination cursor (date from previous page's last item) |
| limit      | integer | No       | 100     | Maximum number of results (1-100)                    |

**Response** (200 OK):

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "data": [
      {
        "id": 1,
        "stock_id": 1,
        "date": "2026-05-12",
        "open": "600.00",
        "high": "650.00",
        "low": "590.00",
        "close": "630.00",
        "volume": 1000000,
        "created_at": "2026-05-12T10:00:00Z"
      }
    ],
    "next_cursor": "2026-05-10",
    "has_more": true
  }
}
```

**Response Schema**:

| Field       | Type            | Description                                    |
| ----------- | --------------- | ---------------------------------------------- |
| data        | array           | List of daily prices (sorted by date desc)     |
| next_cursor | date \| null    | Cursor for next page (null if no more)         |
| has_more    | boolean         | Whether more results exist                     |

**DailyPrice Schema**:

| Field      | Type      | Description            |
| ---------- | --------- | ---------------------- |
| id         | integer   | Price record ID        |
| stock_id   | integer   | Stock ID               |
| date       | date      | Trading date           |
| open       | decimal   | Opening price          |
| high       | decimal   | Highest price          |
| low        | decimal   | Lowest price           |
| close      | decimal   | Closing price          |
| volume     | integer   | Trading volume         |
| created_at | datetime  | Record creation time   |

**Error Responses**:

| Status | Message                     |
| ------ | --------------------------- |
| 404    | Stock not found: {stock_id} |

---

### Bulk Insert Daily Prices

Bulk insert historical daily price data for a stock. Uses upsert mode to prevent duplicates (updates existing records for the same stock_id + date).

**Endpoint**: `POST /stocks/{stock_id}/prices`

**Path Parameters**:

| Parameter | Type    | Required | Description |
| --------- | ------- | -------- | ----------- |
| stock_id  | integer | Yes      | Stock ID    |

**Request Body**:

```json
{
  "prices": [
    {
      "date": "2026-05-12",
      "open": "600.00",
      "high": "650.00",
      "low": "590.00",
      "close": "630.00",
      "volume": 1000000
    },
    {
      "date": "2026-05-11",
      "open": "595.00",
      "high": "640.00",
      "low": "585.00",
      "close": "620.00",
      "volume": 950000
    }
  ]
}
```

**Request Schema**:

| Field  | Type   | Required | Constraints      | Description                   |
| ------ | ------ | -------- | ---------------- | ----------------------------- |
| prices | array  | Yes      | 1-1000 items     | List of daily price records   |

**DailyPrice Item Schema**:

| Field  | Type    | Required | Constraints            | Description      |
| ------ | ------- | -------- | ---------------------- | ---------------- |
| date   | date    | Yes      | -                      | Trading date     |
| open   | decimal | Yes      | > 0                    | Opening price    |
| high   | decimal | Yes      | > 0, >= open, >= close | Highest price    |
| low    | decimal | Yes      | > 0, <= open, <= close | Lowest price     |
| close  | decimal | Yes      | > 0                    | Closing price    |
| volume | integer | Yes      | >= 0                   | Trading volume   |

**Response** (201 Created):

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "stock_id": 1,
    "count": 5,
    "message": "Successfully inserted/updated 5 price records"
  }
}
```

**Error Responses**:

| Status | Message                                    |
| ------ | ------------------------------------------ |
| 404    | Stock not found: {stock_id}                |
| 422    | Validation error (OHLCV consistency check) |

**OHLCV Validation Rules**:

- `high >= low` (highest price must be >= lowest price)
- `high >= open` (highest price must be >= opening price)
- `high >= close` (highest price must be >= closing price)
- `low <= open` (lowest price must be <= opening price)
- `low <= close` (lowest price must be <= closing price)

---

### Get Moving Average

Calculate moving average (MA) for a stock. Common periods include 5, 10, 20, 60, 200.

**Endpoint**: `GET /stocks/{stock_id}/ma/{period}`

**Path Parameters**:

| Parameter | Type    | Required | Description                      |
| --------- | ------- | -------- | -------------------------------- |
| stock_id  | integer | Yes      | Stock ID                         |
| period    | integer | Yes      | MA period (e.g., 200 for 200MA)  |

**Query Parameters**:

| Parameter  | Type | Required | Default | Description                               |
| ---------- | ---- | -------- | ------- | ----------------------------------------- |
| as_of_date | date | No       | today   | Calculation date (format: YYYY-MM-DD)     |

**Response** (200 OK):

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "stock_id": 1,
    "period": 200,
    "date": "2026-05-12",
    "value": "625.50",
    "data_points": 200
  }
}
```

**Response Schema**:

| Field       | Type            | Description                                  |
| ----------- | --------------- | -------------------------------------------- |
| stock_id    | integer         | Stock ID                                     |
| period      | integer         | MA period requested                          |
| date        | date            | Calculation date                             |
| value       | decimal \| null | MA value (null if insufficient data points)  |
| data_points | integer         | Actual data points used for calculation      |

**Error Responses**:

| Status | Message                                     |
| ------ | ------------------------------------------- |
| 404    | Stock not found: {stock_id}                 |
| 400    | Period must be between 1 and 500            |

**Note**: If `data_points < period`, `value` will be `null` indicating insufficient historical data for the requested MA period.

---
