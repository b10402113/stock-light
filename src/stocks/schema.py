"""Stock schemas."""

import datetime
from decimal import Decimal
from enum import IntEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.schemas.base import BaseSchema


class StockSource(IntEnum):
    """股票資料來源"""

    FUGLE = 1
    YFINANCE = 2


class StockMarket(IntEnum):
    """股票市場類型"""

    TAIWAN = 1
    US = 2


class IntradayQuoteResponse(BaseModel):
    """Fugo intraday quote response."""

    symbol: str = Field(..., description="股票代碼")
    name: str = Field(..., description="股票名稱")
    lastPrice: Decimal | None = Field(None, description="最新價")
    change: Decimal | None = Field(None, description="漲跌")
    changePercent: Decimal | None = Field(None, description="漲跌百分比")
    openPrice: Decimal | None = Field(None, description="開盤價")
    highPrice: Decimal | None = Field(None, description="最高價")
    lowPrice: Decimal | None = Field(None, description="最低價")
    previousClose: Decimal | None = Field(None, description="昨收價")
    total: dict[str, Any] | None = Field(None, description="交易統計")
    isClose: bool | None = Field(None, description="是否收盤")


class TickerResponse(BaseModel):
    """Fugle ticker response for stock list."""

    symbol: str = Field(..., description="股票代碼")
    name: str | None = Field(None, description="股票名稱")


class IntradayCandle(BaseModel):
    """Fugo intraday OHLC candle."""

    candle_date: datetime.datetime = Field(..., alias="date", description="日期")
    candle_time: datetime.datetime | None = Field(None, alias="time", description="時間")
    open: Decimal = Field(..., description="開盤價")
    high: Decimal = Field(..., description="最高價")
    low: Decimal = Field(..., description="最低價")
    close: Decimal = Field(..., description="收盤價")
    volume: int = Field(..., description="成交量")

    model_config = ConfigDict(populate_by_name=True)


class HistoricalCandle(BaseModel):
    """Fugo historical OHLC candle."""

    candle_date: datetime.datetime = Field(..., alias="date", description="日期")
    open: Decimal = Field(..., description="開盤價")
    high: Decimal = Field(..., description="最高價")
    low: Decimal = Field(..., description="最低價")
    close: Decimal = Field(..., description="收盤價")
    volume: int = Field(..., description="成交量")

    model_config = ConfigDict(populate_by_name=True)


class StockResponse(BaseModel):
    """股票響應"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str = Field(..., max_length=20, description="股票代碼，如 2330")
    name: str = Field(..., max_length=255, description="股票名稱")
    current_price: Decimal | None = Field(None, description="當前價格")
    calculated_indicators: dict[str, Any] | None = Field(
        None, description="計算後的技術指標"
    )
    is_active: bool = Field(..., description="是否活躍")
    source: StockSource = Field(..., description="資料來源")
    market: StockMarket = Field(..., description="市場類型")


class StockListResponse(BaseModel):
    """股票列表響應（Keyset 分頁）"""

    data: list[StockResponse] = Field(..., description="股票列表")
    next_cursor: int | None = Field(None, description="下一頁游標")
    has_more: bool = Field(..., description="是否有更多數據")


class StockCreate(BaseModel):
    """股票創建請求"""

    symbol: str = Field(..., min_length=1, max_length=20, pattern=r"^[A-Za-z0-9]+\.TW$")
    name: str = Field(..., min_length=1, max_length=255)
    current_price: Decimal | None = Field(None, ge=0, le=100000)
    calculated_indicators: dict[str, Any] | None = None
    is_active: bool = False
    source: StockSource = Field(default=StockSource.FUGLE, description="資料來源")
    market: StockMarket = Field(default=StockMarket.TAIWAN, description="市場類型")


class StockUpdate(BaseModel):
    """股票更新請求"""

    name: str | None = Field(None, min_length=1, max_length=255)
    current_price: Decimal | None = Field(None, ge=0, le=100000)
    calculated_indicators: dict[str, Any] | None = None
    is_active: bool | None = None


class DailyPriceBase(BaseModel):
    """日K線基礎 schema"""

    date: datetime.date = Field(..., description="日期")
    open: Decimal = Field(..., gt=0, description="開盤價")
    high: Decimal = Field(..., gt=0, description="最高價")
    low: Decimal = Field(..., gt=0, description="最低價")
    close: Decimal = Field(..., gt=0, description="收盤價")
    volume: int = Field(..., ge=0, description="成交量")

    @field_validator("high")
    @classmethod
    def validate_high(cls, v: Decimal, info: Any) -> Decimal:
        """驗證最高價 >= 開盤價/收盤價"""
        values = info.data
        if "open" in values and v < values["open"]:
            raise ValueError("high must be >= open")
        if "close" in values and v < values["close"]:
            raise ValueError("high must be >= close")
        return v

    @field_validator("low")
    @classmethod
    def validate_low(cls, v: Decimal, info: Any) -> Decimal:
        """驗證最低價 <= 開盤價/收盤價"""
        values = info.data
        if "open" in values and v > values["open"]:
            raise ValueError("low must be <= open")
        if "close" in values and v > values["close"]:
            raise ValueError("low must be <= close")
        return v

    @field_validator("high")
    @classmethod
    def validate_high_vs_low(cls, v: Decimal, info: Any) -> Decimal:
        """驗證最高價 >= 最低價"""
        values = info.data
        if "low" in values and v < values["low"]:
            raise ValueError("high must be >= low")
        return v


class DailyPriceCreate(DailyPriceBase):
    """日K線創建請求"""

    stock_id: int = Field(..., gt=0, description="股票 ID")


class DailyPriceBulkCreate(BaseModel):
    """日K線批量創建請求"""

    prices: list[DailyPriceBase] = Field(..., min_length=1, max_length=1000, description="價格列表")


class DailyPriceResponse(DailyPriceBase, BaseSchema):
    """日K線響應"""

    id: int = Field(..., description="價格 ID")
    stock_id: int = Field(..., description="股票 ID")
    created_at: datetime.datetime = Field(..., description="創建時間")


class DailyPriceListResponse(BaseModel):
    """日K線列表響應（Keyset 分頁）"""

    data: list[DailyPriceResponse] = Field(..., description="價格列表")
    next_cursor: datetime.date | None = Field(None, description="下一頁游標（日期）")
    has_more: bool = Field(..., description="是否有更多數據")


class MovingAverageResponse(BaseModel):
    """移動平均線響應"""

    stock_id: int = Field(..., description="股票 ID")
    period: int = Field(..., description="移動平均期數")
    date: datetime.date = Field(..., description="計算日期")
    value: Decimal | None = Field(None, description="移動平均值（若數據不足則為 None）")
    data_points: int = Field(..., description="實際使用數據點數")
