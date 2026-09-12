# Feature Spec: Daily Status Notifier (feat-daily-status-notifier) 📢

## 一、 自動化責任與通知契約 (Automation Responsibility Contract)

本規格並非流水帳日誌推送，而是建立系統邊界與操作員之間的責任契約：

> **「早上我不打開遠端、不看遊戲，也能相信腳本自己處理；只有真的需要我介入時才打擾我。」**

### 通知語意契約 (Notification Semantics)
1. **靜默代表自動化持續負責 (Silence means automation is still responsible)**：
   腳本在正常巡航、遇可自癒之輕微異常（單次逾時、自動彈窗排除、正常體力退避）時，一律保持靜默，不發送任何通知。
2. **通知代表責任移交操作員 (A notification indicates an operator handoff)**：
   系統發送的通知嚴格分為兩類，絕無模糊空間：
   - **里程碑通報 (`Milestone Notification` / `AUTOMATION_HEALTHY`)**：特定業務階段達成，宣告自動化進度無虞，目前無需操作員介入 (`NO_ACTION_REQUIRED`)。
   - **人工介入求救 (`Operator Action Required` / `OPERATOR_ACTION_REQUIRED`)**：自動化已耗盡既定恢復政策 (`Recovery Policy`)，發生不可恢復故障 (`Unrecoverable Failure`)，必須由操作員接管遠端。

---

## 二、 通報策略：策略 A（雙階段里程碑通報 / Two-Phase Milestone Notifications）

採用雙階段里程碑設計，兼顧早晨起跑進度確認與終局責任交割 (`Completion Handoff`)：

```mermaid
flowchart TD
    A["08:05 每日重置線"] --> B["Tier 1 Daily Claim Phase"]
    B --> C{"5 大項全數完成?<br/>(含告示牌接取)"}
    C -- "30 分鐘內未完成" --> ERR1["⚠️ OPERATOR_ACTION_REQUIRED<br/>(DAILY_CLAIM_DEADLINE_EXCEEDED)"]
    C -- "全數完成" --> M1["✅ AUTOMATION_HEALTHY (Milestone 1)<br/>Daily Claim Phase Completed"]
    M1 --> D["Tier 3 告示牌懸賞戰鬥"]
    D --> E{"accepted_quests<br/>清空且無殘留?"}
    E -- "全部完成" --> M2["✅ AUTOMATION_HEALTHY (Milestone 2)<br/>Bounty Quests Cleared -> Steady-State Mode"]
```

### 里程碑 1：Daily Claim Phase 與告示牌任務接取完成 (`EVENT_DAILY_CLAIM_PHASE_COMPLETED`)
* **觸發時機**：每日 08:05 重置後，Tier 1 5 個子流程全數完成（[`DailyManager.status["subflows"]`](../../utils/daily_manager.py) 中 `chest`、`hero_draw`、`blood_altar`、`jewelry_workshop`、`bulletin_board` 的 `completed_today == True`）。
* **告示牌完成之嚴謹定義**：
  - 任務已成功在告示牌內完成掃描、比對與點擊接受，寫入 `accepted_quests` 存檔。
  - 退出至城鎮後，經 `detect_building_with_red_dot` 確認告示牌建築物下方之驚嘆號/紅點已消除。
  - **任務本身此時尚未開打，先接到即算完成，不算卡死**。
* **通知訊息內容範例**：
  ```text
  ✅ [AUTOMATION_HEALTHY] Daily Claim Phase 完成，懸賞任務已全數接取
  • 時間: 08:14
  • 速領項目: 寶箱(✓) 酒館(✓) 祭壇(✓) 商店(✓)
  • 已接懸賞 (5項): 破除森林的枷鎖、清除蛤蟆、討伐惡魔、擊敗冰元素、消滅幼蟲
  • 後續動作: 狀態機已接管，依優先序依序討伐中。
  ```

### 里程碑 2：告示牌懸賞任務清空並切換至 Tier 4 (`EVENT_BOUNTY_QUESTS_CLEARED`)
* **觸發時機**：[`QuestScheduler.is_all_completed()`](../../utils/quest_scheduler.py) 成立，`accepted_quests` 列表中所有項目均已討伐完成並移除，狀態機解除懸賞排程器，正式轉入 Tier 4（Transition to Tier 4 Steady-State Mode / Fallback Mode，如關卡刷怪、領地探索或體力耗盡進入 `collect_only` 待機）。
* **通知訊息內容範例**：
  ```text
  🎉 [AUTOMATION_HEALTHY] 每日懸賞任務已全部完成
  • 時間: 08:42
  • 懸賞成果: 5/5 項任務已全部討伐完成
  • 當前狀態: 已轉入 Tier 4 Steady-State Mode
  • 自動化責任交割完成 (Completion Handoff)，無需手動介入。
  ```

