# 開發故事：Daily Status Notifier 與看門狗崩潰警報整合 (PARS) 📜

> 類別：開發歷程複盤（Narrative Log）
>
> ⚠️ **重要聲明**：本文件僅為歷史敘事日誌，記錄當時問題脈絡、執行的修復行動與除錯統計，供團隊複盤回溯。**PARS 故事不是架構規範，絕不可作為未來開發或架構設計的依據或證據**。架構規範請以 [Notification System Contract](../features/notification/notification_contract.md) 為準。

---

## 1. Problem (問題脈絡)

在每日 08:05 跨越重置線時，操作員面臨以下自動化痛點：
1. **晨間營運焦慮 (Operational Anxiety)**：操作員無法在不打開遠端桌面的情況下得知腳本是否已完成日常速領（Tier 1）與懸賞討伐（Tier 3），缺乏自動化責任移交與完成通報。
2. **看門狗崩潰迴圈靜默 (Silent Crash Loop)**：當遊戲行程遭遇連續 Crash 或心跳逾時重開時，外部看門狗雖然會自動拉起，但若進入頻繁崩潰迴圈（如 5 次/90 秒），操作員無法第一時間收到告警接管。
3. **資訊過載與洗屏風險**：若將除錯日誌直接推送到 Discord，會產生大量冗餘通知，破壞「靜默代表自動化持續負責，通知代表責任移交操作員」的通報哲學。

---

## 2. Action (架構設計與實作行動)

### 2.1 六角架構解耦 (Ports & Adapters)
- 於 `ports/` 定義純抽象協定 `NotificationPort` 與 `NotificationHistoryPort`。
- 於 `runtime/` 實作具體適配器 `DiscordWebhookAdapter` 與 `JsonNotificationHistoryStore`。
- 於 `states/` 實作應用調度器 `DailyPipelineNotifier` 與 `DailyReconciliationService`，完全隔離基礎設施與 HTTP 細節。

### 2.2 雙階段里程碑與雙警報機制
- **Milestone 1**：Tier 1 5 大項（寶箱、抽角、祭壇、珠寶店、告示牌接取）完成後發布 `AUTOMATION_HEALTHY`。
- **Milestone 2**：8 項告示牌懸賞任務全數討伐完成並切換至 Tier 4 時發布 `AUTOMATION_HEALTHY`。
- **Alarm 1 (`DAILY_CLAIM_DEADLINE_EXCEEDED`)**：08:05 重置後逾 30 分鐘速領未完成，發送紅色警報。
- **Alarm 2 (`SUPERVISOR_CRASH_LOOP_EXCEEDED`)**：看門狗在滑動窗口內重啟超過 5 次，發送紅色警報。

### 2.3 歷史訊息 Desired-State 收斂
- 每日 07:00 起跑線，調用 Discord HTTP DELETE 刪除前日歷史通知，保持頻道版面乾淨。

### 2.4 回歸除錯與 Profile 隔離
- 排除 `NullDailyPipelineNotifier` 查詢語言時調用 `set_active_profile` 造成本機配置污染測試環境之隱蔽副作用。
- 修復 `runtime/supervisor.py` 中 `incident_journal` 函式導入缺漏。

---

## 3. Result (成果驗證)

1. **單元與行為測試 100% 綠燈**：
   - 全套測試：`Ran 1068 tests in 367.485s, OK (skipped=14)`，零 Failure、零 Error。
   - 專案通知測試 (`test_daily_milestone_notifications`, `test_notification_port`, `test_supervisor_alarm`)：54/54 通過。
2. **獨立 Dry-Run 支援**：
   - 支援 `python main.py --test-notify [all|milestone1|milestone2|deadline] [--live]` 離線預覽，不需啟動遊戲即可驗證 Payload 格式。
