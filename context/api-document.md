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

All error responses follow a unified format with HTTP status codes:

```json
{
  "code": 400,
  "msg": "Error description",
  "data": null
}
```

#### HTTP Status Codes

| Status Code | Error Type | Description |
|------------|------------|-------------|
| 400 | Bad Request | Request parameter error |
| 401 | Unauthorized | Not authenticated |
| 403 | Forbidden | No permission |
| 404 | Not Found | Resource does not exist |
| 422 | Unprocessable Entity | Parameter validation failed |
| 429 | Too Many Requests | Request too frequent |
| 500 | Internal Server Error | Server internal error |

#### Error Response Examples

**400 Bad Request**
```json
{
  "code": 400,
  "msg": "Request parameter error",
  "data": null
}
```

**401 Unauthorized**
```json
{
  "code": 401,
  "msg": "Not authenticated",
  "data": null
}
```

**422 Validation Error**
```json
{
  "code": 422,
  "msg": "body.email: invalid email format; body.password: string too short",
  "data": {
    "errors": [
      {"loc": ["body", "email"], "msg": "invalid email format"},
      {"loc": ["body", "password"], "msg": "string too short"}
    ]
  }
}
```

**500 Internal Server Error**
```json
{
  "code": 500,
  "msg": "Server internal error",
  "data": null
}
```

---

## API documentation

- Health: @context/api/api-health.md
- User: @context/api/api-user.md
- Plan: @context/api/api-plan.md
- Stock: @context/api/api-stock.md
- Oauth: @context/api/api-oauth.md
- Subscription: @context/api/api-subscription.md
- Notification: @context/api/api-notification.md
- Watchlist: @context/api/api-watchlist.md

## Changelog

### v1.11.0 (2026-05-16)

- Unified Error Response Handling
- All error responses follow consistent JSON format: {"code": int, "msg": str, "data": any}
- HTTP-level exception classes for each status code (400, 401, 403, 404, 422, 429, 500)
- Global exception handlers for FastAPI built-in exceptions
- RequestValidationError handler with detailed validation messages
- HTTPException handler for standard FastAPI errors
- Generic Exception handler with logging for unhandled errors
- Comprehensive test coverage (11 tests)

### v1.10.0 (2026-05-10)

- Added Scheduled Reminders API
- Create, list, get, update, delete scheduled reminders
- Support for daily, weekly, monthly frequencies
- Trigger at scheduled times regardless of indicator conditions
- Combined quota with indicator subscriptions (Plan-level)
- Automatic next_trigger_at calculation
- Scheduler integration for processing due reminders

### v1.9.0 (2026-05-10)

- Enhanced Indicator Subscription API
- Added title, message, signal_type fields to subscriptions
- Enriched responses with stock details (symbol, name, price)
- Integrated Plan-level quota validation (max_subscriptions per level)
- Stock details retrieved from Redis cache for current price
- Subscription type badge in unified response format

### v1.8.0 (2026-05-10)

- Added Plans API
- User Level System with 4 tiers (Regular, Pro, Pro Max, Admin)
- Level configuration with pricing and quotas
- Plan management for user subscriptions
- Admin-only endpoints for plan creation/update/cancellation
- Billing cycle support (monthly/yearly)
- Auto-downgrade on expiration
- Permanent access for Admin level

### v1.7.0 (2026-05-09)

- Added Health Check API
- Public endpoint for monitoring systems and load balancers
- Check PostgreSQL connection (SELECT 1)
- Check Redis connection (ping)
- HTTP 200 if healthy, HTTP 503 if unhealthy
- No authentication required

### v1.6.0 (2026-05-06)

- Improved Stock Search API fallback strategy
- Changed from fetching all TSE/OTC tickers to single ticker lookup
- Added `GET /intraday/ticker/{symbol}` endpoint to FugoClient
- More efficient API usage: queries only the needed ticker
- Reduced latency and API call volume for single symbol searches

### v1.5.0 (2026-05-02)

- Added Notifications API
- List notification history with keyset pagination
- Get notification history detail by ID
- Track notification send status (pending, sent, failed)
- LINE message ID tracking for delivery verification
- Keyset pagination on triggered_at descending

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
