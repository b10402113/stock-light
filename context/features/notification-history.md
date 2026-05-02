# NotificationHistory Spec

## Overview

NotificationHistoryTable records every notification sent to users when their IndicatorSubscription conditions are triggered. It serves as an audit trail and history log for all notification attempts, tracking delivery status and LINE message IDs for troubleshooting.

## Requirements

### Data Model

- Create SQLAlchemy NotificationHistory model in `src/subscriptions/model.py` (same domain as IndicatorSubscription):
  - Inherits from `Base` (provides `id`, `created_at`, `updated_at`, `is_deleted`)
  - `user_id`: Integer foreign key to users.id (matches User model)
  - `indicator_subscription_id`: Integer foreign key to indicator_subscriptions.id (matches IndicatorSubscription model)
  - `triggered_value`: Numeric(10, 4) - the value that triggered the notification (matches target_value type)
  - `send_status`: String(20) - enum values: pending, sent, failed
  - `line_message_id`: Nullable String(100) - LINE message ID for tracking
  - `triggered_at`: DateTime(timezone=True) - when the condition was triggered

### Database Migration

- Create Alembic migration with:
  - Foreign key constraint on `user_id` referencing `users.id`
  - Foreign key constraint on `indicator_subscription_id` referencing `indicator_subscriptions.id`
  - Index on `user_id` (foreign key index)
  - Index on `indicator_subscription_id` (foreign key index)
  - Index on `triggered_at` for time-range queries
  - Index on `send_status` for filtering failed notifications
  - Composite index on `(user_id, triggered_at DESC)` for user notification history

### Relationships

- `user`: Many-to-one relationship to User model
- `indicator_subscription`: Many-to-one relationship to IndicatorSubscription model

### Service Layer

- Create NotificationHistoryService in `src/subscriptions/service.py`:
  - `create_log()` - create notification log entry before sending
  - `get_user_history()` - get notification history for a user with keyset pagination
  - `update_status()` - update send_status and line_message_id after LINE API call
  - `get_failed_notifications()` - query for retry mechanism (filter by send_status='failed')

### API Endpoints

- GET /notifications/history - list current user's notification history (keyset paginated)
- GET /notifications/history/{id} - get specific notification details

### Pagination

- Use keyset pagination on `triggered_at DESC` (not `id`, because timestamps are more meaningful for history)
- Default limit: 20 items per page
- Cursor: `triggered_at` value (ISO 8601 format)

## References

- @doc/database-mermaid.md - NotificationHistoryTable schema definition
- @doc/database-standard.md - Column conventions and index naming
- @src/subscriptions/model.py - IndicatorSubscription model for relationship
- @src/users/model.py - User model for relationship
- @src/models/base.py - Base model with common fields
