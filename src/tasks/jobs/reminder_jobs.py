"""Scheduled reminder processing jobs."""

import logging
from datetime import datetime, timezone

from sqlalchemy import select

from src.clients.redis_client import StockRedisClient
from src.database import SessionFactory
from src.subscriptions.model import ScheduledReminder
from src.subscriptions.service import ScheduledReminderService

logger = logging.getLogger(__name__)


async def process_scheduled_reminders(ctx: dict) -> None:
    """Process all scheduled reminders that are due.

    This job runs periodically to check and trigger scheduled reminders.
    For each due reminder:
    1. Fetch latest stock price from Redis
    2. Send LINE notification with stock info
    3. Update next_trigger_at for the next occurrence

    Args:
        ctx: ARQ context with redis pool
    """
    logger.info("Processing scheduled reminders")

    try:
        redis_pool = ctx["redis"]
        redis_client = StockRedisClient(pool=redis_pool)
        now = datetime.now(timezone.utc)

        async with SessionFactory() as session:
            # Get all due reminders
            reminders = await ScheduledReminderService.get_due_reminders(session, now)

            if not reminders:
                logger.debug("No scheduled reminders due")
                return

            logger.info(f"Found {len(reminders)} due scheduled reminders")

            for reminder in reminders:
                try:
                    # Get stock price from Redis
                    stock_price = await redis_client.get_stock_price(reminder.stock_id)

                    # Get stock info for notification
                    stock = reminder.stock
                    price_str = f"${stock_price:.2f}" if stock_price else "N/A"

                    # Build notification message
                    message = (
                        f"📊 {reminder.title}\n"
                        f"{stock.symbol} {stock.name}\n"
                        f"目前價格: {price_str}\n"
                        f"{reminder.message}"
                    )

                    # TODO: Send LINE notification via webhook
                    # For now, just log the notification
                    logger.info(
                        f"Reminder triggered: user_id={reminder.user_id}, "
                        f"stock={stock.symbol}, price={price_str}"
                    )

                    # Update next trigger time
                    await ScheduledReminderService.update_trigger_time(session, reminder)

                    logger.debug(
                        f"Updated reminder {reminder.id}, "
                        f"next_trigger_at={reminder.next_trigger_at}"
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to process reminder {reminder.id}: {e}"
                    )
                    # Continue processing other reminders

    except Exception as e:
        logger.error(f"Failed to process scheduled reminders: {e}")
        raise