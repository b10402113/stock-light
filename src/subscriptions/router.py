"""Subscription API endpoints."""

from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import CurrentUser
from src.clients.redis_client import StockRedisClient
from src.database import get_db
from src.response import Response
from src.subscriptions import service
from src.subscriptions.schema import (
    IndicatorConfigResponse,
    IndicatorSubscriptionCreate,
    IndicatorSubscriptionResponse,
    IndicatorSubscriptionUpdate,
    ScheduledReminderCreate,
    ScheduledReminderResponse,
    ScheduledReminderListResponse,
    ScheduledReminderUpdate,
    SubscriptionListResponse,
)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


# ============ Redis Client Dependency ============


async def get_redis_client() -> AsyncGenerator[StockRedisClient, None]:
    """Dependency that creates Redis client for each request.

    Creates a new Redis connection for each request to avoid event loop issues.
    For production, consider using app state to manage a shared pool.

    Yields:
        StockRedisClient: Redis client instance
    """
    client = StockRedisClient()
    try:
        yield client
    finally:
        await client.close()


# ============ Scheduled Reminder Endpoints (before /{subscription_id}) ============


@router.get(
    "/reminders",
    response_model=Response[ScheduledReminderListResponse],
    summary="取得用戶定期提醒列表",
    description="取得當前用戶的所有定期提醒（支援 Keyset 分頁）",
)
async def list_reminders(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    redis_client: StockRedisClient = Depends(get_redis_client),
    cursor: Optional[int] = Query(None, description="分頁游標（上一頁最後一筆的 ID）"),
    limit: int = Query(20, ge=1, le=100, description="每頁數量"),
) -> Response[ScheduledReminderListResponse]:
    """List all scheduled reminders for the current user."""
    reminders, next_cursor = await service.ScheduledReminderService.get_user_reminders(
        db, current_user.id, cursor, limit
    )

    response_data = [
        await service.ScheduledReminderService.enrich_reminder_with_stock(
            db, reminder, redis_client
        )
        for reminder in reminders
    ]

    return Response(
        data=ScheduledReminderListResponse(
            data=response_data,
            next_cursor=next_cursor,
            has_more=next_cursor is not None,
        )
    )


@router.post(
    "/reminders",
    response_model=Response[ScheduledReminderResponse],
    status_code=status.HTTP_201_CREATED,
    summary="創建定期提醒",
    description="為當前用戶創建新的定期提醒",
)
async def create_reminder(
    data: ScheduledReminderCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    redis_client: StockRedisClient = Depends(get_redis_client),
) -> Response[ScheduledReminderResponse]:
    """Create a new scheduled reminder."""
    try:
        reminder = await service.ScheduledReminderService.create(db, current_user.id, data)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Reminder already exists",
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

    response = await service.ScheduledReminderService.enrich_reminder_with_stock(
        db, reminder, redis_client
    )

    return Response(data=response)


@router.get(
    "/reminders/{reminder_id}",
    response_model=Response[ScheduledReminderResponse],
    summary="取得定期提醒詳細",
    description="取得特定定期提醒的詳細資訊",
)
async def get_reminder(
    reminder_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    redis_client: StockRedisClient = Depends(get_redis_client),
) -> Response[ScheduledReminderResponse]:
    """Get a single scheduled reminder."""
    reminder = await service.ScheduledReminderService.get_by_id(db, reminder_id)
    if not reminder or reminder.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reminder not found: {reminder_id}",
        )

    response = await service.ScheduledReminderService.enrich_reminder_with_stock(
        db, reminder, redis_client
    )

    return Response(data=response)


@router.patch(
    "/reminders/{reminder_id}",
    response_model=Response[ScheduledReminderResponse],
    summary="更新定期提醒",
    description="更新定期提醒的標題、訊息、頻率或時間設定",
)
async def update_reminder(
    reminder_id: int,
    data: ScheduledReminderUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    redis_client: StockRedisClient = Depends(get_redis_client),
) -> Response[ScheduledReminderResponse]:
    """Update a scheduled reminder."""
    reminder = await service.ScheduledReminderService.get_by_id(db, reminder_id)
    if not reminder or reminder.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reminder not found: {reminder_id}",
        )

    updated = await service.ScheduledReminderService.update(db, reminder, data)

    response = await service.ScheduledReminderService.enrich_reminder_with_stock(
        db, updated, redis_client
    )

    return Response(data=response)


