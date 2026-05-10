"""Unit tests for ARQ worker tasks."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.config import settings
from src.tasks.worker import update_stock_prices_master, DefaultWorkerSettings


@pytest.mark.asyncio
class TestUpdateStockPricesMaster:
    """Tests for master task logic."""

    async def test_no_active_stocks(self):
        """Test that no jobs are dispatched when no active stocks."""
        # Mock context with redis (ARQ standard key)
        mock_redis = MagicMock()
        ctx = {"redis": mock_redis}

        # Mock Redis client to return empty active stocks
        with patch("src.tasks.jobs.price_update_jobs.StockRedisClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.get_active_stocks.return_value = []

            # Run master task
            await update_stock_prices_master(ctx)

            # Verify StockRedisClient was initialized with pool
            mock_client_class.assert_called_once_with(pool=mock_redis)

            # Verify no jobs were enqueued
            assert mock_redis.enqueue_job.call_count == 0

    async def test_stocks_needing_update_identified(self):
        """Test that stocks needing updates are correctly identified."""
        mock_redis = MagicMock()
        mock_redis.enqueue_job = AsyncMock()
        ctx = {"redis": mock_redis}

        # Mock active stocks
        active_stocks = ["2330.TW", "2454.TW", "1101.TW"]

        # Mock stock info - first stock is old, second is recent, third has no record
        current_time = int(time.time())

        with patch("src.tasks.jobs.price_update_jobs.StockRedisClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.get_active_stocks.return_value = active_stocks

            # Mock get_stock_info for each stock
            def mock_get_info(symbol):
                if symbol == "2330.TW":
                    # Old stock (10 minutes ago)
                    return {"price": 500.0, "updated_at": current_time - 600}
                elif symbol == "2454.TW":
                    # Recent stock (2 minutes ago)
                    return {"price": 300.0, "updated_at": current_time - 120}
                elif symbol == "1101.TW":
                    # No record
                    return None

            mock_client.get_stock_info.side_effect = mock_get_info

            # Run master task
            await update_stock_prices_master(ctx)

            # Verify only stocks needing update were dispatched
            # 2330.TW (old) and 1101.TW (no record) should be in batch
            assert mock_redis.enqueue_job.call_count == 1

            # Get the batch from the enqueue_job call
            call_args = mock_redis.enqueue_job.call_args
            batch = call_args[0][1]  # Second argument is the batch list

            assert "2330.TW" in batch
            assert "1101.TW" in batch
            assert "2454.TW" not in batch

    async def test_batch_splitting(self):
        """Test that stocks are properly batched when exceeding batch size."""
        mock_redis = MagicMock()
        mock_redis.enqueue_job = AsyncMock()
        ctx = {"redis": mock_redis}

        # Create 120 stocks (should create 3 batches: 50, 50, 20)
        active_stocks = [f"{i}.TW" for i in range(120)]

        current_time = int(time.time())

        with patch("src.tasks.jobs.price_update_jobs.StockRedisClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.get_active_stocks.return_value = active_stocks

            # All stocks are old (need update)
            mock_client.get_stock_info.return_value = {
                "price": 100.0,
                "updated_at": current_time - 600,
            }

            # Run master task
            await update_stock_prices_master(ctx)

            # Verify 3 batches were dispatched
            assert mock_redis.enqueue_job.call_count == 3

            # Verify batch sizes
            calls = mock_redis.enqueue_job.call_args_list
            batch_sizes = [len(call[0][1]) for call in calls]

            assert batch_sizes == [50, 50, 20]

    async def test_error_handling_continues_on_redis_failure(self):
        """Test that master task continues even if checking a stock fails."""
        mock_redis = MagicMock()
        mock_redis.enqueue_job = AsyncMock()
        ctx = {"redis": mock_redis}

        active_stocks = ["2330.TW", "2454.TW", "1101.TW"]
        current_time = int(time.time())

        with patch("src.tasks.jobs.price_update_jobs.StockRedisClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.get_active_stocks.return_value = active_stocks

            def mock_get_info(symbol):
                if symbol == "2454.TW":
                    # Simulate error
                    raise Exception("Redis error")
                elif symbol == "2330.TW":
                    return {"price": 500.0, "updated_at": current_time - 600}
                elif symbol == "1101.TW":
                    return None

            mock_client.get_stock_info.side_effect = mock_get_info

            # Run master task
            await update_stock_prices_master(ctx)

            # Only 2 stocks should be in batch (error stock is skipped)
            call_args = mock_redis.enqueue_job.call_args
            batch = call_args[0][1]

            assert len(batch) == 2
            assert "2330.TW" in batch
            assert "1101.TW" in batch
            # 2454.TW should NOT be in batch (error caused it to be skipped)
            assert "2454.TW" not in batch

    async def test_redis_connection_failure_logged(self):
        """Test that Redis connection failure is logged and task raises."""
        mock_redis = MagicMock()
        ctx = {"redis": mock_redis}

        with patch("src.tasks.jobs.price_update_jobs.StockRedisClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Simulate connection failure
            from src.exceptions import BizException, ErrorCode

            mock_client.get_active_stocks.side_effect = BizException(
                ErrorCode.REDIS_CONNECTION_ERROR,
                "Redis connection failed",
            )

            # Run master task - should raise
            with pytest.raises(BizException):
                await update_stock_prices_master(ctx)

    async def test_no_dispatch_when_all_stocks_recent(self):
        """Test that no jobs are dispatched when all stocks are recently updated."""
        mock_redis = MagicMock()
        ctx = {"redis": mock_redis}

        active_stocks = ["2330.TW", "2454.TW"]
        current_time = int(time.time())

        with patch("src.tasks.jobs.price_update_jobs.StockRedisClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.get_active_stocks.return_value = active_stocks

            # All stocks recently updated (1 minute ago)
            mock_client.get_stock_info.return_value = {
                "price": 100.0,
                "updated_at": current_time - 60,
            }

            # Run master task
            await update_stock_prices_master(ctx)

            # Verify no jobs were dispatched
            assert mock_redis.enqueue_job.call_count == 0


class TestDefaultWorkerSettings:
    """Tests for DefaultWorkerSettings configuration."""

    def test_cron_jobs_configured(self):
        """Test that cron jobs are properly configured."""
        assert len(DefaultWorkerSettings.cron_jobs) == 4

        # Verify master task cron job runs every 5 minutes
        master_cron = DefaultWorkerSettings.cron_jobs[0]
        assert master_cron.minute == set(range(0, 60, 5))

        # Verify persistence task cron job runs every 1 minute
        persist_cron = DefaultWorkerSettings.cron_jobs[1]
        assert persist_cron.minute == set(range(60))

    def test_functions_registered(self):
        """Test that task functions are registered."""
        assert update_stock_prices_master in DefaultWorkerSettings.functions
        expected_functions = [
            "update_stock_prices_master",
            "persist_redis_to_database",
            "sync_active_stocks_to_redis",
            "process_scheduled_reminders",
        ]
        actual_functions = [f.__name__ for f in DefaultWorkerSettings.functions]
        for expected in expected_functions:
            assert expected in actual_functions

    def test_worker_settings_attributes(self):
        """Test that DefaultWorkerSettings has required attributes."""
        assert hasattr(DefaultWorkerSettings, "redis_settings")
        assert hasattr(DefaultWorkerSettings, "job_timeout")
        assert hasattr(DefaultWorkerSettings, "max_tries")
        assert hasattr(DefaultWorkerSettings, "on_startup")
        assert hasattr(DefaultWorkerSettings, "on_shutdown")

        # Verify settings match config
        assert DefaultWorkerSettings.job_timeout == settings.ARQ_JOB_TIMEOUT
        assert DefaultWorkerSettings.max_tries == settings.ARQ_MAX_TRIES