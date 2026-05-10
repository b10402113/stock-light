"""Subscription business logic."""

from datetime import datetime, timedelta, timezone, time
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.redis_client import StockRedisClient
from src.plans import service as plans_service
from src.stocks import service as stocks_service
from src.stocks.model import Stock
from src.subscriptions.model import IndicatorSubscription, NotificationHistory, ScheduledReminder
from src.subscriptions.schema import (
    FrequencyType,
    IndicatorSubscriptionCreate,
    IndicatorSubscriptionResponse,
    IndicatorSubscriptionUpdate,
    ScheduledReminderCreate,
    ScheduledReminderResponse,
    ScheduledReminderUpdate,
    StockBrief,
)


class SubscriptionService:
    """指標訂閱業務邏輯"""

    @staticmethod
    async def enrich_subscription_with_stock(
        db: AsyncSession,
        subscription: IndicatorSubscription,
        redis_client: StockRedisClient | None = None,
    ) -> IndicatorSubscriptionResponse:
        """Enrich subscription with stock details.

        Args:
            db: 資料庫會話
            subscription: 訂閱實體
            redis_client: Redis client for price lookup

        Returns:
            IndicatorSubscriptionResponse: Response with stock details
        """
        stock = await stocks_service.StockService.get_by_id(db, subscription.stock_id)
        if not stock:
            raise ValueError(f"Stock not found: {subscription.stock_id}")

        # Get current price from Redis or database
        current_price: Optional[Decimal] = None
        if redis_client:
            cached_price = await redis_client.get_stock_price(subscription.stock_id)
            if cached_price is not None:
                current_price = Decimal(str(cached_price))

        if current_price is None:
            current_price = stock.current_price

        # Build stock brief
        stock_brief = StockBrief(
            id=stock.id,
            symbol=stock.symbol,
            name=stock.name,
            current_price=current_price,
            change_percent=None,  # Would need prev_close to calculate
        )

        return IndicatorSubscriptionResponse(
            id=subscription.id,
            stock=stock_brief,
            subscription_type="indicator",
            title=subscription.title,
            message=subscription.message,
            signal_type=subscription.signal_type,
            indicator_type=subscription.indicator_type,
            operator=subscription.operator,
            target_value=subscription.target_value,
            compound_condition=subscription.compound_condition,
            is_triggered=subscription.is_triggered,
            cooldown_end_at=subscription.cooldown_end_at,
            is_active=subscription.is_active,
            created_at=subscription.created_at,
            updated_at=subscription.updated_at,
        )

    @staticmethod
    async def get_by_id(
        db: AsyncSession, subscription_id: int
    ) -> IndicatorSubscription | None:
        """根據 ID 取得訂閱.

        Args:
            db: 資料庫會話
            subscription_id: 訂閱 ID

        Returns:
            IndicatorSubscription | None: 訂閱實體或 None
        """
        stmt = select(IndicatorSubscription).where(
            IndicatorSubscription.id == subscription_id,
            IndicatorSubscription.is_deleted.is_(False),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_subscriptions(
        db: AsyncSession,
        user_id: int,
        cursor: int | None = None,
        limit: int = 20,
    ) -> tuple[list[IndicatorSubscription], int | None]:
        """取得用戶所有訂閱 (Keyset Pagination).

        Args:
            db: 資料庫會話
            user_id: 用戶 ID
            cursor: 分頁游標 (上一頁最後一筆的 ID)
            limit: 每頁數量

        Returns:
            tuple[list[IndicatorSubscription], int | None]: 訂閱列表和下一頁游標
        """
        stmt = (
            select(IndicatorSubscription)
            .where(
                IndicatorSubscription.user_id == user_id,
                IndicatorSubscription.is_deleted.is_(False),
            )
            .order_by(IndicatorSubscription.id.asc())
            .limit(limit)
        )

        if cursor:
            stmt = stmt.where(IndicatorSubscription.id > cursor)

        result = await db.execute(stmt)
        subscriptions = list(result.scalars().all())

        next_cursor = None
        if len(subscriptions) == limit:
            next_cursor = subscriptions[-1].id

        return subscriptions, next_cursor

    @staticmethod
    async def check_quota(db: AsyncSession, user_id: int) -> tuple[bool, int, int]:
        """檢查用戶訂閱配額 (Plan-level quota).

        Args:
            db: 資料庫會話
            user_id: 用戶 ID

        Returns:
            tuple[bool, int, int]: (是否超額, 已使用數量, 配額上限)
        """
        # Get user quota from Plan level
        max_subscriptions, _ = await plans_service.PlanService.get_user_quota(db, user_id)

        # Count active subscriptions
        count = await db.scalar(
            select(func.count())
            .select_from(IndicatorSubscription)
            .where(
                IndicatorSubscription.user_id == user_id,
                IndicatorSubscription.is_deleted.is_(False),
                IndicatorSubscription.is_active.is_(True),
            )
        )
        used = count or 0

        # Level 4 (Admin) has unlimited quota (-1)
        if max_subscriptions == -1:
            return True, used, -1

        return used < max_subscriptions, used, max_subscriptions

    @staticmethod
    async def check_duplicate(
        db: AsyncSession,
        user_id: int,
        stock_id: int,
        indicator_type: str,
        operator: str,
        target_value: Decimal,
    ) -> bool:
        """檢查是否已存在相同訂閱.

        Args:
            db: 資料庫會話
            user_id: 用戶 ID
            stock_id: 股票 ID
            indicator_type: 指標類型
            operator: 運算子
            target_value: 目標值

        Returns:
            bool: 是否存在重複
        """
        exists = await db.scalar(
            select(func.count())
            .select_from(IndicatorSubscription)
            .where(
                IndicatorSubscription.user_id == user_id,
                IndicatorSubscription.stock_id == stock_id,
                IndicatorSubscription.indicator_type == indicator_type,
                IndicatorSubscription.operator == operator,
                IndicatorSubscription.target_value == target_value,
                IndicatorSubscription.is_deleted.is_(False),
            )
        )
        return (exists or 0) > 0

    @staticmethod
    async def create(
        db: AsyncSession,
        user_id: int,
        data: IndicatorSubscriptionCreate,
    ) -> IndicatorSubscription:
        """創建訂閱.

        Args:
            db: 資料庫會話
            user_id: 用戶 ID
            data: 訂閱創建數據

        Returns:
            IndicatorSubscription: 創建後的訂閱實體

        Raises:
            ValueError: 配額超額、股票不存在、或重複訂閱
        """
        # Check quota
        has_quota, used, quota = await SubscriptionService.check_quota(db, user_id)
        if not has_quota:
            raise ValueError(
                f"Subscription quota exceeded: used {used}/{quota}"
            )

        # Verify stock exists and is active
        stock = await db.get(Stock, data.stock_id)
        if not stock or stock.is_deleted or not stock.is_active:
            raise ValueError(f"Stock not found or inactive: {data.stock_id}")

        # Check for duplicate
        is_duplicate = await SubscriptionService.check_duplicate(
            db,
            user_id,
            data.stock_id,
            data.indicator_type.value,
            data.operator.value,
            data.target_value,
        )
        if is_duplicate:
            raise ValueError(
                f"Duplicate subscription already exists for this condition"
            )

        subscription = IndicatorSubscription(
            user_id=user_id,
            stock_id=data.stock_id,
            title=data.title,
            message=data.message,
            signal_type=data.signal_type.value,
            indicator_type=data.indicator_type.value,
            operator=data.operator.value,
            target_value=data.target_value,
            compound_condition=data.compound_condition,
        )
        db.add(subscription)
        await db.commit()
        await db.refresh(subscription)
        return subscription

    @staticmethod
    async def update(
        db: AsyncSession,
        subscription: IndicatorSubscription,
        data: IndicatorSubscriptionUpdate,
    ) -> IndicatorSubscription:
        """更新訂閱.

        Args:
            db: 資料庫會話
            subscription: 訂閱實體
            data: 訂閱更新數據

        Returns:
            IndicatorSubscription: 更新後的訂閱實體
        """
        update_data = data.model_dump(exclude_unset=True)

        # Convert enum values to strings if present
        if "signal_type" in update_data and update_data["signal_type"]:
            update_data["signal_type"] = update_data["signal_type"].value
        if "indicator_type" in update_data and update_data["indicator_type"]:
            update_data["indicator_type"] = update_data["indicator_type"].value
        if "operator" in update_data and update_data["operator"]:
            update_data["operator"] = update_data["operator"].value

        for key, value in update_data.items():
            setattr(subscription, key, value)

        await db.commit()
        await db.refresh(subscription)
        return subscription

    @staticmethod
    async def soft_delete(
        db: AsyncSession, subscription: IndicatorSubscription
    ) -> IndicatorSubscription:
        """軟刪除訂閱.

        Args:
            db: 資料庫會話
            subscription: 訂閱實體

        Returns:
            IndicatorSubscription: 軟刪除後的訂閱實體
        """
        subscription.soft_delete()
        await db.commit()
        await db.refresh(subscription)
        return subscription

    @staticmethod
    async def get_active_subscriptions_for_stock(
        db: AsyncSession, stock_id: int
    ) -> list[IndicatorSubscription]:
        """取得股票的所有活躍訂閱 (用於觸發檢查).

        Args:
            db: 資料庫會話
            stock_id: 股票 ID

        Returns:
            list[IndicatorSubscription]: 活躍訂閱列表
        """
        stmt = (
            select(IndicatorSubscription)
            .where(
                IndicatorSubscription.stock_id == stock_id,
                IndicatorSubscription.is_deleted.is_(False),
                IndicatorSubscription.is_active.is_(True),
            )
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())


class NotificationHistoryService:
    """通知歷史業務邏輯"""

    @staticmethod
    async def create_log(
        db: AsyncSession,
        user_id: int,
        indicator_subscription_id: int,
        triggered_value: Decimal,
    ) -> NotificationHistory:
        """創建通知歷史記錄.

        Args:
            db: 資料庫會話
            user_id: 用戶 ID
            indicator_subscription_id: 訂閱 ID
            triggered_value: 觸發值

        Returns:
            NotificationHistory: 創建後的通知歷史實體
        """
        log = NotificationHistory(
            user_id=user_id,
            indicator_subscription_id=indicator_subscription_id,
            triggered_value=triggered_value,
            send_status="pending",
            triggered_at=datetime.now(),
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)
        return log

    @staticmethod
    async def get_user_history(
        db: AsyncSession,
        user_id: int,
        cursor: datetime | None = None,
        limit: int = 20,
    ) -> tuple[list[NotificationHistory], datetime | None]:
        """取得用戶通知歷史 (Keyset Pagination on triggered_at DESC).

        Args:
            db: 資料庫會話
            user_id: 用戶 ID
            cursor: 分頁游標 (上一頁最後一筆的 triggered_at)
            limit: 每頁數量

        Returns:
            tuple[list[NotificationHistory], datetime | None]: 通知歷史列表和下一頁游標
        """
        stmt = (
            select(NotificationHistory)
            .where(
                NotificationHistory.user_id == user_id,
                NotificationHistory.is_deleted.is_(False),
            )
            .order_by(NotificationHistory.triggered_at.desc())
            .limit(limit)
        )

        if cursor:
            stmt = stmt.where(NotificationHistory.triggered_at < cursor)

        result = await db.execute(stmt)
        histories = list(result.scalars().all())

        next_cursor = None
        if len(histories) == limit:
            next_cursor = histories[-1].triggered_at

        return histories, next_cursor

    @staticmethod
    async def get_by_id(
        db: AsyncSession, history_id: int
    ) -> NotificationHistory | None:
        """根據 ID 取得通知歷史.

        Args:
            db: 資料庫會話
            history_id: 通知歷史 ID

        Returns:
            NotificationHistory | None: 通知歷史實體或 None
        """
        stmt = select(NotificationHistory).where(
            NotificationHistory.id == history_id,
            NotificationHistory.is_deleted.is_(False),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def update_status(
        db: AsyncSession,
        history: NotificationHistory,
        send_status: str,
        line_message_id: str | None = None,
    ) -> NotificationHistory:
        """更新通知發送狀態.

        Args:
            db: 資料庫會話
            history: 通知歷史實體
            send_status: 發送狀態 (sent, failed)
            line_message_id: LINE 訊息 ID

        Returns:
            NotificationHistory: 更新後的通知歷史實體
        """
        history.send_status = send_status
        if line_message_id:
            history.line_message_id = line_message_id
        await db.commit()
        await db.refresh(history)
        return history

    @staticmethod
    async def get_failed_notifications(
        db: AsyncSession, limit: int = 100
    ) -> list[NotificationHistory]:
        """取得發送失敗的通知 (用於重試機制).

        Args:
            db: 資料庫會話
            limit: 最大數量

        Returns:
            list[NotificationHistory]: 失敗通知列表
        """
        stmt = (
            select(NotificationHistory)
            .where(
                NotificationHistory.send_status == "failed",
                NotificationHistory.is_deleted.is_(False),
            )
            .order_by(NotificationHistory.triggered_at.asc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())


class ScheduledReminderService:
    """定期提醒業務邏輯"""

    @staticmethod
    def calculate_next_trigger_time(
        frequency_type: FrequencyType,
        reminder_time: str,
        day_of_week: int,
        day_of_month: int,
    ) -> datetime:
        """Calculate next trigger timestamp based on frequency settings.

        Args:
            frequency_type: Frequency type (daily/weekly/monthly)
            reminder_time: Time string in HH:MM format
            day_of_week: Day of week (0-6) for weekly
            day_of_month: Day of month (1-28) for monthly

        Returns:
            datetime: Next trigger timestamp
        """
        now = datetime.now(timezone.utc)
        time_parts = datetime.strptime(reminder_time, "%H:%M")
        target_time = time_parts.time()

        if frequency_type == FrequencyType.DAILY:
            # Next day at reminder_time
            next_date = now.date() + timedelta(days=1)
            return datetime.combine(next_date, target_time, tzinfo=timezone.utc)

        elif frequency_type == FrequencyType.WEEKLY:
            # Find next occurrence of day_of_week (0=Monday, 6=Sunday)
            days_ahead = (day_of_week - now.weekday()) % 7
            if days_ahead == 0:
                # If today is the target day, check if time has passed
                if now.time() >= target_time:
                    days_ahead = 7
            next_date = now.date() + timedelta(days=days_ahead)
            return datetime.combine(next_date, target_time, tzinfo=timezone.utc)

        elif frequency_type == FrequencyType.MONTHLY:
            # Find next occurrence of day_of_month
            next_year = now.year
            next_month = now.month

            if now.day >= day_of_month:
                next_month += 1
                if next_month > 12:
                    next_month = 1
                    next_year += 1

            try:
                next_date = now.replace(year=next_year, month=next_month, day=day_of_month).date()
            except ValueError:
                # Handle edge case for invalid dates (e.g., Feb 30)
                # Use last day of month
                if next_month == 12:
                    next_year += 1
                    next_month = 1
                else:
                    next_month += 1
                last_day = (now.replace(year=next_year, month=next_month, day=1) - timedelta(days=1)).day
                next_date = now.replace(year=next_year, month=next_month - 1, day=min(day_of_month, last_day)).date()

            return datetime.combine(next_date, target_time, tzinfo=timezone.utc)

        # Default to daily if unknown
        next_date = now.date() + timedelta(days=1)
        return datetime.combine(next_date, target_time, tzinfo=timezone.utc)

    @staticmethod
    async def enrich_reminder_with_stock(
        db: AsyncSession,
        reminder: ScheduledReminder,
        redis_client: StockRedisClient | None = None,
    ) -> ScheduledReminderResponse:
        """Enrich reminder with stock details.

        Args:
            db: 資料庫會話
            reminder: 提醒實體
            redis_client: Redis client for price lookup

        Returns:
            ScheduledReminderResponse: Response with stock details
        """
        stock = await stocks_service.StockService.get_by_id(db, reminder.stock_id)
        if not stock:
            raise ValueError(f"Stock not found: {reminder.stock_id}")

        current_price: Optional[Decimal] = None
        if redis_client:
            cached_price = await redis_client.get_stock_price(reminder.stock_id)
            if cached_price is not None:
                current_price = Decimal(str(cached_price))

        if current_price is None:
            current_price = stock.current_price

        stock_brief = StockBrief(
            id=stock.id,
            symbol=stock.symbol,
            name=stock.name,
            current_price=current_price,
            change_percent=None,
        )

        # Convert time to HH:MM string
        reminder_time_str = reminder.reminder_time.strftime("%H:%M")

        return ScheduledReminderResponse(
            id=reminder.id,
            stock=stock_brief,
            subscription_type="reminder",
            title=reminder.title,
            message=reminder.message,
            frequency_type=reminder.frequency_type,
            reminder_time=reminder_time_str,
            day_of_week=reminder.day_of_week,
            day_of_month=reminder.day_of_month,
            next_trigger_at=reminder.next_trigger_at,
            is_active=reminder.is_active,
            created_at=reminder.created_at,
            updated_at=reminder.updated_at,
        )

    @staticmethod
    async def get_by_id(db: AsyncSession, reminder_id: int) -> ScheduledReminder | None:
        """根據 ID 取得提醒.

        Args:
            db: 資料庫會話
            reminder_id: 提醒 ID

        Returns:
            ScheduledReminder | None: 提醒實體或 None
        """
        stmt = select(ScheduledReminder).where(
            ScheduledReminder.id == reminder_id,
            ScheduledReminder.is_deleted.is_(False),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_reminders(
        db: AsyncSession,
        user_id: int,
        cursor: int | None = None,
        limit: int = 20,
    ) -> tuple[list[ScheduledReminder], int | None]:
        """取得用戶所有定期提醒 (Keyset Pagination).

        Args:
            db: 資料庫會話
            user_id: 用戶 ID
            cursor: 分頁游標 (上一頁最後一筆的 ID)
            limit: 每頁數量

        Returns:
            tuple[list[ScheduledReminder], int | None]: 提醒列表和下一頁游標
        """
        stmt = (
            select(ScheduledReminder)
            .where(
                ScheduledReminder.user_id == user_id,
                ScheduledReminder.is_deleted.is_(False),
            )
            .order_by(ScheduledReminder.id.asc())
            .limit(limit)
        )

        if cursor:
            stmt = stmt.where(ScheduledReminder.id > cursor)

        result = await db.execute(stmt)
        reminders = list(result.scalars().all())

        next_cursor = None
        if len(reminders) == limit:
            next_cursor = reminders[-1].id

        return reminders, next_cursor

    @staticmethod
    async def check_quota(db: AsyncSession, user_id: int) -> tuple[bool, int, int]:
        """檢查用戶訂閱配額 (包含指標訂閱和定期提醒).

        Args:
            db: 資料庫會話
            user_id: 用戶 ID

        Returns:
            tuple[bool, int, int]: (是否超額, 已使用數量, 配額上限)
        """
        max_subscriptions, _ = await plans_service.PlanService.get_user_quota(db, user_id)

        # Count active indicator subscriptions
        indicator_count = await db.scalar(
            select(func.count())
            .select_from(IndicatorSubscription)
            .where(
                IndicatorSubscription.user_id == user_id,
                IndicatorSubscription.is_deleted.is_(False),
                IndicatorSubscription.is_active.is_(True),
            )
        )

        # Count active scheduled reminders
        reminder_count = await db.scalar(
            select(func.count())
            .select_from(ScheduledReminder)
            .where(
                ScheduledReminder.user_id == user_id,
                ScheduledReminder.is_deleted.is_(False),
                ScheduledReminder.is_active.is_(True),
            )
        )

        used = (indicator_count or 0) + (reminder_count or 0)

        if max_subscriptions == -1:
            return True, used, -1

        return used < max_subscriptions, used, max_subscriptions

    @staticmethod
    async def check_duplicate(
        db: AsyncSession,
        user_id: int,
        stock_id: int,
        frequency_type: str,
        reminder_time: str,
        day_of_week: int,
        day_of_month: int,
    ) -> bool:
        """檢查是否已存在相同提醒.

        Args:
            db: 資料庫會話
            user_id: 用戶 ID
            stock_id: 股票 ID
            frequency_type: 頻率類型
            reminder_time: 提醒時間 (HH:MM)
            day_of_week: 週幾 (週頻率)
            day_of_month: 月幾號 (月頻率)

        Returns:
            bool: 是否存在重複
        """
        time_obj = datetime.strptime(reminder_time, "%H:%M").time()

        exists = await db.scalar(
            select(func.count())
            .select_from(ScheduledReminder)
            .where(
                ScheduledReminder.user_id == user_id,
                ScheduledReminder.stock_id == stock_id,
                ScheduledReminder.frequency_type == frequency_type,
                ScheduledReminder.reminder_time == time_obj,
                ScheduledReminder.day_of_week == day_of_week,
                ScheduledReminder.day_of_month == day_of_month,
                ScheduledReminder.is_deleted.is_(False),
            )
        )
        return (exists or 0) > 0

    @staticmethod
    async def create(
        db: AsyncSession,
        user_id: int,
        data: ScheduledReminderCreate,
    ) -> ScheduledReminder:
        """創建定期提醒.

        Args:
            db: 資料庫會話
            user_id: 用戶 ID
            data: 提醒創建數據

        Returns:
            ScheduledReminder: 創建後的提醒實體

        Raises:
            ValueError: 配額超額、股票不存在、或重複提醒
        """
        has_quota, used, quota = await ScheduledReminderService.check_quota(db, user_id)
        if not has_quota:
            raise ValueError(f"Subscription quota exceeded: used {used}/{quota}")

        stock = await db.get(Stock, data.stock_id)
        if not stock or stock.is_deleted or not stock.is_active:
            raise ValueError(f"Stock not found or inactive: {data.stock_id}")

        is_duplicate = await ScheduledReminderService.check_duplicate(
            db,
            user_id,
            data.stock_id,
            data.frequency_type.value,
            data.reminder_time,
            data.day_of_week,
            data.day_of_month,
        )
        if is_duplicate:
            raise ValueError("Duplicate reminder already exists for this configuration")

        next_trigger = ScheduledReminderService.calculate_next_trigger_time(
            data.frequency_type,
            data.reminder_time,
            data.day_of_week,
            data.day_of_month,
        )

        time_obj = datetime.strptime(data.reminder_time, "%H:%M").time()

        reminder = ScheduledReminder(
            user_id=user_id,
            stock_id=data.stock_id,
            title=data.title,
            message=data.message,
            frequency_type=data.frequency_type.value,
            reminder_time=time_obj,
            day_of_week=data.day_of_week,
            day_of_month=data.day_of_month,
            next_trigger_at=next_trigger,
        )
        db.add(reminder)
        await db.commit()
        await db.refresh(reminder)
        return reminder

    @staticmethod
    async def update(
        db: AsyncSession,
        reminder: ScheduledReminder,
        data: ScheduledReminderUpdate,
    ) -> ScheduledReminder:
        """更新定期提醒.

        Args:
            db: 資料庫會話
            reminder: 提醒實體
            data: 提醒更新數據

        Returns:
            ScheduledReminder: 更新後的提醒實體
        """
        update_data = data.model_dump(exclude_unset=True)

        frequency_type = update_data.get("frequency_type", FrequencyType(reminder.frequency_type))
        if isinstance(frequency_type, FrequencyType):
            frequency_type = frequency_type.value

        reminder_time = update_data.get("reminder_time", reminder.reminder_time.strftime("%H:%M"))
        day_of_week = update_data.get("day_of_week", reminder.day_of_week)
        day_of_month = update_data.get("day_of_month", reminder.day_of_month)

        if "frequency_type" in update_data:
            update_data["frequency_type"] = frequency_type
        if "reminder_time" in update_data:
            update_data["reminder_time"] = datetime.strptime(reminder_time, "%H:%M").time()

        for key, value in update_data.items():
            setattr(reminder, key, value)

        # Recalculate next_trigger_at if frequency settings changed
        if any(k in update_data for k in ["frequency_type", "reminder_time", "day_of_week", "day_of_month"]):
            reminder.next_trigger_at = ScheduledReminderService.calculate_next_trigger_time(
                FrequencyType(frequency_type),
                reminder_time,
                day_of_week,
                day_of_month,
            )

        await db.commit()
        await db.refresh(reminder)
        return reminder

    @staticmethod
    async def soft_delete(db: AsyncSession, reminder: ScheduledReminder) -> ScheduledReminder:
        """軟刪除定期提醒.

        Args:
            db: 資料庫會話
            reminder: 提醒實體

        Returns:
            ScheduledReminder: 軟刪除後的提醒實體
        """
        reminder.soft_delete()
        await db.commit()
        await db.refresh(reminder)
        return reminder

    @staticmethod
    async def get_due_reminders(db: AsyncSession, now: datetime) -> list[ScheduledReminder]:
        """取得需要觸發的提醒.

        Args:
            db: 資料庫會話
            now: 當前時間

        Returns:
            list[ScheduledReminder]: 需觸發的提醒列表
        """
        stmt = (
            select(ScheduledReminder)
            .where(
                ScheduledReminder.next_trigger_at <= now,
                ScheduledReminder.is_active.is_(True),
                ScheduledReminder.is_deleted.is_(False),
            )
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def update_trigger_time(db: AsyncSession, reminder: ScheduledReminder) -> ScheduledReminder:
        """更新提醒的觸發時間.

        Args:
            db: 資料庫會話
            reminder: 提醒實體

        Returns:
            ScheduledReminder: 更新後的提醒實體
        """
        reminder.last_triggered_at = datetime.now(timezone.utc)
        reminder.next_trigger_at = ScheduledReminderService.calculate_next_trigger_time(
            FrequencyType(reminder.frequency_type),
            reminder.reminder_time.strftime("%H:%M"),
            reminder.day_of_week,
            reminder.day_of_month,
        )
        await db.commit()
        await db.refresh(reminder)
        return reminder