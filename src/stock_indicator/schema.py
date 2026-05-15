"""Stock indicator schemas."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class IndicatorType(StrEnum):
    """Indicator type enum for indicator_key prefix"""
    RSI = "rsi"
    SMA = "sma"
    MACD = "macd"
    KDJ = "kdj"


class RSIData(BaseModel):
    """RSI indicator data structure"""

    value: Decimal = Field(..., description="RSI value (0-100)")


class SMAData(BaseModel):
    """SMA indicator data structure"""

    value: Decimal = Field(..., ge=0, description="SMA value")


class KDJData(BaseModel):
    """KDJ indicator data structure"""

    k: Decimal = Field(..., description="K value")
    d: Decimal = Field(..., description="D value")
    j: Decimal = Field(..., description="J value")


class MACDData(BaseModel):
    """MACD indicator data structure"""

    macd: Decimal = Field(..., description="MACD line")
    signal: Decimal = Field(..., description="Signal line")
    histogram: Decimal = Field(..., description="MACD histogram (MACD - Signal)")


class StockIndicatorResponse(BaseModel):
    """Stock indicator response schema"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Indicator record ID")
    stock_id: int = Field(..., description="Stock ID")
    indicator_key: str = Field(..., description="Indicator key (e.g., RSI_14, MACD_12_26_9)")
    data: dict = Field(..., description="Indicator data as JSONB")
    created_at: datetime = Field(..., description="Created timestamp")
    updated_at: datetime = Field(..., description="Updated timestamp")


class StockIndicatorUpsert(BaseModel):
    """Schema for upserting stock indicator"""

    stock_id: int = Field(..., description="Stock ID")
    indicator_key: str = Field(..., max_length=50, description="Indicator key")
    data: dict = Field(..., description="Indicator data")


def generate_indicator_key(indicator_type: IndicatorType, params: list[int]) -> str:
    """Generate standardized indicator key.

    Args:
        indicator_type: Indicator type enum
        params: List of period parameters

    Returns:
        str: Indicator key (e.g., RSI_14, MACD_12_26_9)

    Examples:
        RSI: generate_indicator_key(IndicatorType.RSI, [14]) -> "RSI_14"
        SMA: generate_indicator_key(IndicatorType.SMA, [20]) -> "SMA_20"
        KDJ: generate_indicator_key(IndicatorType.KDJ, [9, 3, 3]) -> "KDJ_9_3_3"
        MACD: generate_indicator_key(IndicatorType.MACD, [12, 26, 9]) -> "MACD_12_26_9"
    """
    type_str = indicator_type.value.upper()
    params_str = "_".join(str(p) for p in params)
    return f"{type_str}_{params_str}" if params_str else type_str


def parse_indicator_key(indicator_key: str) -> tuple[IndicatorType, list[int]]:
    """Parse indicator key to extract type and parameters.

    Args:
        indicator_key: Indicator key string (e.g., RSI_14, MACD_12_26_9)

    Returns:
        tuple: (IndicatorType, list of parameters)

    Raises:
        ValueError: If indicator key format is invalid
    """
    parts = indicator_key.split("_")
    if not parts:
        raise ValueError(f"Invalid indicator key: {indicator_key}")

    type_str = parts[0].lower()
    try:
        indicator_type = IndicatorType(type_str)
    except ValueError:
        raise ValueError(f"Unknown indicator type: {type_str}")

    params = []
    for part in parts[1:]:
        try:
            params.append(int(part))
        except ValueError:
            raise ValueError(f"Invalid parameter in indicator key: {part}")

    return indicator_type, params