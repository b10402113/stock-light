"""Tests for BacktestService."""

import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.backtest.service import BacktestService


@pytest.mark.asyncio
class TestBacktestService:
    """Test BacktestService methods."""

    async def test_check_data_coverage_full(self, db_session: AsyncSession):
        """Test check_data_coverage when data is complete."""
        # Create test stock and daily prices
        from src.stocks.model import DailyPrice, Stock
        from src.stocks.schema import StockSource, StockMarket
        from decimal import Decimal

        stock = Stock(
            symbol="2330",
            name="台積電",
            source=StockSource.FUGLE,
            market=StockMarket.TAIWAN,
        )
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        # Add daily prices for a week (5 trading days)
        start_date = datetime.date(2026, 1, 6)  # Monday
        for i in range(5):
            price = DailyPrice(
                stock_id=stock.id,
                date=start_date + datetime.timedelta(days=i),
                open=Decimal("500"),
                high=Decimal("510"),
                low=Decimal("495"),
                close=Decimal("505"),
                volume=1000000,
            )
            db_session.add(price)

        await db_session.commit()

        # Check coverage
        actual, expected = await BacktestService.check_data_coverage(
            db_session,
            stock.id,
            start_date,
            start_date + datetime.timedelta(days=4),
        )

        # Should have 5 actual records, ~3-4 expected trading days (5 calendar days * 5/7)
        assert actual == 5
        assert expected >= 3

    async def test_check_data_coverage_empty(self, db_session: AsyncSession):
        """Test check_data_coverage when no data exists."""
        from src.stocks.model import Stock
        from src.stocks.schema import StockSource, StockMarket

        stock = Stock(
            symbol="2454",
            name="聯發科",
            source=StockSource.FUGLE,
            market=StockMarket.TAIWAN,
        )
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        start_date = datetime.date(2026, 1, 6)
        end_date = datetime.date(2026, 1, 10)

        # Check coverage (should be 0)
        actual, expected = await BacktestService.check_data_coverage(
            db_session,
            stock.id,
            start_date,
            end_date,
        )

        assert actual == 0
        assert expected >= 1

    async def test_get_existing_dates(self, db_session: AsyncSession):
        """Test get_existing_dates returns correct dates."""
        from src.stocks.model import DailyPrice, Stock
        from src.stocks.schema import StockSource, StockMarket
        from decimal import Decimal

        stock = Stock(
            symbol="1101",
            name="台泥",
            source=StockSource.FUGLE,
            market=StockMarket.TAIWAN,
        )
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        # Add prices for specific dates
        dates = [
            datetime.date(2026, 1, 6),
            datetime.date(2026, 1, 7),
            datetime.date(2026, 1, 9),  # Skip Jan 8
        ]
        for date in dates:
            price = DailyPrice(
                stock_id=stock.id,
                date=date,
                open=Decimal("50"),
                high=Decimal("52"),
                low=Decimal("49"),
                close=Decimal("51"),
                volume=500000,
            )
            db_session.add(price)

        await db_session.commit()

        # Get existing dates
        start_date = datetime.date(2026, 1, 6)
        end_date = datetime.date(2026, 1, 10)

        existing = await BacktestService.get_existing_dates(
            db_session,
            stock.id,
            start_date,
            end_date,
        )

        # Should return the 3 dates we added (sorted)
        assert len(existing) == 3
        assert existing[0] == datetime.date(2026, 1, 6)
        assert existing[1] == datetime.date(2026, 1, 7)
        assert existing[2] == datetime.date(2026, 1, 9)

    def test_calculate_missing_ranges_empty_existing(self):
        """Test calculate_missing_ranges when no existing dates."""
        start_date = datetime.date(2026, 1, 6)
        end_date = datetime.date(2026, 1, 10)

        # No existing dates
        missing = BacktestService.calculate_missing_ranges(
            start_date,
            end_date,
            [],
        )

        # Should return entire range
        assert len(missing) == 1
        assert missing[0] == (start_date, end_date)

    def test_calculate_missing_ranges_partial(self):
        """Test calculate_missing_ranges with gaps."""
        # Mon Jan 6, Tue Jan 7, Wed Jan 8, Thu Jan 9, Fri Jan 10
        start_date = datetime.date(2026, 1, 6)
        end_date = datetime.date(2026, 1, 10)

        # Existing: Jan 6, Jan 8, Jan 10 (missing Jan 7, Jan 9)
        existing = [
            datetime.date(2026, 1, 6),
            datetime.date(2026, 1, 8),
            datetime.date(2026, 1, 10),
        ]

        missing = BacktestService.calculate_missing_ranges(
            start_date,
            end_date,
            existing,
        )

        # Should return 2 missing ranges: Jan 7, Jan 9
        assert len(missing) == 2
        assert missing[0] == (datetime.date(2026, 1, 7), datetime.date(2026, 1, 7))
        assert missing[1] == (datetime.date(2026, 1, 9), datetime.date(2026, 1, 9))

    def test_calculate_missing_ranges_skip_weekends(self):
        """Test calculate_missing_ranges skips weekends."""
        # Mon Jan 5 to Fri Jan 10 (includes weekend)
        start_date = datetime.date(2026, 1, 5)
        end_date = datetime.date(2026, 1, 12)  # Mon to next Mon (includes Sat/Sun)

        # Existing: All weekdays
        existing = [
            datetime.date(2026, 1, 5),  # Mon
            datetime.date(2026, 1, 6),  # Tue
            datetime.date(2026, 1, 7),  # Wed
            datetime.date(2026, 1, 8),  # Thu
            datetime.date(2026, 1, 9),  # Fri
            datetime.date(2026, 1, 12), # Mon
        ]

        missing = BacktestService.calculate_missing_ranges(
            start_date,
            end_date,
            existing,
        )

        # Should return empty (weekends are skipped)
        assert len(missing) == 0

    def test_calculate_missing_ranges_full_missing(self):
        """Test calculate_missing_ranges with continuous gap."""
        start_date = datetime.date(2026, 1, 6)
        end_date = datetime.date(2026, 1, 10)

        # Existing: only Jan 10
        existing = [datetime.date(2026, 1, 10)]

        missing = BacktestService.calculate_missing_ranges(
            start_date,
            end_date,
            existing,
        )

        # Should return one range: Jan 6-9
        assert len(missing) == 1
        assert missing[0] == (datetime.date(2026, 1, 6), datetime.date(2026, 1, 9))

    async def test_trigger_fetch_job(self):
        """Test trigger_fetch_job enqueues ARQ job."""
        mock_redis = AsyncMock()
        mock_job = MagicMock()
        mock_job.job_id = "test_job_123"
        mock_redis.enqueue_job.return_value = mock_job

        missing_ranges = [
            (datetime.date(2026, 1, 6), datetime.date(2026, 1, 7)),
            (datetime.date(2026, 1, 9), datetime.date(2026, 1, 10)),
        ]

        job_id = await BacktestService.trigger_fetch_job(
            mock_redis,
            1,
            missing_ranges,
        )

        assert job_id == "test_job_123"
        mock_redis.enqueue_job.assert_called_once()

        # Verify call args
        call_args = mock_redis.enqueue_job.call_args
        assert call_args[0][0] == "fetch_missing_daily_prices"
        assert call_args[0][1] == 1
        assert len(call_args[0][2]) == 2