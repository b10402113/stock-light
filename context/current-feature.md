# Current Feature

## Status

Not Started

## Goals

<!-- Add goals when starting a new feature -->

## Notes

<!-- Add notes, constraints, or technical decisions when starting a new feature -->

## History

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