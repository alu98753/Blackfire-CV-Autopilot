# 遊戲進程終止、Steam 原生直連啟動與視窗自動還原置頂全螢幕開發故事 (PARS Framework) 🛡️

## Purpose (目的)
在 long-running 24/7 自動掛機過程中，遊戲可能遭遇嚴重凍結死鎖、意外彈窗連續失敗、視窗被使用者意外最小化/手動關閉，或是待機狀態下遊戲崩潰。舊有架構在遊戲視窗遺失或嚴重死鎖時會進入無窮 Log 警告迴圈，無法自我復原。本工程旨在建立具備 **PID 安全護欄之進程強行終止 (`taskkill`)**、**Steam 原生協定直連啟動 (`SteamGameLauncher`)**、**0 位移平滑還原置頂全螢幕 (`SetForegroundWindow` + `SC_MAXIMIZE`)** 以及 **全域 Watchdog / 手動關閉 5 次遺失自動重開** 之終極自癒閉環。

---

## Action (行動)

1. **獨立 `GameRelaunchSubflow` 重啟自癒模組**：
   - 建立 [GameRelaunchSubflow](file:///e:/Side_Project/BlackfireCrusade_tool/states/exceptions/subflows/game_relaunch.py)，封裝進程終止與 Steam 重新啟動邏輯。
   - **PID 安全護欄**：讀取 `os.getpid()`，若 HWND 取得之 PID 為腳本 PID 則 100% 豁免防誤殺。嚴禁使用 `WINDOWTITLE` 萬用字元，防範誤殺含有工作目錄路徑之 PowerShell 視窗。
   - 使用 `taskkill /f /im BlackfireCrusade.exe` 精確終止 Unity 遊戲進程，並輪詢 `FindWindow` 確保進程徹底銷毀。

2. **`ScreenCapturer` 最小化自動還原與 0 位移強效全螢幕**：
   - 於 [ScreenCapturer](file:///e:/Side_Project/BlackfireCrusade_tool/capture/screen.py) 的 `get_window_rect()` 加入 `IsIconic(hwnd)` 檢查，自動呼叫 `ensure_window_on_monitor()`。
   - **0 位移平滑全螢幕**：`SW_RESTORE` 解除最小化後重新取得 `GetWindowRect`，若視窗已在目標顯示器上，跳過 `SetWindowPos` 以消除 10px 偏移抖動。
   - 結合 `SetForegroundWindow` 奪取焦點與 `WM_SYSCOMMAND (SC_MAXIMIZE)` 標題列訊息雙保險，解決 1280x720 視窗大小無法填滿全螢幕問題。

3. **`ExceptionWatchdog` 智慧動態逾時與視窗遺失自動重開**：
   - 於 [ExceptionWatchdog](file:///e:/Side_Project/BlackfireCrusade_tool/states/exceptions/watchdog.py) 加入連續卡死計數器 `consecutive_stuck_count`（連續 2 次逾時自動發起重啟）。
   - 針對 `COLLECT_ONLY` 實作 `max(diamond_cd, bread_cd) + 60s` 智慧動態 CD 逾時與 HWND 遺失檢查。
   - 於 [GameStateMachine.step()](file:///e:/Side_Project/BlackfireCrusade_tool/states/state_machine.py) 加入 `window_lost_count`。連刷 5 次 (~2.5s) 找不到遊戲視窗（手動關閉或崩潰）時，自動發起 `GameRelaunchSubflow` 重開。

4. **單元測試驗證與誤觸門檻優化**：
   - 建立 [test_game_relaunch_recovery.py](file:///e:/Side_Project/BlackfireCrusade_tool/tests/test_game_relaunch_recovery.py) 包含 6 大針對性單元測試。
   - 將 `navigation.py` 與 `state_machine.py` 中 `common/confirm.png` 的尋路/全域防護門檻提高至 `0.90`，徹底消除 False Positive。

---

## Result (結果)
- **單元測試**：相關單元測試 100% 綠燈通過 (OK)。
- **實務測試**：
  1. 遊戲被手動關閉或最小化時，腳本能於 2.5 秒內感知並自動重開/置頂全螢幕。
  2. 背包清理與裝備分解每步點擊即時刷新 `notify_ui_progress()`，不再發生長作業假陽性卡死。

---

## So What (核心價值)
- **真正無人值守 24/7 安定性**：補齊了「遊戲崩潰/手動關閉/視窗最小化/死鎖卡死」四大情境的自動重開與平滑全螢幕復原閉環。
- **高維護性與低風險**：PID 護欄與精確匹配確保重啟流程不會誤殺腳本或 Terminal 進程。

---

## Influence (影響)
- 規範了「畫面視窗管理 (Capturer) + 重啟自癒 (Subflow) + 防護門檻 (Watchdog)」的標準自癒設計。
- 奠定了腳本面對 Windows 視窗層級變動時的防禦標準。
