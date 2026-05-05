⏺ StockLight 代碼組織規範

一、目錄結構

stocklight-backend/
├── src/
│ ├── main.py # FastAPI 入口，只做掛載 router
│ ├── config.py # Pydantic Settings，環境變數
│ ├── database.py # SQLAlchemy engine/session
│ │
│ ├── core/ # 跨模塊共享工具
│ │ ├── **init**.py
│ │ ├── exceptions.py # 全域異常類
│ │ ├── dependencies.py # FastAPI Depends（get_db, get_current_user）
│ │ ├── base_client.py # API 客戶端基類
│ │ ├── retry.py # 重試裝飾器
│ │ ├── circuit_breaker.py # 斷路器
│ │ └── cache.py # Redis 快取（未來）
│ │
│ ├── external/ # 外部服務封裝
│ │ ├── **init**.py
│ │ ├── fugo_client.py # 富果 API
│ │ ├── line_client.py # LINE Messaging API
│ │ └── openai_client.py # OpenAI API
│ │
│ ├── modules/ #業務模組
│ │ ├── **init**.py
│ │ │
│ │ ├── users/
│ │ │ ├── **init**.py
│ │ │ ├── router.py # API 路由
│ │ │ ├── service.py #業務邏輯
│ │ │ ├── schema.py # Pydantic Request/Response
│ │ │ └── model.py # SQLAlchemy Model
│ │ │
│ │ ├── stocks/
│ │ │ ├── **init**.py
│ │ │ ├── router.py
│ │ │ ├── service.py
│ │ │ ├── schema.py
│ │ │ └── model.py
│ │ │
│ │ ├── subscriptions/
│ │ │ ├── **init**.py
│ │ │ ├── router.py
│ │ │ ├── service.py
│ │ │ ├── schema.py
│ │ │ └── model.py
│ │ │
│ │ ├── indicators/
│ │ │ ├── **init**.py
│ │ │ ├── calculator.py # 指標計算（RSI/KD/MACD）
│ │ │ └── service.py # 指標業務邏輯
│ │ │
│ │ └── notifications/
│ │ ├── **init**.py
│ │ ├── service.py # 通知發送邏輯
│ │ └── template.py # LINE Flex Message 模板
│ │
│ ├── tasks/ # 定時任務
│ │ ├── **init**.py
│ │ ├── scheduler.py # APScheduler 配置
│ │ ├── update_prices.py # 收盤更新價格
│ │ └── check_alerts.py # 檢查觸發條件
│ │
│ └── webhooks/ # 外部 webhook 接收
│ ├── **init**.py
│ ├── line_webhook.py # LINE webhook 處理
│ └── service.py # webhook 指令解析
│
├── tests/
│ ├── conftest.py # pytest fixtures
│ ├── test_users/
│ ├── test_stocks/
│ ├── test_subscriptions/
│ └── test_indicators/
│
├── alembic/
│ ├── versions/
│ └── env.py
│
├── alembic.ini
├── requirements.txt
├── Dockerfile
├── .env.example
└── pyproject.toml

---

二、模塊內部分層結構

每個業務模組（users/stocks/subscriptions）包含 4 層：

router.py ──► service.py ──► model.py
│ │
│ │
▼ ▼
schema.pyexternal/

各層職責（嚴格定義）

┌─────────┬────────────┬──────────────────────────────────────────────────────────────────────────────────────────────┬────────────────────────────────────────────────────────────────────┐
│ 層級 │ 檔案 │ 允許做的事 │ 禁止做的事 │
├─────────┼────────────┼──────────────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────┤
│ router │ router.py │ 1. 定義 API 路徑2. 呼叫 service3. 使用 Depends 注入4. 驗證 schema5. 處理 HTTP 異常 │ 1. 直接操作 DB2. 呼叫 external/3. 寫業務邏輯4. 直接返回 model 物件 │
├─────────┼────────────┼──────────────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────┤
│ service │ service.py │ 1.業務邏輯判斷2. 操作 model（CRUD）3. 呼叫其他 service4. 呼叫 external/5. 返回 model 或 dict │ 1. 定義 API 路徑2. 處理 HTTP 異常3. 直接返回 schema │
├─────────┼────────────┼──────────────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────┤
│ schema │ schema.py │ 1. 定義 Request/Response2. Pydantic validation │ 1. 包含 DB 查詢2. 包含業務邏輯 │
├─────────┼────────────┼──────────────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────┤
│ model │ model.py │ 1. 定義 DB 表結構2. SQLAlchemy ORM │ 1. 包含業務邏輯2. 包含 validation │
└─────────┴────────────┴──────────────────────────────────────────────────────────────────────────────────────────────┴────────────────────────────────────────────────────────────────────┘

