# Health Endpoint Spec

## Overview

Add a `/health` endpoint to check the availability of database (PostgreSQL) and Redis connections. This endpoint must be PUBLIC (no authentication required) for monitoring systems and load balancers to verify service health.

## Requirements

- Endpoint path: `/health`
- No authentication required (public endpoint)
- Check PostgreSQL connection: execute `SELECT 1`
- Check Redis connection: use existing `StockRedisClient.ping()` method
- Return JSON response with status of each component
- HTTP 200 if all healthy, HTTP 503 if any component fails

## Implementation Details

### Response Schema

```json
{
  "status": "healthy",
  "components": {
    "database": "ok",
    "redis": "ok"
  }
}
```

### Database Check

Use SQLAlchemy async session:
```python
await db.execute(text("SELECT 1"))
```

### Redis Check

Use existing `StockRedisClient.ping()` method from `src/stocks/redis_client.py`.

### Files to Modify

1. `src/main.py` - Add `/health` endpoint (public, no router prefix)
2. `src/dependencies.py` - May need public database session getter (no auth)

## References

- @src/main.py - FastAPI application entry point
- @src/config.py - Environment configuration
- @src/stocks/redis_client.py - Existing Redis client with ping method