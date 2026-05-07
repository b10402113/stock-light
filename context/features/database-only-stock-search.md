# Database-Only Stock Search with Taiwan Seed Data Spec

## Overview

Remove YFinance API fallback from stock search functionality and populate database with complete Taiwan stock seed data (TSE + OTC markets). This ensures all searches are database-only, improving performance and reliability while eliminating external API dependencies for stock discovery.

## Requirements

### Search Function Simplification
- Remove `_fallback_yfinance` method from StockService
- Remove YFinanceClient parameter from `search_stocks` method signature
- Simplify search logic to only query local database
- Remove YFinanceClient dependency injection from stocks router
- Update unit tests to reflect database-only behavior

### Taiwan Stock Seed Data
- Fetch all Taiwan stocks via Fugle API endpoint: `https://api.fugle.tw/marketdata/v1.0/stock/intraday/tickers`
- Create seed script: `scripts/seed_taiwan_stocks.py`
- Required fields: symbol, name, current_price
- Handle symbol format from Fugle API response (4-digit codes)
- Store raw symbol format without .TW suffix (e.g., "2330", "1234")
- Seed script logic:
  - Call Fugle API tickers endpoint
  - Parse response to extract symbol, name, and current price
  - Insert stocks into database with `is_active=True`
  - Use bulk insert for performance
  - Skip existing stocks (check by symbol uniqueness)
  - Support re-running seed script (upsert logic)
- Expected volume: ~2,500 stocks (TSE + OTC markets)

### Database Preparation
- Verify Stock model has all required fields
- Ensure unique index on symbol column exists
- Consider adding market column to distinguish TSE vs OTC
- Update Stock schema if new fields are needed

### Testing & Validation
- Verify search returns results for common Taiwan stocks (e.g., "2330", "台積電")
- Test edge cases: partial symbol matching, Chinese name search
- Ensure all existing tests still pass after removing YFinance fallback
- Performance test: search response time with 2,500+ stocks in database

## References

- @src/stocks/service.py - Current search implementation with YFinance fallback
- @src/stocks/router.py - Dependency injection of YFinanceClient
- @src/stocks/model.py - Stock model structure
- @src/stocks/schema.py - Stock schemas
- @src/clients/yfinance_client.py - YFinance client to be removed from search flow
- @context/current-feature.md - Previous implementation history
- @CLAUDE.md - Domain self-containment principle, client layer rules