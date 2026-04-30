# Current Feature: Users & Auth Tables Update

## Status

Complete

## Goals

- Update `src/users/model.py` - add display_name, picture_url, quota, subscription_status
- Update `src/auth/models.py` - add access_token, refresh_token, expires_at
- Create migration file to add columns to both tables
- Run migration to apply changes
- Update related schemas and services to handle new fields
- Write tests for new functionality

## Notes

- New columns have default values or are nullable to ensure backward compatibility
- access_token and refresh_token should be encrypted before storage (future enhancement)
- quota default value: 10
- subscription_status default value: 'free'
- No impact on existing data or APIs

## History

- 2026-04-30: Users & Auth Tables Update
  - Added display_name, picture_url, quota, subscription_status to users table
  - Added access_token, refresh_token, expires_at to oauth_accounts table
  - Created migration: 2026-04-30_update_users_oauth_tables.py
  - All tests passing (34/34)

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

- 2026-04-30: OAuth 2.0 Login with Google and LINE
  - Implemented OAuth 2.0 authorization code flow
  - Added oauth_accounts table for third-party account linking
  - Modified users table: email and hashed_password now nullable
  - Created OAuthClient for provider API interactions
  - Implemented auto account binding by email
  - Added GET /auth/{provider} and GET /auth/{provider}/callback endpoints

- 2026-04-30: Backend Login with JWT
  - Implemented POST /users/login endpoint
  - Added JWT token generation using PyJWT
  - Created authentication dependencies (get_current_user_id, get_current_user)
  - Added LoginRequest and LoginResponse schemas
  - Added comprehensive tests (34 passing)

- 2026-04-30: Backend Account Registration
  - Implemented user registration endpoint POST /users/register
  - Added email validation and uniqueness check
  - Implemented bcrypt password hashing
  - Created User model and Alembic migration
  - Added unit tests (11 passing)
