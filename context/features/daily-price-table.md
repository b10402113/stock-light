# DailyPrice Historical Data Table Spec

## Overview

Add a DailyPrice table to the stock domain to store historical OHLCV (Open, High, Low, Close, Volume) data. This enables calculation of moving averages (e.g., 200MA) and supports backtesting functionality. The current Stock model only has current_price, which is insufficient for historical analysis.

## Requirements

### Database Model
- Create DailyPrice model in src/stocks/model.py
- Primary key: BIGSERIAL (follow project convention, avoid UUID)
- Foreign key: stock_id references stocks.id (Integer)
- Date field: Date type, nullable=False
- OHLCV fields:
  - open, high, low, close: Numeric(10, 2) for precision
  - volume: BigInteger for large volume values
- Index strategy:
  - Composite unique index on (stock_id, date) to prevent duplicates
  - Individual indexes on stock_id and date for query performance
- No NULL values (follow project convention)
- Soft delete pattern: Consider if needed for data correction scenarios

### Schema Definition
- Create DailyPriceBase schema with OHLCV fields
- Create DailyPriceCreate schema for data insertion
- Create DailyPriceResponse schema for API responses
- Create DailyPriceListResponse with pagination support (keyset pagination)
- Add date range query parameters (start_date, end_date)

### Service Layer
- Add DailyPriceService class or extend StockService
- Methods:
  - bulk_insert_prices(): Batch insert historical data
  - get_prices_by_range(): Query prices within date range
  - calculate_ma(): Calculate moving average for given period (e.g., 200MA)
  - get_latest_prices(): Get most recent N days of data
- Consider caching strategy for frequently accessed data (Redis)

### API Endpoints
- GET /stocks/{stock_id}/prices - List historical prices with pagination
- Query params: start_date, end_date, limit, cursor
- POST /stocks/{stock_id}/prices - Bulk insert historical data (admin only)
- GET /stocks/{stock_id}/ma/{period} - Get moving average calculation

### Data Integration
- Extend YFinanceClient to fetch historical daily data using yfinance.history()
- Add batch job for daily price data synchronization
- yfinance is sync-only, use run_in_threadpool for async wrapper
- Handle missing data scenarios (weekends, holidays)

### Migration
- Create Alembic migration: daily_prices_table creation
- Composite unique index idx_daily_price_stock_date
- No default values needed (all fields required)
- Consider partitioning strategy for large datasets (future)

### Testing
- Model tests: DailyPrice creation and constraints
- Service tests: MA calculation, date range queries
- API tests: Pagination, date filtering
- Integration tests: Bulk insert performance
- Edge cases: Missing dates, duplicate prevention

## Implementation Pattern

```python
# src/stocks/model.py
from datetime import date
from decimal import Decimal
from sqlalchemy import BigInteger, Date, ForeignKey, Index, Numeric, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

class DailyPrice(Base):
    """日K線歷史資料表"""
    __tablename__ = "daily_prices"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # BIGSERIAL
    stock_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stocks.id"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)

    __table_args__ = (
        Index("idx_daily_price_stock_date", "stock_id", "date", unique=True),
    )

# src/stocks/schema.py
from datetime import date
from decimal import Decimal
from pydantic import Field

class DailyPriceBase(BaseModel):
    date: date
    open: Decimal = Field(..., gt=0)
    high: Decimal = Field(..., gt=0)
    low: Decimal = Field(..., gt=0)
    close: Decimal = Field(..., gt=0)
    volume: int = Field(..., ge=0)

class DailyPriceCreate(DailyPriceBase):
    stock_id: int

class DailyPriceResponse(DailyPriceBase):
    id: int
    stock_id: int
    created_at: datetime
```

## Data Considerations

### Performance
- Expected data volume: 100 stocks × 365 days × 5 years = 182,500 rows
- Composite index covers most query patterns (stock_id + date range)
- Consider Redis caching for frequently calculated indicators (200MA)

### Data Quality
- Validate OHLCV consistency (high >= low, high >= open/close, low <= open/close)
- Handle adjusted prices (stock splits, dividends) - future consideration
- Missing data handling: weekends, holidays, suspended trading

### Backtesting Support
- Ensure data completeness for accurate backtesting
- Provide efficient date range queries
- Consider adding adjusted_close field for corporate actions (future)

## References

- @src/stocks/model.py - Stock model to add relationship
- @src/stocks/schema.py - Schemas to define
- @src/stocks/service.py - Service methods to add
- @src/stocks/router.py - Endpoints to add
- @src/clients/yfinance_client.py - YFinanceClient to extend
- @docs/architecture.md - Domain-driven structure reference
- @src/models/base.py - Base model pattern
- @context/current-feature.md - Feature history tracking