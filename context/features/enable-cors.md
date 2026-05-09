# Enable CORS Spec

## Overview

Enable Cross-Origin Resource Sharing (CORS) on the FastAPI backend to allow the frontend application (running on a different origin) to communicate with the API. This is essential for local development and production deployment where frontend and backend are served from different domains/ports.

## Requirements

- Add CORS middleware to FastAPI application in `src/main.py`
- Configure allowed origins for both development and production environments
- Support credentials for authentication cookies/headers
- Allow standard HTTP methods (GET, POST, PUT, DELETE, OPTIONS, PATCH)
- Allow common headers including Authorization and Content-Type
- Environment-specific origin configuration via `src/config.py`

## Implementation Details

### CORS Configuration

**IMPORTANT: CORS middleware must be added AFTER `app = FastAPI(...)` creation, before registering routers.**

**Allowed Origins:**
- Use existing `settings.cors_origins_list` from `src/config.py` (line 82-83)
- Default: `http://localhost:3000,http://localhost:5173` (Vite default)
- Production: Set via `CORS_ORIGINS` environment variable

**Allowed Methods:**
- GET, POST, PUT, DELETE, OPTIONS, PATCH

**Allowed Headers:**
- Authorization (for JWT tokens)
- Content-Type
- Accept
- Origin
- X-Requested-With

**Credentials:** Enable to support cookie-based authentication if needed

### Files to Modify

1. `src/main.py` - Add `CORSMiddleware` from `fastapi.middleware.cors` after app creation

## References

- @src/main.py - FastAPI application entry point
- @src/config.py - Environment configuration
- [FastAPI CORS Documentation](https://fastapi.tiangolo.com/tutorial/cors/)