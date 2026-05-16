"""Authentication schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from src.schemas.base import BaseSchema


class UserRegisterRequest(BaseModel):
    """用戶註冊請求"""

    email: EmailStr = Field(..., description="用戶信箱")
    password: str = Field(..., min_length=8, max_length=128, description="密碼")


class LoginRequest(BaseModel):
    """登入請求"""

    email: EmailStr = Field(..., description="用戶信箱")
    password: str = Field(..., min_length=8, max_length=128, description="密碼")


class LoginResponse(BaseModel):
    """登入響應"""

    access_token: str = Field(..., description="JWT 存取權杖")
    token_type: str = Field(default="bearer", description="權杖類型")


class OAuthUrlResponse(BaseModel):
    """OAuth 授權 URL 響應"""

    authorization_url: str = Field(..., description="授權 URL")
    state: str = Field(..., description="CSRF 防護 state token")


class OAuthCallbackRequest(BaseModel):
    """OAuth 回調請求"""

    code: str = Field(..., description="授權碼")
    state: str = Field(..., description="CSRF 防護 state token")


class UserResponse(BaseSchema):
    """用戶響應"""

    id: int
    email: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
