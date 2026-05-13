"""Backtest service - data coverage check and job triggering."""

import datetime
import logging

from arq import create_pool
from arq.connections import ArqRedis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.stocks.model import DailyPrice, Stock
from src.stocks.service import StockService

logger = logging.getLogger(__name__)


class BacktestService:
    """回測服務 - 資料覆蓋率檢查與任務觸發"""

    @staticmethod
    async def check_data_coverage(
        db: AsyncSession,
        stock_id: int,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> tuple[int, int]:
        """檢查日期區間內的資料覆蓋率.

        Args:
            db: 資料庫會話
            stock_id: 股票 ID
            start_date: 開始日期
            end_date: 束日期

        Returns:
            tuple[int, int]: (實際資料數量, 預期交易日數量)
        """
        # 查詢實際存在的資料數量
        stmt = select(func.count()).select_from(DailyPrice).where(
            DailyPrice.stock_id == stock_id,
            DailyPrice.date >= start_date,
            DailyPrice.date <= end_date,
            DailyPrice.is_deleted.is_(False),
        )
        result = await db.execute(stmt)
        actual_count = result.scalar_one()

        # 簡化邏輯：計算日曆天數（週末不交易，但先用簡化版本）
        # 預期交易日 ≈ 日曆天數 * 5/7（排除週末）
        calendar_days = (end_date - start_date).days + 1
        expected_trading_days = max(1, int(calendar_days * 5 / 7))

        return actual_count, expected_trading_days

    @staticmethod
    async def get_existing_dates(
        db: AsyncSession,
        stock_id: int,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> list[datetime.date]:
        """取得區間內已存在的日期列表.

        Args:
            db: 資料庫會話
            stock_id: 股票 ID
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            list[datetime.date]: 已存在的日期列表（升序）
        """
        stmt = select(DailyPrice.date).where(
            DailyPrice.stock_id == stock_id,
            DailyPrice.date >= start_date,
            DailyPrice.date <= end_date,
            DailyPrice.is_deleted.is_(False),
        ).order_by(DailyPrice.date.asc())

        result = await db.execute(stmt)
        return [row[0] for row in result.fetchall()]

    @staticmethod
    def calculate_missing_ranges(
        start_date: datetime.date,
        end_date: datetime.date,
        existing_dates: list[datetime.date],
    ) -> list[tuple[datetime.date, datetime.date]]:
        """計算缺失的日期區間.

        Args:
            start_date: 開始日期
            end_date: 結束日期
            existing_dates: 已存在的日期列表（升序）

        Returns:
            list[tuple[datetime.date, datetime.date]]: 缺失日期區間列表 [(start, end), ...]
        """
        if not existing_dates:
            # 整個區間都缺失
            return [(start_date, end_date)]

        existing_set = set(existing_dates)
        missing_ranges = []
        current_gap_start = None

        # 逐日檢查（只檢查週一到週五）
        current = start_date
        while current <= end_date:
            # 跳過週末
            if current.weekday() >= 5:  # 週六、週日
                current += datetime.timedelta(days=1)
                continue

            is_missing = current not in existing_set

            if is_missing and current_gap_start is None:
                # 開始新的缺失區間
                current_gap_start = current
            elif not is_missing and current_gap_start is not None:
                # 缺失區間結束
                missing_ranges.append((current_gap_start, current - datetime.timedelta(days=1)))
                current_gap_start = None

            current += datetime.timedelta(days=1)

        # 處理結尾的缺失區間
        if current_gap_start is not None:
            # 找到範圍內的最後一個交易日（週一到週五）
            last_trading_day = end_date
            while last_trading_day.weekday() >= 5 and last_trading_day > current_gap_start:
                last_trading_day -= datetime.timedelta(days=1)
            missing_ranges.append((current_gap_start, last_trading_day))

        return missing_ranges

    @staticmethod
    async def trigger_fetch_job(
        redis_pool: ArqRedis | None,
        stock_id: int,
        missing_ranges: list[tuple[datetime.date, datetime.date]],
    ) -> str:
        """觸發 ARQ 任務抓取缺失資料.

        Args:
            redis_pool: ARQ Redis 連線池（若 None 則建立新連線）
            stock_id: 股票 ID
            missing_ranges: 缺失日期區間列表

        Returns:
            str: 任務 ID
        """
        if redis_pool is None:
            from src.tasks.config import redis_settings
            redis_pool = await create_pool(redis_settings)

        # 將日期區間轉換為字串格式（ARQ 序列化）
        date_ranges_str = [
            {"start_date": r[0].isoformat(), "end_date": r[1].isoformat()}
            for r in missing_ranges
        ]

        job = await redis_pool.enqueue_job(
            "fetch_missing_daily_prices",
            stock_id,
            date_ranges_str,
        )

        logger.info(f"Enqueued fetch_missing_daily_prices job: {job.job_id} for stock_id={stock_id}")
        return job.job_id

    @staticmethod
    async def get_stock_source(db: AsyncSession, stock_id: int) -> tuple[Stock, int]:
        """取得股票資訊與資料來源.

        Args:
            db: 資料庫會話
            stock_id: 股票 ID

        Returns:
            tuple[Stock, int]: (股票實體, source)

        Raises:
            ValueError: 股票不存在
        """
        stock = await StockService.get_by_id(db, stock_id)
        if not stock:
            raise ValueError(f"Stock not found: {stock_id}")
        return stock, stock.source