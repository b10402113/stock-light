"""Subscription API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import CurrentUser
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
        Response[SubscriptionListResponse]: List of subscriptions
    """
    subscriptions, next_cursor = await service.SubscriptionService.get_user_subscriptions(
        db, current_user.id, cursor, limit
    )

    response_data = [
        IndicatorSubscriptionResponse(
            id=sub.id,
            user_id=sub.user_id,
            stock_id=sub.stock_id,
            indicator_type=sub.indicator_type,
            operator=sub.operator,
            target_value=sub.target_value,
            compound_condition=sub.compound_condition,
            is_triggered=sub.is_triggered,
            cooldown_end_at=sub.cooldown_end_at,
            is_active=sub.is_active,
            created_at=sub.created_at,
            updated_at=sub.updated_at,
        )
        for sub in subscriptions
    ]

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
        data: Subscription creation data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Response[IndicatorSubscriptionResponse]: Created subscription

    Raises:
        HTTPException: 400 if quota exceeded, stock not found, or duplicate
    """
    try:
        subscription = await service.SubscriptionService.create(db, current_user.id, data)
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

    return Response(
        data=IndicatorSubscriptionResponse(
            id=subscription.id,
            user_id=subscription.user_id,
            stock_id=subscription.stock_id,
            indicator_type=subscription.indicator_type,
            operator=subscription.operator,
            target_value=subscription.target_value,
            compound_condition=subscription.compound_condition,
            is_triggered=subscription.is_triggered,
            cooldown_end_at=subscription.cooldown_end_at,
            is_active=subscription.is_active,
            created_at=subscription.created_at,
            updated_at=subscription.updated_at,
        )
    )


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
        Response[IndicatorSubscriptionResponse]: Subscription details

    Raises:
        HTTPException: 404 if subscription not found or not owned by user
    """
    subscription = await service.SubscriptionService.get_by_id(db, subscription_id)
    if not subscription or subscription.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription not found: {subscription_id}",
        )

    return Response(
        data=IndicatorSubscriptionResponse(
            id=subscription.id,
            user_id=subscription.user_id,
            stock_id=subscription.stock_id,
            indicator_type=subscription.indicator_type,
            operator=subscription.operator,
            target_value=subscription.target_value,
            compound_condition=subscription.compound_condition,
            is_triggered=subscription.is_triggered,
            cooldown_end_at=subscription.cooldown_end_at,
            is_active=subscription.is_active,
            created_at=subscription.created_at,
            updated_at=subscription.updated_at,
        )
    )


@router.patch(
    "/{subscription_id}",
    response_model=Response[IndicatorSubscriptionResponse],
    summary="更新訂閱",
    description="更新訂閱的指標類型、運算子或目標值",
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
        Response[IndicatorSubscriptionResponse]: Updated subscription

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

    return Response(
        data=IndicatorSubscriptionResponse(
            id=updated.id,
            user_id=updated.user_id,
            stock_id=updated.stock_id,
            indicator_type=updated.indicator_type,
            operator=updated.operator,
            target_value=updated.target_value,
            compound_condition=updated.compound_condition,
            is_triggered=updated.is_triggered,
            cooldown_end_at=updated.cooldown_end_at,
            is_active=updated.is_active,
            created_at=updated.created_at,
            updated_at=updated.updated_at,
        )
    )


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
        Response[IndicatorSubscriptionResponse]: Deleted subscription

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

    return Response(
        data=IndicatorSubscriptionResponse(
            id=deleted.id,
            user_id=deleted.user_id,
            stock_id=deleted.stock_id,
            indicator_type=deleted.indicator_type,
            operator=deleted.operator,
            target_value=deleted.target_value,
            compound_condition=deleted.compound_condition,
            is_triggered=deleted.is_triggered,
            cooldown_end_at=deleted.cooldown_end_at,
            is_active=deleted.is_active,
            created_at=deleted.created_at,
            updated_at=deleted.updated_at,
        )
    )
