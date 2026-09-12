# 開發故事：Discord Webhook 訊息 ID 提取契約、持久化業務事實與有界重試收斂 (PARS) 📜

> 類別：開發歷程複盤（Narrative Log）
>
> ⚠️ **重要聲明**：本文件僅為歷史敘事日誌，記錄當時問題脈絡、執行的修復行動與除錯統計，供團隊複盤回溯。**PARS 故事不是架構規範，絕不可作為未來開發或架構設計的依據或證據**。架構規範請以 [Discord Notification Archival Contract](../features/daily_task/discord_notification_archival_contract.md) 為準。

---

## 1. Problem (問題脈絡)

在引入 Discord Webhook 通知架構後，實機測試與代碼審查發現數個關鍵契約脆弱點：
1. **Discord Webhook 訊息 ID 提取與歷史追蹤失效**：原實作在發送 Discord Webhook 時，未嚴格限定必須回傳 Snowflake ID 才算成功；在未帶 `?wait=true` 或回應非 200 時可能拿到空 ID，導致成功發送的訊息無法登錄至 `notification_history.json`，隔日 07:00 Desired-State 收斂即無法透過 HTTP DELETE 清理。
2. **里程碑 2 判定缺乏持久化業務事實 (Ephemeral State Loss)**：原判定依賴記憶體中 `quest_scheduler.is_all_completed()`，但一旦完成後立即解除排程器，若當時通知發送失敗或網路抖動，後續週期性輪詢無法獲知「今日懸賞已打完」這一事實；若從 `accepted_quests == []` 反推，又會在尚未接取任何懸賞時造成誤判。
3. **單一 Tick 出站網路延遲無上限 (Unbound Outbound Latency)**：若背景輪詢中累積多個未發送通知，原函式依序發送多個 HTTP 請求；更嚴重的是，原代碼以 `bool(result)`（等於 `result.success`）作為中斷依據，當第一筆請求發送失敗時，後續原則仍會接連嘗試發送，導致在網路異常時單一幀卡頓數秒。

---

## 2. Action (架構設計與實作行動)

### 2.1 嚴格 HTTP 200 + Snowflake ID 成功契約
- 修改 [`DiscordWebhookAdapter`](../../runtime/discord_webhook_adapter.py)，發送時強制追加 `?wait=true` 查詢參數。
- 嚴格限定僅當 HTTP 狀態碼為 200 且回應包含合法 Snowflake ID 時，`NotificationResult.success` 才為 True，且僅在此時才調用 `track_dispatched_message` 登錄歷史並寫入當日 notified date。

### 2.2 先記業務事實，再發通知 (Durable Business Fact First)
- 在 [`DailyManager`](../../utils/daily_manager.py) 增加 `record_bounty_quests_completed()` 與持久化欄位 `bounty_quests.completed_today`，隨 08:05 重置週期自動清除。
- 狀態機在偵測到 `quest_scheduler.is_all_completed()` 時，依序執行「持久化業務事實 ➔ 發送通知 ➔ 解除排程器」，確保即使當下通知失敗，業務事實已安全落盤於 `daily_status.json`。

### 2.3 週期性收斂與解耦 Attempt 與 Success
- 於 [`DailyPipelineNotifier`](../../states/daily_pipeline_notifier.py) 實作 `reconcile_pending_notifications()`，每 60 秒定期評估 Milestone 1、Milestone 2 與 Deadline Alarm。
- 引入 `PolicyOutcomeStatus`（`NOT_APPLICABLE`、`ATTEMPTED_SUCCESS`、`ATTEMPTED_FAILED`）與 `PolicyEvaluationResult`，明確將「是否嘗試對外發送 (attempted)」與「發送是否成功 (success)」解耦。
- 強制規定單一 Tick 只要有任何原則發起過對外 HTTP 請求（無論成敗），即刻中斷當前 Tick 評估，將出站請求延遲嚴格限制在至多 1 次。

### 2.4 真實 Discord Webhook 端到端驗證
- 執行真實 Discord 頻道 E2E 驗證：POST 200 成功取得 19 位 Snowflake ID ➔ 歷史檔案成功登錄 ➔ 呼叫 DELETE 得到 HTTP 204 清理成功 ➔ 二次呼叫 DELETE 得到 HTTP 404 冪等確認。

---

## 3. Result (成果驗證)

1. **雙工作樹對比與全套測試零迴歸**：
   - Main Baseline (`temp-main`)：`Ran 1064 tests in 381.090s, FAILED (failures=1, errors=1, skipped=15)`（2 個環境預存失敗）。
   - Feature HEAD (`BlackfireCrusade_tool`)：`Ran 1085 tests in 388.316s, OK (skipped=14)`，新增 21 個測試案例，零 Failure、零 Error，`BRANCH_REGRESSIONS: NONE`。
2. **長效規範收斂**：
   - 更新 [Discord Notification Archival Contract](../features/daily_task/discord_notification_archival_contract.md)。
   - 於專案規範建立「PolicyEvaluationResult 禁止依賴隱式 bool 做流程調度決策」契約。
   - 於 `branch_completion_workflow` 補齊對稱銷毀契約（Push main 成功後對稱刪除 local 與 remote 分支）。
