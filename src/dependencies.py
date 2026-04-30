from typing import Annotated

import jwt
from fastapi import Depends, Header
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from src.config import settings
from src.database import AsyncSession, get_db
from src.exceptions import BizException, ErrorCode
from src.users.model import User
from src.users.service import UserService


async def get_current_user_id(
    authorization: str | None = Header(None),
) -> int:
    """
    從 JWT Token 中提取 user_id

    Args:
        authorization: Authorization header

    Returns:
        int: 用戶 ID

    Raises:
        BizException: 未授權、Token 過期或無效
    """
    if not authorization:
        raise BizException(ErrorCode.UNAUTHORIZED, "未提供認證資訊")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise BizException(ErrorCode.TOKEN_INVALID, "Token 格式錯誤")

    token = parts[1]

    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
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
    """
    根據 JWT Token 載入完整用戶實體

    Args:
        user_id: 從 Token 提取的用戶 ID
        db: 資料庫會話

    Returns:
        User: 用戶實體

    Raises:
        BizException: 用戶不存在或已停用
    """
    user = await UserService.get_by_id(db, user_id)
    if not user:
        raise BizException(ErrorCode.USER_NOT_FOUND, "用戶不存在")
    if not user.is_active:
        raise BizException(ErrorCode.USER_DISABLED, "用戶已停用")
    return user


# 依賴注入別名
CurrentUserId = Annotated[int, Depends(get_current_user_id)]
CurrentUser = Annotated[User, Depends(get_current_user)]
