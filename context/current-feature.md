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