### 冪等性防重複規則 (Idempotency)
每個日曆天（依據 `DailyManager.status["last_daily_reset_date"]`）的里程碑 1 與里程碑 2 **各自僅允許發送一次**。即使 Child Bot 中途重啟，重新載入狀態後亦嚴禁重複推送已完成之里程碑。

---

## 三、 異常警報判定機制：恢復政策耗盡之不可恢復故障 (`OPERATOR_ACTION_REQUIRED`)

警報必須精確，嚴禁虛警報。僅當符合以下兩項硬性阻斷條件時，立即發送 `OPERATOR_ACTION_REQUIRED`：

### 規則 1：Supervisor 連續崩潰 / 重啟超限 (`SUPERVISOR_CRASH_LOOP_EXCEEDED`)
* **配置統一收攏 ([config/defaults.toml](../../config/defaults.toml))**：
  於 `config/defaults.toml` 新增看守者配置區塊：
  ```toml
  [supervisor]
  watchdog_timeout = 90.0        # 心跳逾時門檻 (秒)
  relaunch_buffer_seconds = 30.0 # 重啟後遊戲載入與狀態辨識緩衝 (秒)
  max_restarts = 5               # 滑動窗口內允許之最大重啟次數
  ```
* **滑動觀測窗口公式**：
  - 單次重啟可再次觀測遊戲之週期：
    $$T_{\text{relaunch}} = \text{watchdog\_timeout} + \text{relaunch\_buffer\_seconds} = 90.0 + 30.0 = 120.0 \text{ 秒}$$
  - 滑動觀測窗口時長：
    $$T_{\text{window}} = T_{\text{relaunch}} \times \text{max\_restarts} = 120.0 \times 5 = 600.0 \text{ 秒} = 10.0 \text{ 分鐘}$$
* **觸發條件**：
  在 $T_{\text{window}}$（10.0 分鐘）時間範圍內，[`Supervisor`](../../runtime/supervisor.py) 對 Child Bot 發起的非手動重啟次數（crash、heartbeat stale、unexpected exit）累計超過 `max_restarts`（預設 5 次），判定外部重啟無法自癒恢復。
* **Supervisor 成功修復定義（重置計數與窗口的標準）**：
  當 Child Bot 重啟後，**連續維持有效 Heartbeat 心跳達到 $T_{\text{relaunch}}$（即 $90\text{s} + 30\text{s} = 120\text{s}$），且向 Heartbeat 回報之狀態屬於有效業務狀態（如非 `UNKNOWN`、非 `POPUP_RECOVERY`，已進入 `NAVIGATING`、`BATTLE`、`COLLECT_ONLY` 等）**，Supervisor 即判定本次重啟修復成功，將重啟次數累計清零並重置窗口。
* **警報內容範例**：
  ```text
  🚨 [OPERATOR_ACTION_REQUIRED] Supervisor 連續重啟超限！
  • 警報代碼: SUPERVISOR_CRASH_LOOP_EXCEEDED
  • 狀態: 在 10.0 分鐘內已連續重啟 5 次，仍無法恢復遊戲運行。
  • 最後終止原因: heartbeat_stale (NAVIGATING 逾時)
  • 請連線遠端查看遊戲與進程狀態。
  ```

### 規則 2：關鍵路徑超時卡死 (`DAILY_CLAIM_DEADLINE_EXCEEDED`)
* **觸發條件**：
  08:05 跨日重置後，若時間已超過 **30 分鐘**（即到達 **08:35**），Tier 1 5 大速領項目（`chest`、`hero_draw`、`blood_altar`、`jewelry_workshop`、`bulletin_board`）中，仍有任一項目之 `completed_today == False`（且未被配置顯式停用）。
* **判定語意**：
  正常情況下 Daily Claim Phase 在 5~10 分鐘內必定完成。若超過 30 分鐘仍未全部完成，代表腳本卡在未知的阻塞（如未識別的全螢幕活動強制彈窗、登入反覆失敗、或建築點擊未如期觸發），立即升級發報。
* **警報內容範例**：
  ```text
  🚨 [OPERATOR_ACTION_REQUIRED] Daily Claim Phase 超時卡死！
  • 警報代碼: DAILY_CLAIM_DEADLINE_EXCEEDED
  • 狀態: 08:05 重置後超過 30 分鐘仍未完成所有速領項目。
  • 未完成子流程: bulletin_board (告示牌尚未成功接取)
  • 當前狀態機狀態: POPUP_RECOVERY
  • 請連線遠端檢查是否有未知彈窗阻擋。
  ```

