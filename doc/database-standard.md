⏺ StockLight 数据庫性能规范

一、索引设计原則

1. 索引決策表（AI直接查表執行）

┌──────────────────┬───────────────┬──────────────┬─────────────────────────────────────────────────────────────────────────────────┐
│ 場景 │ 是否加索引 │ 索引類型 │ SQL 範例 │
├──────────────────┼───────────────┼──────────────┼─────────────────────────────────────────────────────────────────────────────────┤
│ 主鍵 │ ✅ 自動 │ B-tree │ id SERIAL PRIMARY KEY │
├──────────────────┼───────────────┼──────────────┼─────────────────────────────────────────────────────────────────────────────────┤
│ 外鍵 │ ✅ 必須 │ B-tree │ CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id) │
├──────────────────┼───────────────┼──────────────┼─────────────────────────────────────────────────────────────────────────────────┤
│ WHERE 單欄位查詢 │ ✅ 必須 │ B-tree │ CREATE INDEX idx_users_line_user_id ON users(line_user_id) │
├──────────────────┼───────────────┼──────────────┼─────────────────────────────────────────────────────────────────────────────────┤
│ WHERE 多欄位 AND │ ✅ 必須 │ 複合索引 │ CREATE INDEX idx_subscriptions_user_symbol ON subscriptions(user_id, symbol) │
├──────────────────┼───────────────┼──────────────┼─────────────────────────────────────────────────────────────────────────────────┤
│ WHERE 多欄位 OR │ ⚠️ 審慎評估 │ 多個單欄索引 │ 視查詢頻率決定 │
├──────────────────┼───────────────┼──────────────┼─────────────────────────────────────────────────────────────────────────────────┤
│ ORDER BY 欄位 │ ⚠️ 如有 LIMIT │ B-tree │ CREATE INDEX idx_stock_prices_date_desc ON stock_prices(symbol, date DESC) │
├──────────────────┼───────────────┼──────────────┼─────────────────────────────────────────────────────────────────────────────────┤
│ LIKE '%keyword%' │ ❌ 無效 │ - │ 改用全文檢索或外部搜尋 │
├──────────────────┼───────────────┼──────────────┼─────────────────────────────────────────────────────────────────────────────────┤
│ LIKE 'keyword%' │ ✅ 有效 │ B-tree │ 可用一般索引 │
├──────────────────┼───────────────┼──────────────┼─────────────────────────────────────────────────────────────────────────────────┤
│ JSONB 欄位查詢 │ ✅ 如有需求 │ GIN │ CREATE INDEX idx_subscriptions_condition ON subscriptions USING GIN (condition) │
└──────────────────┴───────────────┴──────────────┴─────────────────────────────────────────────────────────────────────────────────┘

2. 複合索引設計規則（必須遵循）

規則 1：最左前綴原則
複合索引 = 欄位A, 欄位B, 欄位C

✅ 有效查詢：
WHERE A = ?
WHERE A = ? AND B = ?
WHERE A = ? AND B = ? AND C = ?

❌ 無效查詢（無法使用索引）：
WHERE B = ?
WHERE C = ?
WHERE B = ? AND C = ?

規則 2：選擇性高的欄位放前面
選擇性 = 不重複值數量 / 總行數

✅ 好的索引順序：
(user_id, symbol) -- user_id 選擇性高

❌ 差的索引順序：
(symbol, user_id) -- symbol 重複值多（台股只有2500檔）

規則 3：覆蓋索引（Covering Index）
如果 SELECT 的欄位都在索引中，可避免回表

範例：
查詢：SELECT symbol, close FROM stock_prices WHERE symbol = '2330.TW' ORDER BY date DESC LIMIT 1
索引：CREATE INDEX idx_stock_prices_symbol_date_close ON stock_prices(symbol, date DESC, close)

3. StockLight 各表索引清單（建表時直接執行）

-- users 表
CREATE UNIQUE INDEX idx_users_line_user_id ON users(line_user_id);
CREATE INDEX idx_users_created_at ON users(created_at);

-- stocks 表
CREATE UNIQUE INDEX idx_stocks_symbol ON stocks(symbol);
CREATE INDEX idx_stocks_is_active ON stocks(is_active) WHERE is_active = TRUE;

-- stock_prices 表（重點優化）
CREATE INDEX idx_stock_prices_symbol_date ON stock_prices(symbol, date DESC);
CREATE INDEX idx_stock_prices_symbol_date_close ON stock_prices(symbol, date DESC, close);

