"""Tests for scheduled reminder endpoints."""

import pytest
from datetime import datetime, timezone
from httpx import AsyncClient

from src.subscriptions.schema import FrequencyType
from src.subscriptions.service import ScheduledReminderService


class TestScheduledReminderRouter:
    """Tests for scheduled reminder router endpoints"""

    @pytest.fixture
    async def auth_headers(self, client: AsyncClient) -> dict[str, str]:
        """Create authenticated user and return headers with token"""
        # Register user
        await client.post(
            "/auth/register",
            json={"email": "reminder_test@example.com", "password": "password123"},
        )

        # Login to get token
        login_response = await client.post(
            "/auth/login",
            json={"email": "reminder_test@example.com", "password": "password123"},
        )
        token = login_response.json()["data"]["access_token"]

        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    async def stock_id(self, client: AsyncClient) -> int:
        """Create a test stock and return its ID"""
        response = await client.post(
            "/stocks",
            json={"symbol": "2330.TW", "name": "台積電", "is_active": True},
        )
        return response.json()["data"]["id"]

    @pytest.mark.asyncio
    async def test_create_reminder_daily_success(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test successful daily reminder creation"""
        response = await client.post(
            "/subscriptions/reminders",
            json={
                "stock_id": stock_id,
                "title": "Daily 2330 Reminder",
                "message": "Check 2330 daily performance",
                "frequency_type": "daily",
                "reminder_time": "17:00",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["stock"]["id"] == stock_id
        assert data["data"]["stock"]["symbol"] == "2330.TW"
        assert data["data"]["subscription_type"] == "reminder"
        assert data["data"]["title"] == "Daily 2330 Reminder"
        assert data["data"]["message"] == "Check 2330 daily performance"
        assert data["data"]["frequency_type"] == "daily"
        assert data["data"]["reminder_time"] == "17:00"
        assert data["data"]["day_of_week"] == 0
        assert data["data"]["day_of_month"] == 0
        assert data["data"]["is_active"] is True
        assert "next_trigger_at" in data["data"]

    @pytest.mark.asyncio
    async def test_create_reminder_weekly_success(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test successful weekly reminder creation"""
        response = await client.post(
            "/subscriptions/reminders",
            json={
                "stock_id": stock_id,
                "title": "Weekly 2330 Reminder",
                "message": "Check 2330 weekly performance",
                "frequency_type": "weekly",
                "reminder_time": "09:30",
                "day_of_week": 2,  # Wednesday
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["data"]["frequency_type"] == "weekly"
        assert data["data"]["day_of_week"] == 2
        assert data["data"]["reminder_time"] == "09:30"

    @pytest.mark.asyncio
    async def test_create_reminder_monthly_success(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test successful monthly reminder creation"""
        response = await client.post(
            "/subscriptions/reminders",
            json={
                "stock_id": stock_id,
                "title": "Monthly Report",
                "message": "Monthly check on 2330",
                "frequency_type": "monthly",
                "reminder_time": "18:00",
                "day_of_month": 15,
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["data"]["frequency_type"] == "monthly"
        assert data["data"]["day_of_month"] == 15
        assert data["data"]["reminder_time"] == "18:00"

    @pytest.mark.asyncio
    async def test_create_reminder_missing_auth(self, client: AsyncClient, stock_id: int):
        """Test creating reminder without authentication"""
        response = await client.post(
            "/subscriptions/reminders",
            json={
                "stock_id": stock_id,
                "frequency_type": "daily",
                "reminder_time": "17:00",
            },
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_reminder_invalid_frequency_type(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test creating reminder with invalid frequency type"""
        response = await client.post(
            "/subscriptions/reminders",
            json={
                "stock_id": stock_id,
                "frequency_type": "invalid",
                "reminder_time": "17:00",
            },
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_reminder_invalid_time_format(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test creating reminder with invalid time format"""
        response = await client.post(
            "/subscriptions/reminders",
            json={
                "stock_id": stock_id,
                "frequency_type": "daily",
                "reminder_time": "25:00",  # Invalid hour
            },
            headers=auth_headers,
        )

        # Returns 400 because service catches the ValueError
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_reminder_invalid_day_of_week(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test creating reminder with invalid day_of_week"""
        response = await client.post(
            "/subscriptions/reminders",
            json={
                "stock_id": stock_id,
                "frequency_type": "weekly",
                "reminder_time": "17:00",
                "day_of_week": 7,  # Invalid (0-6 only)
            },
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_reminder_invalid_day_of_month(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test creating reminder with invalid day_of_month"""
        response = await client.post(
            "/subscriptions/reminders",
            json={
                "stock_id": stock_id,
                "frequency_type": "monthly",
                "reminder_time": "17:00",
                "day_of_month": 29,  # Invalid (1-28 only)
            },
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_reminder_invalid_stock(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test creating reminder with non-existent stock"""
        response = await client.post(
            "/subscriptions/reminders",
            json={
                "stock_id": 999,
                "frequency_type": "daily",
                "reminder_time": "17:00",
            },
            headers=auth_headers,
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_reminder_duplicate(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test creating duplicate reminder"""
        # Create first reminder
        await client.post(
            "/subscriptions/reminders",
            json={
                "stock_id": stock_id,
                "frequency_type": "daily",
                "reminder_time": "17:00",
            },
            headers=auth_headers,
        )

        # Try to create duplicate
        response = await client.post(
            "/subscriptions/reminders",
            json={
                "stock_id": stock_id,
                "frequency_type": "daily",
                "reminder_time": "17:00",
            },
            headers=auth_headers,
        )

        assert response.status_code == 400 or response.status_code == 409

    @pytest.mark.asyncio
    async def test_list_reminders(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test listing user's reminders"""
        # Create multiple reminders with different times to avoid duplicates
        await client.post(
            "/subscriptions/reminders",
            json={
                "stock_id": stock_id,
                "frequency_type": "daily",
                "reminder_time": "09:00",
            },
            headers=auth_headers,
        )
        await client.post(
            "/subscriptions/reminders",
            json={
                "stock_id": stock_id,
                "frequency_type": "daily",
                "reminder_time": "17:00",
            },
            headers=auth_headers,
        )

        response = await client.get("/subscriptions/reminders", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]["data"]) == 2
        assert data["data"]["has_more"] is False
        # Check stock details are included
        assert data["data"]["data"][0]["stock"]["symbol"] == "2330.TW"

    @pytest.mark.asyncio
    async def test_list_reminders_pagination(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test reminder list pagination"""
        # Create 5 reminders with different times
        times = ["09:00", "10:00", "11:00", "12:00", "13:00"]
        for t in times:
            await client.post(
                "/subscriptions/reminders",
                json={
                    "stock_id": stock_id,
                    "frequency_type": "daily",
                    "reminder_time": t,
                },
                headers=auth_headers,
            )

        # Get first page (limit 2)
        response = await client.get("/subscriptions/reminders?limit=2", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["data"]) == 2
        assert data["data"]["has_more"] is True
        next_cursor = data["data"]["next_cursor"]

        # Get second page
        response2 = await client.get(
            f"/subscriptions/reminders?limit=2&cursor={next_cursor}",
            headers=auth_headers,
        )

        assert response2.status_code == 200
        data2 = response2.json()
        assert len(data2["data"]["data"]) == 2

    @pytest.mark.asyncio
    async def test_get_reminder_success(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test getting a single reminder"""
        # Create reminder
        create_response = await client.post(
            "/subscriptions/reminders",
            json={
                "stock_id": stock_id,
                "frequency_type": "daily",
                "reminder_time": "17:00",
            },
            headers=auth_headers,
        )
        reminder_id = create_response.json()["data"]["id"]

        response = await client.get(
            f"/subscriptions/reminders/{reminder_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["frequency_type"] == "daily"
        assert data["data"]["stock"]["id"] == stock_id

    @pytest.mark.asyncio
    async def test_get_reminder_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test getting non-existent reminder"""
        response = await client.get("/subscriptions/reminders/999", headers=auth_headers)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_reminder_success(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test updating a reminder"""
        # Create reminder
        create_response = await client.post(
            "/subscriptions/reminders",
            json={
                "stock_id": stock_id,
                "frequency_type": "daily",
                "reminder_time": "17:00",
            },
            headers=auth_headers,
        )
        reminder_id = create_response.json()["data"]["id"]

        # Update reminder
        response = await client.patch(
            f"/subscriptions/reminders/{reminder_id}",
            json={"title": "Updated Title", "reminder_time": "18:00", "is_active": False},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["title"] == "Updated Title"
        assert data["data"]["reminder_time"] == "18:00"
        assert data["data"]["is_active"] is False

    @pytest.mark.asyncio
    async def test_update_reminder_frequency_type(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test updating reminder frequency type recalculates next_trigger_at"""
        # Create daily reminder
        create_response = await client.post(
            "/subscriptions/reminders",
            json={
                "stock_id": stock_id,
                "frequency_type": "daily",
                "reminder_time": "17:00",
            },
            headers=auth_headers,
        )
        reminder_id = create_response.json()["data"]["id"]
        original_next_trigger = create_response.json()["data"]["next_trigger_at"]

        # Update to weekly
        response = await client.patch(
            f"/subscriptions/reminders/{reminder_id}",
            json={"frequency_type": "weekly", "day_of_week": 3},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["frequency_type"] == "weekly"
        assert data["data"]["day_of_week"] == 3
        # next_trigger_at should be recalculated
        assert data["data"]["next_trigger_at"] != original_next_trigger

    @pytest.mark.asyncio
    async def test_delete_reminder_success(
        self, client: AsyncClient, auth_headers: dict, stock_id: int
    ):
        """Test soft deleting a reminder"""
        # Create reminder
        create_response = await client.post(
            "/subscriptions/reminders",
            json={
                "stock_id": stock_id,
                "frequency_type": "daily",
                "reminder_time": "17:00",
            },
            headers=auth_headers,
        )
        reminder_id = create_response.json()["data"]["id"]

        # Delete reminder
        response = await client.delete(
            f"/subscriptions/reminders/{reminder_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200

        # Verify reminder is deleted (not found)
        get_response = await client.get(
            f"/subscriptions/reminders/{reminder_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404


class TestScheduledReminderService:
    """Tests for ScheduledReminderService"""

    @pytest.mark.asyncio
    async def test_calculate_next_trigger_time_daily(self):
        """Test calculating next trigger time for daily frequency"""
        now = datetime(2026, 5, 10, 10, 0, 0, tzinfo=timezone.utc)

        # Daily at 17:00 - should be next day
        next_trigger = ScheduledReminderService.calculate_next_trigger_time(
            FrequencyType.DAILY, "17:00", 0, 0
        )

        # Should be tomorrow at 17:00 UTC
        assert next_trigger.hour == 17
        assert next_trigger.minute == 0
        assert next_trigger.day == now.day + 1 or (next_trigger.month != now.month and next_trigger.day == 1)

    @pytest.mark.asyncio
    async def test_calculate_next_trigger_time_weekly(self):
        """Test calculating next trigger time for weekly frequency"""
        # Weekly on Wednesday (day_of_week=2)
        next_trigger = ScheduledReminderService.calculate_next_trigger_time(
            FrequencyType.WEEKLY, "09:30", 2, 0
        )

        # Should be a Wednesday at 09:30 UTC
        assert next_trigger.hour == 9
        assert next_trigger.minute == 30
        # Wednesday = 2 in Python's weekday (0=Monday)
        assert next_trigger.weekday() == 2

    @pytest.mark.asyncio
    async def test_calculate_next_trigger_time_monthly(self):
        """Test calculating next trigger time for monthly frequency"""
        # Monthly on the 15th
        next_trigger = ScheduledReminderService.calculate_next_trigger_time(
            FrequencyType.MONTHLY, "18:00", 0, 15
        )

        # Should be on the 15th at 18:00 UTC
        assert next_trigger.hour == 18
        assert next_trigger.minute == 0
        assert next_trigger.day == 15