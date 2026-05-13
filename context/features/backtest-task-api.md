# Backtest Task API Spec

## Overview

實作觸發任務 API 與查詢任務狀態 API，用於處理股票回測前的資料完整性檢查與缺失資料的異步補充。

API 流程：
1. 檢查 `DailyPrice` 資料表，確認該股票在要求日期區間內是否有足夠資料
2. 資料完整 → 直接回傳資料或開始執行回測
3. 料缺失 → 建立 ARQ 任務抓取缺失資料，回傳 HTTP 202 Accepted + job_id

## Requirements

### 1. Trigger Task API - POST /stocks/{stock_id}/backtest/trigger

**功能描述**：
- 接收前端請求，包含 `stock_id`、日期區間 (`start_date`, `end_date`)
- 檢查資料庫 `DailyPrice` 在該區間的資料覆蓋率
- 根據覆蓋率決定回應策略

**請求 Schema**：
```python
class BacktestTriggerRequest(BaseModel):
    start_date: datetime.date
    end_date: datetime.date
    # 未來可擴充：strategy_type, parameters 等
```

**回應策略**：

| 覆蓋率 | HTTP Status | 回應內容 |
|--------|-------------|----------|
| 100% (完整) | 200 OK | `{ "status": "ready", "data_count": N, "message": "Data ready for backtest" }` |
| 0% ~ 99% (缺失) | 202 Accepted | `{ "status": "pending", "job_id": "xxx", "missing_dates": [...], "message": "Job created to fetch missing data" }` |

**資料覆蓋率計算邏輯**：
- 查詢 `DailyPrice` 計算實際存在的交易日數量
- 考慮交易日 vs 非交易日（週末、假日）- 使用簡化邏輯或未來整合交易日曆
- 回傳缺失的日期區間（可分段）

### 2. Query Task Status API - GET /tasks/{job_id}

**功能描述**：
- 查詢 ARQ 任務執行狀態
- 支援狀態：`pending`, `in_progress`, `completed`, `failed`

**回應 Schema**：
```python
class TaskStatusResponse(BaseModel):
    job_id: str
    status: str  # pending | in_progress | completed | failed
    created_at: datetime.datetime | None
    started_at: datetime.datetime | None
    finished_at: datetime.datetime | None
    result: dict | None  # 任務完成後的結果
    error: str | None    # 失敗時的錯誤訊息
```

**ARQ 任務狀態對應**：
- 使用 ARQ 內建的 `ArqRedis.get_job_result()` 或 `Job.status`
- 若任務不存在，回傳 HTTP 404

### 3. ARQ Job - fetch_missing_daily_prices

**任務功能**：
- 接收 `stock_id`、缺失日期區間列表
- 根據股票 `source` (Fugle/YFinance) 呼叫對應 API 取得歷史價格
- 使用 `DailyPriceService.bulk_insert_prices` 寫入資料庫（upsert）

**Job 定義位置**：
- 新增 `src/tasks/jobs/backtest_jobs.py`
- 在 `src/tasks/jobs/__init__.py` 加入 export
- 在 `src/tasks/worker.py` 的 `DefaultWorkerSettings.functions` 加入此 job

**Job Schema**：
```python
# 任務參數
async def fetch_missing_daily_prices(ctx: dict, stock_id: int, date_ranges: list[tuple[date, date]]) -> dict:
    """
    Args:
        ctx: ARQ context
        stock_id: 股票 ID
        date_ranges: 缺失日期區間列表 [(start, end), ...]

    Returns:
        {"stock_id": int, "fetched_count": int, "success": bool}
    """
```

### 4. Service Layer - BacktestService

**新增方法**：
- `check_data_coverage(db, stock_id, start_date, end_date)` - 檢查資料覆蓋率
- `calculate_missing_ranges(db, stock_id, start_date, end_date)` - 計算缺失日期區間
- `trigger_backtest_job(redis, stock_id, missing_ranges)` - 建立 ARQ 任務

### 5. Router Layer

**新增 endpoints**：
- POST `/stocks/{stock_id}/backtest/trigger` - 觸發任務
- GET `/tasks/{job_id}` - 查詢任務狀態（可放在 `src/tasks/router.py` 或共用模組）

**注意**：
- GET `/tasks/{job_id}` 為通用 API，建議放在 `src/tasks/router.py` 新模組
- 需在 `src/main.py` mount 新 router

### 6. 資料庫查詢優化

**索引使用**：
- 已有 `idx_daily_price_stock_date` (stock_id, date) composite index
- 查詢覆蓋率時使用 index-only scan

**查詢邏輯**：
```sql
-- 計算區間內實際資料數
SELECT COUNT(*) FROM daily_prices
WHERE stock_id = ? AND date >= ? AND date <= ? AND is_deleted = FALSE;

-- 取得區間內所有日期（用於比對缺失）
SELECT date FROM daily_prices
WHERE stock_id = ? AND date >= ? AND date <= ? AND is_deleted = FALSE
ORDER BY date;
```

### 7. 錯誤處理

| 場景 | HTTP Status | Error Message |
|------|-------------|---------------|
| Stock 不存在 | 404 Not Found | "Stock not found: {stock_id}" |
| 日期區間無效 (start > end) | 400 Bad Request | "Invalid date range: start_date must be before end_date" |
| 任務不存在 | 404 Not Found | "Task not found: {job_id}" |

### 8. 測試需求

**Test Coverage**：
- BacktestService.check_data_coverage (完整/部分/空)
- BacktestService.calculate_missing_ranges
- Trigger API 回應狀態碼 (200 vs 202)
- Task Status API 各狀態回應
- ARQ Job fetch_missing_daily_prices 執行
- Edge cases: invalid date range, stock not found

**Test Files**：
- `tests/test_backtest_service.py`
- `tests/test_backtest_router.py`
- `tests/test_tasks_router.py`

## References

- @src/stocks/service.py - DailyPriceService 現有方法
- @src/stocks/model.py - DailyPrice model 定義
- @src/tasks/jobs/price_update_jobs.py - ARQ job 實作範例
- @src/tasks/worker.py - WorkerSettings 配置
- @doc/rules/database.md - 資料庫查詢規範