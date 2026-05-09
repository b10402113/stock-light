# [Project Name]

You are a senior software engineer proficient in the Python language, familiar with cloud-native development and software engineering best practices. Your task is to assist me in completing the development of this project in a high-quality, maintainable manner.

## Project overview

[Description]

## 1. Tech Stack & Environment

- **Language**:
- **Web Framework / HTTP Library**:
- **Database / ORM**:
- **Build / Test / Quality**:
  - **Build**:
  - **Test**:
  - **Code Style**:
  - **Static Analysis**:

---

## Common Commands

### Environment Setup

```bash
#
# Install UV package manager (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync

# Install development dependencies
uv sync --dev
```

### Development Server

```bash
# Run development server with hot reload
uv run uvicorn src:app --reload --host 0.0.0.0 --port 8000

# Run production server
uv run uvicorn src:app --host 0.0.0.0 --port 8000 --workers 4
```

### Database Operations

```bash
# Initialize database (first time setup)
uv run aerich init-db

# Generate migration after model changes
uv run aerich migrate --name "describe_your_changes"

# Apply migrations
uv run aerich upgrade

# View migration history
uv run aerich history
```

### Testing

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_users.py

# Run with coverage report
uv run pytest --cov=src --cov-report=html
```
