"""User API endpoints (CRUD only)."""

from fastapi import APIRouter

from src.response import Response
from src.auth.dependencies import CurrentUser
from src.auth.schema import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=Response[UserResponse],
    summary="取得當前用戶資訊",
    description="取得當前登入用戶的個人資訊",
)
async def get_current_user_info(
    current_user: CurrentUser,
) -> Response[UserResponse]:
    """Get current user info.

    Args:
        current_user: Current authenticated user

    Returns:
        Response[UserResponse]: Current user info
    """
    return Response(data=UserResponse.model_validate(current_user))

