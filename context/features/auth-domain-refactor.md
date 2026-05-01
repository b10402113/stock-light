# Auth Domain Refactor Spec

## Overview

將所有與「登入、Token 簽發、第三方 OAuth」相關的邏輯從 users domain 抽離，建立一個獨立的 auth domain。讓 users domain 專注於「使用者資料 CRUD、個人檔案管理」，auth domain 專注於「認證、授權、Token 管理」。

## Requirements

### 1. 建立 auth domain 目錄結構

```
src/auth/
├── routers/
│   ├── __init__.py
│   ├── local.py       # POST /auth/login (帳密登入)
│   ├── google.py      # GET /auth/google, GET /auth/google/callback
│   └── line.py        # GET /auth/line, GET /auth/line/callback
├── __init__.py
├── router.py          # 整合 routers/ 下的路由
├── service.py         # 登入商業邏輯 (JWT 簽發、OAuth 流程)
├── schema.py          # LoginRequest, LoginResponse, OAuthUrlResponse 等
├── google_client.py   # Google OAuth API 客戶端
├── line_client.py     # LINE Login API 客戶端
├── dependencies.py    # get_current_user_id, get_current_user
└── utils.py           # JWT、密碼處理等工具函數
```

### 2. 需搬移的程式碼

#### 從 users/router.py 搬移到 auth:
- `/users/login` endpoint → auth/routers/local.py
- `/auth/{provider}` endpoint → auth/routers/{provider}.py
- `/auth/{provider}/callback` endpoint → auth/routers/{provider}.py

#### 從 users/service.py 搬移到 auth/service.py:
- `login()` 方法
- `_create_access_token()` 方法
- `generate_oauth_state()` 方法
- `verify_oauth_state()` 方法
- `oauth_login()` 方法
- `_find_or_create_oauth_user()` 方法
- `_hash_password()` 和 `_verify_password()` → auth/utils.py

#### 從 users/oauth_client.py 搬移:
- `OAuthProvider` class → auth/schema.py
- Google 相關邏輯 → auth/google_client.py
- LINE Login 相關邏輯 → auth/line_client.py

#### 從 users/schema.py 搬移到 auth/schema.py:
- `LoginRequest`
- `LoginResponse`
- `OAuthUrlResponse`
- `OAuthCallbackRequest`

#### 從 dependencies.py 搬移到 auth/dependencies.py:
- `get_current_user_id()`
- `get_current_user()`
- `CurrentUserId` alias
- `CurrentUser` alias

### 3. users domain 清理後保留

- `router.py`: 只保留 `/users/register`
- `service.py`: 只保留 `register()`, `get_by_email()`, `get_by_id()`
- `schema.py`: 只保留 `UserRegisterRequest`, `UserResponse`
- `model.py`: 保留 `User`, `OAuthAccount` (資料模型不變)

### 4. 跨 domain 呼叫規則

- auth.service 可以呼叫 users.service (`get_by_email`, `get_by_id`) 來查找/驗證使用者
- auth.service 可以直接操作 `OAuthAccount` model 來建立 OAuth 綁定
- users.service 不呼叫 auth (單向依賴)

### 5. 更新 main.py

- 移除 `from src.users.router import auth_router`
- 加入 `from src.auth.router import router as auth_router`
- 路由註冊保持一致

### 6. 更新測試

- 測試檔案搬移: `test_users_router.py` 中登入相關測試 → `tests/auth/test_auth_router.py`
- 測試檔案搬移: `test_users_service.py` 中登入相關測試 → `tests/auth/test_auth_service.py`
- `test_dependencies.py` → `tests/auth/test_dependencies.py`

## References

- @src/users/router.py - 現有路由
- @src/users/service.py - 現有服務邏輯
- @src/users/oauth_client.py - 現有 OAuth 客戶端
- @src/users/schema.py - 現有 Schema
- @src/users/model.py - 資料模型
- @src/dependencies.py - 现有認證依賴
- @src/main.py - 主程式入口
- @tests/test_users_router.py - 路由測試
- @tests/test_users_service.py - 服務測試
- @tests/test_dependencies.py - 依賴測試
- @tests/conftest.py - 測試配置