-- subscriptions 表（重點優化）
CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_user_symbol ON subscriptions(user_id, symbol);
CREATE INDEX idx_subscriptions_is_active ON subscriptions(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_subscriptions_next_check_at ON subscriptions(next_check_at) WHERE is_active = TRUE;

-- notification_logs 表
CREATE INDEX idx_notification_logs_user_id ON notification_logs(user_id);
CREATE INDEX idx_notification_logs_created_at ON notification_logs(created_at);

---

二、大表預判與應對策略

1. 大表預判標準

┌───────────────────┬────────────┬──────────┬────────────────────────────────────┐
│ 表名 │ 預估數據量 │ 是否大表 │ 判斷依據 │
├───────────────────┼────────────┼──────────┼────────────────────────────────────┤
│ users │ < 10,000 │ ❌ │ 百人用戶 │
├───────────────────┼────────────┼──────────┼────────────────────────────────────┤
│ stocks │ ~ 2,500 │ ❌ │ 台股總數 │
├───────────────────┼────────────┼──────────┼────────────────────────────────────┤
│ stock_prices │ 高風險 │ ✅ │ 2500股 × 200天 × 12月 ≈ 600萬行/年 │
├───────────────────┼────────────┼──────────┼────────────────────────────────────┤
│ subscriptions │ < 50,000 │ ⚠️ │ 每人平均5個 │
├───────────────────┼────────────┼──────────┼────────────────────────────────────┤
│ notification_logs │ 高風險 │ ✅ │ 每日通知數 × 365天 ≈ 百萬行/年 │
└───────────────────┴────────────┴──────────┴────────────────────────────────────┘

2. 大表應對策略清單（AI執行時逐一檢查）

stock_prices 表策略：
┌─────────────────────────────────────────────────────────────┐
│ [✓] 必須使用複合索引 │
│ [✓] 必須限制查詢時間範圍（WHERE date >= ?） │
│ [✓] 禁止 SELECT \*，只取必要欄位 │
│ [✓] 使用 PARTITION BY RANGE (date) -- 可選，百人規模暫不需要 │
│ [✓] 定期清理超過 200 天的舊數據（每月執行） │
└─────────────────────────────────────────────────────────────┘

notification_logs 表策略：
┌─────────────────────────────────────────────────────────────┐
│ [✓] 必須有時間索引 │
│ [✓] 定期歸檔超過 90 天的日誌到 cold_storage 表 │
│ [✓] 使用軟刪除而非硬刪除 │
│ [✓] 寫入使用批量插入 │
└─────────────────────────────────────────────────────────────┘

3. 大表清理任務（Celery 任務）

# tasks/cleanup.py

from datetime import datetime, timedelta
from sqlalchemy import delete
from src.database import SessionLocal
from src.modules.stocks.model import StockPrice
from src.modules.notifications.model import NotificationLog

async def cleanup_old_prices():
"""每月清理超過 200 天的價格數據"""
db = SessionLocal()
try:
cutoff_date = datetime.utcnow() - timedelta(days=200)

          # 批量刪除，避免鎖表
          stmt = delete(StockPrice).where(StockPrice.date < cutoff_date)
          result = db.execute(stmt)
          db.commit()

          logger.info(f"Deleted {result.rowcount} old price records")
      finally:
          db.close()

async def archive_old_logs():
"""每月歸檔超過 90 天的通知日誌"""
db = SessionLocal()
try:
cutoff_date = datetime.utcnow() - timedelta(days=90)

          # 移動到歸檔表（冷存儲）
          stmt = """
              INSERT INTO notification_logs_archive
              SELECT * FROM notification_logs
              WHERE created_at < :cutoff
          """
          db.execute(stmt, {"cutoff": cutoff_date})

          # 刪除原表數據
          db.execute(
              delete(NotificationLog).where(NotificationLog.created_at < cutoff_date)
          )
          db.commit()
      finally:
          db.close()

---

三、分頁查詢規範

1. 分頁方式對比（強制使用 Keyset）

┌───────────┬───────────────────────────┬──────┬───────────────────┐
│ 方式 │ SQL │ 性能 │ 問題 │
├───────────┼───────────────────────────┼──────┼───────────────────┤
│ ❌ OFFSET │ OFFSET 10000 LIMIT 20 │ 差 │ 需掃描前 10000 行 │
├───────────┼───────────────────────────┼──────┼───────────────────┤
│ ✅ Keyset │ WHERE id > 10000 LIMIT 20 │ 好 │ 只掃描 20 行 │
└───────────┴───────────────────────────┴──────┴───────────────────┘

2. Keyset 分頁實現（所有列表查詢必須使用）

# ❌ 錯誤：使用 OFFSET

@router.get("/subscriptions")
async def list_subscriptions(
db: Session = Depends(get_db),
page: int = 1,
page_size: int = 20,
):
offset = (page - 1) \* page_size
subscriptions = db.query(Subscription).offset(offset).limit(page_size).all()
return subscriptions

# ✅ 正確：使用 Keyset 分頁

@router.get("/subscriptions")
async def list_subscriptions(
db: Session = Depends(get_db),
cursor: Optional[int] = None, # 上一頁最後一筆的 id
limit: int = 20,
):
query = db.query(Subscription).order_by(Subscription.id.asc())

      if cursor:
          query = query.filter(Subscription.id > cursor)

      subscriptions = query.limit(limit).all()

      # 返回下一頁游標
      next_cursor = None
      if len(subscriptions) == limit:
          next_cursor = subscriptions[-1].id

      return {
          "data": subscriptions,
          "next_cursor": next_cursor,
          "has_more": next_cursor is not None,
      }

3. 多欄位排序分頁（時間 + ID）

# 複合游標分頁（用於按時間排序）

@router.get("/notifications")
async def list_notifications(
db: Session = Depends(get_db),
cursor_date: Optional[datetime] = None,
cursor_id: Optional[int] = None,
limit: int = 20,
):
query = db.query(NotificationLog).order_by(
NotificationLog.created_at.desc(),
NotificationLog.id.desc()
)

      if cursor_date and cursor_id:
          query = query.filter(
              or_(
                  NotificationLog.created_at < cursor_date,
                  and_(
                      NotificationLog.created_at == cursor_date,
                      NotificationLog.id < cursor_id
                  )
              )
          )

      notifications = query.limit(limit).all()

      next_cursor_date = None
      next_cursor_id = None
      if len(notifications) == limit:
          next_cursor_date = notifications[-1].created_at
          next_cursor_id = notifications[-1].id

      return {
          "data": notifications,
          "next_cursor_date": next_cursor_date,
          "next_cursor_id": next_cursor_id,
          "has_more": next_cursor_date is not None,
      }

4. 分頁響應 Schema（統一格式）

# core/schema.py

from pydantic import BaseModel
from typing import Generic, TypeVar, Optional, List

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
"""統一分頁響應格式"""
data: List[T]
next_cursor: Optional[int] = None
has_more: bool = False

      class Config:
          from_attributes = True

---

四、通用欄位約定（建表時必須包含）

1. 所有表必須包含的欄位

-- 每個表必須包含以下欄位（範例）
CREATE TABLE users (
id SERIAL PRIMARY KEY, -- 主鍵（自增）
line_user_id VARCHAR(50) NOT NULL, --業務欄位
created_at TIMESTAMPTZ DEFAULT NOW(), -- 創建時間（必須）
updated_at TIMESTAMPTZ DEFAULT NOW(), -- 更新時間（必須）
is_deleted BOOLEAN DEFAULT FALSE -- 軟刪除標記（必須）
);

2. 欄位命名與類型規範

┌──────────────┬────────────┬─────────────────────┬────────┬─────────────────────┐
│ 欄位用途 │ 欄位名 │ 類型 │ 預設值 │ 說明 │
├──────────────┼────────────┼─────────────────────┼────────┼─────────────────────┤
│ 主鍵 │ id │ SERIAL 或 BIGSERIAL │ 自增 │ 所有表必須 │
├──────────────┼────────────┼─────────────────────┼────────┼─────────────────────┤
│ 外鍵 │ {table}\_id │ INTEGER 或 BIGINT │ - │ 例：user_id │
├──────────────┼────────────┼─────────────────────┼────────┼─────────────────────┤
│ 創建時間 │ created_at │ TIMESTAMPTZ │ NOW() │ 時區敏感 │
├──────────────┼────────────┼─────────────────────┼────────┼─────────────────────┤
│ 更新時間 │ updated_at │ TIMESTAMPTZ │ NOW() │ 需 trigger 更新 │
├──────────────┼────────────┼─────────────────────┼────────┼─────────────────────┤
│ 軟刪除 │ is_deleted │ BOOLEAN │ FALSE │ 禁止硬刪除 │
├──────────────┼────────────┼─────────────────────┼────────┼─────────────────────┤
│ 啟用狀態 │ is_active │ BOOLEAN │ TRUE │ 業務狀態 │
├──────────────┼────────────┼─────────────────────┼────────┼─────────────────────┤
│ 時間範圍查詢 │ {event}\_at │ TIMESTAMPTZ │ - │ 例：triggered_at │
├──────────────┼────────────┼─────────────────────┼────────┼─────────────────────┤
│ 金額/價格 │ price │ DECIMAL(10,2) │ - │ 精確計算 │
├──────────────┼────────────┼─────────────────────┼────────┼─────────────────────┤
│ 百分比 │ rate │ DECIMAL(5,4) │ - │ 例：0.1234 = 12.34% │
├──────────────┼────────────┼─────────────────────┼────────┼─────────────────────┤
│ JSON 數據 │ metadata │ JSONB │ {} │ 結構化 JSON │
└──────────────┴────────────┴─────────────────────┴────────┴─────────────────────┘

3. updated_at 自動更新 Trigger（建表後執行）

-- 所有表必須執行此函數
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
NEW.updated_at = NOW();
RETURN NEW;
END;

$$
LANGUAGE plpgsql;

  -- 為每個表創建 trigger（範例）
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

  CREATE TRIGGER update_subscriptions_updated_at
    BEFORE UPDATE ON subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

  4. 軟刪除實現規範

  # model.py 基類
from sqlalchemy import Boolean, Column, DateTime, Integer
from sqlalchemy.ext.declarative import declared_attr
from datetime import datetime

  class BaseModel:
    """所有 Model 的基類"""

      id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

      @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower() + 's'

      def soft_delete(self):
        """軟刪除"""
        self.is_deleted = True
        self.updated_at = datetime.utcnow()

  # service.py 查詢時過濾軟刪除
def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """✅ 必須過濾軟刪除"""
    return db.query(User).filter(
        User.id == user_id,
        User.is_deleted == False  # 所有查詢必須加此條件
    ).first()

  def delete_user(db: Session, user_id: int):
    """✅ 軟刪除而非硬刪除"""
    user = get_user_by_id(db, user_id)
    if user:
        user.is_deleted = True
        db.commit()

  ---
五、完整建表範例（AI 直接執行）

  -- 用戶表
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    line_user_id VARCHAR(50) NOT NULL,
    free_quota INTEGER DEFAULT 10,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE
);

  CREATE UNIQUE INDEX idx_users_line_user_id ON users(line_user_id);
