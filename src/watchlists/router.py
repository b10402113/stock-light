"""Watchlist API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import CurrentUser
from src.database import get_db
from src.response import Response
from src.watchlists import service
from src.watchlists.schema import (
    WatchlistCreate,
    WatchlistDetailResponse,
    WatchlistResponse,
    WatchlistStockAdd,
    WatchlistStockResponse,
    WatchlistStockUpdate,
    WatchlistUpdate,
)

router = APIRouter(prefix="/watchlists", tags=["watchlists"])


@router.get(
    "",
    response_model=Response[list[WatchlistResponse]],
    summary="取得用戶自選股清單列表",
    description="取得當前用戶的所有自選股清單",
)
async def list_watchlists(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> Response[list[WatchlistResponse]]:
    """List all watchlists for the current user.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        Response[list[WatchlistResponse]]: List of watchlists
    """
    watchlists = await service.WatchlistService.get_user_watchlists(db, current_user.id)

    # Build response with stock counts
    response_data = []
    for wl in watchlists:
        stock_count = await service.WatchlistService.get_stock_count(db, wl.id)
        response_data.append(
            WatchlistResponse(
                id=wl.id,
                name=wl.name,
                description=wl.description,
                is_default=wl.is_default,
                stock_count=stock_count,
                created_at=wl.created_at,
            )
        )

    return Response(data=response_data)


@router.post(
    "",
    response_model=Response[WatchlistResponse],
    status_code=status.HTTP_201_CREATED,
    summary="創建自選股清單",
    description="為當前用戶創建新的自選股清單",
)
async def create_watchlist(
    data: WatchlistCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> Response[WatchlistResponse]:
    """Create a new watchlist.

    Args:
        data: Watchlist creation data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Response[WatchlistResponse]: Created watchlist
    """
    watchlist = await service.WatchlistService.create(db, current_user.id, data)
    return Response(
        data=WatchlistResponse(
            id=watchlist.id,
            name=watchlist.name,
            description=watchlist.description,
            is_default=watchlist.is_default,
            stock_count=0,
            created_at=watchlist.created_at,
        )
    )


@router.get(
    "/{watchlist_id}",
    response_model=Response[WatchlistDetailResponse],
    summary="取得自選股清單詳細",
    description="取得特定自選股清單及其股票列表",
)
async def get_watchlist(
    watchlist_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> Response[WatchlistDetailResponse]:
    """Get a single watchlist with its stocks.

    Args:
        watchlist_id: Watchlist ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Response[WatchlistDetailResponse]: Watchlist details

    Raises:
        HTTPException: 404 if watchlist not found or not owned by user
    """
    watchlist = await service.WatchlistService.get_by_id(db, watchlist_id)
    if not watchlist or watchlist.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Watchlist not found: {watchlist_id}",
        )

    # Build stock list
    stocks = []
    for ws in watchlist.watchlist_stocks:
        if not ws.is_deleted and ws.stock:
            stocks.append(
                WatchlistStockResponse(
                    watchlist_id=ws.watchlist_id,
                    stock_id=ws.stock_id,
                    symbol=ws.stock.symbol,
                    name=ws.stock.name,
                    current_price=ws.stock.current_price,
                    notes=ws.notes,
                    sort_order=ws.sort_order,
                    created_at=ws.created_at,
                )
            )

    # Sort by sort_order
    stocks.sort(key=lambda x: x.sort_order)

    return Response(
        data=WatchlistDetailResponse(
            id=watchlist.id,
            name=watchlist.name,
            description=watchlist.description,
            is_default=watchlist.is_default,
            stocks=stocks,
        )
    )


@router.patch(
    "/{watchlist_id}",
    response_model=Response[WatchlistResponse],
    summary="更新自選股清單",
    description="更新自選股清單名稱或描述",
)
async def update_watchlist(
    watchlist_id: int,
    data: WatchlistUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> Response[WatchlistResponse]:
    """Update a watchlist.

    Args:
        watchlist_id: Watchlist ID
        data: Watchlist update data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Response[WatchlistResponse]: Updated watchlist

    Raises:
        HTTPException: 404 if watchlist not found or not owned by user
    """
    watchlist = await service.WatchlistService.get_by_id(db, watchlist_id)
    if not watchlist or watchlist.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Watchlist not found: {watchlist_id}",
        )

    updated = await service.WatchlistService.update(db, watchlist, data)
    stock_count = await service.WatchlistService.get_stock_count(db, watchlist_id)

    return Response(
        data=WatchlistResponse(
            id=updated.id,
            name=updated.name,
            description=updated.description,
            is_default=updated.is_default,
            stock_count=stock_count,
            created_at=updated.created_at,
        )
    )


@router.delete(
    "/{watchlist_id}",
    response_model=Response[WatchlistResponse],
    summary="刪除自選股清單",
    description="軟刪除自選股清單（標記為已刪除）",
)
async def delete_watchlist(
    watchlist_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> Response[WatchlistResponse]:
    """Soft delete a watchlist.

    Args:
        watchlist_id: Watchlist ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Response[WatchlistResponse]: Deleted watchlist

    Raises:
        HTTPException: 404 if watchlist not found or not owned by user
    """
    watchlist = await service.WatchlistService.get_by_id(db, watchlist_id)
    if not watchlist or watchlist.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Watchlist not found: {watchlist_id}",
        )

    deleted = await service.WatchlistService.soft_delete(db, watchlist)
    stock_count = await service.WatchlistService.get_stock_count(db, watchlist_id)

    return Response(
        data=WatchlistResponse(
            id=deleted.id,
            name=deleted.name,
            description=deleted.description,
            is_default=deleted.is_default,
            stock_count=stock_count,
            created_at=deleted.created_at,
        )
    )


@router.post(
    "/{watchlist_id}/stocks",
    response_model=Response[WatchlistStockResponse],
    status_code=status.HTTP_201_CREATED,
    summary="添加股票到自選股清單",
    description="將股票添加到指定的自選股清單",
)
async def add_stock_to_watchlist(
    watchlist_id: int,
    data: WatchlistStockAdd,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> Response[WatchlistStockResponse]:
    """Add a stock to a watchlist.

    Args:
        watchlist_id: Watchlist ID
        data: Stock addition data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Response[WatchlistStockResponse]: Added stock

    Raises:
        HTTPException: 404 if watchlist not found or not owned by user
        HTTPException: 400 if stock not found or inactive
        HTTPException: 409 if stock already in watchlist
    """
    watchlist = await service.WatchlistService.get_by_id(db, watchlist_id)
    if not watchlist or watchlist.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Watchlist not found: {watchlist_id}",
        )

    # Check if stock already exists in watchlist
    existing = await service.WatchlistService.get_watchlist_stock(
        db, watchlist_id, data.stock_id
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stock already in watchlist: {data.stock_id}",
        )

    try:
        watchlist_stock = await service.WatchlistService.add_stock(db, watchlist_id, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Get stock info
    stock = watchlist_stock.stock

    return Response(
        data=WatchlistStockResponse(
            watchlist_id=watchlist_stock.watchlist_id,
            stock_id=watchlist_stock.stock_id,
            symbol=stock.symbol,
            name=stock.name,
            current_price=stock.current_price,
            notes=watchlist_stock.notes,
            sort_order=watchlist_stock.sort_order,
            created_at=watchlist_stock.created_at,
        )
    )


@router.delete(
    "/{watchlist_id}/stocks/{stock_id}",
    response_model=Response[WatchlistStockResponse],
    summary="從自選股清單移除股票",
    description="從自選股清單移除指定股票",
)
async def remove_stock_from_watchlist(
    watchlist_id: int,
    stock_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> Response[WatchlistStockResponse]:
    """Remove a stock from a watchlist.

    Args:
        watchlist_id: Watchlist ID
        stock_id: Stock ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Response[WatchlistStockResponse]: Removed stock

    Raises:
        HTTPException: 404 if watchlist or stock not found
    """
    watchlist = await service.WatchlistService.get_by_id(db, watchlist_id)
    if not watchlist or watchlist.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Watchlist not found: {watchlist_id}",
        )

    watchlist_stock = await service.WatchlistService.get_watchlist_stock(
        db, watchlist_id, stock_id
    )
    if not watchlist_stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock not found in watchlist: {stock_id}",
        )

    removed = await service.WatchlistService.remove_stock(db, watchlist_stock)
    stock = removed.stock

    return Response(
        data=WatchlistStockResponse(
            watchlist_id=removed.watchlist_id,
            stock_id=removed.stock_id,
            symbol=stock.symbol,
            name=stock.name,
            current_price=stock.current_price,
            notes=removed.notes,
            sort_order=removed.sort_order,
            created_at=removed.created_at,
        )
    )


@router.patch(
    "/{watchlist_id}/stocks/{stock_id}",
    response_model=Response[WatchlistStockResponse],
    summary="更新自選股清單內股票",
    description="更新自選股清單內股票的備註或排序",
)
async def update_stock_in_watchlist(
    watchlist_id: int,
    stock_id: int,
    data: WatchlistStockUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> Response[WatchlistStockResponse]:
    """Update a stock in a watchlist.

    Args:
        watchlist_id: Watchlist ID
        stock_id: Stock ID
        data: Stock update data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Response[WatchlistStockResponse]: Updated stock

    Raises:
        HTTPException: 404 if watchlist or stock not found
    """
    watchlist = await service.WatchlistService.get_by_id(db, watchlist_id)
    if not watchlist or watchlist.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Watchlist not found: {watchlist_id}",
        )

    watchlist_stock = await service.WatchlistService.get_watchlist_stock(
        db, watchlist_id, stock_id
    )
    if not watchlist_stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock not found in watchlist: {stock_id}",
        )

    updated = await service.WatchlistService.update_stock(db, watchlist_stock, data)
    stock = updated.stock

    return Response(
        data=WatchlistStockResponse(
            watchlist_id=updated.watchlist_id,
            stock_id=updated.stock_id,
            symbol=stock.symbol,
            name=stock.name,
            current_price=stock.current_price,
            notes=updated.notes,
            sort_order=updated.sort_order,
            created_at=updated.created_at,
        )
    )