"""Subscription schemas."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SignalType(StrEnum):
    """信號類型"""
    BUY = "buy"
    SELL = "sell"


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


class SendStatus(StrEnum):
    """通知發送狀態"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class StockBrief(BaseModel):
    """股票簡要信息"""

    id: int
    symbol: str
    name: str
    current_price: Optional[Decimal] = None
    change_percent: Optional[Decimal] = None


class IndicatorSubscriptionBase(BaseModel):
    """Base schema for indicator subscription"""

    stock_id: int = Field(..., description="Target stock ID")
    title: str = Field("", max_length=50, description="Alert title (max 50 chars)")
    message: str = Field("", max_length=200, description="Alert message content (max 200 chars)")
    signal_type: SignalType = Field(SignalType.BUY, description="Signal type: buy or sell")
    indicator_type: IndicatorType = Field(..., description="Type of indicator (rsi, macd, kd, price)")
    operator: Operator = Field(..., description="Comparison operator")
    target_value: Decimal = Field(..., ge=0, description="Target value for the indicator")
    compound_condition: Optional[dict] = Field(None, description="Complex conditions (AND/OR logic)")


class IndicatorSubscriptionCreate(IndicatorSubscriptionBase):
    """Schema for creating a subscription"""

    pass


class IndicatorSubscriptionUpdate(BaseModel):
    """Schema for updating a subscription"""

    title: Optional[str] = Field(None, max_length=50, description="Alert title")
    message: Optional[str] = Field(None, max_length=200, description="Alert message content")
    signal_type: Optional[SignalType] = Field(None, description="Signal type")
    indicator_type: Optional[IndicatorType] = Field(None, description="Type of indicator")
    operator: Optional[Operator] = Field(None, description="Comparison operator")
    target_value: Optional[Decimal] = Field(None, ge=0, description="Target value")
    compound_condition: Optional[dict] = Field(None, description="Complex conditions")
    is_active: Optional[bool] = Field(None, description="Subscription active status")


class IndicatorSubscriptionResponse(BaseModel):
    """Schema for subscription response"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    stock: StockBrief
    subscription_type: str = "indicator"
    title: str
    message: str
    signal_type: str
    indicator_type: str
    operator: str
    target_value: Decimal
    compound_condition: Optional[dict] = None
    is_triggered: bool
    cooldown_end_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SubscriptionListRequest(BaseModel):
    """訂閱列表請求"""

    type: Optional[str] = Field(None, description="Filter by type: 'indicator' or 'reminder'")
    cursor: Optional[int] = Field(None, description="Pagination cursor (last id)")
    limit: int = Field(20, ge=1, le=100, description="Number of items per page")


class SubscriptionListResponse(BaseModel):
    """Schema for paginated subscription list response"""

    data: list[IndicatorSubscriptionResponse]
    next_cursor: Optional[int] = None
    has_more: bool = False


class NotificationHistoryResponse(BaseModel):
    """Schema for notification history response"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    indicator_subscription_id: int
    triggered_value: Decimal
    send_status: str
    line_message_id: Optional[str] = None
    triggered_at: datetime
    created_at: datetime


class NotificationHistoryListResponse(BaseModel):
    """Schema for paginated notification history list response"""

    data: list[NotificationHistoryResponse]
    next_cursor: Optional[datetime] = None
    has_more: bool = False
