# Stock Subscription Notification Flow Spec

## Overview

當用戶訂閱某隻股票時,系統需要自動檢查並準備必要的數據,確保訂閱條件可以正常監控。此流程包含驗證訂閱條件、檢查股票狀態,以及自動觸發數據準備任務。

## Requirements

### 1. Subscription Validation (Node B)

用戶提交訂閱時,需檢查以下條件:

- **股票存在性驗證**: 確認請求的 stock_id 在 stocks 表中存在
- **訂閱條件合法性**: 驗證訂閱條件 (indicator_type, operator, target_value) 是否符合系統定義的合法值
- **返回結果**: 若驗證失敗,返回錯誤通知給用戶;成功則繼續流程

### 2. Stock Active Status & Indicator Data Check (Node C)

驗證通過後,檢查股票的數據準備狀態:

- **檢查股票是否為 Active**: 查詢 Redis 中該股票的 active 狀態
- **檢查 calculated_indicator 資料**: 確認用戶提及的技術指標 (如 RSI, KD, MACD) 是否已存在於 calculated_indicator 資料表中
- **判斷邏輯**:
  - 若股票為 Active 且所需指標已計算 → 流程結束 (Node D)
  - 若股票不為 Active 或指標缺失 → 觸發數據準備流程 (Node E)

### 3. Automatic Data Preparation (Node E)

當股票數據未準備時,自動執行以下操作:

- **設置股票為 Active**: 將該股票標記為 active 狀態並存入 Redis
- **觸發 Worker 任務**: 啟動 ARQ Worker 任務執行以下步驟:
  1. **取得即時股價**: 從 Fugle/YFinance API 取得該股票當前價格
  2. **抓取歷史股價**: 取得該股票 100 天的歷史股價資訊 (OHLCV)
  3. **計算技術指標**: 基於歷史股價計算所需技術指標並存入 calculated_indicator 表

## References

- @src/stocks/model.py - Stock model definition
- @src/subscriptions/schema.py - Subscription request schema
- @src/stocks/indicators.py - Technical indicator calculation logic
- @src/tasks/worker.py - ARQ Worker task definitions
- @doc/rules/database.md - Database constraints and soft delete rules
- @context/features/history-stock-download-worker.md - Related worker task spec (if exists)

## Implementation Notes

1. **API Endpoint**: 此邏輯應整合至 POST `/subscriptions/indicators` endpoint 的 service 層
2. **Async Flow**: Worker 任務應為非同步執行,避免阻塞 API 响应
3. **Indicator Coverage**: 需確認 calculated_indicator 表結構是否支援所有 indicator_type
4. **Error Handling**: Worker 失敗時應有重試機制並記錄錯誤 log
5. **Performance**: 避免每次訂閱都重新計算已存在的指標,使用 caching 確認狀態