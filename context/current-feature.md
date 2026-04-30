# Auth Domain Refactor

## Status

Complete

## Goals

- Extract all authentication logic (login, JWT signing, third-party OAuth) from the `users` domain into a new independent `auth` domain
- The `users` domain should only focus on user data CRUD and profile management
- Within `auth`, use folder structure to separate different providers (Google, LINE)
- Maintain backward compatibility for existing API endpoints
- Update imports and dependencies after refactor
- Ensure all tests pass after the refactor

## Notes

### Current State Analysis

**users/service.py** currently contains mixed concerns:
- User registration (register) - should stay in users
- User login (login) - password-based - **move to auth**
- OAuth login (oauth_login) - third-party - **move to auth**
- JWT token creation (_create_access_token) - **move to auth**
- Password hashing/verification - **move to auth**
- OAuth state generation/verification - **move to auth**
- OAuth user finding/creation (_find_or_create_oauth_user) - **move to auth**
- User CRUD methods (get_by_email, get_by_id) - stay in users

**users/router.py** currently exposes:
- /users/register - stays in users (or move to auth/register)
- /users/login - **move to auth**
- /auth/{provider} - **move to auth**
- /auth/{provider}/callback - **move to auth**

**users/model.py** currently contains:
- User model - keep in users (but OAuthAccount should move to auth or be shared)
- OAuthAccount model - **move to auth**

**users/oauth_client.py** - **move to auth/providers/** with provider-specific structure

**dependencies.py** - JWT parsing (get_current_user_id, get_current_user) - **move to auth**

### New Auth Domain Structure

```
src/
├── auth/                    # NEW: Authentication domain
│   ├── router.py           # Auth endpoints
│   ├── service.py          # Auth business logic
│   ├── schema.py           # Auth Request/Response
│   ├── dependencies.py     # JWT token validation
│   ├── token.py            # JWT token creation/verification
│   ├── providers/           # Provider-specific implementations
│   │   ├── __init__.py
│   │   ├── base.py         # Abstract base class
│   │   ├── google.py       # Google OAuth
│   │   └── line.py         # LINE OAuth
│   └── models.py            # OAuthAccount model
│
├── users/                   # Users domain (simplified)
│   ├── router.py           # User CRUD endpoints
│   ├── service.py          # User CRUD business logic
│   ├── schema.py           # User Request/Response
│   └── model.py            # User model
```

### New API Endpoints

```
# Auth domain (NEW)
POST /auth/register      # Email/password registration
POST /auth/login         # Email/password login
GET  /auth/{provider}     # OAuth authorization URL
GET  /auth/{provider}/callback  # OAuth callback

# Users domain (SIMPLIFIED)
GET    /users/me          # Get current user profile
PATCH  /users/me          # Update user profile
DELETE /users/me          # Deactivate account
```

### Data Model Changes

**users/model.py** (keep in users):
```python
class User(Base):
    """用戶資料表"""
    __tablename__ = "users"
    email: Mapped[str | None]
    hashed_password: Mapped[str | None]
    is_active: Mapped[bool]
    line_user_id: Mapped[str | None]  # Keep for messaging
    # Remove: oauth_accounts relationship
```

**auth/models.py** (new):
```python
class OAuthAccount(Base):
    """第三方登入帳戶關聯表"""
    __tablename__ = "oauth_accounts"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), ...)
    provider: Mapped[str]
    provider_user_id: Mapped[str]
    # ... other fields
```

### Cross-Domain Dependencies

- **auth → users**: Auth needs to call user service for creating/linking users
- **users → auth**: None (one-way dependency)
- **dependencies.py**: Should import from `auth.dependencies`

### Migration Steps

1. Create `auth/` domain structure
2. Move OAuth models to `auth/models.py`
3. Move OAuth client to `auth/providers/` with provider separation
4. Move token logic to `auth/token.py`
5. Move auth dependencies to `auth/dependencies.py`
6. Move auth schemas to `auth/schema.py`
7. Move auth business logic to `auth/service.py`
8. Move auth endpoints to `auth/router.py`
9. Update `users/` to remove auth-specific code
10. Update `main.py` to include auth router
11. Update imports across the codebase
12. Run tests and fix any issues

### Potential Issues

- OAuthAccount relationship in User model - needs to be handled carefully
- Existing tests may need updates for new imports
- Line user_id in User model is used by subscriptions/messaging - ensure it stays
- Database migrations are NOT needed (same table structure)

## History

- 2026-04-30: Auth Domain Refactor
  - Created new `src/auth/` domain for authentication logic
  - Separated OAuth providers into `auth/providers/` (google.py, line.py)
  - Moved JWT utilities to `auth/token.py`
  - Moved auth dependencies to `auth/dependencies.py`
  - Moved auth schemas to `auth/schema.py`
  - Moved auth business logic to `auth/service.py`
  - Moved auth endpoints to `auth/router.py` (`/auth/register`, `/auth/login`, `/auth/{provider}`)
  - Simplified `users/` domain to focus on CRUD operations only
  - Updated API endpoints: `/users/register` → `/auth/register`, `/users/login` → `/auth/login`
  - All tests passing (34/34)
