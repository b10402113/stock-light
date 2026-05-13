from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
import time

from src.config import settings
from src.database import get_db
from src.clients.redis_client import StockRedisClient
from src.exceptions import BizException
from src.response import Response
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