CREATE INDEX idx_users_created_at ON users(created_at);

  CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

  -- 股票表
CREATE TABLE stocks (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    name VARCHAR(50) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE
);

  CREATE UNIQUE INDEX idx_stocks_symbol ON stocks(symbol);
CREATE INDEX idx_stocks_is_active ON stocks(is_active) WHERE is_active = TRUE;

  CREATE TRIGGER update_stocks_updated_at
    BEFORE UPDATE ON stocks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

  -- 股票價格表（大表優化）
CREATE TABLE stock_prices (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    open DECIMAL(10,2),
    high DECIMAL(10,2),
    low DECIMAL(10,2),
    close DECIMAL(10,2),
    volume BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE,
    UNIQUE(symbol, date)
);

  -- 大表索引（覆蓋索引優化）
CREATE INDEX idx_stock_prices_symbol_date ON stock_prices(symbol, date DESC);
CREATE INDEX idx_stock_prices_symbol_date_close ON stock_prices(symbol, date DESC, close);

  CREATE TRIGGER update_stock_prices_updated_at
    BEFORE UPDATE ON stock_prices
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

  -- 訂閱表
CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    symbol VARCHAR(20) NOT NULL,
    condition_type VARCHAR(20) NOT NULL,
    condition_value JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    next_check_at TIMESTAMPTZ,
    last_triggered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE
);

  CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_user_symbol ON subscriptions(user_id, symbol);
