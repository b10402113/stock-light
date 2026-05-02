"""Notification history API endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import CurrentUser
from src.database import get_db
from src.response import Response
from src.subscriptions import service
from src.subscriptions.schema import (
    NotificationHistoryListResponse,
    NotificationHistoryResponse,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get(
    "/history",
    response_model=Response[NotificationHistoryListResponse],
    summary="取得通知歷史",
    description="取得當前用戶的通知歷史（支援 Keyset 分頁，依 triggered_at 降序排列）",
)
async def list_notification_history(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    cursor: Optional[datetime] = Query(None, description="分頁游標（上一頁最後一筆的 triggered_at）"),
    limit: int = Query(20, ge=1, le=100, description="每頁數量"),
) -> Response[NotificationHistoryListResponse]:
    """List notification history for the current user.

    Args:
        current_user: Current authenticated user
        db: Database session
        cursor: Pagination cursor (triggered_at of last item from previous page)
        limit: Items per page

    Returns:
        Response[NotificationHistoryListResponse]: List of notification history
    """
    histories, next_cursor = await service.NotificationHistoryService.get_user_history(
        db, current_user.id, cursor, limit
    )

    response_data = [
        NotificationHistoryResponse(
            id=h.id,
            user_id=h.user_id,
            indicator_subscription_id=h.indicator_subscription_id,
            triggered_value=h.triggered_value,
            send_status=h.send_status,
            line_message_id=h.line_message_id,
            triggered_at=h.triggered_at,
            created_at=h.created_at,
        )
        for h in histories
    ]

    return Response(
        data=NotificationHistoryListResponse(
            data=response_data,
            next_cursor=next_cursor,
            has_more=next_cursor is not None,
        )
    )


@router.get(
    "/history/{history_id}",
    response_model=Response[NotificationHistoryResponse],
    summary="取得通知詳細",
    description="取得特定通知歷史的詳細資訊",
)
async def get_notification_history(
    history_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> Response[NotificationHistoryResponse]:
    """Get a single notification history.

    Args:
        history_id: Notification history ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Response[NotificationHistoryResponse]: Notification history details

    Raises:
        HTTPException: 404 if notification history not found or not owned by user
    """
    history = await service.NotificationHistoryService.get_by_id(db, history_id)
    if not history or history.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification history not found: {history_id}",
        )

    return Response(
        data=NotificationHistoryResponse(
            id=history.id,
            user_id=history.user_id,
            indicator_subscription_id=history.indicator_subscription_id,
            triggered_value=history.triggered_value,
            send_status=history.send_status,
            line_message_id=history.line_message_id,
            triggered_at=history.triggered_at,
            created_at=history.created_at,
        )
    )
