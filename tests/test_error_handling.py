"""Test unified error response handling"""
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from fastapi.exceptions import RequestValidationError, HTTPException

from src.exceptions import (
    BadRequestError,
    UnauthorizedError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
    RateLimitError,
    InternalServerError,
)
from src.response import Response


# Create a test app with exception handlers
app = FastAPI()


@app.exception_handler(BadRequestError)
async def bad_request_handler(request: Request, exc: BadRequestError):
    return {
        "status_code": 400,
        "content": {"code": 400, "msg": exc.message, "data": exc.data},
    }


@app.exception_handler(UnauthorizedError)
async def unauthorized_handler(request: Request, exc: UnauthorizedError):
    return {
        "status_code": 401,
        "content": {"code": 401, "msg": exc.message, "data": exc.data},
    }


@app.exception_handler(ForbiddenError)
async def forbidden_handler(request: Request, exc: ForbiddenError):
    return {
        "status_code": 403,
        "content": {"code": 403, "msg": exc.message, "data": exc.data},
    }


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return {
        "status_code": 404,
        "content": {"code": 404, "msg": exc.message, "data": exc.data},
    }


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    return {
        "status_code": 422,
        "content": {"code": 422, "msg": exc.message, "data": exc.data},
    }


@app.exception_handler(RateLimitError)
async def rate_limit_handler(request: Request, exc: RateLimitError):
    return {
        "status_code": 429,
        "content": {"code": 429, "msg": exc.message, "data": exc.data},
    }


@app.exception_handler(InternalServerError)
async def internal_server_error_handler(request: Request, exc: InternalServerError):
    return {
        "status_code": 500,
        "content": {"code": 500, "msg": exc.message, "data": exc.data},
    }


# Test endpoints
@app.get("/bad-request")
async def bad_request_endpoint():
    raise BadRequestError("Custom bad request message", {"field": "value"})


@app.get("/unauthorized")
async def unauthorized_endpoint():
    raise UnauthorizedError()


@app.get("/forbidden")
async def forbidden_endpoint():
    raise ForbiddenError()


@app.get("/not-found")
async def not_found_endpoint():
    raise NotFoundError()


@app.get("/validation-error")
async def validation_error_endpoint():
    raise ValidationError("Validation failed", {"errors": ["field1", "field2"]})


@app.get("/rate-limit")
async def rate_limit_endpoint():
    raise RateLimitError()


@app.get("/internal-error")
async def internal_error_endpoint():
    raise InternalServerError()


client = TestClient(app)


class TestHTTPExceptions:
    """Test HTTP-level exception classes"""

    def test_bad_request_error(self):
        """Test 400 Bad Request"""
        with pytest.raises(BadRequestError) as exc_info:
            raise BadRequestError("Custom message")
        assert exc_info.value.status_code == 400
        assert exc_info.value.message == "Custom message"
        assert exc_info.value.data is None

    def test_bad_request_error_with_data(self):
        """Test 400 with custom data"""
        with pytest.raises(BadRequestError) as exc_info:
            raise BadRequestError("Error", {"key": "value"})
        assert exc_info.value.data == {"key": "value"}

    def test_unauthorized_error(self):
        """Test 401 Unauthorized"""
        with pytest.raises(UnauthorizedError) as exc_info:
            raise UnauthorizedError()
        assert exc_info.value.status_code == 401
        assert exc_info.value.message == "Not authenticated"

    def test_forbidden_error(self):
        """Test 403 Forbidden"""
        with pytest.raises(ForbiddenError) as exc_info:
            raise ForbiddenError("No access")
        assert exc_info.value.status_code == 403
        assert exc_info.value.message == "No access"

    def test_not_found_error(self):
        """Test 404 Not Found"""
        with pytest.raises(NotFoundError) as exc_info:
            raise NotFoundError("User not found")
        assert exc_info.value.status_code == 404
        assert exc_info.value.message == "User not found"

    def test_validation_error(self):
        """Test 422 Validation Error"""
        with pytest.raises(ValidationError) as exc_info:
            raise ValidationError("Invalid parameters", {"fields": ["email"]})
        assert exc_info.value.status_code == 422
        assert exc_info.value.data == {"fields": ["email"]}

    def test_rate_limit_error(self):
        """Test 429 Rate Limit"""
        with pytest.raises(RateLimitError) as exc_info:
            raise RateLimitError("Too many requests")
        assert exc_info.value.status_code == 429
        assert exc_info.value.message == "Too many requests"

    def test_internal_server_error(self):
        """Test 500 Internal Server Error"""
        with pytest.raises(InternalServerError) as exc_info:
            raise InternalServerError("Database connection failed")
        assert exc_info.value.status_code == 500
        assert exc_info.value.message == "Database connection failed"


class TestResponseFormat:
    """Test unified response format"""

    def test_response_format(self):
        """Test Response model structure"""
        response = Response(code=0, message="success", data={"key": "value"})
        assert response.code == 0
        assert response.message == "success"
        assert response.data == {"key": "value"}

    def test_response_with_none_data(self):
        """Test Response with None data"""
        response = Response(code=400, message="error", data=None)
        assert response.data is None

    def test_response_model_dump(self):
        """Test Response serialization"""
        response = Response(code=400, message="error", data=None)
        dumped = response.model_dump()
        assert dumped == {"code": 400, "message": "error", "data": None}