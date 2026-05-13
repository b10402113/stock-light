"""Backtest API endpoints."""

from arq import create_pool
from arq.connections import ArqRedis
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.backtest.schema import BacktestTriggerRequest, BacktestTriggerResponse
from src.backtest.service import BacktestService
from src.database import get_db
from src.response import Response
from src.stocks.service import StockService
from src.tasks.config import redis_settings

router = APIRouter(prefix="/stocks", tags=["backtest"])


async def get_arq_redis() -> ArqRedis:
    """Get ARQ Redis connection pool."""
    return await create_pool(redis_settings)


@router.post(
    "/{stock_id}/backtest/trigger",
    response_model=Response[BacktestTriggerResponse],
    summary="觸發回測任務",
    description="檢查資料覆蓋率，若完整回傳 ready，若缺失建立 ARQ 任務回傳 pending",
)
async def trigger_backtest(
    stock_id: int,
    data: BacktestTriggerRequest,
    db: AsyncSession = Depends(get_db),
    redis: ArqRedis = Depends(get_arq_redis),
) -> JSONResponse:
    """Trigger backtest - check data coverage and create job if needed.

    Args:
        stock_id: Stock ID
        data: Backtest trigger request with date range
        db: Database session
        redis: ARQ Redis connection pool

    Returns:
        JSONResponse:
        - 200 OK with status="ready" if data complete
        - 202 Accepted with status="pending" and job_id if data missing

    Raises:
        HTTPException: 404 if stock not found
        HTTPException: 400 if date range invalid
    """
    # Validate stock exists
    stock = await StockService.get_by_id(db, stock_id)
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock not found: {stock_id}",
        )

    # Check data coverage
    actual_count, expected_count = await BacktestService.check_data_coverage(
        db,
        stock_id,
        data.start_date,
        data.end_date,
    )

    # Calculate coverage percentage
    coverage_pct = actual_count / expected_count if expected_count > 0 else 0.0

    # If 100% coverage, return ready status
    if coverage_pct >= 1.0:
        response = BacktestTriggerResponse(
            status="ready",
            data_count=actual_count,
            job_id=None,
            missing_ranges=None,
            message="Data ready for backtest",
        )
        return JSONResponse(
            content=Response(data=response).model_dump(),
            status_code=status.HTTP_200_OK,
        )

    # If incomplete, calculate missing ranges and create job
    existing_dates = await BacktestService.get_existing_dates(
        db,
        stock_id,
        data.start_date,
        data.end_date,
    )

    missing_ranges = BacktestService.calculate_missing_ranges(
        data.start_date,
        data.end_date,
        existing_dates,
    )

    # Convert to dict format for response
    missing_ranges_dict = [
        {"start_date": r[0].isoformat(), "end_date": r[1].isoformat()}
        for r in missing_ranges
    ]

    # Create ARQ job
    job_id = await BacktestService.trigger_fetch_job(
        redis,
        stock_id,
        missing_ranges,
    )

    response = BacktestTriggerResponse(
        status="pending",
        data_count=None,
        job_id=job_id,
        missing_ranges=missing_ranges_dict,
        message="Job created to fetch missing data",
    )

    return JSONResponse(
        content=Response(data=response).model_dump(),
        status_code=status.HTTP_202_ACCEPTED,
    )