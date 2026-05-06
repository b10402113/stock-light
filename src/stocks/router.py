"""Stock API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.yfinance_client import YFinanceClient
from src.database import get_db
from src.response import Response
from src.stocks import service
from src.stocks.schema import StockCreate, StockListResponse, StockResponse, StockUpdate

router = APIRouter(prefix="/stocks", tags=["stocks"])


def get_yfinance_client() -> YFinanceClient:
    """Dependency to get YFinanceClient instance."""
    return YFinanceClient()


@router.get(
    "",
    response_model=Response[StockListResponse],
    summary="取得股票列表",
    description="取得所有股票列表（支援 Keyset 分頁）",
)
async def list_stocks(
    db: AsyncSession = Depends(get_db),
    is_active: bool | None = None,
    cursor: Optional[int] = Query(None, description="分頁游標（上一頁最後一筆的 ID）"),
    limit: int = Query(100, ge=1, le=100, description="每頁數量"),
) -> Response[StockListResponse]:
    """List all stocks.

    Args:
        db: Database session
        is_active: Filter by active status
        cursor: Pagination cursor
        limit: Items per page

    Returns:
        Response[StockListResponse]: List of stocks with pagination info
    """
    stocks, next_cursor = await service.StockService.get_stocks(
        db, is_active=is_active, cursor=cursor, limit=limit
    )
    return Response(
        data=StockListResponse(
            data=[StockResponse.model_validate(s) for s in stocks],
            next_cursor=next_cursor,
            has_more=next_cursor is not None,
        )
    )


@router.get(
    "/search",
    response_model=Response[StockListResponse],
    summary="搜索股票",
    description="根據股票代碼或名稱搜索股票（支援 Keyset 分頁）。先從資料庫搜尋，若無結果則從 YFinance API 搜尋並存入資料庫。",
)
async def search_stocks(
    q: str = Query(..., min_length=1, description="搜索關鍵字（匹配代碼或名稱）"),
    db: AsyncSession = Depends(get_db),
    yfinance_client: YFinanceClient = Depends(get_yfinance_client),
    cursor: Optional[int] = Query(None, description="分頁游標（上一頁最後一筆的 ID）"),
    limit: int = Query(100, ge=1, le=100, description="每頁數量"),
) -> Response[StockListResponse]:
    """Search stocks by symbol or name (database first, YFinance API fallback).

    Args:
        q: Search query (matches symbol or name)
        db: Database session
        yfinance_client: YFinance API client for fallback
        cursor: Pagination cursor
        limit: Items per page

    Returns:
        Response[StockListResponse]: List of matching stocks with pagination info
    """
    stocks, next_cursor = await service.StockService.search_stocks(
        db,
        query=q,
        cursor=cursor,
        limit=limit,
        yfinance_client=yfinance_client,
    )
    return Response(
        data=StockListResponse(
            data=[StockResponse.model_validate(s) for s in stocks],
            next_cursor=next_cursor,
            has_more=next_cursor is not None,
        )
    )


@router.get(
    "/{symbol}",
    response_model=Response[StockResponse],
    summary="取得單一股票",
    description="根據股票代碼取得股票資訊",
)
async def get_stock(
    symbol: str,
    db: AsyncSession = Depends(get_db),
) -> Response[StockResponse]:
    """Get a single stock by symbol.

    Args:
        symbol: Stock symbol (e.g., 2330.TW)
        db: Database session

    Returns:
        Response[StockResponse]: Stock info

    Raises:
        HTTPException: 404 if stock not found
    """
    stock = await service.StockService.get_by_symbol(db, symbol)
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock not found: {symbol}",
        )
    return Response(data=StockResponse.model_validate(stock))


@router.post(
    "",
    response_model=Response[StockResponse],
    status_code=status.HTTP_201_CREATED,
    summary="創建股票",
    description="創建新的股票資料",
)
async def create_stock(
    data: StockCreate,
    db: AsyncSession = Depends(get_db),
) -> Response[StockResponse]:
    """Create a new stock.

    Args:
        data: Stock creation data
        db: Database session

    Returns:
        Response[StockResponse]: Created stock

    Raises:
        HTTPException: 409 if stock already exists
    """
    try:
        stock = await service.StockService.create(db, data)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stock already exists: {data.symbol}",
        )
    return Response(data=StockResponse.model_validate(stock))


@router.patch(
    "/{symbol}",
    response_model=Response[StockResponse],
    summary="更新股票",
    description="更新股票資訊",
)
async def update_stock(
    symbol: str,
    data: StockUpdate,
    db: AsyncSession = Depends(get_db),
) -> Response[StockResponse]:
    """Update a stock.

    Args:
        symbol: Stock symbol
        data: Stock update data
        db: Database session

    Returns:
        Response[StockResponse]: Updated stock

    Raises:
        HTTPException: 404 if stock not found
    """
    stock = await service.StockService.get_by_symbol(db, symbol)
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock not found: {symbol}",
        )

    updated_stock = await service.StockService.update(db, stock, data)
    return Response(data=StockResponse.model_validate(updated_stock))


@router.delete(
    "/{symbol}",
    response_model=Response[StockResponse],
    summary="刪除股票",
    description="軟刪除股票（標記為已刪除）",
)
async def delete_stock(
    symbol: str,
    db: AsyncSession = Depends(get_db),
) -> Response[StockResponse]:
    """Soft delete a stock.

    Args:
        symbol: Stock symbol
        db: Database session

    Returns:
        Response[StockResponse]: Deleted stock

    Raises:
        HTTPException: 404 if stock not found
    """
    stock = await service.StockService.get_by_symbol(db, symbol)
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock not found: {symbol}",
        )

    deleted_stock = await service.StockService.soft_delete(db, stock)
    return Response(data=StockResponse.model_validate(deleted_stock))
