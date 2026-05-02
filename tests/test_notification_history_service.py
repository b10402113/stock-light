"""Tests for NotificationHistoryService."""

import pytest
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from src.subscriptions.service import NotificationHistoryService


class TestNotificationHistoryService:
    """Tests for NotificationHistoryService"""

    @pytest.mark.asyncio
    async def test_create_log(self, db: AsyncSession, test_user_id: int, test_subscription_id: int):
        """Test creating notification history log"""
        log = await NotificationHistoryService.create_log(
            db,
            user_id=test_user_id,
            indicator_subscription_id=test_subscription_id,
            triggered_value=Decimal("30.5"),
        )
        assert log.id is not None
        assert log.user_id == test_user_id
        assert log.indicator_subscription_id == test_subscription_id
        assert log.triggered_value == Decimal("30.5")
        assert log.send_status == "pending"
        assert log.line_message_id is None
        assert log.triggered_at is not None

    @pytest.mark.asyncio
    async def test_get_user_history_empty(self, db: AsyncSession, test_user_id: int):
        """Test getting user notification history when empty"""
        histories, next_cursor = await NotificationHistoryService.get_user_history(
            db, user_id=test_user_id
        )
        assert histories == []
        assert next_cursor is None

    @pytest.mark.asyncio
    async def test_get_user_history_with_data(
        self, db: AsyncSession, test_user_id: int, test_subscription_id: int
    ):
        """Test getting user notification history with data"""
        # Create multiple logs
        log1 = await NotificationHistoryService.create_log(
            db, test_user_id, test_subscription_id, Decimal("30.0")
        )
        log2 = await NotificationHistoryService.create_log(
            db, test_user_id, test_subscription_id, Decimal("31.0")
        )

        histories, next_cursor = await NotificationHistoryService.get_user_history(
            db, user_id=test_user_id, limit=10
        )
        assert len(histories) == 2
        # Should be ordered by triggered_at DESC (newest first)
        assert histories[0].id == log2.id
        assert histories[1].id == log1.id
        assert next_cursor is None  # Less than limit

    @pytest.mark.asyncio
    async def test_get_user_history_pagination(
        self, db: AsyncSession, test_user_id: int, test_subscription_id: int
    ):
        """Test getting user notification history with pagination"""
        # Create 3 logs
        await NotificationHistoryService.create_log(
            db, test_user_id, test_subscription_id, Decimal("30.0")
        )
        await NotificationHistoryService.create_log(
            db, test_user_id, test_subscription_id, Decimal("31.0")
        )
        log3 = await NotificationHistoryService.create_log(
            db, test_user_id, test_subscription_id, Decimal("32.0")
        )

        # Get first page with limit 2
        histories, next_cursor = await NotificationHistoryService.get_user_history(
            db, user_id=test_user_id, limit=2
        )
        assert len(histories) == 2
        assert histories[0].id == log3.id  # Newest first
        assert next_cursor is not None

        # Get second page
        histories2, next_cursor2 = await NotificationHistoryService.get_user_history(
            db, user_id=test_user_id, cursor=next_cursor, limit=2
        )
        assert len(histories2) == 1
        assert next_cursor2 is None

    @pytest.mark.asyncio
    async def test_get_by_id(self, db: AsyncSession, test_user_id: int, test_subscription_id: int):
        """Test getting notification history by ID"""
        log = await NotificationHistoryService.create_log(
            db, test_user_id, test_subscription_id, Decimal("30.0")
        )

        found = await NotificationHistoryService.get_by_id(db, log.id)
        assert found is not None
        assert found.id == log.id
        assert found.triggered_value == Decimal("30.0")

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, db: AsyncSession):
        """Test getting notification history by ID when not found"""
        found = await NotificationHistoryService.get_by_id(db, 99999)
        assert found is None

    @pytest.mark.asyncio
    async def test_update_status_sent(
        self, db: AsyncSession, test_user_id: int, test_subscription_id: int
    ):
        """Test updating notification status to sent"""
        log = await NotificationHistoryService.create_log(
            db, test_user_id, test_subscription_id, Decimal("30.0")
        )
        assert log.send_status == "pending"

        updated = await NotificationHistoryService.update_status(
            db, log, "sent", line_message_id="msg_123"
        )
        assert updated.send_status == "sent"
        assert updated.line_message_id == "msg_123"

    @pytest.mark.asyncio
    async def test_update_status_failed(
        self, db: AsyncSession, test_user_id: int, test_subscription_id: int
    ):
        """Test updating notification status to failed"""
        log = await NotificationHistoryService.create_log(
            db, test_user_id, test_subscription_id, Decimal("30.0")
        )

        updated = await NotificationHistoryService.update_status(
            db, log, "failed"
        )
        assert updated.send_status == "failed"
        assert updated.line_message_id is None

    @pytest.mark.asyncio
    async def test_get_failed_notifications_empty(self, db: AsyncSession):
        """Test getting failed notifications when empty"""
        failed = await NotificationHistoryService.get_failed_notifications(db)
        assert failed == []

    @pytest.mark.asyncio
    async def test_get_failed_notifications_with_data(
        self, db: AsyncSession, test_user_id: int, test_subscription_id: int
    ):
        """Test getting failed notifications"""
        # Create a failed notification
        log1 = await NotificationHistoryService.create_log(
            db, test_user_id, test_subscription_id, Decimal("30.0")
        )
        await NotificationHistoryService.update_status(db, log1, "failed")

        # Create a sent notification
        log2 = await NotificationHistoryService.create_log(
            db, test_user_id, test_subscription_id, Decimal("31.0")
        )
        await NotificationHistoryService.update_status(db, log2, "sent")

        failed = await NotificationHistoryService.get_failed_notifications(db)
        assert len(failed) == 1
        assert failed[0].id == log1.id
        assert failed[0].send_status == "failed"