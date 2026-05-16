"""User schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from src.schemas.base import BaseSchema


class UserResponse(BaseSchema):
    """用戶響應"""

    id: int
    email: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

