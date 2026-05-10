"""Subscription API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import CurrentUser
from src.clients.redis_client import StockRedisClient
from src.database import get_db
from src.response import Response
from src.subscriptions import service
from src.subscriptions.schema import (
    IndicatorSubscriptionCreate,
    IndicatorSubscriptionResponse,
    IndicatorSubscriptionUpdate,
    SubscriptionListResponse,
)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get(
    "",
    response_model=Response[SubscriptionListResponse],
    summary="取得用戶訂閱列表",
    description="取得當前用戶的所有指標訂閱（支援 Keyset 分頁）",
)
async def list_subscriptions(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    cursor: Optional[int] = Query(None, description="分頁游標（上一頁最後一筆的 ID）"),
    limit: int = Query(20, ge=1, le=100, description="每頁數量"),
) -> Response[SubscriptionListResponse]:
    """List all subscriptions for the current user.

    Args:
        current_user: Current authenticated user
        db: Database session
        cursor: Pagination cursor
        limit: Items per page

    Returns:
        Response[SubscriptionListResponse]: List of subscriptions with stock details
    """
    subscriptions, next_cursor = await service.SubscriptionService.get_user_subscriptions(
        db, current_user.id, cursor, limit
    )

    redis_client = StockRedisClient()
    response_data = [
        await service.SubscriptionService.enrich_subscription_with_stock(
            db, sub, redis_client
        )
        for sub in subscriptions
    ]
    await redis_client.close()

    return Response(
        data=SubscriptionListResponse(
            data=response_data,
            next_cursor=next_cursor,
            has_more=next_cursor is not None,
        )
    )


@router.post(
    "",
    response_model=Response[IndicatorSubscriptionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="創建指標訂閱",
    description="為當前用戶創建新的指標訂閱",
)
async def create_subscription(
    data: IndicatorSubscriptionCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> Response[IndicatorSubscriptionResponse]:
    """Create a new subscription.

    Args:
        data: Subscription creation data (includes title, message, signal_type)
        current_user: Current authenticated user
        db: Database session

    Returns:
        Response[IndicatorSubscriptionResponse]: Created subscription with stock details

    Raises:
        HTTPException: 403 if quota exceeded, 400 if stock not found or duplicate, 409 if conflict
    """
    try:
        subscription = await service.SubscriptionService.create(db, current_user.id, data)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Subscription already exists",
        )
    except ValueError as e:
        if "quota" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    redis_client = StockRedisClient()
    response = await service.SubscriptionService.enrich_subscription_with_stock(
        db, subscription, redis_client
    )
    await redis_client.close()

    return Response(data=response)


@router.get(
    "/{subscription_id}",
    response_model=Response[IndicatorSubscriptionResponse],
    summary="取得訂閱詳細",
    description="取得特定訂閱的詳細資訊",
)
async def get_subscription(
    subscription_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> Response[IndicatorSubscriptionResponse]:
    """Get a single subscription.

    Args:
        subscription_id: Subscription ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Response[IndicatorSubscriptionResponse]: Subscription details with stock info

    Raises:
        HTTPException: 404 if subscription not found or not owned by user
    """
    subscription = await service.SubscriptionService.get_by_id(db, subscription_id)
    if not subscription or subscription.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription not found: {subscription_id}",
        )

    redis_client = StockRedisClient()
    response = await service.SubscriptionService.enrich_subscription_with_stock(
        db, subscription, redis_client
    )
    await redis_client.close()

    return Response(data=response)


@router.patch(
    "/{subscription_id}",
    response_model=Response[IndicatorSubscriptionResponse],
    summary="更新訂閱",
    description="更新訂閱的標題、訊息、信號類型、指標類型、運算子或目標值",
)
async def update_subscription(
    subscription_id: int,
    data: IndicatorSubscriptionUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> Response[IndicatorSubscriptionResponse]:
    """Update a subscription.

    Args:
        subscription_id: Subscription ID
        data: Subscription update data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Response[IndicatorSubscriptionResponse]: Updated subscription with stock details

    Raises:
        HTTPException: 404 if subscription not found or not owned by user
    """
    subscription = await service.SubscriptionService.get_by_id(db, subscription_id)
    if not subscription or subscription.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription not found: {subscription_id}",
        )

    updated = await service.SubscriptionService.update(db, subscription, data)

    redis_client = StockRedisClient()
    response = await service.SubscriptionService.enrich_subscription_with_stock(
        db, updated, redis_client
    )
    await redis_client.close()

    return Response(data=response)


@router.delete(
    "/{subscription_id}",
    response_model=Response[IndicatorSubscriptionResponse],
    summary="刪除訂閱",
    description="軟刪除訂閱（標記為已刪除）",
)
async def delete_subscription(
    subscription_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> Response[IndicatorSubscriptionResponse]:
    """Soft delete a subscription.

    Args:
        subscription_id: Subscription ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Response[IndicatorSubscriptionResponse]: Deleted subscription with stock details

    Raises:
        HTTPException: 404 if subscription not found or not owned by user
    """
    subscription = await service.SubscriptionService.get_by_id(db, subscription_id)
    if not subscription or subscription.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription not found: {subscription_id}",
        )

    deleted = await service.SubscriptionService.soft_delete(db, subscription)

    redis_client = StockRedisClient()
    response = await service.SubscriptionService.enrich_subscription_with_stock(
        db, deleted, redis_client
    )
    await redis_client.close()

    return Response(data=response)