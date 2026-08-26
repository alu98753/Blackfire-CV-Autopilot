# ⏸️ 終端機與遊戲視窗空白鍵隨時暫停與狀態機內部時鐘補償機制開發故事 (PARS Framework)

> 本故事記錄自動掛機系統如何透過「腳本狀態機凍結 (State Machine Freeze)」、「內部安全時鐘補償 (Internal Clock Compensation)」與「雙路徑熱鍵監聽」，解決過去臨時接管遊戲必須依賴 `Ctrl + C` 強制中斷的痛點。

---

## 🎯 一、Purpose (目的與痛點)

### 1. 歷史痛點
在自動掛機運行期間（例如長時間地下城探索、每日任務流水線或大廳巡邏），當使用者需要臨時手動調整裝備、查看數值或手動領取特定獎勵時：
* **只能按 `Ctrl + C` 終止**：中斷後必須重啟 `run.bat`，導致長流程狀態（如地下城多層探索計數、退避進度）全部遺失。
* **不能單純 `time.sleep()` 暫停**：若僅在主迴圈停頓而未同步調整狀態機內部時鐘，一旦暫停超過 30 秒或 90 秒，恢復掛機的瞬間就會立刻觸發 `ExceptionWatchdog` 逾時誤判，導致腳本誤以為遊戲卡死而強制發起彈窗復原或遊戲重啟。

### 2. 核心目標
* **隨時隨地一鍵暫停/繼續**：在終端機 (Terminal) 或遊戲視窗 (Game) 聚焦時按下 `[Space 空白鍵]` 即可瞬間切換。
* **腳本內部安全時鐘無痛補償**：所有腳本內部的防卡死逾時、戰鬥計時與過渡等待時間戳，在恢復時自動抹除暫停時間，達到零誤判、無縫接續掛機。
* **客觀遊戲數據正常流逝**：地下城 30 分鐘 CD、定時領取倒數與每日重置等真實世界冷卻維持正常走時，不受手動暫停影響。

---

## 🛠️ 二、Action (行動與腳本底層實作細節)

### 1. 腳本狀態機如何達成「真正安全暫停」？

系統在腳本層面實作了三層凍結與保護機制：

```mermaid
graph TD
    subgraph ⏸️ 1. 主迴圈狀態凍結 (Main Loop Freeze)
        PauseSignal["接收到暫停訊號 (is_paused = True)"]
        PauseSignal --> SkipStep["🛑 跳過 state_machine.step()"]
        SkipStep --> SkipCapture["🛑 停止每幀全螢幕截圖與 OCR 比對 (零 CPU 浪費)"]
        SkipCapture --> SkipClick["🛑 停止所有滑鼠發射與點擊動作 (避免搶奪滑鼠)"]
        SkipClick --> IdleSleep["進入 50ms 輕量休眠等待"]
    end

    subgraph 🛡️ 2. 狀態與上下文原樣鎖定 (State & Context Lock)
        IdleSleep --> LockState["保留 current_state (如 NAVIGATING, LOBBY, BATTLE)"]
        LockState --> LockContext["保留 context 參數、子流程進度與地下城探索記憶"]
    end

    subgraph ⏱️ 3. 恢復時之原子化時間補償 (Timer Compensation)
        ResumeSignal["接收到恢復訊號 (is_paused = False)"]
        ResumeSignal --> CalcDuration["計算暫停時長 Δt = now - pause_start"]
        CalcDuration --> CompMethod["呼叫 compensate_internal_timers(Δt)"]
    end
```

### 2. 內部安全時鐘補償的精確數學實作 (`compensate_internal_timers`)

當暫停經過 $\Delta t_{\text{pause}}$ 秒時，[GameStateMachine](../../states/state_machine.py) 執行集中補償：

