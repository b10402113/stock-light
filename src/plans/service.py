"""Plan business logic."""

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.plans.model import LevelConfig, Plan
from src.plans.schema import BillingCycle, PlanCreate, PlanUpdate


class PlanService:
    """方案業務邏輯"""

    @staticmethod
    async def get_level_configs(db: AsyncSession) -> list[LevelConfig]:
        """取得所有等級配置.

        Args:
            db: 資料庫會話

        Returns:
            list[LevelConfig]: 等級配置列表
        """
        stmt = select(LevelConfig).order_by(LevelConfig.level.asc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_level_config(db: AsyncSession, level: int) -> LevelConfig | None:
        """取得特定等級配置.

        Args:
            db: 資料庫會話
            level: 等級 (1-4)

        Returns:
            LevelConfig | None: 等級配置或 None
        """
        return await db.get(LevelConfig, level)

    @staticmethod
    async def get_user_active_plan(db: AsyncSession, user_id: int) -> Plan | None:
        """取得用戶當前活躍方案.

        Args:
            db: 資料庫會話
            user_id: 用戶 ID

        Returns:
            Plan | None: 活躍方案或 None
        """
        stmt = (
            select(Plan)
            .where(
                Plan.user_id == user_id,
                Plan.is_active.is_(True),
                Plan.is_deleted.is_(False),
            )
            .options(selectinload(Plan.user))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_quota(db: AsyncSession, user_id: int) -> tuple[int, int]:
        """取得用戶訂閱配額.

        Args:
            db: 資料庫會話
            user_id: 用戶 ID

        Returns:
            tuple[int, int]: (最大訂閱數, 最大警報數)
        """
        plan = await PlanService.get_user_active_plan(db, user_id)
        if not plan:
            # Default to Level 1 if no active plan
            level_config = await PlanService.get_level_config(db, 1)
        else:
            level_config = await PlanService.get_level_config(db, plan.level)

        if not level_config:
            # Fallback to Level 1 config
            return 10, 10

        return level_config.max_subscriptions, level_config.max_alerts

    @staticmethod
    def calculate_due_date(
        billing_cycle: BillingCycle, start_date: datetime | None = None
    ) -> datetime:
        """計算到期日.

        Args:
            billing_cycle: 計費週期
            start_date: 起始日期 (默認為當前時間)

        Returns:
            datetime: 到期日
        """
        if start_date is None:
            start_date = datetime.now()

        if billing_cycle == BillingCycle.MONTHLY:
            return start_date + timedelta(days=30)
        else:  # YEARLY
            return start_date + timedelta(days=365)

    @staticmethod
    async def create_plan(
        db: AsyncSession, data: PlanCreate, admin_id: int
    ) -> Plan:
        """創建方案.

        Args:
            db: 資料庫會話
            data: 方案創建數據
            admin_id: 操作者 ID (需為 Admin)

        Returns:
            Plan: 創建後的方案實體

        Raises:
            ValueError: 等級不存在、非 Admin 操作
        """
        # Verify admin permission
        admin_plan = await PlanService.get_user_active_plan(db, admin_id)
        if not admin_plan or admin_plan.level != 4:
            raise ValueError("Only Admin can create plans for other users")

        # Verify level exists
        level_config = await PlanService.get_level_config(db, data.level)
        if not level_config:
            raise ValueError(f"Level config not found: {data.level}")

        # Deactivate existing active plan for user
        existing_plan = await PlanService.get_user_active_plan(db, data.user_id)
        if existing_plan:
            existing_plan.is_active = False

        # Calculate price and due_date
        price = (
            level_config.monthly_price
            if data.billing_cycle == BillingCycle.MONTHLY
            else level_config.yearly_price
        )
        due_date = PlanService.calculate_due_date(data.billing_cycle)

        # Admin level (4) has permanent access
        if data.level == 4:
            due_date = datetime.max

        plan = Plan(
            user_id=data.user_id,
            level=data.level,
            billing_cycle=data.billing_cycle.value,
            price=price,
            due_date=due_date,
            is_active=True,
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)
        return plan

    @staticmethod
    async def update_plan(
        db: AsyncSession, plan: Plan, data: PlanUpdate, admin_id: int
    ) -> Plan:
        """更新方案.

        Args:
            db: 資料庫會話
            plan: 方案實體
            data: 方案更新數據
            admin_id: 操作者 ID (需為 Admin)

        Returns:
            Plan: 更新後的方案實體

        Raises:
            ValueError: 非 Admin 操作
        """
        # Verify admin permission
        admin_plan = await PlanService.get_user_active_plan(db, admin_id)
        if not admin_plan or admin_plan.level != 4:
            raise ValueError("Only Admin can update plans")

        update_data = data.model_dump(exclude_unset=True)

        if "billing_cycle" in update_data and update_data["billing_cycle"]:
            update_data["billing_cycle"] = update_data["billing_cycle"].value

        for key, value in update_data.items():
            setattr(plan, key, value)

        await db.commit()
        await db.refresh(plan)
        return plan

    @staticmethod
    async def cancel_plan(db: AsyncSession, plan: Plan, admin_id: int) -> Plan:
        """取消方案.

        Args:
            db: 資料庫會話
            plan: 方案實體
            admin_id: 操作者 ID (需為 Admin)

        Returns:
            Plan: 取消後的方案實體

        Raises:
            ValueError: 非 Admin 操作
        """
        # Verify admin permission
        admin_plan = await PlanService.get_user_active_plan(db, admin_id)
        if not admin_plan or admin_plan.level != 4:
            raise ValueError("Only Admin can cancel plans")

        plan.is_active = False
        await db.commit()
        await db.refresh(plan)
        return plan

    @staticmethod
    async def get_by_id(db: AsyncSession, plan_id: int) -> Plan | None:
        """根據 ID 取得方案.

        Args:
            db: 資料庫會話
            plan_id: 方案 ID

        Returns:
            Plan | None: 方案實體或 None
        """
        stmt = select(Plan).where(
            Plan.id == plan_id,
            Plan.is_deleted.is_(False),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def check_expired_plans(db: AsyncSession) -> list[Plan]:
        """檢查過期方案.

        Args:
            db: 資料庫會話

        Returns:
            list[Plan]: 過期方案列表
        """
        now = datetime.now()
        stmt = (
            select(Plan)
            .where(
                Plan.is_active.is_(True),
                Plan.is_deleted.is_(False),
                Plan.due_date < now,
                Plan.level != 4,  # Admin 永不過期
            )
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())