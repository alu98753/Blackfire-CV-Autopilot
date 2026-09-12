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
- **業務事實持久化先行**：當 `QuestScheduler.is_all_completed()` 成立時，`DailyManager` 優先將 `bounty_quests.completed_today = True` 持久化至 JSON 存檔中，隨後才嘗試發送通知與解除排程器 (`quest_scheduler = None`)。每日 08:05 重置時該欄位隨子流程一同重置為 `False`。
- **觸發與冪等保證**：依據持久化業務事實發送通知，轉入 Tier 4 長駐模式。同一 08:05 重置週期內僅發送一次。

### 3. 警報 1：日常速領逾時未完成 (`DAILY_CLAIM_DEADLINE_EXCEEDED`)
- **觸發條件**：自 08:05 起算經過 `daily_claim_deadline_minutes`（預設 30 分鐘，即 08:35 後），Tier 1 仍有子流程未標記完成。
- **發送行為**：列出未完成子流程清單與當前狀態機狀態，提醒操作員確認。同一週期僅發送一次。

### 4. 警報 2：Supervisor 看門狗崩潰迴圈超限 (`SUPERVISOR_CRASH_LOOP_EXCEEDED`)
- **觸發條件**：滑動窗口 `T_window` 內（以當前看門狗逾時與緩衝時間動態計算）累積重啟次數超過 `max_restarts`（預設 5 次）。
- **自癒重置**：子行程存活時間超過穩定門檻（預設 120 秒）且進入 `NAVIGATING` 或 `BATTLE` 狀態時，自動清空計數器與警報狀態。

---

## 三、 歷史訊息收斂與重試排程 (Desired-State Reconciliation)

為防止歷史通知長期佔用 Discord 頻道版面，並保證網路故障時通知具備穩定補發機制，系統採用 Desired-State 收斂架構：

1. **起跑線規則 (07:00 Line)**：
   - 每日 07:00 起跑點，系統主動檢查前日歷史訊息記錄（`user_data/<profile>/runtime/notification_history.json`）。
   - 對所有標記為前日週期的 Discord 訊息（包括 Milestone 1、Milestone 2、Deadline Alarm），依據記錄之 `message_id` 調用 Discord API 刪除（HTTP DELETE）。
   - 若 Discord 回應 404（訊息已被手動刪除），視為已收斂成功。
   - 刪除成功後將記錄自 `dispatched_messages` 列表中剔除 (Eviction)。當過期項目全數清空後，寫入 `last_reconciled_date = today_tag` 鎖定 (Daily Completion Latch)，當日不再重複掃描。

2. **嚴格派發契約 (Strict Tracked Dispatch Contract)**：
   - 在帶有 `?wait=true` 條件下，只有 Discord 伺服器確認並回傳 HTTP 200 與有效 Snowflake ID 時，才視為 `success=True`。
   - 若收到 HTTP 204、連線超時、伺服器異常或缺少 ID，均判定為發送失敗。
   - Milestone 1、Milestone 2 與 Deadline Alarm 均統一遵循該契約：僅當發送成功且取得有效 `external_message_id` 時，方可記錄 `last_*_date`；否則保留重試資格 (Retry Eligibility)。

3. **待發送通知週期性對齊 (Pending Notification Reconciliation)**：
   - 狀態機主迴圈透過 `DailyPipelineNotifier.reconcile_pending_notifications()` 週期性檢驗業務完成事實與通知達成狀態。
   - **掃描間隔節流**：內部採用單調時鐘（`time.monotonic()`）維持 60 秒掃描間隔（`_pending_reconcile_interval_seconds = 60.0`），避免主迴圈高頻無冷卻發起外部 HTTP 請求。
   - **客觀事實驅動**：
     - Milestone 1 依據 `DailyManager.is_tier1_daily_claim_completed()` 補發。
     - Milestone 2 依據 `DailyManager.is_bounty_quests_completed()` 補發，不再依賴揮發性 `quest_scheduler` 物件存續或 `accepted_quests == []` 反推。
     - Deadline Alarm 依據 08:05 重置逾時狀態補發。
   - **單次 Tick 網路延遲有界上界 (At-most-one Outbound Request)**：
     - 單一週期依優先級（`Deadline Alarm` ➔ `Milestone 1` ➔ `Milestone 2`）檢驗，一旦觸發第一個待發送通知之網路請求即返回，將剩餘通知交由下一個週期處理，確保單一狀態機步驟外部網路阻塞時間擁有明確上限。

4. **多實例隔離與原子存取 (Crash Consistency)**：
   - 各 Profile（如 `native`、`sandbox`）各自擁有獨立的 `notification_history.json`，歷史記錄互不干擾。
   - `JsonNotificationHistoryStore` 透過同目錄暫存檔原子替換 (`os.replace`) 與 `fsync` 保證寫入一致性，避免異常中斷破壞 JSON 格式或造成快取假陽性。

---

## 四、 執行緒安全與主流程零阻斷 (Non-blocking Invariant)

1. **同步與非同步派發準則**：
   - `NotificationPort` 基礎介面支援 Daemon Thread 非同步發送（`sync=False`）。
   - 但非同步派發無法向呼叫者回傳 message ID。因此，凡需要記錄 `message_id` 於翌日 07:00 執行對帳清理之領域訊息（Milestone 1、Milestone 2、Deadline Alarm），Production 呼叫路徑一律使用 `sync=True`。

2. **例外吞吐保證**：
   - 基礎設施層的所有網路錯誤（DNS 解析失敗、連線超時、HTTP 5xx）僅於日誌輸出 `logging.warning`，絕不拋出未捕獲例外至遊戲主調度器。

3. **設定讀取無副作用**：
   - `get_supervisor_settings(profile)`、`get_notification_language(profile)` 與 `get_notification_webhook_url(profile)` 必須直接解析指定 Profile 設定檔，嚴禁調用 `set_active_profile` 造成全域狀態機與模式配置被污染。
