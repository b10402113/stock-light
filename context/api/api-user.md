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

| Field    | Type   | Required | Constraints        | Description   |
| -------- | ------ | -------- | ------------------ | ------------- |
| email    | string | Yes      | Valid email format | User email    |
| password | string | Yes      | 8-128 characters   | User password |

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

| Status | Code | Message             |
| ------ | ---- | ------------------- |
| 400    | 1001 | User already exists |

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

| Field    | Type   | Required | Constraints        | Description   |
| -------- | ------ | -------- | ------------------ | ------------- |
| email    | string | Yes      | Valid email format | User email    |
| password | string | Yes      | 8-128 characters   | User password |

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

| Status | Code | Message             |
| ------ | ---- | ------------------- |
| 400    | 1002 | User not found      |
| 400    | 1003 | Invalid credentials |

---
