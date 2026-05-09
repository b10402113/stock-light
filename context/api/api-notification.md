## Notifications API

### List Notification History

Get notification history for the authenticated user with keyset pagination.

**Endpoint**: `GET /notifications/history`

**Authentication**: Required (JWT Bearer token)

**Headers**:

| Header        | Value          | Required |
| ------------- | -------------- | -------- |
| Authorization | Bearer {token} | Yes      |

**Query Parameters**:

| Parameter | Type     | Required | Default | Description                                     |
| --------- | -------- | -------- | ------- | ----------------------------------------------- |
| cursor    | datetime | No       | -       | Pagination cursor (triggered_at from last item) |
| limit     | integer  | No       | 20      | Items per page (1-100)                          |

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
        "indicator_subscription_id": 1,
        "triggered_value": "30.5000",
        "send_status": "sent",
        "line_message_id": "msg_abc123",
        "triggered_at": "2026-05-02T10:30:00Z",
        "created_at": "2026-05-02T10:30:00Z"
      }
    ],
    "next_cursor": null,
    "has_more": false
  }
}
```

**Response Schema**:

| Field       | Type             | Description                            |
| ----------- | ---------------- | -------------------------------------- |
| data        | array            | List of notification history           |
| next_cursor | datetime \| null | Cursor for next page (null if no more) |
| has_more    | boolean          | Whether more results exist             |

**Notification History Schema**:

| Field                     | Type           | Description                           |
| ------------------------- | -------------- | ------------------------------------- |
| id                        | integer        | Notification history ID               |
| user_id                   | integer        | User ID                               |
| indicator_subscription_id | integer        | Subscription ID that triggered        |
| triggered_value           | decimal        | Value that triggered the notification |
| send_status               | string         | Status: pending, sent, failed         |
| line_message_id           | string \| null | LINE message ID for tracking          |
| triggered_at              | datetime       | When condition was triggered          |
| created_at                | datetime       | Log creation timestamp                |

**Send Status Values**:

| Value   | Description                     |
| ------- | ------------------------------- |
| pending | Notification queued for sending |
| sent    | Successfully delivered          |
| failed  | Failed to send (can retry)      |

---

### Get Notification History Detail

Get a single notification history entry by ID.

**Endpoint**: `GET /notifications/history/{history_id}`

**Authentication**: Required (JWT Bearer token)

**Path Parameters**:

| Parameter  | Type    | Required | Description             |
| ---------- | ------- | -------- | ----------------------- |
| history_id | integer | Yes      | Notification history ID |

**Response** (200 OK):

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "user_id": 1,
    "indicator_subscription_id": 1,
    "triggered_value": "30.5000",
    "send_status": "sent",
    "line_message_id": "msg_abc123",
    "triggered_at": "2026-05-02T10:30:00Z",
    "created_at": "2026-05-02T10:30:00Z"
  }
}
```

**Error Responses**:

| Status | Message                              |
| ------ | ------------------------------------ |
| 404    | Notification history not found: {id} |

---
