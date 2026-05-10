"""Plan API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends

from src.database import get_db
from src.response import Response
from src.auth.dependencies import CurrentUser, CurrentUserId
from src.plans.model import LevelConfig, Plan
from src.plans.schema import (
    LevelConfigResponse,
    PlanCreate,
    PlanResponse,
    PlanUpdate,
    PlanWithLevelResponse,
)
from src.plans.service import PlanService
from src.exceptions import BizException, ErrorCode

from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get(
    "/levels",
    response_model=Response[list[LevelConfigResponse]],
    summary="取得所有等級配置",
    description="取得所有用戶等級的配置資訊（含價格與配額）",
)
async def get_level_configs(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response[list[LevelConfigResponse]]:
    """Get all level configurations.

    Args:
        db: Database session

    Returns:
        Response[list[LevelConfigResponse]]: Level config list
    """
    configs = await PlanService.get_level_configs(db)
    return Response(
        data=[LevelConfigResponse.model_validate(c) for c in configs]
    )


@router.get(
    "/me",
    response_model=Response[PlanWithLevelResponse],
    summary="取得當前用戶方案",
    description="取得當前登入用戶的活躍方案與等級配置",
)
async def get_my_plan(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response[PlanWithLevelResponse]:
    """Get current user's active plan.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        Response[PlanWithLevelResponse]: Current user's plan with level config
    """
    plan = await PlanService.get_user_active_plan(db, current_user.id)
    if not plan:
        raise BizException(ErrorCode.DATA_NOT_FOUND, "無活躍方案")

    level_config = await PlanService.get_level_config(db, plan.level)
    if not level_config:
        raise BizException(ErrorCode.DATA_NOT_FOUND, "等級配置不存在")

    response_data = PlanWithLevelResponse(
        id=plan.id,
        user_id=plan.user_id,
        level=plan.level,
        billing_cycle=plan.billing_cycle,
        price=float(plan.price),
        due_date=plan.due_date,
        is_active=plan.is_active,
        created_at=plan.created_at,
        level_config=LevelConfigResponse.model_validate(level_config),
    )
    return Response(data=response_data)


@router.post(
    "",
    response_model=Response[PlanResponse],
    summary="創建方案 (Admin)",
    description="為指定用戶創建新方案（需 Admin 權限）",
)
async def create_plan(
    data: PlanCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response[PlanResponse]:
    """Create plan for user (Admin only).

    Args:
        data: Plan creation data
        current_user: Current authenticated user (must be Admin)
        db: Database session

    Returns:
        Response[PlanResponse]: Created plan

    Raises:
        BizException: Unauthorized, level not found
    """
    try:
        plan = await PlanService.create_plan(db, data, current_user.id)
        return Response(data=PlanResponse.model_validate(plan))
    except ValueError as e:
        raise BizException(ErrorCode.PERMISSION_DENIED, str(e))


@router.put(
    "/{plan_id}",
    response_model=Response[PlanResponse],
    summary="更新方案 (Admin)",
    description="更新指定方案的資訊（需 Admin 權限）",
)
async def update_plan(
    plan_id: int,
    data: PlanUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response[PlanResponse]:
    """Update plan (Admin only).

    Args:
        plan_id: Plan ID
        data: Plan update data
        current_user: Current authenticated user (must be Admin)
        db: Database session

    Returns:
        Response[PlanResponse]: Updated plan

    Raises:
        BizException: Plan not found, unauthorized
    """
    plan = await PlanService.get_by_id(db, plan_id)
    if not plan:
        raise BizException(ErrorCode.DATA_NOT_FOUND, "方案不存在")

    try:
        updated_plan = await PlanService.update_plan(db, plan, data, current_user.id)
        return Response(data=PlanResponse.model_validate(updated_plan))
    except ValueError as e:
        raise BizException(ErrorCode.PERMISSION_DENIED, str(e))


@router.delete(
    "/{plan_id}",
    response_model=Response[PlanResponse],
    summary="取消方案 (Admin)",
    description="取消指定方案（需 Admin 權限）",
)
async def cancel_plan(
    plan_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response[PlanResponse]:
    """Cancel plan (Admin only).

    Args:
        plan_id: Plan ID
        current_user: Current authenticated user (must be Admin)
        db: Database session

    Returns:
        Response[PlanResponse]: Cancelled plan

    Raises:
        BizException: Plan not found, unauthorized
    """
    plan = await PlanService.get_by_id(db, plan_id)
    if not plan:
        raise BizException(ErrorCode.DATA_NOT_FOUND, "方案不存在")

    try:
        cancelled_plan = await PlanService.cancel_plan(db, plan, current_user.id)
        return Response(data=PlanResponse.model_validate(cancelled_plan))
    except ValueError as e:
        raise BizException(ErrorCode.PERMISSION_DENIED, str(e))