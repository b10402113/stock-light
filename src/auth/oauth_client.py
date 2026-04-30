"""OAuth client factory."""

from src.auth.providers.base import OAuthProvider, BaseOAuthClient
from src.auth.providers.google import GoogleOAuthProvider
from src.auth.providers.line import LineOAuthProvider


class OAuthClientFactory:
    """Factory for creating OAuth provider clients."""

    _clients = {
        OAuthProvider.GOOGLE: GoogleOAuthProvider,
        OAuthProvider.LINE: LineOAuthProvider,
    }

    @classmethod
    def get_client(cls, provider: str) -> BaseOAuthClient:
        """Get OAuth client for the given provider."""
        client_class = cls._clients.get(provider)
        if not client_class:
            raise ValueError(f"Unsupported provider: {provider}")
        return client_class()


oauth_client = OAuthClientFactory
