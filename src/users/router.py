from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.exceptions import BizException, ErrorCode
from src.response import Response
from src.users.oauth_client import OAuthProvider, oauth_client
from src.users.schema import (
    LoginRequest,
    LoginResponse,
    OAuthUrlResponse,
    UserRegisterRequest,
    UserResponse,
)
from src.users.service import UserService

router = APIRouter(prefix="/users", tags=["users"])

# ==================== Email/Password Auth ====================


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


@router.post(
    "/login",
    response_model=Response[LoginResponse],
    status_code=status.HTTP_200_OK,
    summary="用戶登入",
    description="使用信箱和密碼登入，返回 JWT 存取權杖",
)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> Response[LoginResponse]:
    """
    用戶登入

    Args:
        data: 登入請求資料
        db: 資料庫會話

    Returns:
        Response[LoginResponse]: JWT 存取權杖
    """
    result = await UserService.login(db, data)
    return Response(data=result)


# ==================== OAuth Auth ====================

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.get(
    "/{provider}",
    response_model=Response[OAuthUrlResponse],
    status_code=status.HTTP_200_OK,
    summary="OAuth 授權",
    description="產生 OAuth 授權 URL，前端跳轉至該 URL",
)
async def oauth_authorize(provider: str) -> Response[OAuthUrlResponse]:
    """
    產生 OAuth 授權 URL

    Args:
        provider: OAuth provider ("google" | "line")

    Returns:
        Response[OAuthUrlResponse]: 授權 URL 和 state token
    """
    if provider not in (OAuthProvider.GOOGLE, OAuthProvider.LINE):
        raise BizException(ErrorCode.PARAM_ERROR, f"不支援的登入方式: {provider}")

    state = UserService.generate_oauth_state(provider)
    url = oauth_client.get_authorization_url(provider, state)
    return Response(data=OAuthUrlResponse(authorization_url=url, state=state))


@auth_router.get(
    "/{provider}/callback",
    response_model=Response[LoginResponse],
    status_code=status.HTTP_200_OK,
    summary="OAuth 回調",
    description="處理 OAuth provider 回調，返回 JWT",
)
async def oauth_callback(
    provider: str,
    code: str = Query(..., description="授權碼"),
    state: str = Query(..., description="State token"),
    db: AsyncSession = Depends(get_db),
) -> Response[LoginResponse]:
    """
    OAuth 回調端點

    Args:
        provider: OAuth provider
        code: 授權碼
        state: State token
        db: 資料庫會話

    Returns:
        Response[LoginResponse]: JWT 存取權杖
    """
    result = await UserService.oauth_login(db, provider, code, state)
    return Response(data=result)
