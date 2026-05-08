# 測試規範 (testing.md)

## 1. 非同步測試客戶端 (Async Test Client)

- **強制套件**：進行 API 整合測試時，必須使用 `httpx.AsyncClient` 搭配 `ASGITransport`。
- **禁用舊套件**：嚴禁使用已停止維護的 `async_asgi_testclient`。

```python
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_create_subscription(client: AsyncClient):
    resp = await client.post("/subscriptions", json={"symbol": "2330.TW"})
    assert resp.status_code == 201
```

## 2. 依賴覆寫 (Dependency Overrides)

- **使用時機**：在測試中繞過外部依賴（如 JWT 身份驗證解析、第三方 API 客戶端），以專注測試核心業務邏輯
- **實作方式**：透過 FastAPI 內建的 app.dependency_overrides 進行依賴抽換，並在測試結束後清除覆寫

```python
from src.auth.dependencies import parse_jwt_data
from src.main import app
import pytest

def fake_user():
    # 模擬通過身分驗證的使用者資料
    return {"user_id": "00000000-0000-0000-0000-000000000001"}

@pytest.fixture(autouse=True)
def _override_auth():
    # 將正式的依賴替換為 fake_user
    app.dependency_overrides[parse_jwt_data] = fake_user
    yield
    # 測試結束後還原
    app.dependency_overrides.clear()
```

## 3. 資料庫測試原則 (Anti-patterns)

• ❌ **嚴禁 Mock 資料庫**：在整合測試中 Mock 資料庫或 ORM Session，會導致測試環境與正式環境行為不一致（例如遺漏唯一鍵衝突、外鍵限制或預設值問題），最終將在正式環境引發錯誤。
• ✅ **必須使用真實資料庫**：整合測試應使用真實的 PostgreSQL 實例（建議透過 Testcontainers 動態啟動，或建立一個獨立的臨時測試 Schema），確保 SQL 語法與資料表結構的正確性。
