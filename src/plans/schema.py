"""Plan schemas."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict

from src.schemas.base import BaseSchema


class BillingCycle(str, Enum):
    """計費週期"""

    MONTHLY = "monthly"
    YEARLY = "yearly"


class LevelConfigResponse(BaseModel):
    """等級配置響應"""

    model_config = ConfigDict(from_attributes=True)

    level: int
    name: str
    monthly_price: float
    yearly_price: float
    max_subscriptions: int
    max_alerts: int
    features: dict | None = None
    is_purchasable: bool


class PlanResponse(BaseSchema):
    """方案響應"""

    id: int
    user_id: int
    level: int
    billing_cycle: str
    price: float
    due_date: datetime
    is_active: bool
    created_at: datetime


class PlanWithLevelResponse(BaseSchema):
    """方案含等級配置響應"""

    id: int
    user_id: int
    level: int
    billing_cycle: str
    price: float
    due_date: datetime
    is_active: bool
    created_at: datetime
    level_config: LevelConfigResponse


class PlanCreate(BaseModel):
    """創建方案請求"""

    user_id: int
    level: int
    billing_cycle: BillingCycle


class PlanUpdate(BaseModel):
    """更新方案請求"""

    level: int | None = None
    billing_cycle: BillingCycle | None = None
    due_date: datetime | None = None
    is_active: bool | None = None