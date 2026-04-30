import httpx

from src.config import settings


class OAuthProvider:
    GOOGLE = "google"
    LINE = "line"


class OAuthClient:
    """OAuth 2.0 客戶端"""

    GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

    LINE_AUTH_URL = "https://access.line.me/oauth2/v2.1/authorize"
    LINE_TOKEN_URL = "https://api.line.me/oauth2/v2.1/token"
    LINE_PROFILE_URL = "https://api.line.me/v2/profile"
    LINE_VERIFY_URL = "https://api.line.me/oauth2/v2.1/verify"

    def __init__(self):
        self.settings = settings

    def get_authorization_url(self, provider: str, state: str) -> str:
        """產生授權 URL"""
        if provider == OAuthProvider.GOOGLE:
            params = {
                "client_id": self.settings.GOOGLE_CLIENT_ID,
                "redirect_uri": self.settings.GOOGLE_REDIRECT_URI,
                "response_type": "code",
                "scope": "openid email profile",
                "state": state,
                "access_type": "offline",
                "prompt": "consent",
            }
            return f"{self.GOOGLE_AUTH_URL}?{httpx.QueryParams(params)}"

        elif provider == OAuthProvider.LINE:
            params = {
                "client_id": self.settings.LINE_LOGIN_CHANNEL_ID,
                "redirect_uri": self.settings.LINE_LOGIN_REDIRECT_URI,
                "response_type": "code",
                "scope": "profile openid email",
                "state": state,
                "bot_prompt": "normal",
            }
            return f"{self.LINE_AUTH_URL}?{httpx.QueryParams(params)}"

        raise ValueError(f"Unsupported provider: {provider}")

    async def exchange_token(self, provider: str, code: str) -> dict:
        """用授權碼換取 token"""
        if provider == OAuthProvider.GOOGLE:
            data = {
                "client_id": self.settings.GOOGLE_CLIENT_ID,
                "client_secret": self.settings.GOOGLE_CLIENT_SECRET,
                "code": code,
                "redirect_uri": self.settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            }
            async with httpx.AsyncClient() as client:
                resp = await client.post(self.GOOGLE_TOKEN_URL, data=data)
                resp.raise_for_status()
                return resp.json()

        elif provider == OAuthProvider.LINE:
            data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.settings.LINE_LOGIN_REDIRECT_URI,
                "client_id": self.settings.LINE_LOGIN_CHANNEL_ID,
                "client_secret": self.settings.LINE_LOGIN_CHANNEL_SECRET,
            }
            async with httpx.AsyncClient() as client:
                resp = await client.post(self.LINE_TOKEN_URL, data=data)
                resp.raise_for_status()
                return resp.json()

        raise ValueError(f"Unsupported provider: {provider}")

    async def get_user_info(self, provider: str, access_token: str) -> dict:
        """取得用戶資訊"""
        if provider == OAuthProvider.GOOGLE:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    self.GOOGLE_USERINFO_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                resp.raise_for_status()
                data = resp.json()
                return {
                    "id": data["id"],
                    "email": data.get("email"),
                    "name": data.get("name"),
                    "picture": data.get("picture"),
                }

        elif provider == OAuthProvider.LINE:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    self.LINE_PROFILE_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                resp.raise_for_status()
                data = resp.json()
                return {
                    "id": data["userId"],
                    "name": data["displayName"],
                    "picture": data.get("pictureUrl"),
                    "email": None,  # LINE 需要 email scope 且用戶同意
                }

        raise ValueError(f"Unsupported provider: {provider}")


oauth_client = OAuthClient()
