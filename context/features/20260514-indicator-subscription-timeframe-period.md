# Indicator Subscription Timeframe and Period Fields Spec

## Overview

Extend indicator subscriptions to support timeframe (day/week) and period configuration for technical indicators. Users need to specify the data granularity and indicator calculation period when creating subscriptions.

## Requirements

### Core Fields to Add

- **timeframe**: Required field for data granularity
  - Values: `"D"` (day) or `"W"` (week)
  - Default: `"D"`
  - Affects which historical data is used for indicator calculation

- **period**: Optional field for indicator calculation period
  - Applicable to: `RSI`, `SMA` (Simple Moving Average)
  - Values: Integer (e.g., 7, 14, 21)
  - Default: 14 for RSI, configurable for SMA
  - Not applicable to: `MACD`, `KD` (these have fixed periods)

### Indicator-Specific Validation

| Indicator | period Required? | Default Period | Valid Range |
|-----------|------------------|----------------|-------------|
| RSI       | Optional         | 14             | 5-50        |
| SMA       | Optional         | 20             | 5-200       |
| MACD      | Not applicable   | 12/26/9 (fixed)| N/A         |
| KD        | Not applicable   | 9 (fixed)      | N/A         |
| PRICE     | Not applicable   | N/A            | N/A         |

### Database Schema Changes

1. Add `timeframe` column to `indicator_subscriptions` table
   - Type: `VARCHAR(1)`
   - NOT NULL, DEFAULT `'D'`
   - Constraint: CHECK (timeframe IN ('D', 'W'))

2. Add `period` column to `indicator_subscriptions` table
   - Type: `SMALLINT`
   - NULL (optional)
   - CHECK constraint: (period >= 5 AND period <= 200) OR period IS NULL

3. Update unique constraint `uix_user_stock_single_condition`
   - Include `timeframe` and `period` to allow same condition with different timeframes/periods

### Schema Updates

- Add `Timeframe` enum (D, W) to `src/subscriptions/schema.py`
- Update `IndicatorSubscriptionBase`:
  - Add `timeframe: Timeframe = Field(Timeframe.D, description="Data timeframe: D (day) or W (week)")`
  - Add `period: Optional[int] = Field(None, ge=5, le=200, description="Indicator period for RSI/SMA")`
- Add model validator to ensure `period` is only set for RSI/SMA indicators
- Update `IndicatorSubscriptionUpdate`, `IndicatorSubscriptionResponse` with new fields
- Update `CompoundCondition.Condition` to also include `timeframe` and `period` for each condition

### API Behavior

- **GET `/subscriptions/indicators/config`**: Return indicator field requirements for frontend
  - Response structure:
    ```json
    {
      "indicators": {
        "rsi": {
          "label": "RSI (Relative Strength Index)",
          "timeframe": {"required": true, "default": "D", "options": ["D", "W"]},
          "period": {"required": false, "default": 14, "min": 5, "max": 50},
          "operators": [">", "<", ">=", "<=", "==", "!="]
        },
        "sma": {
          "label": "SMA (Simple Moving Average)",
          "timeframe": {"required": true, "default": "D", "options": ["D", "W"]},
          "period": {"required": false, "default": 20, "min": 5, "max": 200},
          "operators": [">", "<", ">=", "<=", "==", "!="]
        },
        "macd": {
          "label": "MACD",
          "timeframe": {"required": true, "default": "D", "options": ["D", "W"]},
          "period": null,
          "operators": [">", "<", ">=", "<=", "==", "!="],
          "note": "Fixed periods: 12/26/9"
        },
        "kd": {
          "label": "KD (Stochastic Oscillator)",
          "timeframe": {"required": true, "default": "D", "options": ["D", "W"]},
          "period": null,
          "operators": [">", "<", ">=", "<=", "==", "!="],
          "note": "Fixed period: 9"
        },
        "price": {
          "label": "Price",
          "timeframe": {"required": true, "default": "D", "options": ["D", "W"]},
          "period": null,
          "operators": [">", "<", ">=", "<=", "==", "!="]
        }
      }
    }
    ```

- POST `/subscriptions/indicators`: Accept new fields, validate based on indicator_type
- PATCH `/subscriptions/indicators/{id}`: Allow updating timeframe/period
- GET `/subscriptions/indicators`: Return timeframe/period in response
- Indicator calculation job must respect `timeframe` and `period` when evaluating conditions

### Migration Considerations

- Backfill existing subscriptions with `timeframe='D'` and `period=NULL`
- No data loss - existing behavior preserved (daily data, default periods)
- Update calculated_indicators structure to nested format by timeframe:
  ```json
  {
    "D": {
      "rsi_14": 65.5,
      "rsi_7": 70.2,
      "sma_20": 125.5,
      "sma_50": 120.8,
      "kd_k": 72.3,
      "kd_d": 68.1,
      "macd": 0.85,
      "macd_signal": 0.72,
      "macd_hist": 0.13
    },
    "W": {
      "rsi_14": 68.2,
      "sma_20": 128.0
    },
    "calculated_at": "2026-05-14T10:30:00Z"
  }
  ```

## Implementation Plan

### Phase 1: Database Migration

1. Create Alembic migration
   - Add `timeframe` column (VARCHAR(1), NOT NULL, DEFAULT 'D')
   - Add `period` column (SMALLINT, NULL)
   - Add CHECK constraints
   - Update unique index to include new columns
   - Backfill existing data

2. Update `src/subscriptions/model.py`
   - Add `timeframe` and `period` mapped columns
   - Update `__table_args__` indexes

### Phase 2: Schema & Validation

1. Update `src/subscriptions/schema.py`
   - Add `Timeframe` enum
   - Add fields to all relevant schemas
   - Add validators for period/indicator compatibility
   - Update `Condition` model for compound conditions
   - Add `IndicatorConfigResponse` schema for GET config endpoint

2. Update `src/subscriptions/service.py`
   - Handle new fields in create/update logic
   - Update query filters if needed
   - Add `get_indicator_config()` static method to return field requirements

3. Update `src/subscriptions/router.py`
   - Add GET `/subscriptions/indicators/config` endpoint
   - Return IndicatorConfigResponse with indicator requirements

### Phase 3: Indicator Calculation Integration

1. Update `src/stocks/indicators.py`
   - Support configurable periods for RSI and SMA
   - Calculate indicators for both daily and weekly data
   - Store period-specific values in `calculated_indicators`

2. Update `src/tasks/jobs/indicator_jobs.py`
   - Calculate multiple period variants
   - Respect subscription timeframe when evaluating

### Phase 4: Tests

- Add GET `/subscriptions/indicators/config` endpoint tests
  - Verify response structure and all indicator configs
  - Verify correct defaults and validation ranges
- Add test cases for valid timeframe/period combinations
- Add validation tests for invalid period with MACD/KD
- Add unique constraint tests (same stock, different timeframe)
- Add indicator calculation tests with custom periods
- Update existing subscription tests with new fields

## References

- @src/subscriptions/schema.py - IndicatorSubscriptionBase, Condition model
- @src/subscriptions/model.py - IndicatorSubscription table schema
- @src/stocks/indicators.py - Indicator calculation logic
- @context/features/20260513-technical-indicator-calculation.md - Indicator calculation feature
- @docs/rules/database.md - Migration guidelines