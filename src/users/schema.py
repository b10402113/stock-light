from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegisterRequest(BaseModel):
    """用戶註冊請求"""

    email: EmailStr = Field(..., description="用戶信箱")
    password: str = Field(..., min_length=8, max_length=128, description="密碼")


class UserResponse(BaseModel):
    """用戶響應"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    is_active: bool
