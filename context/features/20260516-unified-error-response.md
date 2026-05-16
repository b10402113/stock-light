# Unified Error Response Handling Spec

## Overview

Implement a unified error response format across all API endpoints. All error responses should follow a consistent JSON structure with error code, message, and data fields. Implement global exception handling to catch and format all exceptions uniformly.

## Requirements

### 1. Unified Error Response Format

All API error responses must use the following JSON structure:

```json
{
  "code": 400,
  "msg": "error message",
  "data": null
}
```

### 2. Error Code Definitions

| Error Code | Description |
|------------|-------------|
| 400 | Bad Request - Request parameter error |
| 401 | Unauthorized - Not authenticated |
| 403 | Forbidden - No permission |
| 404 | Not Found - Resource does not exist |
| 422 | Unprocessable Entity - Parameter validation failed |
| 429 | Too Many Requests - Request too frequent |
| 500 | Internal Server Error - Server internal error |

### 3. Global Exception Handler

- Create custom exception classes in `src/exceptions.py`
- Implement global exception handlers in FastAPI
- Catch all exceptions and return unified error format
- Handle both custom exceptions and built-in FastAPI/Pydantic exceptions

### 4. Exception Classes

Create exception classes for each error code:

- `BadRequestError` (400)
- `UnauthorizedError` (401)
- `ForbiddenError` (403)
- `NotFoundError` (404)
- `ValidationError` (422)
- `RateLimitError` (429)
- `InternalServerError` (500)

### 5. Response Schema

Create Pydantic schema for error response:

```python
class ErrorResponse(BaseModel):
    code: int
    msg: str
    data: Optional[Any] = None
```

### 6. Exception Handler Implementation

- Register exception handlers in `src/main.py`
- Override default FastAPI exception handlers (RequestValidationError, HTTPException)
- Add global handler for unhandled exceptions (Exception)
- Log internal server errors for debugging

## References

- @src/exceptions.py
- @src/main.py
- @docs/rules/api-spec.md