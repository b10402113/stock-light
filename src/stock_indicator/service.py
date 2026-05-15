"""Stock indicator business logic."""

import logging
from datetime import datetime, timezone

from sqlalchemy import and_, delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.stock_indicator.model import StockIndicator
from src.stock_indicator.schema import (
    StockIndicatorResponse,
    StockIndicatorUpsert,
)

logger = logging.getLogger(__name__)


class StockIndicatorService:
    """Stock indicator calculation and storage business logic"""

    @staticmethod
    async def upsert_indicator(
        db: AsyncSession,
        stock_id: int,
        indicator_key: str,
        data: dict,
    ) -> StockIndicator:
        """Upsert (insert or update) indicator for a stock.

        Args:
            db: Database session
            stock_id: Stock ID
            indicator_key: Indicator key (e.g., RSI_14, MACD_12_26_9)
            data: Indicator data as dictionary

        Returns:
            StockIndicator: Upserted indicator entity
        """
        values = {
            "stock_id": stock_id,
            "indicator_key": indicator_key,
            "data": data,
        }

        stmt = insert(StockIndicator).values(values)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_stock_indicator_stock_key",
            set_={
                "data": stmt.excluded.data,
            },
        )
        stmt = stmt.returning(StockIndicator)

        result = await db.execute(stmt)
        await db.commit()
        indicator = result.scalar_one()
        logger.info(
            f"Upserted indicator {indicator_key} for stock_id={stock_id}"
        )
        return indicator

    @staticmethod
    async def bulk_upsert_indicators(
        db: AsyncSession,
        indicators: list[StockIndicatorUpsert],
    ) -> int:
        """Bulk upsert multiple indicators.

        Args:
            db: Database session
            indicators: List of indicator upsert data

        Returns:
            int: Number of indicators upserted
        """
        if not indicators:
            return 0

        values = [
            {
                "stock_id": ind.stock_id,
                "indicator_key": ind.indicator_key,
                "data": ind.data,
            }
            for ind in indicators
        ]

        stmt = insert(StockIndicator).values(values)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_stock_indicator_stock_key",
            set_={
                "data": stmt.excluded.data,
            },
        )

        result = await db.execute(stmt)
        await db.commit()
        logger.info(f"Bulk upserted {result.rowcount} indicators")
        return result.rowcount

    @staticmethod
    async def get_by_stock(db: AsyncSession, stock_id: int) -> list[StockIndicator]:
        """Get all indicators for a specific stock.

        Args:
            db: Database session
            stock_id: Stock ID

        Returns:
            list[StockIndicator]: List of indicators for the stock
        """
        stmt = select(StockIndicator).where(
            StockIndicator.stock_id == stock_id,
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_by_type(
        db: AsyncSession,
        indicator_key: str,
        limit: int = 100,
    ) -> list[StockIndicator]:
        """Get all stocks with a specific indicator type.

        Args:
            db: Database session
            indicator_key: Indicator key to filter by
            limit: Maximum number of results

        Returns:
            list[StockIndicator]: List of indicators matching the key
        """
        stmt = (
            select(StockIndicator)
            .where(StockIndicator.indicator_key == indicator_key)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_by_stock_and_key(
        db: AsyncSession,
        stock_id: int,
        indicator_key: str,
    ) -> StockIndicator | None:
        """Get specific indicator for a stock by key.

        Args:
            db: Database session
            stock_id: Stock ID
            indicator_key: Indicator key

        Returns:
            StockIndicator | None: Indicator or None if not found
        """
        stmt = select(StockIndicator).where(
            and_(
                StockIndicator.stock_id == stock_id,
                StockIndicator.indicator_key == indicator_key,
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def delete_by_stock(db: AsyncSession, stock_id: int) -> int:
        """Delete all indicators for a stock.

        Args:
            db: Database session
            stock_id: Stock ID

        Returns:
            int: Number of indicators deleted
        """
        stmt = delete(StockIndicator).where(StockIndicator.stock_id == stock_id)
        result = await db.execute(stmt)
        await db.commit()
        logger.info(f"Deleted {result.rowcount} indicators for stock_id={stock_id}")
        return result.rowcount

    @staticmethod
    async def get_stocks_with_indicators(
        db: AsyncSession,
        indicator_types: list[str] | None = None,
    ) -> list[int]:
        """Get list of stock IDs that have indicator subscriptions.

        This method queries indicator subscriptions to find stocks that need
        indicator calculation. Used by worker to determine which stocks to process.

        Args:
            db: Database session
            indicator_types: Optional filter by indicator types (e.g., ["rsi", "kd"])

        Returns:
            list[int]: List of stock IDs with active indicator subscriptions
        """
        from src.subscriptions.model import IndicatorSubscription

        stmt = (
            select(IndicatorSubscription.stock_id)
            .where(
                IndicatorSubscription.is_deleted.is_(False),
                IndicatorSubscription.is_active.is_(True),
            )
            .distinct()
        )

        result = await db.execute(stmt)
        stock_ids = [row[0] for row in result.all()]
        logger.info(f"Found {len(stock_ids)} stocks with indicator subscriptions")
        return stock_ids

    @staticmethod
    async def get_required_indicator_keys(
        db: AsyncSession,
        stock_id: int,
    ) -> list[str]:
        """Get list of indicator keys required for a stock based on its subscriptions.

        Parses subscriptions to determine which indicators need to be calculated
        for this stock.

        Args:
            db: Database session
            stock_id: Stock ID

        Returns:
            list[str]: List of indicator keys (e.g., ["RSI_14", "MACD_12_26_9"])
        """
        from src.subscriptions.model import IndicatorSubscription
        from src.subscriptions.schema import IndicatorType as SubIndicatorType

        stmt = select(IndicatorSubscription).where(
            IndicatorSubscription.stock_id == stock_id,
            IndicatorSubscription.is_deleted.is_(False),
            IndicatorSubscription.is_active.is_(True),
        )
        result = await db.execute(stmt)
        subscriptions = list(result.scalars().all())

        indicator_keys = []

        for sub in subscriptions:
            # Handle single condition
            if sub.indicator_type:
                key = StockIndicatorService._subscription_to_indicator_key(
                    sub.indicator_type,
                    sub.timeframe,
                    sub.period,
                )
                if key:
                    indicator_keys.append(key)

            # Handle compound condition
            if sub.compound_condition:
                for condition in sub.compound_condition.get("conditions", []):
                    ind_type = condition.get("indicator_type")
                    timeframe = condition.get("timeframe", "D")
                    period = condition.get("period")
                    if ind_type:
                        key = StockIndicatorService._subscription_to_indicator_key(
                            ind_type,
                            timeframe,
                            period,
                        )
                        if key:
                            indicator_keys.append(key)

        # Remove duplicates
        unique_keys = list(set(indicator_keys))
        logger.info(
            f"Stock {stock_id} requires indicators: {unique_keys}"
        )
        return unique_keys

    @staticmethod
    def _subscription_to_indicator_key(
        indicator_type: str,
        timeframe: str,
        period: int | None,
    ) -> str | None:
        """Convert subscription indicator type to indicator key.

        Args:
            indicator_type: Indicator type from subscription (e.g., "rsi", "kd")
            timeframe: Timeframe (D or W)
            period: Period for RSI/SMA

        Returns:
            str | None: Indicator key or None if not applicable
        """
        from src.stock_indicator.schema import IndicatorType, generate_indicator_key

        # Price indicator doesn't need calculation
        if indicator_type.lower() == "price":
            return None

        try:
            ind_type = IndicatorType(indicator_type.lower())
        except ValueError:
            return None

        # Default periods for indicators without configurable period
        default_params = {
            IndicatorType.KDJ: [9, 3, 3],
            IndicatorType.MACD: [12, 26, 9],
        }

        if ind_type in default_params:
            return generate_indicator_key(ind_type, default_params[ind_type], timeframe)
        elif ind_type in (IndicatorType.RSI, IndicatorType.SMA):
            # Use provided period or default
            params = [period] if period else [14] if ind_type == IndicatorType.RSI else [20]
            return generate_indicator_key(ind_type, params, timeframe)

        return None