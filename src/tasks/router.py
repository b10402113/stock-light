"""Task status API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from arq import create_pool
from arq.connections import ArqRedis

from src.backtest.schema import TaskStatusResponse
from src.response import Response
from src.tasks.config import redis_settings

router = APIRouter(prefix="/tasks", tags=["tasks"])


async def get_arq_redis() -> ArqRedis:
    """Get ARQ Redis connection pool."""
    return await create_pool(redis_settings)


@router.get(
    "/{job_id}",
    response_model=Response[TaskStatusResponse],
    summary="查詢任務狀態",
    description="查詢 ARQ 任務執行狀態（pending/in_progress/completed/failed）",
)
async def get_task_status(
    job_id: str,
    redis: ArqRedis = Depends(get_arq_redis),
) -> Response[TaskStatusResponse]:
    """Get task status by job_id.

    Args:
        job_id: ARQ job ID
        redis: ARQ Redis connection pool

    Returns:
        Response[TaskStatusResponse]: Task status info

    Raises:
        HTTPException: 404 if task not found
    """
    job = await redis.get_job(job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task not found: {job_id}",
        )

    # ARQ job object has these fields
    # job.status: 'pending' | 'in_progress' | 'completed' | 'failed'
    # job.enqueue_time: when job was created
    # job.start_time: when job started execution
    # job.finish_time: when job finished
    # job.result: job return value
    # job.exc: exception if failed

    status_str = job.status if job.status else "pending"

    response = TaskStatusResponse(
        job_id=job_id,
        status=status_str,
        created_at=job.enqueue_time,
        started_at=job.start_time,
        finished_at=job.finish_time,
        result=job.result,
        error=str(job.exc) if job.exc else None,
    )

    return Response(data=response)