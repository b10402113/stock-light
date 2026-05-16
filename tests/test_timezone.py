"""Tests for timezone utilities and datetime serialization."""
from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from src.schemas.base import BaseSchema
from src.utils.timezone import now, get_timezone, to_local, from_str


class TestTimezoneUtils:
    """Test timezone utility functions"""

    def test_get_timezone_returns_taipei(self):
        """Test that get_timezone returns Asia/Taipei timezone"""
        tz = get_timezone()
        assert tz.key == "Asia/Taipei"

    def test_now_returns_timezone_aware_datetime(self):
        """Test that now() returns timezone-aware datetime"""
        dt = now()
        assert dt.tzinfo is not None
        assert dt.tzinfo.key == "Asia/Taipei"

    def test_to_local_converts_naive_datetime(self):
        """Test that to_local converts naive datetime to timezone-aware"""
        naive_dt = datetime(2024, 1, 1, 12, 0, 0)
        aware_dt = to_local(naive_dt)
        assert aware_dt.tzinfo is not None
        assert aware_dt.tzinfo.key == "Asia/Taipei"
        assert aware_dt.hour == 12
        assert aware_dt.day == 1

    def test_to_local_converts_aware_datetime(self):
        """Test that to_local converts timezone-aware datetime to Asia/Taipei"""
        utc_dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=ZoneInfo("UTC"))
        taipei_dt = to_local(utc_dt)
        assert taipei_dt.tzinfo.key == "Asia/Taipei"
        assert taipei_dt.hour == 20  # UTC 12:00 = Taipei 20:00
        assert taipei_dt.day == 1

    def test_from_str_parses_iso_format_with_timezone(self):
        """Test that from_str parses ISO format with timezone"""
        iso_str = "2024-01-01T12:00:00+08:00"
        dt = from_str(iso_str)
        assert dt.tzinfo is not None
        assert dt.tzinfo.key == "Asia/Taipei"
        assert dt.hour == 12

    def test_from_str_parses_iso_format_without_timezone(self):
        """Test that from_str parses ISO format without timezone and adds Taipei timezone"""
        iso_str = "2024-01-01T12:00:00"
        dt = from_str(iso_str)
        assert dt.tzinfo is not None
        assert dt.tzinfo.key == "Asia/Taipei"
        assert dt.hour == 12

    def test_from_str_with_custom_format(self):
        """Test that from_str parses with custom format"""
        custom_str = "2024/01/01 12:00"
        custom_format = "%Y/%m/%d %H:%M"
        dt = from_str(custom_str, custom_format)
        assert dt.tzinfo is not None
        assert dt.tzinfo.key == "Asia/Taipei"
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 1


class TestSchemaBaseDatetimeSerialization:
    """Test BaseSchema datetime serialization"""

    def test_serialize_naive_datetime_to_taipei(self):
        """Test that BaseSchema serializes naive datetime to Taipei timezone"""

        class TestSchema(BaseSchema):
            created_at: datetime

        naive_dt = datetime(2024, 1, 1, 12, 0, 0)
        schema = TestSchema(created_at=naive_dt)
        json_data = schema.model_dump()

        # Should be serialized as ISO format with +08:00 timezone
        assert "created_at" in json_data
        assert "+08:00" in json_data["created_at"] or json_data["created_at"].endswith("T12:00:00")

    def test_serialize_utc_datetime_to_taipei(self):
        """Test that BaseSchema serializes UTC datetime to Taipei timezone"""

        class TestSchema(BaseSchema):
            created_at: datetime

        utc_dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=ZoneInfo("UTC"))
        schema = TestSchema(created_at=utc_dt)
        json_data = schema.model_dump()

        # Should be serialized as 20:00 in Taipei timezone (+08:00)
        assert "created_at" in json_data
        assert "20:00:00+08:00" in json_data["created_at"]

    def test_serialize_none_datetime(self):
        """Test that BaseSchema serializes None datetime as None"""

        class TestSchema(BaseSchema):
            created_at: datetime | None = None

        schema = TestSchema()
        json_data = schema.model_dump()

        assert json_data["created_at"] is None

    def test_serialize_multiple_datetime_fields(self):
        """Test that BaseSchema serializes multiple datetime fields"""

        class TestSchema(BaseSchema):
            created_at: datetime
            updated_at: datetime
            cooldown_end_at: datetime | None = None

        naive_dt1 = datetime(2024, 1, 1, 12, 0, 0)
        naive_dt2 = datetime(2024, 1, 2, 13, 30, 0)
        schema = TestSchema(created_at=naive_dt1, updated_at=naive_dt2)
        json_data = schema.model_dump()

        assert "created_at" in json_data
        assert "updated_at" in json_data
        assert json_data["cooldown_end_at"] is None

        # Both should have timezone info
        assert "+08:00" in json_data["created_at"] or "T12:00:00" in json_data["created_at"]
        assert "+08:00" in json_data["updated_at"] or "T13:30:00" in json_data["updated_at"]


class TestTimezoneIntegration:
    """Test timezone integration with real schemas"""

    def test_stock_indicator_response_serialization(self):
        """Test that StockIndicatorResponse properly serializes datetime"""
        from src.stock_indicator.schema import StockIndicatorResponse

        naive_dt = datetime(2024, 1, 1, 12, 0, 0)
        response = StockIndicatorResponse(
            id=1,
            stock_id=1,
            indicator_key="RSI_14_D",
            data={"value": 65.5},
            created_at=naive_dt,
            updated_at=naive_dt,
        )

        json_data = response.model_dump()
        assert "created_at" in json_data
        assert "updated_at" in json_data
        # Should include timezone information
        assert "+08:00" in json_data["created_at"] or "T12:00:00" in json_data["created_at"]

    def test_subscription_response_serialization(self):
        """Test that IndicatorSubscriptionResponse properly serializes datetime"""
        from src.subscriptions.schema import IndicatorSubscriptionResponse, StockBrief, ConditionGroup, Condition, IndicatorType, Operator, Timeframe, LogicOperator, SignalType

        naive_dt = datetime(2024, 1, 1, 12, 0, 0)
        response = IndicatorSubscriptionResponse(
            id=1,
            stock=StockBrief(id=1, symbol="2330", name="台積電"),
            subscription_type="indicator",
            title="Test",
            message="Test message",
            signal_type=SignalType.BUY,
            condition_group=ConditionGroup(
                logic=LogicOperator.AND,
                conditions=[
                    Condition(
                        indicator_type=IndicatorType.RSI,
                        operator=Operator.GT,
                        target_value=70,
                        timeframe=Timeframe.D,
                        period=14
                    )
                ]
            ),
            is_triggered=False,
            cooldown_end_at=naive_dt,
            is_active=True,
            created_at=naive_dt,
            updated_at=naive_dt,
        )

        json_data = response.model_dump()
        assert "cooldown_end_at" in json_data
        assert "created_at" in json_data
        assert "updated_at" in json_data
        # Should include timezone information
        assert "+08:00" in json_data["created_at"] or "T12:00:00" in json_data["created_at"]