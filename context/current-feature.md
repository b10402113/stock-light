# Current Feature

## Status

Not Started

## Goals

<!-- Add goals when starting a new feature -->

## Notes

<!-- Add notes when starting a new feature -->

## History

- 2026-05-16: Indicator Subscription Simplification
  - Removed redundant single-condition fields (indicator_type, operator, target_value, timeframe, period)
  - Made condition_group required JSONB with CHECK constraint (1-10 conditions)
  - Renamed compound_condition to condition_group in all schemas
  - Added Alembic migration to convert existing subscriptions to condition_group format
  - Simplified service logic by removing dual-mode handling
  - Updated StockIndicatorService to extract conditions uniformly from condition_group
  - Updated all 106 subscription-related tests to use condition_group format
  - Updated API documentation with new schema structure
  - Benefits: One format for all conditions (1-N), cleaner code, consistent API
- 2026-05-16: Indicator Update Cron Job Refactor
  - Renamed calculate_stock_indicators to update_indicator
  - Simplified job to run every minute (CRON_INDICATOR_MINUTES=*/1)
  - Removed stock_id parameter, job now queries all subscriptions automatically
  - Updated worker imports and cron job registration
  - Updated test files to use new function name
  - Benefits: Cleaner code, automatic processing of all subscribed stocks
- 2026-05-16: Indicator Subscription Notification Check Implementation
  - Added Redis tracking in update_indicator job (REDIS_INDICATOR_UPDATED_KEY)
  - Created check_indicator_subscriptions cron job running every minute
  - Implemented condition evaluation logic (evaluate_subscription, AND/OR logic)
  - Added helper functions (build_indicator_key, extract_indicator_value, compare_values)
  - Implemented notification sending with cooldown support
  - Registered cron job in DefaultWorkerSettings
  - Added configuration settings (SUBSCRIPTION_COOLDOWN_HOURS, SUBSCRIPTION_CHECK_BATCH_SIZE)
  - Created comprehensive tests (35 tests, all passing)
  - Fixed bug: cron job minute parameter must be set, not range object
  - Verified working: jobs executed successfully, notifications sent
  - Benefits: High-performance subscription check (only updated stocks), immediate notifications
- 2026-05-16: Unified Error Response Handling Implementation
  - Created HTTP-level exception classes (BadRequestError, UnauthorizedError, ForbiddenError, NotFoundError, ValidationError, RateLimitError, InternalServerError)
  - Implemented global exception handlers for each HTTP status code
  - Override RequestValidationError for consistent validation error messages
  - Override HTTPException for standard FastAPI errors
  - Add generic Exception handler with logging for unhandled errors
  - Created comprehensive test suite (11 tests, all passing)
  - Updated API documentation with unified error response format and examples
  - Benefits: Consistent error format across all endpoints, better error messages, easier debugging