"""Authentication API endpoints."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.exceptions import BizException, ErrorCode
from src.response import Response
from src.auth.providers.base import OAuthProvider
from src.auth.oauth_client import OAuthClientFactory
from src.auth.schema import (
    LoginRequest,
    LoginResponse,
    OAuthUrlResponse,
    UserRegisterRequest,
    UserResponse,
)
from src.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


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
    """Register a new user.

    Args:
        data: Registration request data
        db: Database session

    Returns:
        Response[UserResponse]: Registered user info
    """
    user = await AuthService.register(db, data)
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
    """User login with email and password.

    Args:
        data: Login request data
        db: Database session

    Returns:
        Response[LoginResponse]: JWT access token
    """
    result = await AuthService.login(db, data)
    return Response(data=result)


# ==================== OAuth Auth ====================


@router.get(
    "/{provider}",
    response_model=Response[OAuthUrlResponse],
    status_code=status.HTTP_200_OK,
    summary="OAuth 授權",
    description="產生 OAuth 授權 URL，前端跳轉至該 URL",
)
async def oauth_authorize(provider: str) -> Response[OAuthUrlResponse]:
    """Generate OAuth authorization URL.

    Args:
        provider: OAuth provider ("google" | "line")

    Returns:
        Response[OAuthUrlResponse]: Authorization URL and state token
    """
    if provider not in (OAuthProvider.GOOGLE, OAuthProvider.LINE):
        raise BizException(ErrorCode.PARAM_ERROR, f"不支援的登入方式: {provider}")

    state = AuthService.generate_oauth_state(provider)
    client = OAuthClientFactory.get_client(provider)
    url = client.get_authorization_url(state)
    return Response(data=OAuthUrlResponse(authorization_url=url, state=state))


@router.get(
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
    """OAuth callback endpoint.

    Args:
        provider: OAuth provider
        code: Authorization code
        state: State token
        db: Database session

    Returns:
        Response[LoginResponse]: JWT access token
    """
    result = await AuthService.oauth_login(db, provider, code, state)
    return Response(data=result)
