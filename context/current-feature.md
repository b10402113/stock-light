# Indicator Update Cron Job Refactor

## Status

In Progress

## Goals

- Remove existing `calculate_stock_indicators` job and its cron entry from worker
- Create new `update_indicator` cron job that runs every minute
- Query `indicator_subscriptions` to get required indicators and calculate them
- Upsert calculated indicators to `stock_indicator` table
- Update `CRON_INDICATOR_MINUTES` config to `*/1`

## Notes

- Keep existing helper functions: `StockIndicatorService.get_required_indicator_keys()`, yfinance fallback
- Use existing calculator from `src/stock_indicator/calculator.py`
- Maintain Redis retry tracking for failed stocks
- Parse `condition_group` JSONB to extract indicator_type, period, timeframe

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