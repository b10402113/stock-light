# YFinance Ticker Search Client Spec

## Overview

Create a new client module for Yahoo Finance API integration using the yfinance Python library. This client will provide stock ticker search functionality as an alternative or fallback data source alongside the existing Fugle API client.

## Requirements

### Dependency Setup
- Install yfinance package via pip
- Add yfinance to requirements.txt with appropriate version pinning
- Verify compatibility with existing async architecture

### Documentation Research
- Use Context7 to fetch current yfinance library documentation
- Identify key APIs for ticker search and quote retrieval
- Understand async/sync patterns and rate limiting considerations
- Document available fields and response formats

### Implementation Requirements
- Create new client module following domain self-containment principle
- Location: `src/stocks/clients/yfinance_client.py` (new clients subdirectory)
- Implement ticker search functionality:
  - Search by symbol (e.g., "AAPL", "2330.TW")
  - Search by company name (partial matching)
  - Return standardized response format compatible with existing schemas
- Follow existing client pattern from `src/stocks/client.py` (FugoClient)
- Pure API wrapper - no business logic in client layer
- Handle API errors gracefully with appropriate exception handling
- Support both synchronous and async patterns (yfinance is sync-only, may need threadpool wrapper)

### Integration Points
- Update StockService to optionally use YFinance client as fallback
- Maintain compatibility with existing TickerResponse schema if possible
- Consider creating shared client interface/protocol for multiple data sources

## References

- @context/current-feature.md - Previous Fugle ticker implementation history
- @src/stocks/client.py - Existing FugoClient implementation pattern
- @src/stocks/service.py - StockService integration point
- @src/stocks/schema.py - Existing ticker response schemas
- @CLAUDE.md - Domain self-containment principle, client layer rules