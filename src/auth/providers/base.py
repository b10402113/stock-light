"""Base OAuth provider interface."""

from abc import ABC, abstractmethod
from typing import Protocol


class OAuthProvider(Protocol):
    """OAuth provider name."""

    GOOGLE = "google"
    LINE = "line"


class BaseOAuthClient(ABC):
    """Abstract base class for OAuth providers."""

    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        """Generate OAuth authorization URL."""
        pass

    @abstractmethod
    async def exchange_token(self, code: str) -> dict:
        """Exchange authorization code for access token."""
        pass

    @abstractmethod
    async def get_user_info(self, access_token: str) -> dict:
        """Get user info from OAuth provider."""
        pass