---

## 四、 延後處理的潛在風險清單 (Deferred Risk Backlog)

下列項目暫不阻礙第一階段通訊骨架與核心契約之建立，列為後續強化子項目：

1. **地下城冷卻停滯與 Tier 4 插隊調度 (Dungeon Cooldown Stalling)**：
   若所接懸賞任務依賴特定地下城，而該地下城尚在冷卻中，狀態機會先退守 Tier 4。需確保在冷卻結束時能由 `ResultHandler` 順暢插隊切回 Tier 3，不被誤判為停滯。
2. **懸賞執行途中體力耗盡退避 (Stamina Retreat in Collect-Only)**：
   若懸賞任務尚未清空但麵包歸零，狀態機會轉入 `STATE_COLLECT_ONLY` 等待體力自然恢復或定時領取。此情況屬預期內生理待機，後續可擴充於 Milestone 1 附加「麵包偏低，預期可能觸發體力退避」之提示。
3. **告示牌任務已滿彈窗處理 (Task Already Full Handling)**：
   若帳號身上既有歷史任務未解導致告示牌彈出 `task_already_full.png`，目前邏輯會直接退出。需防範因任務滿額未能接滿 5 項時，外部紅點檢查可能反覆退避之邊界狀況。
4. **商店與祭壇之網路重試延遲 (Network & Dialogue Delay)**：
   部分商店造訪或祭壇獻祭偶遇伺服器結算延遲，後續可針對單一子流程加入有界超時以防止長時間拖延。

---

## 五、 系統架構與事件所有權 (Architecture & Event Ownership)

```text
[ Process-Internal: Bot Child ]
DailyManager / StateMachine
       │
       ▼ (Milestone 1 & 2 Events)
 NotificationPort ──────────┐
       ▲                    │
       │ (Crash Loop Events)│
[ Process-External: Supervisor ]    ▼
                           DiscordWebhookAdapter
                                    │ (Outbound HTTP POST)
                                    ▼
                             Discord Channel (iPhone)
```

1. **六角架構與職責邊界 (Hexagonal Architecture)**：
   - 建立抽象介面 `NotificationPort`，僅提供 `notify_milestone(event)` 與 `notify_alarm(event)`。
   - 業務核心（`state_machine`、`daily_manager`、`supervisor`）只依賴抽象埠，不直接引用任何第三方 HTTP 庫或通訊協定。
   - `DiscordWebhookAdapter` 負責將領域事件轉換為 Discord Embed 訊息。未來若更換為 Telegram 或 LINE，僅需新增 Adapter，核心業務零改動。
2. **事件所有權劃分 (Event Ownership by Process Boundary)**：
   - **Process-Internal (Bot Child)**：負責業務成功事件（里程碑 1、里程碑 2）。
   - **Process-External (Supervisor)**：負責看守進程生命週期。當 Bot 進程崩潰、無心跳或連續重啟超限時，由 Supervisor 直接發送 `OPERATOR_ACTION_REQUIRED`。
3. **非同步與超時保護 (Non-blocking & Timeout)**：
   - 所有 Webhook 請求強制設定 `timeout = 3.0` 秒，並於獨立背景執行緒發送。
   - 網路異常、DNS 解析失敗或 Discord 伺服器錯誤時，僅記錄 `logging.warning`，**絕不反向阻礙遊戲畫面處理或主迴圈調度**。
4. **憑證與隱私安全**：
   - Webhook URL 統一自環境變數 `DISCORD_WEBHOOK_URL` 或未被 Git 追蹤的本地設定讀取，嚴禁寫入任何追蹤之設定檔或腳本中。

---

## 六、 頻道生命週期管理：07:00 歷史訊息最終收斂契約 (Historical Message Reconciliation at 07:00)

為了在保障訊息到達時能確實觸發操作員客戶端之推播通知（Push Notification 與未讀提示），系統維持「發送獨立新訊息」而非「原位 PATCH 更新」之架構。同時，為避免長期運作下 Discord 頻道訊息無限積累，系統建立**最終狀態收斂模型 (Desired-State Reconciliation)**，而非脆弱的「每日單次定時腳本」。

