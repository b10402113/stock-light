# Add Source Field to Stock Model Spec

## Overview

Add a `source` field to the Stock model to track where stock data originates (Fugle API or YFinance). This enables debugging data quality issues and supports future source-specific handling.

## Requirements

### Database Field
- Add `source` column as SmallInteger (1-2 bytes)
- Default value: 1 (FUGLE)
- Non-nullable
- Existing stocks will default to FUGLE

### Enum Definition
- Define `StockSource(IntEnum)` in schema.py
- Values: `FUGLE = 1`, `YFINANCE = 2`
- Import from `enum` module (follow ErrorCode pattern)

### Schema Updates
- StockResponse: Add `source: StockSource` field
- StockCreate: Add optional source field with default `StockSource.FUGLE`

### Migration
- Create Alembic migration: `2026-05-06_add_stock_source.py`
- Add column with server default for existing rows

### Seed Script Update
- Update `scripts/seed_taiwan_stocks.py` to set `source=StockSource.FUGLE`

### Testing
- Update test payloads to include source field
- Verify source appears in API responses as integer (1 or 2)

## Implementation Pattern

```python
# src/stocks/schema.py
from enum import IntEnum

class StockSource(IntEnum):
    """股票資料來源"""
    FUGLE = 1
    YFINANCE = 2

# src/stocks/model.py
from sqlalchemy import SmallInteger

source: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
```

## References

- @src/stocks/model.py - Stock model to update
- @src/stocks/schema.py - Schemas and enum to add
- @src/exceptions.py - IntEnum pattern reference (ErrorCode)
- @scripts/seed_taiwan_stocks.py - Seed script to update
- @tests/test_stocks_router.py - Tests to update