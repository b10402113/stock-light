"""Jobs package for ARQ worker tasks."""

from src.tasks.jobs.backtest_jobs import fetch_missing_daily_prices
from src.tasks.jobs.indicator_jobs import update_indicator
from src.tasks.jobs.lifecycle_jobs import startup, shutdown
from src.tasks.jobs.price_update_jobs import update_stock_prices_master, update_stock_prices_batch
from src.tasks.jobs.reminder_jobs import process_scheduled_reminders
from src.tasks.jobs.subscription_jobs import prepare_subscription_data, check_indicator_subscriptions
from src.tasks.jobs.sync_jobs import persist_redis_to_database, sync_active_stocks_to_redis

__all__ = [
    "startup",
    "shutdown",
    "update_stock_prices_master",
    "update_stock_prices_batch",
    "persist_redis_to_database",
    "sync_active_stocks_to_redis",
    "process_scheduled_reminders",
    "fetch_missing_daily_prices",
    "prepare_subscription_data",
    "update_indicator",
    "check_indicator_subscriptions",
]