# 背景任務與非同步決策 (async-tasks.md)

## 1. 路由宣告與非同步策略

處理 API 請求時，根據任務的性質決定路由的宣告方式，**嚴禁在 `async def` 中執行阻塞操作**。

| 任務性質                      | 適用宣告與工具                    | 說明                                                                 |
| :---------------------------- | :-------------------------------- | :------------------------------------------------------------------- |
| **非阻塞 I/O** (可 `await`)   | `async def`                       | 標準非同步情境（如 AsyncSession 查詢、`httpx.AsyncClient` 呼叫）。   |
| **阻塞 I/O** (無非同步套件)   | `def` (同步路由)                  | FastAPI 會自動將其丟入 Threadpool 執行，避免卡死整個 Event Loop。    |
| **混合型** (非同步中夾雜同步) | `async def` + `run_in_threadpool` | 路由保持非同步，僅針對特定的同步函數或舊版套件使用 Threadpool 封裝。 |
| **CPU 密集 / 耗時運算**       | 卸載至 **Celery**                 | 運算時間大於 50ms 的任務，必須交由獨立的 Worker 處理。               |

## 2. 背景任務工具決策表

嚴禁使用 FastAPI 內建的 `BackgroundTasks` 處理與業務高度相關或不容遺失的關鍵任務。

| 判斷指標     | FastAPI `BackgroundTasks`  | Celery                                         |
| :----------- | :------------------------- | :--------------------------------------------- |
| **執行時間** | 極短 (< 1 秒)              | 長（數秒至數分鐘）                             |
| **容錯要求** | 允許失敗且被靜默丟棄       | 需要重試機制 (Retries)、死信佇列 (Dead-letter) |
| **執行環境** | 在同一個 API Worker 行程內 | 獨立的 Worker Pool，不影響 API 效能            |
| **排程需求** | 無，僅限請求結束後立即觸發 | 支援 Cron 定時任務、延遲執行 (ETA)、速率限制   |
| **生命週期** | 隨 API Worker 死亡而消失   | 任務持久化儲存於 Redis/RabbitMQ 代理中         |

## 3. 實作地雷與強制規定 (Anti-patterns)

- **❌ 阻塞 Event Loop**：嚴禁在 `async def` 中使用 `time.sleep()`、`requests.get()` 或同步的資料庫驅動。這會導致整個 Worker 癱瘓，無法處理其他併發請求。
  - **✅ 解法**：改用 `asyncio.sleep()`、`httpx.AsyncClient()` 或 SQLAlchemy Async 驅動。
- **❌ 濫用 BackgroundTasks 發送重要通知**：若發送 Line 通知或寫入重要 Log 時 Worker 發生重啟，任務將永久遺失。
  - **✅ 解法**：涉及外部通訊或資料一致性的背景操作，必須推播至 Celery 處理。
