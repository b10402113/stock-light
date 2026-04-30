from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.response import Response
from src.users.schema import UserRegisterRequest, UserResponse
from src.users.service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "/register",
    response_model=Response[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="用戶註冊",
    description="註冊新用戶帳號",
)
async def register(
    data: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> Response[UserResponse]:
    """
    註冊新用戶

    Args:
        data: 註冊請求資料
        db: 資料庫會話

    Returns:
        Response[UserResponse]: 註冊成功的用戶資訊
    """
    user = await UserService.register(db, data)
    return Response(data=user)
