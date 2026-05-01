"""Stock API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.response import Response
from src.stocks import service
from src.stocks.schema import StockCreate, StockResponse, StockUpdate

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get(
    "",
    response_model=Response[list[StockResponse]],
    summary="取得股票列表",
    description="取得所有股票列表，可選擇只顯示活躍股票",
)
async def list_stocks(
    db: AsyncSession = Depends(get_db),
    is_active: bool | None = None,
    limit: int = 100,
    offset: int = 0,
) -> Response[list[StockResponse]]:
    """List all stocks.

    Args:
        db: Database session
        is_active: Filter by active status
        limit: Maximum number of results
        offset: Offset for pagination

    Returns:
        Response[list[StockResponse]]: List of stocks
    """
    stocks = await service.StockService.get_stocks(
        db, is_active=is_active, limit=limit, offset=offset
    )
    return Response(data=[StockResponse.model_validate(s) for s in stocks])


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
    existing = await service.StockService.get_by_symbol(db, data.symbol)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stock already exists: {data.symbol}",
        )

    stock = await service.StockService.create(db, data)
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
