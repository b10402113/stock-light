# Login API with JWT Spec

## Overview

Implement user login endpoint that validates credentials and returns JWT access token. Also implement JWT validation for authenticated endpoints.

## Requirements

### Login Endpoint

- POST /users/login endpoint
- Accept email and password in request body
- Validate email format and password length (8-128 characters)
- Verify user exists and is active
- Verify password matches bcrypt hash
- Return JWT access token on success
- Return appropriate error codes on failure

### JWT Token Generation

- Use PyJWT library (not python-jose)
- Sign with JWT_SECRET from settings
- Use algorithm from JWT_ALG setting (default HS256)
- Include user_id in token payload
- Set expiration based on JWT_ACCESS_TOKEN_EXPIRE_MINUTES

### JWT Validation (Dependencies)

- Create FastAPI dependency for extracting JWT from Authorization header
- Decode and validate token
- Return user_id from token payload
- Handle expired tokens (TOKEN_EXPIRED error)
- Handle invalid tokens (TOKEN_INVALID error)
- Handle missing Authorization header (UNAUTHORIZED error)

### Response Schema

- LoginRequest: email, password
- LoginResponse: access_token, token_type ("bearer")
- ErrorResponse for error cases

## Technical Details

### Token Payload Structure

```json
{
  "user_id": 1,
  "exp": <timestamp>
}
```

### Authorization Header Format

```
Authorization: Bearer <token>
```

### Dependencies to Create

- `get_current_user_id` - Extract user_id from JWT token
- `get_current_user` - Load full User entity from DB using user_id

## Error Handling

| Scenario            | HTTP Status | Error Code     |
| ------------------- | ----------- | -------------- |
| Invalid credentials | 401         | UNAUTHORIZED   |
| User not found      | 401         | USER_NOT_FOUND |
| User disabled       | 401         | USER_DISABLED  |
| Token expired       | 401         | TOKEN_EXPIRED  |
| Token invalid       | 401         | TOKEN_INVALID  |
| Missing auth header | 401         | UNAUTHORIZED   |

## References

- CLAUDE.md - Authentication section (PyJWT usage)
- CLAUDE.md - Dependencies section (Annotated form)
