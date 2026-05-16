# Current Feature

Indicator Subscription Notification Check

## Status

Complete

## Goals

- 在 `update_indicator` job 中記錄剛更新的股票 ID 到 Redis Set
- 新增 `check_indicator_subscriptions` cron job，每分鐘檢查更新的股票訂閱條件
- 實作條件比對邏輯（evaluate_condition_group, compare_values 等）
- 發送通知並記錄到 `notification_histories` 表
- 支援冷卻時間避免重複通知
- 註冊 worker cron job
- 新增相關配置設定（批次大小、冷卻時間等）
- 完整測試覆蓋（條件比對、job 錯誤處理）

## Notes

**核心設計（Hybrid 方案）**：
- 在 `update_indicator` job 中記錄剛更新的股票 ID 到 Redis
- 新增 `check_indicator_subscriptions` cron job，每分鐘執行
- 只處理 Redis 中記錄的更新股票，而非全部訂閱
- SQL JOIN 查詢這些股票的訂閱 + 指標值
- Python 比對條件邏輯（清晰可測試）
- 批次發送通知並記錄到 `notification_histories`
- 支援冷卻時間避免重複通知

**效能優勢**：
- 假設 1000 股票 × 10000 訂閱，但每分鐘只更新 50 股票
- 只查詢 500 記錄（50 股票 × 10 訂閱），而非全表掃描
- 執行時間 ~85ms（Redis 5ms + SQL 50ms + Python 10ms + Notification 20ms）

**關鍵實作點**：
- Redis Set: `indicator:updated:last_minute`，TTL 120 秒
- SQL 使用索引: `idx_indicator_subs_on_stock_active`, `idx_stock_indicator_stock_id`
- 不使用 ARQ retry（避免重複通知），只記錄錯誤

**參考檔案**：
- src/tasks/jobs/indicator_jobs.py - update_indicator job (需修改)
- src/tasks/jobs/subscription_jobs.py - 新增 check_indicator_subscriptions job
- src/tasks/worker.py - Worker registration
- src/subscriptions/service.py - 新增條件比對邏輯
- src/subscriptions/model.py - IndicatorSubscription, NotificationHistory models
- src/subscriptions/schema.py - ConditionGroup, Condition schemas
- src/stock_indicator/service.py - Indicator service
- src/stock_indicator/model.py - StockIndicator model
- src/config.py - Settings configuration

## History

- 2026-05-16: Indicator Subscription Notification Check Implementation
  - Added Redis tracking in update_indicator job (REDIS_INDICATOR_UPDATED_KEY)
  - Created check_indicator_subscriptions cron job running every minute
  - Implemented condition evaluation logic (evaluate_subscription, AND/OR logic)
  - Added helper functions (build_indicator_key, extract_indicator_value, compare_values)
  - Implemented notification sending with cooldown support
  - Registered cron job in DefaultWorkerSettings
  - Added configuration settings (SUBSCRIPTION_COOLDOWN_HOURS, SUBSCRIPTION_CHECK_BATCH_SIZE)
  - Created comprehensive tests (35 tests, all passing)
  - Fixed bug: cron job minute parameter must be set, not range object
  - Verified working: jobs executed successfully, notifications sent
  - Benefits: High-performance subscription check (only updated stocks), immediate notifications
- 2026-05-16: Indicator Subscription Simplification
  - Removed redundant single-condition fields (indicator_type, operator, target_value, timeframe, period)
  - Made condition_group required JSONB with CHECK constraint (1-10 conditions)
  - Renamed compound_condition to condition_group in all schemas
  - Added Alembic migration to convert existing subscriptions to condition_group format
  - Simplified service logic by removing dual-mode handling
  - Updated StockIndicatorService to extract conditions uniformly from condition_group
  - Updated all 106 subscription-related tests to use condition_group format
  - Updated API documentation with new schema structure
  - Benefits: One format for all conditions (1-N), cleaner code, consistent API
- 2026-05-16: Indicator Update Cron Job Refactor
  - Renamed calculate_stock_indicators to update_indicator
  - Simplified job to run every minute (CRON_INDICATOR_MINUTES=*/1)
  - Removed stock_id parameter, job now queries all subscriptions automatically
  - Updated worker imports and cron job registration
  - Updated test files to use new function name
  - Benefits: Cleaner code, automatic processing of all subscribed stocks