---

三、各層代碼範例

1. router.py 詳細範例

# src/modules/users/router.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from src.core.dependencies import get_db, get_current_user
from src.modules.users import service, schema
from src.modules.users.model import User

router = APIRouter(prefix="/users", tags=["users"])

# ==========允許做的事 ==========

@router.get("/me", response_model=schema.UserResponse)
async def get_me(
db: Session = Depends(get_db),
current_user: User = Depends(get_current_user),
):
"""取得當前用戶資料""" # ✅ 呼叫 service
user = service.get_user_by_id(db, current_user.id)

      # ✅ 處理 HTTP 異常
      if not user:
          raise HTTPException(
              status_code=status.HTTP_404_NOT_FOUND,
              detail="User not found"
          )

      # ✅ 返回 schema
      return schema.UserResponse.from_orm(user)

@router.post("/", response_model=schema.UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
body: schema.UserCreateRequest, # ✅ 使用 schema 驗證
db: Session = Depends(get_db),
):
"""建立用戶""" # ✅ 呼叫 service
user = service.create_user(db, line_user_id=body.line_user_id)

      # ✅ 返回 schema
      return schema.UserResponse.from_orm(user)

@router.get("/", response_model=List[schema.UserResponse])
async def list_users(
db: Session = Depends(get_db),
skip: int = 0,
limit: int = 100,
):
"""列出用戶""" # ✅ 呼叫 service
users = service.list_users(db, skip=skip, limit=limit)

      # ✅ 返回 schema
      return [schema.UserResponse.from_orm(u) for u in users]

# ==========禁止做的事範例（以下代碼禁止出現） ==========

# ❌ 禁止：直接操作 DB

@router.get("/bad-example-1")
async def bad_example_1(db: Session = Depends(get_db)):
user = db.query(User).filter(User.id == 1).first() # 禁止！
return user

# ❌ 禁止：呼叫 external/

@router.get("/bad-example-2")
async def bad_example_2():
from src.external import fugo_client
data = await fugo_client.get_stock_price("2330") # 禁止！
return data

# ❌ 禁止：寫業務邏輯

@router.post("/bad-example-3")
async def bad_example_3(body: schema.UserCreateRequest, db: Session = Depends(get_db)):
if body.line_user_id.startswith("U"): # 禁止！業務邏輯應在 service
user = User(line_user_id=body.line_user_id)
db.add(user)
db.commit()
return user

---

2. service.py 詳細範例

# src/modules/users/service.py

from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from src.modules.users.model import User
from src.modules.subscriptions.service import get_user_subscriptions
from src.external.line_client import LineClient

# ==========允許做的事 ==========

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
"""取得用戶（✅ 操作 model）"""
return db.query(User).filter(User.id == user_id).first()

def get_user_by_line_id(db: Session, line_user_id: str) -> Optional[User]:
"""取得用戶（✅ 操作 model）"""
return db.query(User).filter(User.line_user_id == line_user_id).first()

def create_user(db: Session, line_user_id: str) -> User:
"""建立用戶（✅業務邏輯 + 操作 model）""" # ✅業務邏輯判斷
existing = get_user_by_line_id(db, line_user_id)
if existing:
return existing

      # ✅ 操作 model
      user = User(
          line_user_id=line_user_id,
          created_at=datetime.utcnow(),
          is_active=True,
          free_quota=10,  # ✅業務邏輯：設定免費額度
      )
      db.add(user)
      db.commit()
      db.refresh(user)

      return user

