"""JWT token utilities."""

import jwt
from datetime import datetime, timedelta, timezone

from src.config import settings


def create_access_token(user_id: int) -> str:
    """Create JWT access token.

    Args:
        user_id: User ID

    Returns:
        str: JWT token
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"user_id": user_id, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)


def decode_token(token: str) -> dict:
    """Decode and verify JWT token.

    Args:
        token: JWT token string

    Returns:
        dict: Decoded token payload

    Raises:
        ExpiredSignatureError: Token has expired
        InvalidTokenError: Token is invalid
    """
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
