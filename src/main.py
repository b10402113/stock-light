from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.config import settings
from src.exceptions import BizException
from src.response import Response
from src.users.router import router as users_router

# 建立 FastAPI 應用
app = FastAPI(
    title="StockLight API",
    description="股票到價通知服務",
    version="1.0.0",
    debug=settings.DEBUG,
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


# 註冊路由
app.include_router(users_router)
