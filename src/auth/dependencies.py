"""Authentication dependencies for FastAPI."""

from typing import Annotated

from fastapi import Depends, Header
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.exceptions import BizException, ErrorCode
from src.auth.token import decode_token
from src.users.model import User
from src.users.service import UserService


async def get_current_user_id(
    authorization: str | None = Header(None),
) -> int:
    """Extract user_id from JWT Token.

    Args:
        authorization: Authorization header

    Returns:
        int: User ID

    Raises:
        BizException: Unauthorized, token expired or invalid
    """
    if not authorization:
        raise BizException(ErrorCode.UNAUTHORIZED, "未提供認證資訊")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise BizException(ErrorCode.TOKEN_INVALID, "Token 格式錯誤")

    token = parts[1]

    try:
        payload = decode_token(token)
        user_id = payload.get("user_id")
        if not user_id:
            raise BizException(ErrorCode.TOKEN_INVALID, "Token 內容無效")
        return user_id
    except ExpiredSignatureError:
        raise BizException(ErrorCode.TOKEN_EXPIRED, "Token 已過期")
    except InvalidTokenError:
        raise BizException(ErrorCode.TOKEN_INVALID, "Token 無效")


async def get_current_user(
    user_id: Annotated[int, Depends(get_current_user_id)],
    db: AsyncSession = Depends(get_db),
) -> User:
    """Load full User entity based on JWT Token.

    Args:
        user_id: User ID extracted from Token
        db: Database session

    Returns:
        User: User entity

    Raises:
        BizException: User not found or disabled
    """
    user = await UserService.get_by_id(db, user_id)
    if not user:
        raise BizException(ErrorCode.USER_NOT_FOUND, "用戶不存在")
    if not user.is_active:
        raise BizException(ErrorCode.USER_DISABLED, "用戶已停用")
    return user


# Dependency injection aliases
CurrentUserId = Annotated[int, Depends(get_current_user_id)]
CurrentUser = Annotated[User, Depends(get_current_user)]
