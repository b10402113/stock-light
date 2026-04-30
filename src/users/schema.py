"""User schemas."""

from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    """用戶響應"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str | None = None
    is_active: bool

