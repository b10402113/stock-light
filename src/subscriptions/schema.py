"""Subscription schemas."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field


class IndicatorType(StrEnum):
    """指標類型"""
    RSI = "rsi"
    MACD = "macd"
    KD = "kd"
    PRICE = "price"


class Operator(StrEnum):
    """比較運算子"""
    GT = ">"
    LT = "<"
    GTE = ">="
    LTE = "<="
    EQ = "=="
    NEQ = "!="


class IndicatorSubscriptionBase(BaseModel):
    """Base schema for indicator subscription"""

    stock_id: int = Field(..., description="Target stock ID")
    indicator_type: IndicatorType = Field(..., description="Type of indicator (rsi, macd, kd, price)")
    operator: Operator = Field(..., description="Comparison operator")
    target_value: Decimal = Field(..., ge=0, description="Target value for the indicator")
    compound_condition: Optional[dict] = Field(None, description="Complex conditions (AND/OR logic)")


class IndicatorSubscriptionCreate(IndicatorSubscriptionBase):
    """Schema for creating a subscription"""

    pass


class IndicatorSubscriptionUpdate(BaseModel):
    """Schema for updating a subscription"""

    indicator_type: Optional[IndicatorType] = Field(None, description="Type of indicator")
    operator: Optional[Operator] = Field(None, description="Comparison operator")
    target_value: Optional[Decimal] = Field(None, ge=0, description="Target value")
    compound_condition: Optional[dict] = Field(None, description="Complex conditions")
    is_active: Optional[bool] = Field(None, description="Subscription active status")


class IndicatorSubscriptionResponse(BaseModel):
    """Schema for subscription response"""

    id: int
    user_id: int
    stock_id: int
    indicator_type: str
    operator: str
    target_value: Decimal
    compound_condition: Optional[dict] = None
    is_triggered: bool
    cooldown_end_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SubscriptionListResponse(BaseModel):
    """Schema for paginated subscription list response"""

    data: list[IndicatorSubscriptionResponse]
    next_cursor: Optional[int] = None
    has_more: bool = False