def check_user_quota(db: Session, user_id: int) -> dict:
"""檢查用戶額度（✅業務邏輯）""" # ✅ 操作 model
user = get_user_by_id(db, user_id)
if not user:
raise ValueError("User not found")

      # ✅ 呼叫其他 service
      subscriptions = get_user_subscriptions(db, user_id)

      # ✅業務邏輯計算
      used_quota = len(subscriptions)
      remaining_quota = user.free_quota - used_quota

      return {
          "used": used_quota,
          "remaining": remaining_quota,
          "can_subscribe": remaining_quota > 0,
      }

async def send_welcome_message(line_user_id: str):
"""發送歡迎訊息（✅ 呼叫 external/）""" # ✅ 呼叫 external/
client = LineClient()
await client.push_message(
line_user_id,
"歡迎使用 StockLight！"
)

def list_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
"""列出用戶（✅ 操作 model）"""
return db.query(User).offset(skip).limit(limit).all()

# ==========禁止做的事範例（以下代碼禁止出現） ==========

# ❌ 禁止：處理 HTTP 畯常（HTTPException）

def bad_example_1(db: Session, user_id: int):
user = get_user_by_id(db, user_id)
if not user:
from fastapi import HTTPException # 禁止！
raise HTTPException(status_code=404, detail="Not found") # 禁止！
return user

# ❌ 禁止：定義 API 路徑（router decorator）

@router.get("/bad") # 禁止！
def bad_example_2():
pass

---

3. schema.py詳細範例

# src/modules/users/schema.py

from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional

# ==========允許做的事 ==========

class UserBase(BaseModel):
"""用戶基礎 schema"""
line_user_id: str = Field(..., description="LINE User ID")

class UserCreateRequest(UserBase):
"""建立用戶請求（✅ Request schema）"""

      # ✅ Pydantic validation
      @validator('line_user_id')
      def validate_line_user_id(cls, v):
          if not v.startswith('U'):
              raise ValueError('LINE User ID must start with U')
          return v

class UserResponse(BaseModel):
"""用戶回應（✅ Response schema）"""
id: int
line_user_id: str
created_at: datetime
is_active: bool
free_quota: int

      class Config:
          from_attributes = True  # Pydantic v2：允許 from_orm

class UserQuotaResponse(BaseModel):
"""額度回應"""
used: int
remaining: int
can_subscribe: bool

# ==========禁止做的事範例（以下代碼禁止出現） ==========

# ❌ 禁止：包含 DB 查詢

class BadSchema(BaseModel):
def get_user(self, db): # 禁止！
return db.query(User).first() # 禁止！

# ❌ 禁止：包含業務邏輯

class BadSchema2(BaseModel):
def calculate_quota(self): # 禁止！
return self.free_quota - 5 # 禁止！

---

4. model.py詳細範例

# src/modules/users/model.py

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from src.database import Base

# ==========允許做的事 ==========

class User(Base):
"""用戶表（✅ 定義 DB 表結構）"""
**tablename** = "users"

      # ✅ SQLAlchemy ORM 定義
      id = Column(Integer, primary_key=True, index=True)
      line_user_id = Column(String(50), unique=True, nullable=False, index=True)
      created_at = Column(DateTime, default=datetime.utcnow)
      is_active = Column(Boolean, default=True)
      free_quota = Column(Integer, default=10)

      # ✅ relationship 定義
      subscriptions = relationship("Subscription", back_populates="user")

# ==========禁止做的事範例（以下代碼禁止出現） ==========

# ❌ 禁止：包含業務邏輯

class BadUser(Base):
**tablename** = "users"

      id = Column(Integer, primary_key=True)
      free_quota = Column(Integer, default=10)

      def can_subscribe(self):  # 禁止！業務邏輯應在 service
          return self.free_quota > 0  # 禁止！

      def check_quota(self, db):  # 禁止！DB 查詢應在 service
          subs = db.query(Subscription).filter_by(user_id=self.id).count()
          return self.free_quota - subs  # 禁止！

---

四、跨模塊調用規則

規則定義

