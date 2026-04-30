# Login API with JWT

## Status

Complete

## Goals

- Implement POST /users/login endpoint for credential validation
- Generate JWT access tokens using PyJWT
- Create FastAPI dependencies for JWT validation
- Support protected endpoints with authentication

## Notes

### Token Configuration
- Use PyJWT library (not python-jose)
- Sign with JWT_SECRET from settings
- Use JWT_ALG setting (default HS256)
- Expiration via JWT_ACCESS_TOKEN_EXPIRE_MINUTES

### Token Payload
```json
{
  "user_id": 1,
  "exp": <timestamp>
}
```

### Dependencies to Create
- `get_current_user_id` - Extract user_id from JWT token
- `get_current_user` - Load full User entity from DB

### Error Codes
| Scenario            | HTTP Status | Error Code     |
| ------------------- | ----------- | -------------- |
| Invalid credentials | 401         | UNAUTHORIZED   |
| User not found      | 401         | USER_NOT_FOUND |
| User disabled       | 401         | USER_DISABLED  |
| Token expired       | 401         | TOKEN_EXPIRED  |
| Token invalid       | 401         | TOKEN_INVALID  |
| Missing auth header | 401         | UNAUTHORIZED   |

## History

- 2026-04-30: Backend Account Registration
  - Implemented user registration endpoint POST /users/register
  - Added email validation and uniqueness check
  - Implemented bcrypt password hashing
  - Created User model and Alembic migration
  - Added unit tests (11 passing)
