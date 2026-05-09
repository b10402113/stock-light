# 數據庫設計與遷移規範

## 核心硬規矩

1. **主鍵設計**：強制使用自增 `BIGINT` (`BIGSERIAL`) 作為主鍵。**絕對禁止使用 UUID**（影響 B-tree 索引效能與查詢速度）。
2. **禁止 NULL**：資料表欄位嚴禁出現 `NULL`。業務上的空值，字串請用 `""` (空字串) 代替，數值請用 `0` 代替。
3. **軟刪除**：禁止硬刪除，必須加入 `is_deleted` (BOOLEAN) 欄位，並在查詢時過濾。

## 基礎結構與 SQLAlchemy 2.0

一律使用非同步 API (`AsyncSession`, `async_sessionmaker`, `create_async_engine`)。

### 必備欄位與通用型態

| Purpose      | Name        | Type          | Default | Notes                 |
| ------------ | ----------- | ------------- | ------- | --------------------- |
| Primary key  | id          | BIGSERIAL     | auto    | 必備，禁用 UUID       |
| Foreign key  | {table}\_id | BIGINT        | -       | 例如 user_id          |
| Created time | created_at  | TIMESTAMPTZ   | NOW()   | Timezone-aware        |
| Updated time | updated_at  | TIMESTAMPTZ   | NOW()   | 必須綁定 Trigger 更新 |
| Soft delete  | is_deleted  | BOOLEAN       | FALSE   | 必備                  |
| Price/Amount | price       | DECIMAL(10,2) | 0       | 禁用 FLOAT            |
| JSON data    | metadata    | JSONB         | '{}'    | 禁用 JSON             |

### 資料庫索引設計原則 (Index Design Principles)

- **必加索引**：Foreign key、WHERE 單一欄位常客、WHERE 多條件 AND (建立 Composite Index)。
- **左側前綴法則 (Leftmost Prefix)**：Composite Index `(a, b, c)` 只能支援 `a` 或 `a, b` 或 `a, b, c` 的查詢。
- **高選擇性優先**：`idx_sub_user_symbol` 優先於 `idx_sub_symbol_user`。

## 大表處理策略 (Large Table Strategies)

針對 `stock_prices` 與 `notification_logs` 等千萬級大表：

- 必須使用 Composite Index (如 `symbol + date`)。
- 查詢必須限制時間範圍 (`WHERE date >= ?`)。
- 嚴禁 `SELECT *`，只抓取必要欄位。
- 採用 Batch Insert 寫入。

## Migrations (Alembic)

- Migrations must be static and reversible
- Use async template: `alembic init -t async migrations`
- Descriptive filenames:
  ```ini
  # alembic.ini
  file_template = %%(year)d-%%(month).2d-%%(day).2d_%%(slug)s
  ```
  → `2026-04-14_add_post_content_idx.py`
