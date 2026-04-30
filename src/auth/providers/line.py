"""LINE OAuth provider."""

import httpx

from src.config import settings
from src.auth.providers.base import BaseOAuthClient


class LineOAuthProvider(BaseOAuthClient):
    """LINE OAuth 2.0 provider."""

    AUTH_URL = "https://access.line.me/oauth2/v2.1/authorize"
    TOKEN_URL = "https://api.line.me/oauth2/v2.1/token"
    PROFILE_URL = "https://api.line.me/v2/profile"

    def get_authorization_url(self, state: str) -> str:
        """Generate LINE OAuth authorization URL."""
        params = {
            "client_id": settings.LINE_LOGIN_CHANNEL_ID,
            "redirect_uri": settings.LINE_LOGIN_REDIRECT_URI,
            "response_type": "code",
            "scope": "profile openid email",
            "state": state,
            "bot_prompt": "normal",
        }
        return f"{self.AUTH_URL}?{httpx.QueryParams(params)}"

    async def exchange_token(self, code: str) -> dict:
        """Exchange authorization code for access token."""
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.LINE_LOGIN_REDIRECT_URI,
            "client_id": settings.LINE_LOGIN_CHANNEL_ID,
            "client_secret": settings.LINE_LOGIN_CHANNEL_SECRET,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.TOKEN_URL, data=data)
            resp.raise_for_status()
            return resp.json()

    async def get_user_info(self, access_token: str) -> dict:
        """Get user info from LINE."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                self.PROFILE_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "id": data["userId"],
                "email": None,  # LINE needs email scope and user consent
                "name": data["displayName"],
                "picture": data.get("pictureUrl"),
            }
