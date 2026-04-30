# Current Feature

## Status

In Progress

## Goals

- 支援 Google OAuth 2.0 登入
- 現有 email/password 登入不受影響
- 相同信箱的自動綁定到同一用戶
- OAuth 用戶可綁定/設定密碼以支援傳統登入
- 統一返回 JWT token

## Notes

### 技術決策

- 使用 OAuth 2.0 Authorization Code Flow
- 新增 `oauth_accounts` 表存放第三方帳戶關聯
- 修改 `users` 表：`email` 和 `hashed_password` 改為可選
- 使用 `oauth_client.py` 封裝第三方 API 呼叫
- 遵循現有架構：router → service → model

### 資料庫變更

1. `users` 表：
   - `email` 改為 `nullable=True`
   - `hashed_password` 改為 `nullable=True`
   - 新增 `line_user_id` 欄位（現有功能需要）

2. 新增 `oauth_accounts` 表：
   - `user_id` (FK)
   - `provider` ("google" | "line")
   - `provider_user_id`
   - `provider_email`
   - `provider_name`
   - `provider_picture`

### API 端點

- `GET /auth/{provider}` - 產生授權 URL
- `GET /auth/{provider}/callback` - OAuth 回調

### 綁定邏輯

1. OAuth 帳戶已存在 → 返回該用戶 JWT
2. OAuth 信箱匹配現有用戶 → 自動綁定
3. 無匹配 → 建立新用戶

## History

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
