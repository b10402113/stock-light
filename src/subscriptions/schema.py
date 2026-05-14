"""Subscription schemas."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SignalType(StrEnum):
    """信號類型"""
    BUY = "buy"
    SELL = "sell"


class IndicatorType(StrEnum):
    """指標類型"""
    RSI = "rsi"
    SMA = "sma"
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


class Timeframe(StrEnum):
    """時間框架"""
    D = "D"
    W = "W"


class SendStatus(StrEnum):
    """通知發送狀態"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class FrequencyType(StrEnum):
    """提醒頻率類型"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class LogicOperator(StrEnum):
    """邏輯運算子"""
    AND = "and"
    OR = "or"


class Condition(BaseModel):
    """Single condition within a compound condition"""

    indicator_type: IndicatorType = Field(..., description="Indicator type: rsi, sma, macd, kd, price")
    operator: Operator = Field(..., description="Comparison operator: >, <, >=, <=, ==, !=")
    target_value: Decimal = Field(..., ge=0, description="Target threshold value")
    timeframe: Timeframe = Field(Timeframe.D, description="Data timeframe: D (day) or W (week)")
    period: Optional[int] = Field(None, ge=5, le=200, description="Indicator period for RSI/SMA")

    @model_validator(mode="after")
    def validate_period_for_indicator(self):
        """Validate that period is only set for RSI/SMA indicators"""
        if self.period is not None:
            if self.indicator_type not in (IndicatorType.RSI, IndicatorType.SMA):
                raise ValueError(f"period is not applicable for {self.indicator_type} indicator")
        return self


class CompoundCondition(BaseModel):
    """Complex conditions with AND/OR logic"""

    logic: LogicOperator = Field(..., description="Logic operator: and, or")
    conditions: list[Condition] = Field(..., min_length=1, description="List of conditions")

    @field_validator("conditions")
    @classmethod
    def validate_conditions_count(cls, v: list[Condition]) -> list[Condition]:
        if len(v) > 10:
            raise ValueError("Maximum 10 conditions allowed")
        return v


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
    timeframe: Timeframe = Field(Timeframe.D, description="Data timeframe: D (day) or W (week)")
    period: Optional[int] = Field(None, ge=5, le=200, description="Indicator period for RSI/SMA")
    indicator_type: Optional[IndicatorType] = Field(None, description="Type of indicator (rsi, sma, macd, kd, price)")
    operator: Optional[Operator] = Field(None, description="Comparison operator")
    target_value: Optional[Decimal] = Field(None, ge=0, description="Target value for the indicator")
    compound_condition: Optional[CompoundCondition] = Field(None, description="Complex conditions (AND/OR logic)")

    @model_validator(mode="after")
    def validate_period_for_indicator(self):
        """Validate that period is only set for RSI/SMA indicators"""
        if self.period is not None:
            if self.indicator_type not in (IndicatorType.RSI, IndicatorType.SMA):
                raise ValueError(f"period is not applicable for {self.indicator_type} indicator")
        return self

    @model_validator(mode="after")
    def validate_condition_fields(self):
        """Validate that at least one condition is provided"""
        has_single = all([self.indicator_type, self.operator, self.target_value])
        has_compound = self.compound_condition is not None

        # Allow both (primary + additional) but require at least one
        if not has_single and not has_compound:
            raise ValueError("Either single condition fields (indicator_type, operator, target_value) or compound_condition must be provided")

        return self


class IndicatorSubscriptionCreate(IndicatorSubscriptionBase):
    """Schema for creating a subscription"""

    pass


class IndicatorSubscriptionUpdate(BaseModel):
    """Schema for updating a subscription"""

    title: Optional[str] = Field(None, max_length=50, description="Alert title")
    message: Optional[str] = Field(None, max_length=200, description="Alert message content")
    signal_type: Optional[SignalType] = Field(None, description="Signal type")
    timeframe: Optional[Timeframe] = Field(None, description="Data timeframe")
    period: Optional[int] = Field(None, ge=5, le=200, description="Indicator period for RSI/SMA")
    indicator_type: Optional[IndicatorType] = Field(None, description="Type of indicator")
    operator: Optional[Operator] = Field(None, description="Comparison operator")
    target_value: Optional[Decimal] = Field(None, ge=0, description="Target value")
    compound_condition: Optional[CompoundCondition] = Field(None, description="Complex conditions")
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
    timeframe: str
    period: Optional[int] = None
    indicator_type: Optional[str] = None
    operator: Optional[str] = None
    target_value: Optional[Decimal] = None
    compound_condition: Optional[CompoundCondition] = None
    is_triggered: bool
    cooldown_end_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TimeframeConfig(BaseModel):
    """Timeframe field configuration"""

    required: bool = Field(..., description="Is timeframe required")
    default: str = Field(..., description="Default timeframe value")
    options: list[str] = Field(..., description="Available timeframe options")


class PeriodConfig(BaseModel):
    """Period field configuration"""

    required: bool = Field(False, description="Is period required")
    default: Optional[int] = Field(None, description="Default period value")
    min: Optional[int] = Field(None, description="Minimum period value")
    max: Optional[int] = Field(None, description="Maximum period value")


class IndicatorFieldConfig(BaseModel):
    """Configuration for a single indicator"""

    label: str = Field(..., description="Human-readable indicator label")
    timeframe: TimeframeConfig = Field(..., description="Timeframe configuration")
    period: Optional[PeriodConfig] = Field(None, description="Period configuration (None if not applicable)")
    operators: list[str] = Field(..., description="Available comparison operators")
    note: Optional[str] = Field(None, description="Additional note for fixed-period indicators")


class IndicatorConfigResponse(BaseModel):
    """Response schema for GET /subscriptions/indicators/config"""

    indicators: dict[str, IndicatorFieldConfig] = Field(..., description="Configuration for each indicator type")


class ScheduledReminderCreate(BaseModel):
    """Schema for creating a scheduled reminder"""

    stock_id: int = Field(..., description="Target stock ID")
    title: str = Field("", max_length=50, description="Reminder title (max 50 chars)")
    message: str = Field("", max_length=200, description="Reminder message content (max 200 chars)")
    frequency_type: FrequencyType = Field(FrequencyType.DAILY, description="Frequency type: daily, weekly, monthly")
    reminder_time: str = Field("17:00", pattern=r"^[0-9]{2}:[0-9]{2}$", description="Time of day (HH:MM format)")
    day_of_week: int = Field(0, ge=0, le=6, description="Day of week (0-6, Mon-Sun) for weekly")
    day_of_month: int = Field(0, ge=0, le=28, description="Day of month (1-28) for monthly")


class ScheduledReminderUpdate(BaseModel):
    """Schema for updating a scheduled reminder"""

    title: Optional[str] = Field(None, max_length=50, description="Reminder title")
    message: Optional[str] = Field(None, max_length=200, description="Reminder message content")
    frequency_type: Optional[FrequencyType] = Field(None, description="Frequency type")
    reminder_time: Optional[str] = Field(None, pattern=r"^[0-9]{2}:[0-9]{2}$", description="Time of day (HH:MM)")
    day_of_week: Optional[int] = Field(None, ge=0, le=6, description="Day of week for weekly")
    day_of_month: Optional[int] = Field(None, ge=0, le=28, description="Day of month for monthly")
    is_active: Optional[bool] = Field(None, description="Reminder active status")


class ScheduledReminderResponse(BaseModel):
    """Schema for scheduled reminder response"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    stock: StockBrief
    subscription_type: str = "reminder"
    title: str
    message: str
    frequency_type: str
    reminder_time: str
    day_of_week: int
    day_of_month: int
    next_trigger_at: datetime
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


class ScheduledReminderListResponse(BaseModel):
    """Schema for paginated scheduled reminder list response"""

    data: list[ScheduledReminderResponse]
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
