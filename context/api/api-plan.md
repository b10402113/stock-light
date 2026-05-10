## Plans API

### Get Level Configs

Get all user level configurations with pricing and quotas.

**Endpoint**: `GET /plans/levels`

**Auth**: Not required

**Response** (200 OK):

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "level": 1,
      "name": "Regular",
      "monthly_price": 0.00,
      "yearly_price": 0.00,
      "max_subscriptions": 10,
      "max_alerts": 10,
      "features": null,
      "is_purchasable": false
    },
    {
      "level": 2,
      "name": "Pro",
      "monthly_price": 99.00,
      "yearly_price": 999.00,
      "max_subscriptions": 50,
      "max_alerts": 50,
      "features": null,
      "is_purchasable": true
    },
    {
      "level": 3,
      "name": "Pro Max",
      "monthly_price": 199.00,
      "yearly_price": 1999.00,
      "max_subscriptions": 100,
      "max_alerts": 100,
      "features": null,
      "is_purchasable": true
    },
    {
      "level": 4,
      "name": "Admin",
      "monthly_price": 0.00,
      "yearly_price": 0.00,
      "max_subscriptions": -1,
      "max_alerts": -1,
      "features": null,
      "is_purchasable": false
    }
  ]
}
```

**Level Config Schema**:

| Field             | Type    | Description                                  |
| ----------------- | ------- | -------------------------------------------- |
| level             | int     | Level number (1-4)                           |
| name              | string  | Level display name                           |
| monthly_price     | float   | Monthly subscription price                   |
| yearly_price      | float   | Yearly subscription price                    |
| max_subscriptions | int     | Maximum subscription limit (-1 = unlimited) |
| max_alerts        | int     | Maximum alert limit (-1 = unlimited)        |
| features          | object  | Feature flags (null if not configured)       |
| is_purchasable    | boolean | Whether this level can be purchased         |

---

### Get My Plan

Get current user's active plan with level configuration.

**Endpoint**: `GET /plans/me`

**Auth**: Required (JWT Token)

**Headers**:

```
Authorization: Bearer <access_token>
```

**Response** (200 OK):

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "user_id": 123,
    "level": 2,
    "billing_cycle": "monthly",
    "price": 99.00,
    "due_date": "2026-06-10T08:35:00Z",
    "is_active": true,
    "created_at": "2026-05-10T08:35:00Z",
    "level_config": {
      "level": 2,
      "name": "Pro",
      "monthly_price": 99.00,
      "yearly_price": 999.00,
      "max_subscriptions": 50,
      "max_alerts": 50,
      "features": null,
      "is_purchasable": true
    }
  }
}
```

**Error Responses**:

| Status | Code | Message          |
| ------ | ---- | ---------------- |
| 401    | 1004 | Unauthorized     |
| 404    | 1006 | No active plan   |

---

### Create Plan (Admin)

Create or upgrade a plan for a specific user. Requires Admin level (4).

**Endpoint**: `POST /plans`

**Auth**: Required (Admin JWT Token)

**Headers**:

```
Authorization: Bearer <admin_access_token>
```

**Request Body**:

```json
{
  "user_id": 123,
  "level": 2,
  "billing_cycle": "monthly"
}
```

**Request Schema**:

| Field         | Type   | Required | Constraints             | Description       |
| ------------- | ------ | -------- | ----------------------- | ----------------- |
| user_id       | int    | Yes      | Existing user ID        | Target user ID    |
| level         | int    | Yes      | 1-4                     | Level to assign   |
| billing_cycle | string | Yes      | "monthly" or "yearly"   | Billing cycle     |

**Response** (200 OK):

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 5,
    "user_id": 123,
    "level": 2,
    "billing_cycle": "monthly",
    "price": 99.00,
    "due_date": "2026-06-10T08:35:00Z",
    "is_active": true,
    "created_at": "2026-05-10T08:35:00Z"
  }
}
```

**Business Logic**:
- Deactivates any existing active plan for the user
- Calculates due_date based on billing_cycle (+30 days for monthly, +365 days for yearly)
- Price is taken from current level_config
- Admin level (4) gets permanent due_date (9999-12-31)

**Error Responses**:

| Status | Code | Message                   |
| ------ | ---- | ------------------------- |
| 401    | 1004 | Unauthorized              |
| 403    | 1005 | Only Admin can create plans |
| 404    | 1006 | Level config not found    |

---

### Update Plan (Admin)

Update an existing plan's details. Requires Admin level (4).

**Endpoint**: `PUT /plans/{plan_id}`

**Auth**: Required (Admin JWT Token)

**Headers**:

```
Authorization: Bearer <admin_access_token>
```

**Path Parameters**:

| Parameter | Type | Description |
| --------- | ---- | ----------- |
| plan_id   | int  | Plan ID     |

**Request Body**:

```json
{
  "level": 3,
  "billing_cycle": "yearly",
  "due_date": "2027-05-10T08:35:00Z",
  "is_active": true
}
```

**Request Schema** (all fields optional):

| Field         | Type      | Constraints             | Description     |
| ------------- | --------- | ----------------------- | --------------- |
| level         | int       | 1-4                     | New level       |
| billing_cycle | string    | "monthly" or "yearly"   | Billing cycle   |
| due_date      | datetime  | ISO 8601 format         | New due date    |
| is_active     | boolean   | true/false              | Active status   |

**Response** (200 OK):

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 5,
    "user_id": 123,
    "level": 3,
    "billing_cycle": "yearly",
    "price": 99.00,
    "due_date": "2027-05-10T08:35:00Z",
    "is_active": true,
    "created_at": "2026-05-10T08:35:00Z"
  }
}
```

**Error Responses**:

| Status | Code | Message                   |
| ------ | ---- | ------------------------- |
| 401    | 1004 | Unauthorized              |
| 403    | 1005 | Only Admin can update plans |
| 404    | 1006 | Plan not found            |

---

### Cancel Plan (Admin)

Cancel (deactivate) a user's plan. Requires Admin level (4).

**Endpoint**: `DELETE /plans/{plan_id}`

**Auth**: Required (Admin JWT Token)

**Headers**:

```
Authorization: Bearer <admin_access_token>
```

**Path Parameters**:

| Parameter | Type | Description |
| --------- | ---- | ----------- |
| plan_id   | int  | Plan ID     |

**Response** (200 OK):

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 5,
    "user_id": 123,
    "level": 2,
    "billing_cycle": "monthly",
    "price": 99.00,
    "due_date": "2026-06-10T08:35:00Z",
    "is_active": false,
    "created_at": "2026-05-10T08:35:00Z"
  }
}
```

**Business Logic**:
- Sets `is_active` to false
- User will need a new plan to restore premium access

**Error Responses**:

| Status | Code | Message                   |
| ------ | ---- | ------------------------- |
| 401    | 1004 | Unauthorized              |
| 403    | 1005 | Only Admin can cancel plans |
| 404    | 1006 | Plan not found            |

---