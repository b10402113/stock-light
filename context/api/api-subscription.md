## Subscriptions API

### List Subscriptions

Get all indicator subscriptions for the authenticated user with keyset pagination.

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

| Field       | Type            | Description                            |
| ----------- | --------------- | -------------------------------------- |
| data        | array           | List of subscriptions                  |
| next_cursor | integer \| null | Cursor for next page (null if no more) |
| has_more    | boolean         | Whether more results exist             |

**Subscription Schema**:

| Field              | Type             | Description                          |
| ------------------ | ---------------- | ------------------------------------ |
| id                 | integer          | Subscription ID                      |
| user_id            | integer          | Owner user ID                        |
| stock_id           | integer          | Target stock ID                      |
| indicator_type     | string           | Indicator type: rsi, macd, kd, price |
| operator           | string           | Comparison: >, <, >=, <=, ==, !=     |
| target_value       | decimal          | Target threshold value               |
| compound_condition | object \| null   | Complex AND/OR conditions            |
| is_triggered       | boolean          | Whether condition was triggered      |
| cooldown_end_at    | datetime \| null | Cooldown period end time             |
| is_active          | boolean          | Subscription active status           |
| created_at         | datetime         | Creation timestamp                   |
| updated_at         | datetime         | Last update timestamp                |

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

| Field              | Type           | Required | Constraints                 | Description                 |
| ------------------ | -------------- | -------- | --------------------------- | --------------------------- |
| stock_id           | integer        | Yes      | Must reference active stock | Target stock ID             |
| indicator_type     | string         | Yes      | Enum: rsi, macd, kd, price  | Type of indicator           |
| operator           | string         | Yes      | Enum: >, <, >=, <=, ==, !=  | Comparison operator         |
| target_value       | decimal        | Yes      | >= 0                        | Target threshold value      |
| compound_condition | object \| null | No       | -                           | Complex conditions (AND/OR) |

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

| Status | Message                               |
| ------ | ------------------------------------- |
| 400    | Stock not found or inactive: {id}     |
| 400    | Duplicate subscription already exists |
| 403    | Subscription quota exceeded: used X/Y |

---

### Get Subscription

Get a single subscription by ID.

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

| Status | Message                      |
| ------ | ---------------------------- |
| 404    | Subscription not found: {id} |

---

### Update Subscription

Update subscription indicator type, operator, target value, or active status.

**Endpoint**: `PATCH /subscriptions/{subscription_id}`

**Authentication**: Required (JWT Bearer token)

**Path Parameters**:

| Parameter       | Type    | Required | Description     |
| --------------- | ------- | -------- | --------------- |
| subscription_id | integer | Yes      | Subscription ID |

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

| Field              | Type            | Required | Constraints                | Description         |
| ------------------ | --------------- | -------- | -------------------------- | ------------------- |
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

| Status | Message                      |
| ------ | ---------------------------- |
| 404    | Subscription not found: {id} |

**Note**: After deletion, the subscription will no longer appear in list results or be accessible by ID.

---
