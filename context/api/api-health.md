# Health Check API

## Overview

Public health check endpoint for monitoring systems and load balancers. No authentication required.

---

## Endpoints

### GET /health

Check database and Redis connection health.

**Authentication**: None (public endpoint)

**Response Schema**:

```json
{
  "status": "pass",
  "version": "1.0.0",
  "description": "StockLight API",
  "uptime": 3600,
  "details": {
    "database": {
      "status": "pass",
      "componentType": "datastore"
    },
    "redis": {
      "status": "pass",
      "componentType": "cache"
    }
  }
}
```

**Fields**:

- `status`: Overall health status
  - `"pass"`: All components healthy
  - `"warn"`: Components healthy but with warnings
  - `"fail"`: At least one component unhealthy
- `version`: Service version
- `description`: Service description
- `uptime`: Seconds since application started
- `details`: Per-component health check results
  - `status`: Component health status (`"pass"`/`"warn"`/`"fail"`)
  - `componentType`: Component type (`"datastore"`/`"cache"`)
  - `message`: Optional error message (only on failure)

**Status Codes**:

- `200 OK`: Status is `"pass"` or `"warn"`
- `503 Service Unavailable`: Status is `"fail"`

**Example Response (Healthy)**:

```json
{
  "status": "pass",
  "version": "1.0.0",
  "description": "StockLight API",
  "uptime": 3600,
  "details": {
    "database": {
      "status": "pass",
      "componentType": "datastore"
    },
    "redis": {
      "status": "pass",
      "componentType": "cache"
    }
  }
}
```

**Example Response (Unhealthy)**:

```json
{
  "status": "fail",
  "version": "1.0.0",
  "description": "StockLight API",
  "uptime": 3600,
  "details": {
    "database": {
      "status": "pass",
      "componentType": "datastore"
    },
    "redis": {
      "status": "fail",
      "componentType": "cache",
      "message": "Redis connection failed"
    }
  }
}
```

---

## Implementation Details

### Database Check

Executes `SELECT 1` query using SQLAlchemy async session.

- Component type: `"datastore"`
- Status `"pass"` on successful query
- Status `"fail"` with error message on failure

### Redis Check

Uses `StockRedisClient.ping()` method to verify Redis connection.

- Component type: `"cache"`
- Status `"pass"` on successful ping
- Status `"fail"` with error message on failure

### Uptime Tracking

Application tracks start time at initialization. Uptime calculated as seconds since start.

---

## Usage

### Monitoring Systems

Configure monitoring tools (Prometheus, Grafana, Datadog) to poll `/health` at regular intervals.

### Load Balancers

Configure health check path to `/health` for automatic instance removal on failure (status `"fail"`).

### Kubernetes

Use as liveness and readiness probe endpoint:
- Liveness probe: Any response indicates service running
- Readiness probe: Check `status === "pass"` to accept traffic