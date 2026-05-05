"""Base HTTP client with retry and error handling."""

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from src.exceptions import BizException, ErrorCode


def get_retry_decorator(max_retries: int = 3):
    """Get retry decorator with configurable max attempts.

    Args:
        max_retries: Maximum number of retry attempts

    Returns:
        Retry decorator
    """
    return retry(
        retry=retry_if_exception_type(BizException),
        stop=stop_after_attempt(max_retries),
        wait=wait_exponential_jitter(initial=1, max=10),
        reraise=True,
    )


class BaseHTTPClient:
    """Base HTTP client with retry mechanism and error handling."""

    def __init__(
        self,
        timeout: int = 10,
        max_retries: int = 3,
    ):
        self.timeout = timeout
        self.max_retries = max_retries

    def _handle_error(
        self,
        response: httpx.Response,
        api_name: str,
        error_code: ErrorCode = ErrorCode.EXTERNAL_SERVICE_TIMEOUT,
    ) -> None:
        """Handle API error responses.

        Args:
            response: HTTP response
            api_name: Name of the API for error messages
            error_code: Error code to use (defaults to EXTERNAL_SERVICE_TIMEOUT)

        Raises:
            BizException: On HTTP errors
        """
        if response.status_code >= 500:
            raise BizException(
                error_code,
                f"{api_name} server error: {response.status_code}",
            )
        elif response.status_code >= 400:
            raise BizException(
                error_code,
                f"{api_name} client error: {response.status_code} - {response.text}",
            )