### 1. 7 大核心契約 (The 7 Core Invariants)
1. **Asia/Taipei 07:00 前**：絕不發起任何收斂刪除動作。
2. **Asia/Taipei 07:00 後 (Earliest Eligible Time)**：所有早於今日（`message_date < today_tag`）且由本程式持久化追蹤之 Webhook 訊息，均被視為過期並持續嘗試收斂至 0。
3. **204 (No Content) / 404 (Not Found)**：均視為 Desired State 已達成，立即自本地持久化佇列中永久移除。
4. **Timeout / 5xx 故障**：保留 ID 於佇列中，進入冷卻並稍後自動重試。
5. **429 (Too Many Requests)**：解析 Discord `Retry-After` 標頭，下次重試時間強制設定為 `now + max(60s, retry_after)`。
6. **崩潰一致性 (Crash Consistency)**：無論在刪除前、刪除中、存檔前或存檔後崩潰，重啟後均具備天然冪等性，絕不造成永久卡死或誤刪當日新訊息。
7. **嚴格白名單邊界 (Webhook-Owned Only)**：永遠只刪除本程式本地持久化追蹤到的 `message_id`，嚴禁對 Discord 頻道進行全域無差別掃描或刪除操作員其他訊息。

### 2. Message ID 捕獲與 URL 安全注入
* **發送端捕獲**：發送 Webhook 請求時，使用標準庫 `urllib.parse` 安全注入 `wait=true` 查詢參數（防止 URL 本身已帶有 `?thread_id=xxx` 時發生字串硬串損毀）。Discord 於回應成功時回傳帶有 Snowflake `id` 之 JSON 物件。
* **領域值物件封裝**：底層通訊埠回傳結構化值物件：
  - 發送結果：`NotificationResult(success: bool, external_message_id: str | None, error: str | None)`。
  - 刪除結果：`DeleteResult(success: bool, status_code: int, retry_after_seconds: float, error: str | None)`。
* **本地持久化儲存**：由 `DailyPipelineNotifier` 負責將 `{"id": message_id, "date": today_tag, "tag": tag, "last_attempt_time": 0.0, "retry_after": 0.0}` 寫入各 Profile 專屬之 `user_data/<profile>/runtime/notification_history.json` 的 `dispatched_messages` 列表中。

### 3. 收斂執行、迭代安全與冷卻退避
* **時區一致性**：`today_tag` 與 07:00 判定統一採用業務時區（`Asia/Taipei`）或注入之 `Clock`，絕不隨 Host OS 機器環境漂移。
* **迭代安全 (List Mutation Safety)**：收斂巡檢時嚴禁邊 iterate 邊刪除元素，一律遍歷清單複本 `list(dispatched_messages)`，刪除成功即時更新並寫入 JSON 存檔。
* **有界冷卻退避 (Cool-down Backoff)**：
  - 單筆訊息若因網絡或 429 刪除失敗，至少等待 `max(60s, retry_after)` 冷卻後才允許再次嘗試，**嚴禁在狀態機主迴圈中每秒高頻狂轟 DELETE API**。
  - 失敗絕不阻礙後續巡檢，系統會在後續狀態機 tick 中持續自然重試，徹底消除「單次失敗導致當天永遠不再清理」之死鎖。
* **雙向崩潰一致性契約 (Crash Consistency Invariant)**：
  - **Crash-before-save**：DELETE 成功 ➔ 存檔前 Crash ➔ 重啟後再次 DELETE ➔ Discord 回 404 ➔ 視為成功並剔除存檔。
  - **Crash-after-save**：DELETE 成功 ➔ 存檔成功 ➔ Crash ➔ 重啟後該 ID 已不在佇列 ➔ 不重複呼叫 DELETE。
* **Null Object 邊界保護**：
  - `NullNotifier.delete_message` 回傳 `DeleteResult(success=False, error="NullNotifier")`，不假裝成功。
  - `NullDailyPipelineNotifier.reconcile_expired_messages()` 直接實作為 `no-op`，杜絕因測試或未注入真實通知埠時誤將本地歷史追蹤 ID 意外抹除之風險。

---

## 七、 多語言支援規格 (Notification i18n Specification)

系統支援通知訊息多語言切換，由獨立模組 [`runtime/notification_i18n.py`](../../runtime/notification_i18n.py) 集中維護文本字典：
* **支援語系**：繁體中文 (`zh-TW`，預設) 與英文 (`en`)。
* **配置階層**：全域設定於 `config/defaults.toml` 的 `[notification] language`，支援各角色於 `user_data/<profile>/config.toml` 獨立覆寫。
* **Fail-Fast 啟動阻斷**：當設定檔傳入未知或非法的語言代碼時，系統於初始化階段直接拋出 `ValueError`，明確阻斷啟動以防止靜默錯誤。
* **未來擴充**：簡體中文 (`zh-CN`)、日文 (`ja`)、韓文 (`ko`) 納入待辦清單追蹤。

