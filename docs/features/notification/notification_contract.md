# Notification System Contract 📢

> 狀態：正式開發準則（Normative）
>
> 核心實作：[NotificationPort](../../../ports/notification_port.py)、[DailyPipelineNotifier](../../../states/daily_pipeline_notifier.py)、[DailyReconciliationService](../../../states/daily_reconciliation.py)、[DiscordWebhookAdapter](../../../runtime/discord_webhook_adapter.py)
>
> 測試防護：[test_daily_milestone_notifications.py](../../../tests/test_daily_milestone_notifications.py)、[test_notification_port.py](../../../tests/test_notification_port.py)、[test_supervisor_alarm.py](../../../tests/test_supervisor_alarm.py)

---

## 一、 責任邊界與六角架構 (Hexagonal Architecture)

本通知系統採用嚴格的六角架構（Ports & Adapters），禁止任何反向依賴：

```text
[ports/]               NotificationPort, NotificationHistoryPort
   ▲
   │ 依賴抽象契約 (Dependency Inversion)
   │
[states/]              DailyPipelineNotifier, DailyReconciliationService
   ▲
   │ 依賴注入 / Factory 裝配
   │
[runtime/]             DiscordWebhookAdapter, JsonNotificationHistoryStore
```

1. **領域與調度層 (`states/`)**：
   - `DailyPipelineNotifier` 負責監聽狀態機與流水線里程碑，裁決發布時機。
   - `DailyReconciliationService` 負責訊息過期收斂邏輯。
   - 領域層僅依賴 `ports/` 下的 Protocol/ABC 介面，**嚴禁直接 import `runtime/` 基礎設施實作**。

2. **基礎設施與適配器層 (`runtime/`)**：
   - `DiscordWebhookAdapter` 實作 `NotificationPort`，負責 HTTP POST/DELETE 與 Discord Rate Limit (HTTP 429) 退避重試。
   - `JsonNotificationHistoryStore` 實作 `NotificationHistoryPort`，負責 JSON 檔案存取。
   - `CrashLoopTracker` 負責滑動窗口重啟頻率計數與穩定狀態重置。

3. **裝配邊界 (`runtime/notifier_factory.py`)**：
   - 負責讀取配置並實例化具體 Adapter，於 `main.py` 或 `runtime/bootstrap.py` 注入至狀態機。

---

## 二、 語意契約與通報分類 (Notification Semantics)

系統發送的通知嚴格分為兩類，不混用、不流水帳洗屏：

| 分類 | 視覺標籤 | Embed 顏色代碼 | 語意約束 |
| :--- | :--- | :--- | :--- |
| **里程碑通報 (Milestone)** | `AUTOMATION_HEALTHY` | 綠色 (`0x2ECC71`) | 宣告特定業務階段已達成，目前無需操作員介入 (`NO_ACTION_REQUIRED`)。 |
| **人工接管求救 (Alarm)** | `OPERATOR_ACTION_REQUIRED` | 紅色 (`0xE74C3C`) | 自動化自癒階梯耗盡，發生不可逆或超限故障，必須由操作員接管遠端。 |

### 1. 里程碑 1：Daily Claim Phase 速領完成
- **觸發條件**：每日 08:05 重置後，Tier 1 5 個子流程全數完成（`chest`、`hero_draw`、`blood_altar`、`jewelry_workshop`、`bulletin_board` 的 `completed_today == True`）。
- **冪等保證**：同一 08:05 重置週期內（以 `cycle_tag` 為鍵）僅發送一次，避免重複通知。

### 2. 里程碑 2：告示牌懸賞全數清空
- **觸發條件**：`QuestScheduler.is_all_completed()` 為 `True`，且已轉入 Tier 4 長駐模式。
- **冪等保證**：同一 08:05 重置週期內僅發送一次。

### 3. 警報 1：日常速領逾時未完成 (`DAILY_CLAIM_DEADLINE_EXCEEDED`)
- **觸發條件**：自 08:05 起算經過 `daily_claim_deadline_minutes`（預設 30 分鐘，即 08:35 後），Tier 1 仍有子流程未標記完成。
- **發送行為**：列出未完成子流程清單與當前狀態機狀態，提醒操作員確認。同一週期僅發送一次。

### 4. 警報 2：Supervisor 看門狗崩潰迴圈超限 (`SUPERVISOR_CRASH_LOOP_EXCEEDED`)
- **觸發條件**：滑動窗口 `T_window` 內（以當前看門狗逾時與緩衝時間動態計算）累積重啟次數超過 `max_restarts`（預設 5 次）。
- **自癒重置**：子行程存活時間超過穩定門檻（預設 120 秒）且進入 `NAVIGATING` 或 `BATTLE` 狀態時，自動清空計數器與警報狀態。

---

## 三、 歷史訊息收斂契約 (Desired-State Reconciliation)

為防止歷史通知長期佔用 Discord 頻道版面，系統採用 Desired-State 收斂機制：

1. **起跑線規則 (07:00 Line)**：
   - 每日 07:00 起跑點，系統主動檢查前日歷史訊息記錄（`user_data/<profile>/notification_history.json`）。
   - 對所有標記為前日週期的 Discord 訊息（包括 Milestone 1、Milestone 2、Deadline Alarm），依據記錄之 `message_id` 調用 Discord API 刪除（HTTP DELETE）。
   - 若 Discord 回應 404（訊息已被手動刪除），視為已收斂成功。
   - 刪除成功後將記錄標記為 `deleted: true`，當日不再重複掃描。

2. **多實例隔離**：
   - 各 Profile（如 `native`、`sandbox`）各自擁有獨立的 `notification_history.json`，歷史記錄互不干擾。

---

## 四、 執行緒安全與主流程零阻斷 (Non-blocking Invariant)

1. **非同步派發預設**：
   - `NotificationPort.notify_milestone()` 與 `NotificationPort.notify_alarm()` 預設以 Daemon Thread 非同步發送（`sync=False`）。
   - HTTP 網路延遲、重試或暫時性斷網絕不阻塞狀態機主迴圈。

2. **例外吞吐保證**：
   - 基礎設施層的所有網路錯誤（DNS 解析失敗、連線超時、HTTP 5xx）僅於日誌輸出 `logging.warning`，絕不拋出未捕獲例外至遊戲主調度器。

3. **設定讀取無副作用**：
   - `get_supervisor_settings(profile)` 與 `get_notification_language(profile)` 必須直接解析指定 Profile 設定檔，嚴禁調用 `set_active_profile` 造成全域狀態機與模式配置被污染。
