from typing import Generic, TypeVar, Optional

from pydantic import BaseModel

T = TypeVar("T")


class Response(BaseModel, Generic[T]):
    """統一 API 響應格式"""

    code: int = 0
    message: str = "success"
    data: Optional[T] = None


class PaginatedData(BaseModel, Generic[T]):
    """分頁數據格式"""

    items: list[T]
    total: int
    page: int
    page_size: int
    has_more: bool


class PaginatedResponse(BaseModel, Generic[T]):
    """統一分頁響應格式"""

    code: int = 0
    message: str = "success"
    data: Optional[PaginatedData[T]] = None
