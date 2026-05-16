"""Base schemas with unified datetime handling."""
from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, field_serializer


class BaseSchema(BaseModel):
    """Base schema with unified datetime serialization.

    All response schemas should inherit from this class to ensure
    consistent datetime serialization to Asia/Taipei timezone.
    """

    model_config = ConfigDict(from_attributes=True)

    @field_serializer(
        "created_at",
        "updated_at",
        "cooldown_end_at",
        "next_trigger_at",
        "due_date",
        "expires_at",
        "last_triggered_at",
        when_used="always",
        check_fields=False,
    )
    def serialize_datetime_to_taipei(self, dt: datetime | None) -> str | None:
        """Serialize datetime to Asia/Taipei timezone ISO format.

        Args:
            dt: Datetime object (naive or timezone-aware) or None

        Returns:
            str | None: ISO format string with timezone offset, or None
        """
        if dt is None:
            return None

        # Convert to Asia/Taipei timezone
        taipei_tz = ZoneInfo("Asia/Taipei")
        if dt.tzinfo is None:
            # Naive datetime: assume it's already in Asia/Taipei
            dt = dt.replace(tzinfo=taipei_tz)
        else:
            # Aware datetime: convert to Asia/Taipei
            dt = dt.astimezone(taipei_tz)

        return dt.isoformat()