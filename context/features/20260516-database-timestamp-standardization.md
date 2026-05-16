# Database Timestamp Standardization Spec

## Overview

Standardize all database timestamp storage to Asia/Taipei timezone (UTC+8) for better clarity and consistency. Currently, timestamps are stored in UTC using `func.now()` and `datetime.utcnow()`, making it difficult to understand the actual local time without conversion.

## Requirements

### Database Configuration
- Configure PostgreSQL to use Asia/Taipei timezone as default
- Update all timestamp columns to store in Asia/Taipei timezone
- Maintain timezone-aware columns (`DateTime(timezone=True)`)

### Code Changes
- Replace `datetime.utcnow()` with timezone-aware datetime generation using Asia/Taipei
- Create utility function for consistent timezone-aware datetime operations
- Update `soft_delete()` methods in base models
- Ensure all new datetime objects are timezone-aware
- Add unified datetime serialization in base schema for API responses

### Migration Strategy
- Create Alembic migration to convert existing UTC timestamps to Asia/Taipei
- Handle conversion of existing data without data loss
- Ensure backward compatibility during transition

### Best Practices
- Always use timezone-aware datetime objects (never naive datetime)
- Centralize timezone handling in utility module
- Add timezone configuration to project settings
- Document timezone handling in project rules

## Implementation Details

### Files to Modify

1. **src/config.py**
   - Add `TIMEZONE: str = "Asia/Taipei"` configuration
   - Add timezone utility methods

2. **src/models/base.py**
   - Import timezone utilities
   - Update `soft_delete()` to use timezone-aware datetime
   - Consider custom `func.now()` that respects timezone

3. **src/schemas/base.py** (new file)
   - Create base Pydantic schema with unified datetime serialization
   - Add `@field_serializer` decorator for datetime fields
   - Ensure all datetime fields serialize to Asia/Taipei timezone format
   - All response schemas inherit from this base class

4. **src/utils/timezone.py** (new file)
   - Create timezone utility functions:
     - `get_timezone()` - returns Asia/Taipei timezone object
     - `now()` - returns current time in Asia/Taipei timezone
     - `to_local(dt)` - converts datetime to Asia/Taipei timezone
     - `from_str(s)` - parses string to timezone-aware datetime

   **Implementation Example:**
   ```python
   from datetime import datetime
   from zoneinfo import ZoneInfo
   from pydantic import BaseModel, field_serializer

   class BaseSchema(BaseModel):
       """Base schema with unified datetime serialization"""

       @field_serializer("created_at", "updated_at", "cooldown_end_at", "next_trigger_at", "due_date", "expires_at", "last_triggered_at", when_used="always")
       def serialize_datetime_to_taipei(self, dt: datetime | None) -> str | None:
           """Serialize datetime to Asia/Taipei timezone ISO format"""
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
   ```

4. **migrations/versions/2026-05-16_set_timezone.py** (new file)
   - Set PostgreSQL timezone to Asia/Taipei
   - Convert existing timestamp columns from UTC to Asia/Taipei
   - Update `server_default` expressions

5. **All schema files**
   - Update response schemas to inherit from `BaseSchema` in `src/schemas/base.py`
   - Remove redundant datetime fields, rely on base class serialization
   - Examples: StockIndicatorResponse, SubscriptionResponse, etc.

6. **All service files**
   - Replace `datetime.utcnow()` with timezone utilities
   - Ensure all datetime operations use timezone-aware objects

### Key Considerations

1. **PostgreSQL Timezone Settings**
   - Can set timezone at database level: `ALTER DATABASE stock_light SET timezone TO 'Asia/Taipei';`
   - Or at column level using `server_default=func.now() AT TIME ZONE 'Asia/Taipei'`

2. **Python Timezone Handling**
   - Use `zoneinfo.ZoneInfo("Asia/Taipei")` (Python 3.9+)
   - Or `pytz.timezone("Asia/Taipei")` (if zoneinfo not available)
   - All datetime objects must have `.tzinfo` set

3. **Migration Safety**
   - Test migration on development database first
   - Verify timestamp conversions are correct (+8 hours)
   - Consider running in batches if large tables exist

4. **Client Display**
   - API responses should include timezone information
   - Frontend can display in user's local timezone if needed
   - Keep database in consistent timezone (Asia/Taipei)

## References

- @src/config.py
- @src/models/base.py
- @src/database.py
- @docs/rules/database.md
- PostgreSQL timezone documentation: https://www.postgresql.org/docs/current/datatype-datetime.html
- Python zoneinfo documentation: https://docs.python.org/3/library/zoneinfo.html

## Testing Strategy

### Unit Tests
- Test timezone utility functions
- Test datetime conversion accuracy
- Test timezone-aware datetime parsing

### Integration Tests
- Verify database timestamps are stored correctly
- Test `soft_delete()` updates timestamps in Asia/Taipei timezone
- Test existing data migration preserves correct time

### Manual Verification
- Check database timestamps after migration
- Verify API responses include correct timestamps
- Compare before/after timestamps for consistency

## Expected Benefits

1. **Clarity**: Developers can immediately understand timestamps without mental UTC conversion
2. **Consistency**: All timestamps in same timezone, no mixed UTC/local times
3. **User Experience**: Timestamps align with user's local time (Taiwan market hours)
4. **Debugging**: Easier to correlate timestamps with logs and user reports
5. **Compliance**: Aligns with Taiwan business operations timezone