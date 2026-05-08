# API 與資料驗證規範 (api-spec.md)

## 1. 資料驗證 (Pydantic 2.7+)

- 內建驗證：善用 Field 內建參數進行驗證（如 min_length、pattern、ge 等），取代額外的邏輯判斷
- 自定義序列化：全面使用 @field_serializer 處理特定欄位格式轉換（如統一 Datetime 為 UTC 並帶上時區資訊）
- 禁用舊版寫法：嚴禁使用 Pydantic v1 舊 API，包含 json_encoders 或 .dict()

```python
# 序列化範例
@field_serializer("*", when_used="json", check_fields=False)
def _serialize_datetimes(self, value):
    # 將 datetime 轉換為帶時區的字串
```

## 2. 依賴注入 (Dependencies)

- 標準語法：統一使用 Annotated[T, Depends(...)] 撰寫依賴注入，禁止依賴預設參數寫法
- 前置驗證：將資料庫查詢與權限驗證邏輯封裝於 Dependency 中，若查無資料或無權限直接在內部拋出 HTTPException
- 依賴鏈：支援依賴互相調用（例如：先解析 JWT 取得 token_data 依賴，再交由另一個依賴驗證資源所有權）

```python
# 依賴注入範例
PostDep = Annotated[dict, Depends(valid_post_id)]

@router.get("/posts/{post_id}")
async def get_post(post: PostDep):
    return post
```

## 3. 分頁實作 (Keyset Pagination)

- 嚴格規範：列表型 API 強制使用游標分頁 (Keyset Pagination)，嚴禁使用 OFFSET（大表效能極差）
- 查詢邏輯：基於主鍵進行範圍過濾與限制（例如：WHERE id > cursor LIMIT limit）
- 統一回傳結構：分頁回應必須包含 data、next_cursor (整數或空值) 與 has_more (布林值)

```python
# 標準分頁回應 Schema
class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    next_cursor: Optional[int] = None
    has_more: bool = False
```

## 4. 身份認證 (JWT)

- 套件選擇：強制使用 PyJWT (import jwt) 解析與核發 Token
- 禁用套件：嚴禁使用已停止維護的 python-jose5. API 介面與 Router 規範

## 5. API 介面與 Router 規範

### 命名慣例：

- API 路徑：RESTful 風格、全小寫、使用複數名詞（如 /users, /subscriptions）
- Schema 命名：{Action}Request 或 {Action}Response（如 UserCreateRequest）
- 文檔安全：透過設定 openapi_url，確保 API 文檔 (Swagger UI) 僅在 local 或 staging 環境開啟，正式環境必須隱藏
- 路由裝飾器：定義端點時，必須明確標示 response_model、status_code，並在 responses 中寫明可能拋出的錯誤碼與說明

### Router 權責限制：

- ✅ 允許：定義路徑、呼叫 Service 層、使用 Depends、Schema 驗證、處理 HTTP 異常
- ❌ 嚴禁：直接操作資料庫 (DB)、直接呼叫外部 API (Client)、跨 Router 呼叫、直接回傳 ORM Model 物件（需透過 Schema 轉換）
