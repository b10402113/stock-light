"""Stock API endpoints."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.response import Response
from src.stocks import service
from src.stocks.schema import (
    DailyPriceBulkCreate,
    DailyPriceListResponse,
    DailyPriceResponse,
    MovingAverageResponse,
    StockCreate,
    StockListResponse,
    StockResponse,
    StockUpdate,
)

router = APIRouter(prefix="/stocks", tags=["stocks"])


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
    description="根據股票代碼或名稱搜索股票（支援 Keyset 分頁）。從資料庫搜尋股票資料。",
)
async def search_stocks(
    q: str = Query(..., min_length=1, description="搜索關鍵字（匹配代碼或名稱）"),
    db: AsyncSession = Depends(get_db),
    cursor: Optional[int] = Query(None, description="分頁游標（上一頁最後一筆的 ID）"),
    limit: int = Query(100, ge=1, le=100, description="每頁數量"),
) -> Response[StockListResponse]:
    """Search stocks by symbol or name (database only).

    Args:
        q: Search query (matches symbol or name)
        db: Database session
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


# DailyPrice endpoints (using stock_id as path parameter)


@router.get(
    "/{stock_id}/prices",
    response_model=Response[DailyPriceListResponse],
    summary="取得股票歷史價格",
    description="取得股票的日K線歷史價格資料（支援 Keyset 分頁）",
)
async def list_daily_prices(
    stock_id: int,
    db: AsyncSession = Depends(get_db),
    start_date: Optional[date] = Query(None, description="開始日期（包含）"),
    end_date: Optional[date] = Query(None, description="結束日期（包含）"),
    cursor: Optional[date] = Query(None, description="分頁游標（上一頁最後一筆的日期）"),
    limit: int = Query(100, ge=1, le=100, description="每頁數量"),
) -> Response[DailyPriceListResponse]:
    """List daily prices for a stock.

    Args:
        stock_id: Stock ID
        db: Database session
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        cursor: Pagination cursor (date)
        limit: Items per page

    Returns:
        Response[DailyPriceListResponse]: List of daily prices with pagination info

    Raises:
        HTTPException: 404 if stock not found
    """
    stock = await service.StockService.get_by_id(db, stock_id)
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock not found: {stock_id}",
        )

    prices, next_cursor = await service.DailyPriceService.get_prices_by_range(
        db,
        stock_id=stock_id,
        start_date=start_date,
        end_date=end_date,
        cursor=cursor,
        limit=limit,
    )

    return Response(
        data=DailyPriceListResponse(
            data=[DailyPriceResponse.model_validate(p) for p in prices],
            next_cursor=next_cursor,
            has_more=next_cursor is not None,
        )
    )


@router.post(
    "/{stock_id}/prices",
    response_model=Response[dict],
    status_code=status.HTTP_201_CREATED,
    summary="批量插入股票歷史價格",
    description="批量插入股票的日K線歷史價格資料（管理員專用，使用 upsert 模式避免重複）",
)
async def bulk_insert_daily_prices(
    stock_id: int,
    data: DailyPriceBulkCreate,
    db: AsyncSession = Depends(get_db),
) -> Response[dict]:
    """Bulk insert daily prices for a stock.

    Args:
        stock_id: Stock ID
        data: Bulk price data
        db: Database session

    Returns:
        Response[dict]: Insert result with count

    Raises:
        HTTPException: 404 if stock not found
    """
    stock = await service.StockService.get_by_id(db, stock_id)
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock not found: {stock_id}",
        )

    count = await service.DailyPriceService.bulk_insert_prices(
        db,
        stock_id=stock_id,
        prices=data.prices,
    )

    return Response(
        data={
            "stock_id": stock_id,
            "count": count,
            "message": f"Successfully inserted/updated {count} price records",
        }
    )


@router.get(
    "/{stock_id}/ma/{period}",
    response_model=Response[MovingAverageResponse],
    summary="取得移動平均線",
    description=f"計算股票的移動平均線（例如 200MA）",
)
async def get_moving_average(
    stock_id: int,
    period: int,
    db: AsyncSession = Depends(get_db),
    as_of_date: Optional[date] = Query(None, description="計算日期（若未提供則使用最新日期）"),
) -> Response[MovingAverageResponse]:
    """Get moving average for a stock.

    Args:
        stock_id: Stock ID
        period: MA period (e.g., 200 for 200MA)
        db: Database session
        as_of_date: Calculation date

    Returns:
        Response[MovingAverageResponse]: MA calculation result

    Raises:
        HTTPException: 404 if stock not found
        HTTPException: 400 if period is invalid
    """
    if period < 1 or period > 500:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Period must be between 1 and 500",
        )

    stock = await service.StockService.get_by_id(db, stock_id)
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock not found: {stock_id}",
        )

    ma_value, data_points = await service.DailyPriceService.calculate_ma(
        db,
        stock_id=stock_id,
        period=period,
        as_of_date=as_of_date,
    )

    # Use as_of_date if provided, otherwise use today
    calculation_date = as_of_date or date.today()

    return Response(
        data=MovingAverageResponse(
            stock_id=stock_id,
            period=period,
            date=calculation_date,
            value=ma_value,
            data_points=data_points,
        )
    )