┌─────────┬──────────────┬──────┬────────────────────┐
│ 調用方 │ 被調用方 │ 允許 │ 禁止 │
├─────────┼──────────────┼──────┼────────────────────┤
│ router │ service │ ✅ │ - │
├─────────┼──────────────┼──────┼────────────────────┤
│ router │ model │ ❌ │ 直接操作 DB │
├─────────┼──────────────┼──────┼────────────────────┤
│ router │ external │ ❌ │ 直接呼叫外部 API │
├─────────┼──────────────┼──────┼────────────────────┤
│ router │ 其他 router │ ❌ │ 跨模組 router 調用 │
├─────────┼──────────────┼──────┼────────────────────┤
│ service │ model │ ✅ │ - │
├─────────┼──────────────┼──────┼────────────────────┤
│ service │ external │ ✅ │ - │
├─────────┼──────────────┼──────┼────────────────────┤
│ service │ 其他 service │ ✅ │ 單向依賴 │
├─────────┼──────────────┼──────┼────────────────────┤
│ service │ router │ ❌ │ 反向依賴 │
├─────────┼──────────────┼──────┼────────────────────┤
│ model │ service │ ❌ │ 反向依賴 │
├─────────┼──────────────┼──────┼────────────────────┤
│ model │ external │ ❌ │ - │
└─────────┴──────────────┴──────┴────────────────────┘

視覺化依賴圖

┌─────────────────────────────────────────────────────┐
│ 跨模組調用規則 │
├─────────────────────────────────────────────────────┤
│ │
│ ┌──────────┐ │
│ │ external │ ◄─── service (✅) │
│ └──────────┘ │
│ │
│ ┌──────────┐ │
│ │ model │ ◄─── service (✅) │
│ └──────────┘ │
│ │
│ ┌──────────┐ │
│ │ service │ ◄─── router (✅) │
│ │ │ ◄─── 其他 service (✅) │
│ └──────────┘ │
│ │
│ ┌──────────┐ │
│ │ router │ ◄─── main.py (✅) │
│ └──────────┘ │
│ │
│ ❌ 禁止的反向依賴： │
│ model ──► service │
│ service ──► router │
│ router ──► external │
│ │
└─────────────────────────────────────────────────────┘

---

跨模組 service 調用範例

# src/modules/subscriptions/service.py

from sqlalchemy.orm import Session
from typing import List

from src.modules.subscriptions.model import Subscription
from src.modules.users.service import get_user_by_id # ✅ 跨模組調用 service
from src.modules.stocks.service import get_stock_by_symbol # ✅
from src.modules.notifications.service import send_notification # ✅
from src.external.line_client import LineClient # ✅

def create_subscription(
db: Session,
user_id: int,
symbol: str,
condition: dict,
) -> Subscription:
"""建立訂閱""" # ✅ 跨模組調用 service
user = get_user_by_id(db, user_id)
if not user:
raise ValueError("User not found")

      stock = get_stock_by_symbol(db, symbol)
      if not stock:
          raise ValueError("Stock not found")

      subscription = Subscription(
          user_id=user_id,
          symbol=symbol,
          condition=condition,
      )
      db.add(subscription)
      db.commit()

      return subscription

def check_and_notify(db: Session, subscription_id: int):
"""檢查觸發並通知"""
subscription = get_subscription(db, subscription_id)

      # ✅ 跨模組調用 service
      if check_condition_triggered(subscription.condition):
          # ✅ 跨模組調用 service
          send_notification(
              user_line_id=subscription.user.line_user_id,
              message=f"股票 {subscription.symbol} 已觸發條件！"
          )

---

禁止的跨模組調用範例

# ❌ 禁止：router 直接呼叫 external

@router.post("/subscribe")
async def bad_example(db: Session = Depends(get_db)):
from src.external.fugo_client import FugoClient
client = FugoClient()
data = await client.get_stock_price("2330") # ❌ 禁止！應在 service
return data

# ❌ 禁止：service 呼叫 router

def bad_example_2():
from src.modules.users.router import get_me # ❌ 禁止！反向依賴
return get_me()

# ❌ 禁止：model 包含業務邏輯

class Subscription(Base):
def check_triggered(self): # ❌ 禁止！應在 indicators/service
pass

---

五、特殊模塊規範

indicators/ 模塊（無 router）

# src/modules/indicators/calculator.py

"""技術指標計算（純計算，無業務邏輯）"""
import pandas as pd
from typing import List

