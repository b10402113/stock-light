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

## Changelog

### v1.0.0 (2026-04-30)

- Initial API release
- User registration endpoint
- User login endpoint with JWT authentication
- Google OAuth 2.0 login
- LINE Login integration
- Auto account binding for OAuth users
