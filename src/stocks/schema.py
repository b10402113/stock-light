"""Stock schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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
    isClose: bool = Field(..., description="是否收盤")


class TickerResponse(BaseModel):
    """Fugle ticker response for stock list."""

    symbol: str = Field(..., description="股票代碼")
    name: str = Field(..., description="股票名稱")


class IntradayCandle(BaseModel):
    """Fugo intraday OHLC candle."""

    candle_date: datetime = Field(..., alias="date", description="日期")
    candle_time: datetime | None = Field(None, alias="time", description="時間")
    open: Decimal = Field(..., description="開盤價")
    high: Decimal = Field(..., description="最高價")
    low: Decimal = Field(..., description="最低價")
    close: Decimal = Field(..., description="收盤價")
    volume: int = Field(..., description="成交量")

    model_config = ConfigDict(populate_by_name=True)


class HistoricalCandle(BaseModel):
    """Fugo historical OHLC candle."""

    candle_date: datetime = Field(..., alias="date", description="日期")
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
    symbol: str = Field(..., max_length=20, description="股票代碼，如 2330.TW")
    name: str = Field(..., max_length=255, description="股票名稱")
    current_price: Decimal | None = Field(None, description="當前價格")
    calculated_indicators: dict[str, Any] | None = Field(
        None, description="計算後的技術指標"
    )
    is_active: bool = Field(..., description="是否活躍")


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
    is_active: bool = True


class StockUpdate(BaseModel):
    """股票更新請求"""

    name: str | None = Field(None, min_length=1, max_length=255)
    current_price: Decimal | None = Field(None, ge=0, le=100000)
    calculated_indicators: dict[str, Any] | None = None
    is_active: bool | None = None
