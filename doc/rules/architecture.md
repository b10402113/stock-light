# 架構與模組開發規範

## 架構總覽 (Architecture Overview)

| Component      | Count | Resources       | Responsibility                 |
| -------------- | ----- | --------------- | ------------------------------ |
| Ingress/Nginx  | 1     | 0.1 CPU, 128MB  | Reverse proxy, SSL termination |
| React Frontend | 1     | 0.1 CPU, 128MB  | Static resource serving        |
| FastAPI        | 2+    | 0.25 CPU, 256MB | API request handling           |
| Postgres       | 1     | 0.5 CPU, 1GB    | Data persistence               |
| Redis          | 1     | 0.25 CPU, 512MB | Cache, Celery Broker           |
| Celery Worker  | 2     | 0.25 CPU, 256MB | Async task execution           |
| Celery Beat    | 1     | 0.1 CPU, 128MB  | Scheduled task dispatch        |

## 專案目錄結構 (Project Structure)

按領域 (Domain) 組織，而非按檔案類型。每個領域必須自給自足。

```text
src/
├── main.py               # FastAPI entry, only mounts routers
├── exceptions.py         # Global exception classes
├── dependencies.py       # Shared dependencies
├── {domain_name}/        # Domain module (e.g., users, stocks, subscriptions)
│   ├── router.py         # API endpoints
│   ├── service.py        # Business logic
│   ├── schema.py         # Pydantic Request/Response
│   ├── model.py          # SQLAlchemy Model
│   └── client.py         # External API clients (if needed)
```

## 跨領域調用規範：必須使用顯式的模組匯入，例如：from src.users import service as user_service。

```python
from src.users import service as user_service
from src.stocks.indicators import calculate_rsi
from src.subscriptions.line_client import LineClient
```

## 模組分層與責任 (Module Layer Structure)

**嚴格遵守單向依賴：router ──► service ──► model / client**

| Layer   | File       | Allowed                                                                                 | Forbidden                                                                        |
| ------- | ---------- | --------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| router  | router.py  | Define API paths, call service, use Depends, validate schema, handle HTTP exceptions    | Direct DB operations, call client.py, write business logic, return model objects |
| service | service.py | Business logic, operate model (CRUD), call other services, call client.py, return model | Define API paths, handle HTTP exceptions, directly return schema                 |
| schema  | schema.py  | Define Request/Response, Pydantic validation                                            | DB queries, business logic                                                       |
| model   | model.py   | Define DB table structure, SQLAlchemy ORM                                               | Business logic, validation                                                       |
| client  | client.py  | Wrap external API calls (Fugo, LINE)                                                    | Business logic                                                                   |

## Cross-module Call Rules

| Caller  | Callee        | Allowed | Forbidden            |
| ------- | ------------- | ------- | -------------------- |
| router  | service       | ✅      | -                    |
| router  | model         | ❌      | Direct DB operations |
| router  | client.py     | ❌      | Direct API calls     |
| router  | other router  | ❌      | Cross-router calls   |
| service | model         | ✅      | -                    |
| service | client.py     | ✅      | -                    |
| service | other service | ✅      | One-way dependency   |
| service | router        | ❌      | Reverse dependency   |
| model   | service       | ❌      | Reverse dependency   |
| model   | client.py     | ❌      | -                    |

### Dependency Graph

```
client.py ◄─── service (✅)
model ◄─── service (✅)
service ◄─── router (✅)
          ◄─── other service (✅)
router ◄─── main.py (✅)

❌ Forbidden reverse dependencies:
model ──► service
service ──► router
router ──► client.py
```
