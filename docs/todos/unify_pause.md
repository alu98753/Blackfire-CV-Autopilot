RFC: 是否需要把暫停這個按鍵統一化 寫一個統一的來管理而非各自管理

這是介紹:

Searched for "pause"
Viewed state_machine.py:360-415

當您按下 `Ctrl + Space` 暫停腳本時，系統的處理原則是：**「遊戲世界的客觀時間繼續流逝，但腳本內部的防卡死/安全計時器全部凍結（恢復時自動補償），防止恢復時被誤判為卡死」**。

具體分類如下：

他分為會繼續的跟會被暫停(補償的)


---

### 一、 ⏸️ 會「暫停 / 凍結補償」的計時器（腳本內部保護機制）
當腳本暫停期間，以下計時器在 `compensate_internal_timers(pause_duration)` 機制下會**扣除暫停時間（時間戳向後順延）**，恢復時不會累積秒數：

1. **看門狗防卡死計時器 (`ExceptionWatchdog`)**：
   - 狀態停滯時間（`last_state_change`）：即使暫停了 10 分鐘，恢復後也不會觸發 60s/90s Watchdog 逾時強行重開。
2. **戰鬥內部會話計時 (`battle_session`)**：
   - 單場戰鬥超時（`started_at`，如 180 秒強退防護）。
   - 血條卡死停滯時間（`hp_stall_started_at`，如 40 秒原地重開防護）。
3. **過場與加載等待計時**：
   - `STATE_LOADING` 的載入過渡計時（`loading_start_time`）。
   - 戰鬥中特徵消失計時（`non_battle_feature_start_time`）。
4. **異常彈窗暫存計時 (`stashed_context['timestamp']`)**：
   - 恢復時不會因為過期而丟失恢復上下文。
5. **模板遺失記憶計時 (`missing_time_*`)**：
   - 所有動態追蹤 UI 遺失的計時器。
6. **使用者手動操作判定**：
   - 自動重置 `user_operating = False`，避免恢復瞬間因時間差誤判為使用者手動干預。

---

### 二、 ▶️ 會「繼續倒數 / 流逝」的計時器（真實遊戲時間）
因為遊戲本身在 Steam/PC 視窗中繼續運行，且這類冷卻依賴真實的牆上時間（Wall-clock time），**刻意不予補償，讓它正常冷卻**：

1. **客觀遊戲冷卻時間 (Game Cooldowns)**：
   - **地下城冷卻 (`dungeon_cooldowns`)**：如地下城 30 分鐘冷卻，暫停 30 分鐘後恢復，地下城冷卻就真的轉好了。
   - **首領討伐冷卻 (`lord_boss_cooldowns`)**：三大 Boss 的 15/20/30 分鐘計時。
   - **定時領取計時器**：
     - 每 120 分鐘的定時領鑽石（`diamond_last_collect_time`）。
     - 每 240 分鐘的體力退避發呆（`stamina_retreat_start_time`）。
2. **每日 08:05 換日重置**：
   - 依賴系統時間 (`datetime.now()`)，若暫停期間跨越清晨 08:05，恢復後的下一幀會立即正確識別為新的一天並發起日常重置。