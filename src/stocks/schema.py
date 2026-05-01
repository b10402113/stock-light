"""Stock schemas."""

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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