```python
def compensate_internal_timers(self, pause_duration: float):
    now = time.time()
    
    # 1. 狀態變更 Watchdog 補償 (最核心：將最後變更時間後移 Δt，使 (now - last_state_change) 不包含暫停時間)
    if self.last_state_change > 0:
        self.last_state_change += pause_duration

    # 2. 單場戰鬥計時器補償 (避免戰鬥超時誤觸)
    if self.battle_start_time is not None:
        self.battle_start_time += pause_duration

    # 3. 彈窗暫存時間戳補償
    if isinstance(self.stashed_context, dict) and "timestamp" in self.stashed_context:
        self.stashed_context["timestamp"] += pause_duration

    # 4. 過渡與結算 Handler 計時器補償
    if loading_handler and loading_handler.loading_start_time:
        loading_handler.loading_start_time += pause_duration
    if battle_handler and battle_handler.non_battle_feature_start_time:
        battle_handler.non_battle_feature_start_time += pause_duration

    # 5. 反射自動補償所有 missing_time_* 模板記憶
    for attr in list(self.__dict__.keys()):
        if attr.startswith("missing_time_"):
            val = getattr(self, attr)
            if isinstance(val, (int, float)):
                setattr(self, attr, val + pause_duration)

    # 6. 滑鼠動作防呆重置
    if self.mouse:
        self.mouse.last_action_time = now
    self.user_operating = False
    self.just_resumed_from_user = True
```

### 3. 雙路徑焦點監聽與 Triple-Space 防誤觸架構 ([PauseController](../../utils/keyboard_listener.py))
* **連按 3 次空白鍵觸發 (Triple-Space)**：在 1.2 秒內連續按下 3 次空白鍵才切換暫停/繼續，徹底防止遊戲操作或打字時因單次按壓造成誤觸。
* **即時視覺進度提示**：每按一次即時提示 `[空白鍵 1/3] -> [空白鍵 2/3] -> [3/3 達成]`。
* **路徑 1 (終端機)**：透過 `msvcrt.kbhit()` 監聽標準輸入字元流。只要終端機獲得焦點，按空白鍵 100% 毫秒級即時捕獲，完全繞開 Windows Terminal 的 HWND 不一致問題。
* **路徑 2 (遊戲視窗)**：透過 `GetAsyncKeyState(VK_SPACE)` 配合視窗標題 (`Blackfire` / `Crusade` / `Godot`) 與頂層 HWND 比對，當使用者在遊戲視窗中連敲空白鍵時即刻暫停，且絕不干擾瀏覽器等其他視窗打字。
* **滑鼠手動操作全時段防護**：使用者在遊戲中手動移動滑鼠超過 3 秒後恢復時，同樣執行 `compensate_internal_timers`，確保無論手動操作多久都不會被 Watchdog 誤判卡死。

---

## 📊 三、Result (成效與驗證)

1. **單元測試全綠通過**：
   * 建立獨立行為測試檔 [tests/test_behavior_pause_resume.py](../../tests/test_behavior_pause_resume.py)，5 項測試案例 100% 通過：
     * `test_pause_resume_lifecycle`：暫停/恢復狀態機生命週期。
     * `test_internal_timers_compensation_math`：內部防卡死計時器精確補償。
     * `test_game_cooldowns_not_affected`：客觀遊戲冷卻未受篡改。
     * `test_watchdog_immunity_after_long_pause`：暫停 120 秒後恢復，Watchdog 零誤判。
     * `test_pause_controller_focus_filtering`：視窗焦點過濾與防抖動。
2. **實機操作體驗大幅提升**：
   * 使用者在大廳、尋路、戰鬥或領取時，隨時按 [Space] 即刻暫停，終端機顯示醒目橫幅；手動操作完再按 [Space]，無縫接續掛機。

---

## 💡 四、So What (核心價值與 Clean Code 收穫)

1. **時鐘職責分明 (Clock Separation)**：
   * 確立了「真實世界時鐘 (Wall Clock)」與「腳本安全時鐘 (Logic Clock)」的嚴格邊界。客觀遊戲冷卻由真實時間驅動，內部防卡死邏輯由補償後的安全時鐘驅動。
2. **集中式封裝降低認知負擔 (High Cohesion, Low Coupling)**：
   * 主迴圈與外部程式碼只需呼叫 `state_machine.pause()` 與 `state_machine.resume()`，所有計時器補償由狀態機內部集中完成，未來擴充新 Handler 零維護負擔。

---

## 🔮 五、Influence (後續影響與延伸)

* **為後續 GUI 介面打下基礎**：本次實作的 `state_machine.pause()` 與 `resume()` 具備標準 API 介面，未來若開發 WebUI、Electron 懸浮窗或桌面小工具，可直接綁定暫停/繼續按鈕。
* **提升整體掛機穩定性與容錯度**：徹底消除了因手動介入導致逾時誤判的邊界異常。
