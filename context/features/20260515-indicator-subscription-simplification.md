# Indicator Subscription Simplification Spec

## Overview

Simplify the indicator subscription data structure by removing redundant individual condition fields (`indicator_type`, `operator`, `target_value`) and always using `compound_condition` JSONB to store conditions. This supports 1~N conditions uniformly and reduces code complexity.

## Requirements

### Database Changes

1. **Remove nullable columns** from `indicator_subscriptions` table:
   - Remove `indicator_type` (VARCHAR(50), nullable)
   - Remove `operator` (VARCHAR(10), nullable)
   - Remove `target_value` (NUMERIC(10,4), nullable)

2. **Make `compound_condition` non-nullable**:
   - Change `compound_condition` from nullable JSONB to required JSONB
   - Add CHECK constraint to validate JSONB structure

3. **Remove unique index for single conditions**:
   - Drop `uix_user_stock_single_condition` index (no longer needed)
   - Create new unique index on `(user_id, stock_id, compound_condition)` where `is_deleted = false`

4. **Create Alembic migration**:
   - Data migration: Convert existing single-condition subscriptions to compound_condition format
   - Example: `{"logic": "and", "conditions": [{"indicator_type": "rsi", "operator": ">", "target_value": 70, "timeframe": "D", "period": 14}]}`

### Schema Changes

1. **Update `Condition` model**:
   - Keep all fields: `indicator_type`, `operator`, `target_value`, `timeframe`, `period`
   - Add validation for each indicator type

2. **Update `CompoundCondition` model**:
   - Rename from "Compound" to just "ConditionGroup" (semantic change - it's always used)
   - Keep `logic` field (AND/OR)
   - Keep `conditions` list with `min_length=1, max_length=10`

3. **Simplify `IndicatorSubscriptionBase` schema**:
   - Remove `indicator_type`, `operator`, `target_value` fields
   - Remove `period` field (now inside each condition)
   - Remove `timeframe` field (now inside each condition)
   - Make `compound_condition` required (rename to `condition_group`)
   - Remove complex validation logic for dual-mode support

4. **Update response schemas**:
   - Remove nullable individual condition fields from response
   - Always return `condition_group`

### Service Changes

1. **Remove dual-mode handling**:
   - Remove `enrich_subscription_with_stock` conversion logic for single vs compound
   - Remove `check_duplicate` logic for both single and compound conditions
   - Simplify to only handle `condition_group`

2. **Update condition evaluation logic**:
   - Simplify alert checking - only one format to evaluate
   - Remove branching for single vs compound conditions

3. **Update worker logic**:
   - Simplify indicator subscription fetching
   - Extract indicator keys from `condition_group.conditions` uniformly

### Test Updates

1. **Update existing tests**:
   - Convert all test fixtures to use `condition_group` format
   - Remove tests for single-condition mode
   - Add tests for single-condition as compound (1 condition in group)

2. **New test coverage**:
   - Test single-condition wrapped in condition_group
   - Test constraint validation
   - Test data migration correctness

## Implementation Steps

1. Create Alembic migration with data conversion
2. Update model.py - remove columns, change compound_condition to required
3. Update schema.py - simplify schemas, rename compound_condition
4. Update service.py - remove dual-mode logic
5. Update router.py - simplify validation
6. Update worker/indicator_jobs.py - extract conditions uniformly
7. Update all tests
8. Run full test suite to verify

## Benefits

- **Reduced complexity**: One format for all conditions (1~N)
- **Cleaner code**: No branching logic for single vs compound
- **Easier maintenance**: Less code to understand and modify
- **Consistent API**: Frontend always sends/receives same structure

## References

- @src/subscriptions/model.py - Current model with nullable fields
- @src/subscriptions/schema.py - Current dual-mode validation
- @src/subscriptions/service.py - Dual-mode handling
- @context/features/20260510-compound-condition-model-fix.md - Previous compound condition work
- @context/features/20260510-compound-condition-schema.md - Schema design history