from pydantic import BaseModel, ConfigDict, EmailStr, Field


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


class UserResponse(BaseModel):
    """用戶響應"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    is_active: bool