CREATE INDEX idx_subscriptions_is_active ON subscriptions(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_subscriptions_next_check_at ON subscriptions(next_check_at) WHERE is_active = TRUE;

  CREATE TRIGGER update_subscriptions_updated_at
    BEFORE UPDATE ON subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

  -- 通知日誌表（大表優化）
CREATE TABLE notification_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    subscription_id INTEGER REFERENCES subscriptions(id),
    symbol VARCHAR(20) NOT NULL,
    message TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE
);

  CREATE INDEX idx_notification_logs_user_id ON notification_logs(user_id);
CREATE INDEX idx_notification_logs_created_at ON notification_logs(created_at);
CREATE INDEX idx_notification_logs_status ON notification_logs(status);

  CREATE TRIGGER update_notification_logs_updated_at
    BEFORE UPDATE ON notification_logs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

  ---
六、AI 建表檢查清單（每次建表必須執行）

  建表檢查清單：
┌─────────────────────────────────────────────────────────────┐
│  [ ] 表名使用複數形式                     │
│  [ ] 主鍵命名為 id，類型為 SERIAL 或 BIGSERIAL          │
│  [ ] 包含 created_at TIMESTAMPTZ 欄位                   │
│  [ ] 包含 updated_at TIMESTAMPTZ 欄位                   │
│  [ ] 包含 is_deleted BOOLEAN 欄位                        │
│  [ ] 外鍵命名為 {table}_id                               │
│  [ ] 創建對應的 updated_at trigger                       │
│  [ ] 根據查詢場景添加索引                                │
│  [ ] 外鍵欄位添加索引                                   │
│  [ ] 時間範圍查詢欄位添加索引                            │
│  [ ] 大表使用 BIGSERIAL 而非 SERIAL                     │
│  [ ] 金額使用 DECIMAL(10,2) 而非 FLOAT                  │
│  [ ] JSON 數據使用 JSONB 而非 JSON                      │
└─────────────────────────────────────────────────────────────┘
$$