@router.delete(
    "/reminders/{reminder_id}",
    response_model=Response[ScheduledReminderResponse],
    summary="刪除定期提醒",
    description="軟刪除定期提醒（標記為已刪除）",
)
async def delete_reminder(
    reminder_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    redis_client: StockRedisClient = Depends(get_redis_client),
) -> Response[ScheduledReminderResponse]:
    """Soft delete a scheduled reminder."""
    reminder = await service.ScheduledReminderService.get_by_id(db, reminder_id)
    if not reminder or reminder.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reminder not found: {reminder_id}",
        )

    deleted = await service.ScheduledReminderService.soft_delete(db, reminder)

    response = await service.ScheduledReminderService.enrich_reminder_with_stock(
        db, deleted, redis_client
    )

    return Response(data=response)


# ============ Indicator Subscription Endpoints ============


@router.get(
    "/indicators/config",
    response_model=Response[IndicatorConfigResponse],
    summary="取得指標配置",
    description="取得所有指標類型的欄位配置（時框、週期、運算子等）",
)
async def get_indicator_config() -> Response[IndicatorConfigResponse]:
    """Get indicator field configuration for frontend.

    Returns configuration for each indicator type including:
    - Required/optional fields
    - Default values
    - Valid ranges
    - Available operators
    """
    config = service.SubscriptionService.get_indicator_config()
    return Response(data=config)


@router.get(
    "",
    response_model=Response[SubscriptionListResponse],
    summary="取得用戶訂閱列表",
    description="取得當前用戶的所有指標訂閱（支援 Keyset 分頁）",
)
async def list_subscriptions(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    redis_client: StockRedisClient = Depends(get_redis_client),
    cursor: Optional[int] = Query(None, description="分頁游標（上一頁最後一筆的 ID）"),
    limit: int = Query(20, ge=1, le=100, description="每頁數量"),
) -> Response[SubscriptionListResponse]:
    """List all subscriptions for the current user."""
    subscriptions, next_cursor = await service.SubscriptionService.get_user_subscriptions(
        db, current_user.id, cursor, limit
    )

    response_data = [
        await service.SubscriptionService.enrich_subscription_with_stock(
            db, sub, redis_client
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
    redis_client: StockRedisClient = Depends(get_redis_client),
) -> Response[IndicatorSubscriptionResponse]:
    """Create a new subscription."""
    try:
        subscription = await service.SubscriptionService.create(
            db, current_user.id, data, redis_client
        )
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

    response = await service.SubscriptionService.enrich_subscription_with_stock(
        db, subscription, redis_client
    )

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
    redis_client: StockRedisClient = Depends(get_redis_client),
) -> Response[IndicatorSubscriptionResponse]:
    """Get a single subscription."""
    subscription = await service.SubscriptionService.get_by_id(db, subscription_id)
    if not subscription or subscription.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription not found: {subscription_id}",
        )

    response = await service.SubscriptionService.enrich_subscription_with_stock(
        db, subscription, redis_client
    )

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
    redis_client: StockRedisClient = Depends(get_redis_client),
) -> Response[IndicatorSubscriptionResponse]:
    """Update a subscription."""
    subscription = await service.SubscriptionService.get_by_id(db, subscription_id)
    if not subscription or subscription.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription not found: {subscription_id}",
        )

    updated = await service.SubscriptionService.update(db, subscription, data)

    response = await service.SubscriptionService.enrich_subscription_with_stock(
        db, updated, redis_client
    )

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
    redis_client: StockRedisClient = Depends(get_redis_client),
) -> Response[IndicatorSubscriptionResponse]:
    """Soft delete a subscription."""
    subscription = await service.SubscriptionService.get_by_id(db, subscription_id)
    if not subscription or subscription.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription not found: {subscription_id}",
        )

    deleted = await service.SubscriptionService.soft_delete(db, subscription)

    response = await service.SubscriptionService.enrich_subscription_with_stock(
        db, deleted, redis_client
    )

    return Response(data=response)