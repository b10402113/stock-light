from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from sqlalchemy import text
import time
import logging

from src.config import settings
from src.database import get_db
from src.clients.redis_client import StockRedisClient
from src.exceptions import BizException, BadRequestError, UnauthorizedError, ForbiddenError, NotFoundError, ValidationError, RateLimitError, InternalServerError
from src.response import Response

logger = logging.getLogger(__name__)
from src.users.router import router as users_router
from src.auth.router import router as auth_router
from src.stocks.router import router as stocks_router
from src.watchlists.router import router as watchlists_router
from src.subscriptions.router import router as subscriptions_router
from src.notifications.router import router as notifications_router
from src.plans.router import router as plans_router
from src.backtest import backtest_router
from src.tasks.router import router as tasks_router

# Track application start time for uptime calculation
APP_START_TIME = time.time()

# 建立 FastAPI 應用
app = FastAPI(
    title="StockLight API",
    description="股票到價通知服務",
    version="1.0.0",
    debug=settings.DEBUG,
)

# CORS middleware - MUST be added after app creation, before routers
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
)


# 全局異常處理 - BizException
@app.exception_handler(BizException)
async def biz_exception_handler(request: Request, exc: BizException):
    """處理業務異常"""
    return JSONResponse(
        status_code=400,
        content=Response(
            code=exc.error_code, message=exc.message, data=None
        ).model_dump(),
    )


# HTTP-level exception handlers
@app.exception_handler(BadRequestError)
async def bad_request_handler(request: Request, exc: BadRequestError):
    """處理 400 Bad Request"""
    return JSONResponse(
        status_code=400,
        content={"code": 400, "msg": exc.message, "data": exc.data},
    )


@app.exception_handler(UnauthorizedError)
async def unauthorized_handler(request: Request, exc: UnauthorizedError):
    """處理 401 Unauthorized"""
    return JSONResponse(
        status_code=401,
        content={"code": 401, "msg": exc.message, "data": exc.data},
    )


@app.exception_handler(ForbiddenError)
async def forbidden_handler(request: Request, exc: ForbiddenError):
    """處理 403 Forbidden"""
    return JSONResponse(
        status_code=403,
        content={"code": 403, "msg": exc.message, "data": exc.data},
    )


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    """處理 404 Not Found"""
    return JSONResponse(
        status_code=404,
        content={"code": 404, "msg": exc.message, "data": exc.data},
    )


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    """處理 422 Unprocessable Entity"""
    return JSONResponse(
        status_code=422,
        content={"code": 422, "msg": exc.message, "data": exc.data},
    )


@app.exception_handler(RateLimitError)
async def rate_limit_handler(request: Request, exc: RateLimitError):
    """處理 429 Too Many Requests"""
    return JSONResponse(
        status_code=429,
        content={"code": 429, "msg": exc.message, "data": exc.data},
    )


@app.exception_handler(InternalServerError)
async def internal_server_error_handler(request: Request, exc: InternalServerError):
    """處理 500 Internal Server Error"""
    return JSONResponse(
        status_code=500,
        content={"code": 500, "msg": exc.message, "data": exc.data},
    )


# FastAPI built-in exception handlers
@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(request: Request, exc: RequestValidationError):
    """處理 Pydantic 验证错误"""
    errors = exc.errors()
    error_messages = [f"{err.get('loc', [])}: {err.get('msg', '')}" for err in errors]
    message = "; ".join(error_messages) if error_messages else "Parameter validation failed"

    return JSONResponse(
        status_code=422,
        content={"code": 422, "msg": message, "data": {"errors": errors}},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """處理 FastAPI HTTPException"""
    # Map HTTP status codes to our unified format
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "msg": exc.detail, "data": None},
    )


# Global exception handler for unhandled exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """處理所有未捕获的异常"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={"code": 500, "msg": "Server internal error", "data": None},
    )


# Health check endpoint (public, no auth required)
@app.get("/health", tags=["Health"])
async def health_check():
    """Check database and Redis connection health.

    Returns:
        HTTP 200 with detailed health status if healthy/warn
        HTTP 503 with detailed health status if fail

    Response format follows standard health check schema:
    - status: "pass", "warn", or "fail"
    - version: service version
    - description: service description
    - uptime: seconds since app started
    - details: per-component status with componentType
    """
    details = {}
    overall_status = "pass"

    # Check database
    try:
        async for db in get_db():
            await db.execute(text("SELECT 1"))
            details["database"] = {
                "status": "pass",
                "componentType": "datastore"
            }
            break
    except Exception as exc:
        details["database"] = {
            "status": "fail",
            "componentType": "datastore",
            "message": str(exc)
        }
        overall_status = "fail"

    # Check Redis
    try:
        redis_client = StockRedisClient()
        await redis_client.ping()
        details["redis"] = {
            "status": "pass",
            "componentType": "cache"
        }
        await redis_client.close()
    except BizException as exc:
        details["redis"] = {
            "status": "fail",
            "componentType": "cache",
            "message": exc.message
        }
        overall_status = "fail"
    except Exception as exc:
        details["redis"] = {
            "status": "fail",
            "componentType": "cache",
            "message": str(exc)
        }
        overall_status = "fail"

    # Calculate uptime
    uptime = int(time.time() - APP_START_TIME)

    # Build response
    response = {
        "status": overall_status,
        "version": "1.0.0",
        "description": "StockLight API",
        "uptime": uptime,
        "details": details
    }

    # Return HTTP 503 if status is "fail", 200 otherwise
    status_code = 503 if overall_status == "fail" else 200

    return JSONResponse(
        status_code=status_code,
        content=response,
    )


# 註冊路由
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(stocks_router)
app.include_router(watchlists_router)
app.include_router(subscriptions_router)
app.include_router(notifications_router)
app.include_router(plans_router)
app.include_router(backtest_router)
app.include_router(tasks_router)
