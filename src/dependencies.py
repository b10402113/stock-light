"""Global dependencies (re-exported from auth)."""

from src.auth.dependencies import get_current_user_id, get_current_user, CurrentUserId, CurrentUser

__all__ = [
    "get_current_user_id",
    "get_current_user",
    "CurrentUserId",
    "CurrentUser",
]
