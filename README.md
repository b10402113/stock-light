# Stock Light

## Problem (Core Idea)

Stock Light is a stock price notification service that solves the problem of monitoring stock prices and technical indicators manually. Users can subscribe to specific stock price thresholds or technical indicator conditions via LINE, and the system automatically monitors these conditions and pushes real-time notifications when triggers are met, eliminating the need for constant manual checking.

## Users

- **LINE User**
  Regular users who interact with the system through LINE messaging platform. They can subscribe to stock alerts, manage their subscriptions, and receive notifications when their defined conditions are triggered.

- **Admin User**
  System administrators who manage the backend infrastructure, monitor system health, and ensure the notification service runs smoothly.

## Features

- Stock price threshold alerts (subscribe to specific target prices)
- Technical indicator monitoring (RSI, KD, MACD)
- LINE Messaging API integration for user interaction
- Real-time stock data from Fugle API
- Subscription management (subscribe, unsubscribe, list subscriptions)
- Scheduled monitoring during trading hours
- Webhook handling for LINE user commands
- Price history tracking and technical indicator calculation
- Automatic notification push when conditions are met

## Tech stack

- **Backend Framework**: FastAPI 0.115+
- **Language**: Python 3.11+
- **Database**: PostgreSQL with SQLAlchemy 2.0 (async)
- **Cache & Message Broker**: Redis
- **Async Task Processing**: Celery + Celery Beat
- **Data Validation**: Pydantic 2.7+
- **Migrations**: Alembic 1.13+
- **HTTP Client**: httpx 0.27+
- **Authentication**: PyJWT 2.9+
- **External APIs**:
  - Fugle Market Data API (stock quotes)
  - LINE Messaging API (notifications)
- **Code Quality**: ruff 0.6+ (linting & formatting)
- **Reverse Proxy**: Nginx