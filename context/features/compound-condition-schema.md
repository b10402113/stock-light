# Compound Condition Pydantic Model Spec

## Overview

Define explicit Pydantic models for the `compound_condition` field to enforce structure validation and provide clear API documentation for frontend integration. Currently `compound_condition` is a loose `Optional[dict]` without schema enforcement.

**Note**: The model already uses JSONB for storage (`mapped_column(JSONB, nullable=True)`). This spec focuses on Pydantic schema validation.

## Requirements

### 1. Add LogicOperator Enum

Create new enum in `src/subscriptions/schema.py`:

```python
class LogicOperator(StrEnum):
    """邏輯運算子"""
    AND = "and"
    OR = "or"
```

**Existing Operator Enum** (reuse, no changes needed):
```python
class Operator(StrEnum):
    """比較運算子"""
    GT = ">"
    LT = "<"
    GTE = ">="
    LTE = "<="
    EQ = "=="
    NEQ = "!="
```

### 2. Define Pydantic Models in schema.py

Create explicit models for compound condition structure:

```python
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Condition(BaseModel):
    """Single condition within a compound condition"""
    indicator_type: IndicatorType = Field(..., description="Indicator type: rsi, macd, kd, price")
    operator: Operator = Field(..., description="Comparison operator: >, <, >=, <=, ==, !=")
    target_value: Decimal = Field(..., ge=0, description="Target threshold value")


class CompoundCondition(BaseModel):
    """Complex conditions with AND/OR logic"""
    logic: LogicOperator = Field(..., description="Logic operator: and, or")
    conditions: list[Condition] = Field(..., min_length=1, description="List of conditions")

    @field_validator("conditions")
    @classmethod
    def validate_conditions_count(cls, v: list[Condition]) -> list[Condition]:
        if len(v) > 10:
            raise ValueError("Maximum 10 conditions allowed")
        return v
```

### 2. Update Existing Schemas

Modify `IndicatorSubscriptionBase`, `IndicatorSubscriptionUpdate`, and `IndicatorSubscriptionResponse`:

- Change `compound_condition: Optional[dict]` to `compound_condition: Optional[CompoundCondition]`
- Add validation for Plan-level max conditions quota (Regular=1, Pro=3, Pro Max=unlimited)

### 3. Add Compound Condition Documentation

Create dedicated section in `context/api/api-subscription.md`:

```markdown
### Compound Condition Schema

Compound conditions allow combining multiple indicator conditions with AND/OR logic.

**Structure**:

| Field      | Type            | Required | Description                        |
| ---------- | --------------- | -------- | ---------------------------------- |
| logic      | string          | Yes      | "and" or "or"                      |
| conditions | array[Condition]| Yes      | List of 1-10 conditions            |

**Condition Schema**:

| Field          | Type    | Required | Description                              |
| -------------- | ------- | -------- | ---------------------------------------- |
| indicator_type | string  | Yes      | Indicator: rsi, macd, kd, price          |
| operator       | string  | Yes      | Operator: >, <, >=, <=, ==, !=           |
| target_value   | decimal | Yes      | Target threshold (>= 0)                  |

**Example**:

```json
{
  "compound_condition": {
    "logic": "and",
    "conditions": [
      {"indicator_type": "rsi", "operator": "<", "target_value": "30"},
      {"indicator_type": "macd", "operator": ">", "target_value": "0"}
    ]
  }
}
```

**Logic Behavior**:
- `and`: All conditions must be true to trigger alert
- `or`: Any condition being true triggers alert
```

### 4. Add Tests

- Test valid compound condition with AND logic
- Test valid compound condition with OR logic
- Test invalid logic value (reject non-AND/OR)
- Test empty conditions array (reject)
- Test too many conditions (reject > 10)
- Test nested compound condition (reject if needed)

### 5. Service Layer Validation

Add quota validation in service.py:

```python
async def validate_compound_condition_quota(
    db: AsyncSession,
    user_id: int,
    compound_condition: Optional[CompoundCondition]
) -> None:
    if not compound_condition:
        return

    plan = await plans_service.get_active_plan(db, user_id)
    max_conditions = plan.level_config.max_conditions_per_alert

    if max_conditions != -1 and len(compound_condition.conditions) > max_conditions:
        raise QuotaExceededError(
            f"Condition quota exceeded: {len(compound_condition.conditions)}/{max_conditions}"
        )
```

### 6. Level Config Update (if needed)

Add `max_conditions_per_alert` to LevelConfig if not present:

| Level | Name    | Max Conditions per Alert |
| ----- | ------- | ------------------------ |
| 1     | Regular | 1                        |
| 2     | Pro     | 3                        |
| 3     | Pro Max | 10 (or -1 for unlimited) |
| 4     | Admin   | Unlimited (-1)           |

## References

- @context/api/api-subscription.md - Current API documentation
- @src/subscriptions/schema.py - Existing schema definitions
- @src/subscriptions/model.py - IndicatorSubscription model with JSONB field
- @src/plans/model.py - LevelConfig for quota limits
- @tests/test_compound_condition.py - Existing tests for reference