def calculate_rsi(prices: List[float], period: int = 14) -> float:
"""計算 RSI（✅ 純計算函數）"""
df = pd.DataFrame({'close': prices})
delta = df['close'].diff()
gain = delta.where(delta > 0, 0)
loss = -delta.where(delta < 0, 0)
avg_gain = gain.rolling(period).mean()
avg_loss = loss.rolling(period).mean()
rs = avg_gain / avg_loss
rsi = 100 - (100 / (1 + rs))
return rsi.iloc[-1]

def calculate_kd(prices: List[float], period: int = 9) -> tuple:
"""計算 KD 值（✅ 純計算函數）""" # ...計算邏輯
return k_value, d_value

# src/modules/indicators/service.py

"""指標業務邏輯"""
from sqlalchemy.orm import Session
from typing import List

from src.modules.stocks.service import get_stock_prices
from src.modules.indicators.calculator import calculate_rsi, calculate_kd

def get_stock_rsi(db: Session, symbol: str, period: int = 14) -> float:
"""取得股票 RSI（✅業務邏輯：組合計算 + DB 查詢）""" # ✅ 跨模組調用 service 取得數據
prices = get_stock_prices(db, symbol, days=50)

      # ✅ 呼叫 calculator 計算
      rsi = calculate_rsi(prices, period)

      return rsi

def check_rsi_condition(db: Session, symbol: str, operator: str, value: float) -> bool:
"""檢查 RSI條件是否觸發（✅業務邏輯）"""
rsi = get_stock_rsi(db, symbol)

      if operator == ">":
          return rsi > value
      elif operator == "<":
          return rsi < value

      return False

---

notifications/ 模塊（無 router、無 model）

# src/modules/notifications/service.py

"""通知業務邏輯"""
from src.external.line_client import LineClient
from src.modules.notifications.template import AlertTemplate

async def send_price_alert(line_user_id: str, symbol: str, price: float, target_price: float):
"""發送到價通知（✅業務邏輯）""" # ✅呼叫 external/
client = LineClient()

      # ✅呼叫 template
      message = AlertTemplate.price_alert(symbol, price, target_price)

      await client.push_message(line_user_id, message)

async def send_indicator_alert(line_user_id: str, symbol: str, indicator: str, value: float):
"""發送指標通知"""
client = LineClient()
message = AlertTemplate.indicator_alert(symbol, indicator, value)
await client.push_message(line_user_id, message)

# src/modules/notifications/template.py

"""LINE Flex Message 模板"""
def price_alert(symbol: str, current_price: float, target_price: float) -> dict:
"""到價通知模板（✅ 純模板生成）"""
return {
"type": "flex",
"contents": {
"type": "bubble",
"body": {
"type": "box",
"contents": [
{"type": "text", "text": f"{symbol} 到價通知"},
{"type": "text", "text": f"目標價: {target_price}"},
{"type": "text", "text": f"目前價: {current_price}"},
]
}
}
}

---

六、external/ 層規範

# src/external/fugo_client.py

from src.core.base_client import BaseAPIClient
from src.core.retry import retry_with_backoff
from src.core.circuit_breaker import CircuitBreaker, with_circuit_breaker
import httpx

class FugoClient(BaseAPIClient):
"""富果 API 客戶端（✅ 只封裝 API 調用）"""

      def __init__(self, api_key: str):
          super().__init__(
              base_url="https://api.fugle.tw",
              timeout=10.0,
          )
          self.api_key = api_key
          self.circuit_breaker = CircuitBreaker()

      @with_circuit_breaker(breaker=FugoClient.circuit_breaker)
      @retry_with_backoff(max_retries=3)
      async def get_intraday(self, symbol: str) -> dict:
          """取得即時行情（✅ API 封裝）"""
          response = await self.client.get(
              f"/marketdata/v0.3/stock/intraday/{symbol}",
              params={"apiToken": self.api_key}
          )
          response.raise_for_status()
          return response.json()

      async def get_historical(self, symbol: str, days: int = 200) -> list:
          """取得歷史數據（✅ API 封裝）"""
          response = await self.client.get(
              f"/marketdata/v0.3/stock/historical/{symbol}",
              params={"apiToken": self.api_key}
          )
          response.raise_for_status()
          data = response.json().get("data", [])
          return data[-days:]  # 取最近 N 天

禁止：

