"""Backtest schemas."""

import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class BacktestTriggerRequest(BaseModel):
    """回測觸發請求"""

    start_date: datetime.date = Field(..., description="開始日期")
    end_date: datetime.date = Field(..., description="結束日期")

    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, v: datetime.date, info: Any) -> datetime.date:
        """驗證結束日期 >= 開始日期"""
        values = info.data
        if "start_date" in values and v < values["start_date"]:
            raise ValueError("end_date must be >= start_date")
        return v


class BacktestTriggerResponse(BaseModel):
    """回測觸發響應"""

    status: str = Field(..., description="狀態: ready | pending")
    data_count: int | None = Field(None, description="資料完整時的數量")
    job_id: str | None = Field(None, description="任務 ID（資料缺失時）")
    missing_ranges: list[dict[str, str]] | None = Field(
        None, description="缺失日期區間（資料缺失時）"
    )
    message: str = Field(..., description="描述訊息")


class TaskStatusResponse(BaseModel):
    """任務狀態響應"""

    job_id: str = Field(..., description="任務 ID")
    status: str = Field(..., description="狀態: pending | in_progress | completed | failed")
    created_at: datetime.datetime | None = Field(None, description="建立時間")
    started_at: datetime.datetime | None = Field(None, description="開始時間")
    finished_at: datetime.datetime | None = Field(None, description="完成時間")
    result: dict[str, Any] | None = Field(None, description="任務結果")
    error: str | None = Field(None, description="錯誤訊息")


class DateRange(BaseModel):
    """日期區間"""

    start_date: datetime.date = Field(..., description="開始日期")
    end_date: datetime.date = Field(..., description="結束日期")