"""Tests for Backtest router endpoints."""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from src.stocks.schema import StockSource, StockMarket


@pytest.mark.asyncio
class TestBacktestRouter:
    """Test backtest API endpoints."""

    async def test_trigger_backtest_stock_not_found(self, client: AsyncClient):
        """Test trigger_backtest returns 404 for non-existent stock."""
        response = await client.post(
            "/stocks/999999/backtest/trigger",
            json={
                "start_date": "2026-01-06",
                "end_date": "2026-01-10",
            },
        )

        assert response.status_code == 404
        data = response.json()
        assert "Stock not found" in data["detail"]

    async def test_trigger_backtest_invalid_date_range(self, client: AsyncClient):
        """Test trigger_backtest returns 422 for invalid date range."""

        # Pydantic validation error returns 422, not 400
        response = await client.post(
            "/stocks/1/backtest/trigger",
            json={
                "start_date": "2026-01-10",
                "end_date": "2026-01-06",  # End before start
            },
        )

        # Pydantic field_validator raises 422 Unprocessable Entity
        assert response.status_code == 422

    async def test_trigger_backtest_data_ready(self, client: AsyncClient, db_session):
        """Test trigger_backtest returns ready status when data complete."""
        from src.stocks.model import DailyPrice, Stock
        from decimal import Decimal

        # Create test stock
        stock = Stock(
            symbol="BACKTEST",
            name="Test Stock",
            source=StockSource.FUGLE,
            market=StockMarket.TAIWAN,
        )
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        # Add complete daily prices
        start_date = datetime.date(2026, 1, 6)
        for i in range(5):  # Mon-Fri
            price = DailyPrice(
                stock_id=stock.id,
                date=start_date + datetime.timedelta(days=i),
                open=Decimal("100"),
                high=Decimal("110"),
                low=Decimal("95"),
                close=Decimal("105"),
                volume=1000000,
            )
            db_session.add(price)

        await db_session.commit()

        # Trigger backtest
        response = await client.post(
            f"/stocks/{stock.id}/backtest/trigger",
            json={
                "start_date": start_date.isoformat(),
                "end_date": (start_date + datetime.timedelta(days=4)).isoformat(),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "ready"
        assert data["data"]["data_count"] == 5
        assert data["data"]["job_id"] is None

    async def test_trigger_backtest_data_missing(self, client: AsyncClient, db_session):
        """Test trigger_backtest returns pending status and creates job when data missing."""
        from src.stocks.model import Stock

        # Create test stock without prices
        stock = Stock(
            symbol="NOPRICE",
            name="No Price Stock",
            source=StockSource.FUGLE,
            market=StockMarket.TAIWAN,
        )
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        # Mock ARQ Redis pool
        mock_redis = AsyncMock()
        mock_job = MagicMock()
        mock_job.job_id = "test_job_abc123"
        mock_redis.enqueue_job.return_value = mock_job

        # Use weekday dates to ensure proper testing
        start_date = datetime.date(2026, 1, 6)  # Tuesday
        end_date = datetime.date(2026, 1, 9)    # Friday (weekday)

        with patch("src.backtest.router.create_pool", return_value=mock_redis):
            # Trigger backtest
            response = await client.post(
                f"/stocks/{stock.id}/backtest/trigger",
                json={
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
            )

            # With no prices, should return 202
            print(f"Response status: {response.status_code}")
            print(f"Response data: {response.json()}")
            assert response.status_code == 202
            data = response.json()
            assert data["data"]["status"] == "pending"
            assert data["data"]["job_id"] == "test_job_abc123"
            assert data["data"]["missing_ranges"] is not None


@pytest.mark.asyncio
class TestTasksRouter:
    """Test tasks API endpoints."""

    async def test_get_task_status_not_found(self, client: AsyncClient):
        """Test get_task_status returns 404 for non-existent job."""
        # Create mock that returns None for get_job
        mock_redis = AsyncMock()
        mock_redis.get_job.return_value = None

        with patch("src.tasks.router.create_pool", return_value=mock_redis):
            response = await client.get("/tasks/nonexistent_job")

            # Should return 404
            assert response.status_code == 404
            data = response.json()
            assert "Task not found" in data["detail"]

    async def test_get_task_status_pending(self, client: AsyncClient):
        """Test get_task_status returns pending status."""
        mock_redis = AsyncMock()
        mock_job = MagicMock()
        mock_job.status = "pending"
        mock_job.enqueue_time = datetime.datetime(2026, 1, 6, 10, 0, 0)
        mock_job.start_time = None
        mock_job.finish_time = None
        mock_job.result = None
        mock_job.exc = None
        mock_redis.get_job.return_value = mock_job

        with patch("src.tasks.router.create_pool", return_value=mock_redis):
            response = await client.get("/tasks/test_job_pending")

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["status"] == "pending"
            assert data["data"]["job_id"] == "test_job_pending"

    async def test_get_task_status_completed(self, client: AsyncClient):
        """Test get_task_status returns completed status with result."""
        mock_redis = AsyncMock()
        mock_job = MagicMock()
        mock_job.status = "completed"
        mock_job.enqueue_time = datetime.datetime(2026, 1, 6, 10, 0, 0)
        mock_job.start_time = datetime.datetime(2026, 1, 6, 10, 0, 5)
        mock_job.finish_time = datetime.datetime(2026, 1, 6, 10, 0, 15)
        mock_job.result = {"stock_id": 1, "fetched_count": 10, "success": True}
        mock_job.exc = None
        mock_redis.get_job.return_value = mock_job

        with patch("src.tasks.router.create_pool", return_value=mock_redis):
            response = await client.get("/tasks/test_job_completed")

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["status"] == "completed"
            assert data["data"]["result"]["fetched_count"] == 10

    async def test_get_task_status_failed(self, client: AsyncClient):
        """Test get_task_status returns failed status with error."""
        mock_redis = AsyncMock()
        mock_job = MagicMock()
        mock_job.status = "failed"
        mock_job.enqueue_time = datetime.datetime(2026, 1, 6, 10, 0, 0)
        mock_job.start_time = datetime.datetime(2026, 1, 6, 10, 0, 5)
        mock_job.finish_time = datetime.datetime(2026, 1, 6, 10, 0, 10)
        mock_job.result = None
        mock_job.exc = Exception("API error")
        mock_redis.get_job.return_value = mock_job

        with patch("src.tasks.router.create_pool", return_value=mock_redis):
            response = await client.get("/tasks/test_job_failed")

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["status"] == "failed"
            assert "API error" in data["data"]["error"]