# ❌ 禁止：包含業務邏輯

class BadFugoClient:
async def check_price_alert(self, symbol: str, target: float): # ❌ 禁止！
data = await self.get_intraday(symbol)
if data['close'] > target: # ❌ 禁止！業務邏輯應在 service
return True

---

七、tasks/ 層規範

# src/tasks/update_prices.py

from apscheduler import AsyncScheduler
from sqlalchemy.orm import Session
from datetime import datetime

from src.database import SessionLocal
from src.modules.stocks.service import update_stock_prices

async def update_prices_task():
"""收盤更新價格定時任務""" # ✅ 建立DB session
db = SessionLocal()

      try:
          # ✅ 呼叫 service
          await update_stock_prices(db)
      finally:
          db.close()

# src/tasks/scheduler.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.tasks.update_prices import update_prices_task
from src.tasks.check_alerts import check_alerts_task

scheduler = AsyncIOScheduler()

# 收盤後更新（14:30）

scheduler.add_job(
update_prices_task,
"cron",
hour=14,
minute=30,
timezone="Asia/Taipei"
)

# 每5分鐘檢查觸發（交易時間）

scheduler.add_job(
check_alerts_task,
"cron",
hour="9-13",
minute="\*/5",
timezone="Asia/Taipei"
)

---

八、命名規範

┌───────────┬───────────────────────────────┬─────────────────────────────────────┐
│ 項目 │ 規範 │ 範例 │
├───────────┼───────────────────────────────┼─────────────────────────────────────┤
│ API 路徑 │ RESTful，小寫，複數 │ /users, /subscriptions │
├───────────┼───────────────────────────────┼─────────────────────────────────────┤
│ 函數名 │ snake_case，動詞開頭 │ get_user_by_id, create_subscription │
├───────────┼───────────────────────────────┼─────────────────────────────────────┤
│ 類名 │ PascalCase │ UserResponse, FugoClient │
├───────────┼───────────────────────────────┼─────────────────────────────────────┤
│ 變數 │ snake_case │ user_id, stock_prices │
├───────────┼───────────────────────────────┼─────────────────────────────────────┤
│ schema 類 │ 命名為 {功能}Request/Response │ UserCreateRequest, UserResponse │
├───────────┼───────────────────────────────┼─────────────────────────────────────┤
│ model 類 │ 單數，表名 │ User, Subscription │
└───────────┴───────────────────────────────┴─────────────────────────────────────┘

---

九、檢查清單（AI執行時使用）

每次新增代碼時檢查：

1. router.py 檢查：


    - ✅ 只呼叫 service？
    - ✅ 使用 Depends？
    - ✅ 返回 schema？
    - ❌ 沒有直接操作 DB？
    - ❌ 沒有呼叫 external/？

2. service.py 檢查：


    - ✅ 包含業務邏輯？
    - ✅ 操作 model？
    - ✅ 可以呼叫 external/？
    - ✅ 可以呼叫其他 service？
    - ❌ 沒有 HTTPException？

3. schema.py 檢查：


    - ✅ 只有 Pydantic validation？
    - ❌ 沒有 DB 查詢？
    - ❌ 沒有業務邏輯？

4. model.py 檢查：


    - ✅ 只有 SQLAlchemy 定義？
    - ❌ 沒有業務邏輯方法？

5. 跨模組調用：


    - ✅ service → service 單向？
    - ❌ 沒有反向依賴？

---

十、違規處理

發現違規時的處理步驟：

1. 檢查違規代碼位置
2. 判斷應該在哪一層
3. 移動代碼到正確位置
4. 更新 import
5. 驗證功能正常

範例：

# ❌ 違規代碼（router 中直接呼叫 external）

@router.get("/price/{symbol}")
async def get_price(symbol: str):
client = FugoClient()
return await client.get_intraday(symbol)

# ✅ 修正步驟：

# 1. 移動到 stocks/service.py

async def get_stock_price(db: Session, symbol: str):
client = FugoClient()
data = await client.get_intraday(symbol)
return data

# 2. router 呼叫 service

@router.get("/price/{symbol}")
async def get_price(symbol: str, db: Session = Depends(get_db)):
return await stocks_service.get_stock_price(db, symbol)
