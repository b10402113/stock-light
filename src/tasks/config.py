"""ARQ Redis connection configuration."""

from arq.connections import RedisSettings

from src.config import settings


def get_redis_settings() -> RedisSettings:
    """Parse REDIS_URL and create RedisSettings for ARQ."""
    # REDIS_URL format: redis://localhost:6379/0
    # Parse the URL to extract host, port, and database
    url = settings.REDIS_URL

    # Remove the redis:// prefix
    if url.startswith("redis://"):
        url = url[8:]

    # Split host:port/database
    parts = url.split("/")
    host_port = parts[0]
    database = int(parts[1]) if len(parts) > 1 else 0

    # Split host and port
    if ":" in host_port:
        host, port = host_port.split(":")
        port = int(port)
    else:
        host = host_port
        port = 6379

    return RedisSettings(
        host=host,
        port=port,
        database=database,
        conn_timeout=settings.REDIS_TIMEOUT,
    )


# ARQ Redis settings instance
redis_settings = get_redis_settings()