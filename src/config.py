from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """應用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    ENVIRONMENT: str = "local"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = True

    # Database - PostgreSQL
    DATABASE_URL: str
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_TIMEOUT: int = 5  # seconds

    # ARQ (Async Job Queue)
    ARQ_JOB_TIMEOUT: int = 300  # seconds
    ARQ_MAX_TRIES: int = 3
    STOCK_UPDATE_INTERVAL: int = 300  # seconds (5 minutes)
    STOCK_BATCH_SIZE: int = 50  # stocks per batch
    REDIS_PERSIST_INTERVAL: int = 900  # seconds (15 minutes)

    # Cron job schedules (minute sets)
    CRON_MASTER_MINUTES: str = "*"  # Every minute: "0-59" or "*"
    CRON_PERSIST_MINUTES: str = "0,15,30,45"  # Every 15 minutes

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # JWT
    JWT_SECRET: str
    JWT_ALG: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # LINE
    LINE_CHANNEL_ACCESS_TOKEN: str
    LINE_CHANNEL_SECRET: str

    # Fugo
    FUGO_API_KEY: str
    FUGO_BASE_URL: str = "https://api.fugle.tw/marketdata/v1.0/stock"
    FUGO_TIMEOUT: int = 10  # seconds
    FUGO_MAX_RETRIES: int = 3

    # Fugle API Rate Limiting
    FUGLE_RATE_LIMIT: int = 50  # requests per minute (time window)
    FUGLE_MAX_CONCURRENT_REQUESTS: int = 10  # max concurrent requests

    # Google OAuth
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/google/callback"

    # LINE Login (不同於 LINE Messaging API)
    LINE_LOGIN_CHANNEL_ID: str | None = None
    LINE_LOGIN_CHANNEL_SECRET: str | None = None
    LINE_LOGIN_REDIRECT_URI: str = "http://localhost:8000/auth/line/callback"

    # Logging
    LOG_LEVEL: str = "INFO"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    def parse_cron_minutes(self, minutes_str: str) -> set[int]:
        """Parse cron minutes string to set of integers.

        Args:
            minutes_str: String like "*", "0-59", "0,15,30,45", "*/5"

        Returns:
            Set of minute integers (0-59)
        """
        if minutes_str == "*":
            return set(range(60))

        # Handle range notation: "0-59"
        if "-" in minutes_str:
            start, end = minutes_str.split("-")
            return set(range(int(start), int(end) + 1))

        # Handle step notation: "*/5" (every 5 minutes)
        if minutes_str.startswith("*/"):
            step = int(minutes_str[2:])
            return set(range(0, 60, step))

        # Handle comma-separated: "0,15,30,45"
        return set(int(m.strip()) for m in minutes_str.split(","))


settings = Settings()
