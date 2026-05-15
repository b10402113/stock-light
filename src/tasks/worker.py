"""ARQ worker for stock price updates.

Defines WorkerSettings with cron jobs and task functions for stock monitoring.
"""

from arq import cron

from src.config import settings
from src.tasks.config import redis_settings
from src.tasks.jobs import (
    calculate_stock_indicators,
    fetch_missing_daily_prices,
    persist_redis_to_database,
    prepare_subscription_data,
    process_scheduled_reminders,
    startup,
    shutdown,
    sync_active_stocks_to_redis,
    update_stock_prices_batch,
    update_stock_prices_master,
)


class DefaultWorkerSettings:
    """ARQ worker configuration for system tasks and scheduling.

    Run with: arq src.tasks.worker.DefaultWorkerSettings
    """

    functions = [
        update_stock_prices_master,
        persist_redis_to_database,
        sync_active_stocks_to_redis,
        process_scheduled_reminders,
        fetch_missing_daily_prices,
        prepare_subscription_data,
        calculate_stock_indicators,
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = redis_settings

    # Job configuration
    job_timeout = settings.ARQ_JOB_TIMEOUT
    max_tries = settings.ARQ_MAX_TRIES
    max_jobs = 10  # Higher concurrency for fast system tasks

    # Cron jobs - configurable via .env
    cron_jobs = [
        # Master task: schedule configurable via CRON_MASTER_MINUTES
        cron(
            update_stock_prices_master,
            minute=settings.parse_cron_minutes(settings.CRON_MASTER_MINUTES),
            run_at_startup=False,  # Don't run immediately on worker start
        ),
        # Persistence task: schedule configurable via CRON_PERSIST_MINUTES
        cron(
            persist_redis_to_database,
            minute=settings.parse_cron_minutes(settings.CRON_PERSIST_MINUTES),
            run_at_startup=False,
        ),
        # Sync active stocks to Redis: schedule configurable via CRON_SYNC_STOCKS_MINUTES
        cron(
            sync_active_stocks_to_redis,
            minute=settings.parse_cron_minutes(settings.CRON_SYNC_STOCKS_MINUTES),
            run_at_startup=False,
        ),
        # Process scheduled reminders: schedule configurable via CRON_REMINDER_MINUTES
        cron(
            process_scheduled_reminders,
            minute=settings.parse_cron_minutes(settings.CRON_REMINDER_MINUTES),
            run_at_startup=False,
        ),
        # Calculate stock indicators: schedule configurable via CRON_INDICATOR_MINUTES
        cron(
            calculate_stock_indicators,
            minute=settings.parse_cron_minutes(settings.CRON_INDICATOR_MINUTES),
            run_at_startup=False,
        ),
    ]


class ApiWorkerSettings:
    """ARQ worker configuration for API batch processing.

    Run with: arq src.tasks.worker.ApiWorkerSettings

    This worker only processes API calls with limited concurrency to avoid rate limiting.
    """

    queue_name = "api_queue"  # Only listen to API-specific queue

    functions = [
        update_stock_prices_batch,
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = redis_settings

    # Job configuration
    job_timeout = settings.ARQ_JOB_TIMEOUT
    max_tries = settings.ARQ_MAX_TRIES
    max_jobs = 1  # Critical: limit to 1 concurrent batch to avoid rate limits

    # No cron_jobs - this worker only receives dispatched jobs from master