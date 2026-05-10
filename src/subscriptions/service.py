"""Subscription business logic."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.redis_client import StockRedisClient
from src.plans import service as plans_service
from src.stocks import service as stocks_service
from src.stocks.model import Stock
from src.subscriptions.model import IndicatorSubscription, NotificationHistory
from src.subscriptions.schema import (
    IndicatorSubscriptionCreate,
    IndicatorSubscriptionResponse,
    IndicatorSubscriptionUpdate,
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