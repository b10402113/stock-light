"""Watchlist schemas."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.base import BaseSchema


# Request schemas
class WatchlistCreate(BaseModel):
    """自選股清單創建請求"""

    name: str = Field(..., min_length=1, max_length=100, description="清單名稱")
    description: str | None = Field(None, max_length=500, description="清單描述")


class WatchlistUpdate(BaseModel):
    """自選股清單更新請求"""

    name: str | None = Field(None, min_length=1, max_length=100, description="清單名稱")
    description: str | None = Field(None, max_length=500, description="清單描述")


class WatchlistStockAdd(BaseModel):
    """添加股票到自選股清單請求"""

    stock_id: int = Field(..., gt=0, description="股票 ID")
    notes: str | None = Field(None, max_length=500, description="備註")


class WatchlistStockUpdate(BaseModel):
    """更新自選股清單內股票請求"""

    notes: str | None = Field(None, max_length=500, description="備註")
    sort_order: int | None = Field(None, ge=0, description="排序順序")


# Response schemas
class WatchlistStockItem(BaseSchema):
    """自選股清單內的股票"""

    stock_id: int = Field(..., description="股票 ID")
    symbol: str = Field(..., description="股票代碼")
    name: str = Field(..., description="股票名稱")
    current_price: Decimal | None = Field(None, description="當前價格")
    notes: str | None = Field(None, description="備註")
    sort_order: int = Field(..., description="排序順序")
    created_at: datetime = Field(..., description="加入時間")


class WatchlistResponse(BaseSchema):
    """自選股清單響應"""

    id: int = Field(..., description="清單 ID")
    name: str = Field(..., description="清單名稱")
    description: str | None = Field(None, description="清單描述")
    is_default: bool = Field(..., description="是否為預設清單")
    stock_count: int = Field(..., description="股票數量")
    created_at: datetime = Field(..., description="創建時間")


class WatchlistDetailResponse(BaseSchema):
    """自選股清單詳細響應（包含股票列表）"""

    id: int = Field(..., description="清單 ID")
    name: str = Field(..., description="清單名稱")
    description: str | None = Field(None, description="清單描述")
    is_default: bool = Field(..., description="是否為預設清單")
    stocks: list[WatchlistStockItem] = Field(default_factory=list, description="股票列表")


class WatchlistStockResponse(BaseSchema):
    """自選股清單內股票響應"""

    watchlist_id: int = Field(..., description="清單 ID")
    stock_id: int = Field(..., description="股票 ID")
    symbol: str = Field(..., description="股票代碼")
    name: str = Field(..., description="股票名稱")
    current_price: Decimal | None = Field(None, description="當前價格")
    notes: str | None = Field(None, description="備註")
    sort_order: int = Field(..., description="排序順序")
    created_at: datetime = Field(..., description="加入時間")
