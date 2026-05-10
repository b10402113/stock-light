# Compound Condition Model Fix Spec

## Overview

Fix two critical issues in the IndicatorSubscription model that were overlooked during the compound condition schema implementation: nullable constraint conflict between single vs compound conditions, and inefficient index design.

## Requirements

### 1. Fix Single Condition Nullable Constraints (Critical)
- Change `indicator_type`, `operator`, `target_value` from `nullable=False` to `nullable=True`
- These fields must be nullable to support compound conditions
- When a compound condition is stored, single condition fields should be NULL
- Current design forces fake values (e.g., indicator_type="none") which is bad practice

### 2. Optimize Index Design
- Remove redundant/ineffective indexes:
  - `is_active_idx`: Boolean field with low cardinality (only true/false) is ineffective
  - `user_id_idx`: Redundant due to leftmost prefix rule (covered by `user_stock_idx`)
- Add optimized partial indexes:
  - `idx_indicator_subs_on_stock_active`: Partial index on `stock_id WHERE (is_active = true AND is_deleted = false)` for price trigger queries
  - `idx_indicator_subs_on_user`: Partial index on `user_id WHERE (is_deleted = false)` for user list queries
  - `uix_user_stock_single_condition`: Unique constraint for single conditions only, with `postgresql_where="(is_deleted = false AND compound_condition IS NULL)"`

## Technical Details

### Note on is_deleted Field
The `is_deleted` field is already defined in the Base model (`src/models/base.py:26-30`) and inherited by all models including IndicatorSubscription. No changes needed - the unique index's `postgresql_where` clause correctly references this inherited field.

### Model Changes
```python
# Single condition fields - must be nullable for compound conditions
indicator_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
operator: Mapped[str | None] = mapped_column(String(10), nullable=True)
target_value: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
```

### Index Strategy
```python
__table_args__ = (
    # Optimized for price trigger queries
    Index(
        "idx_indicator_subs_on_stock_active",
        "stock_id",
        postgresql_where="(is_active = true AND is_deleted = false)"
    ),

    # Optimized for user list queries
    Index(
        "idx_indicator_subs_on_user",
        "user_id",
        postgresql_where="(is_deleted = false)"
    ),

    # Unique constraint only for single conditions
    Index(
        "uix_user_stock_single_condition",
        "user_id",
        "stock_id",
        "indicator_type",
        "operator",
        "target_value",
        unique=True,
        postgresql_where="(is_deleted = false AND compound_condition IS NULL)"
    ),
)
```

## Migration Impact

- Requires database migration to:
  - Change nullable constraints on indicator_type, operator, target_value (from NOT NULL to NULL)
  - Drop redundant indexes: `is_active_idx`, `user_id_idx`, `stock_id_idx`
  - Create new optimized indexes with partial conditions
- Existing data with single conditions will keep their values (no data loss)
- New compound condition subscriptions will have NULL single condition fields

## References

- @src/subscriptions/model.py - Model definition to be fixed
- @src/subscriptions/schema.py - Schema may need adjustment for nullable fields
- @src/subscriptions/service.py - Service logic for handling nullable fields
- @tests/test_compound_condition.py - Tests need update for nullable fields
- @docs/rules/database.md - Index strategy and soft delete guidelines