# PARS 開發故事：主迴圈極簡重構與手動暫停控制體系統一 🎯

- **建立時間**: 2026-08-27
- **影響模組**:
  - 主迴圈調度：`main.py` ([main.py](../../main.py))
  - 滑鼠控制器：`actions/mouse.py` ([MouseController](../../actions/mouse.py))
  - 防卡死監控：`states/exceptions/watchdog.py` ([ExceptionWatchdog](../../states/exceptions/watchdog.py))
  - 行為測試套件：`tests/test_behavior_pause_resume.py`, `tests/test_user_intervention_time_compensation.py`

---

## 1. Purpose (開發目的與問題背景)

在自動掛機運行過程中，舊有的「實體滑鼠游標位移猜測（Anti-Conflict）」機制引發了多項架構缺陷與使用者痛點：
1. **單螢幕後台掛機嚴重誤判**：
   當遊戲在背景運行（最大化覆蓋桌面範圍）、使用者在前景開瀏覽器或編輯代碼時，滑鼠在螢幕上的任何位移都會被主迴圈每 5ms 的 `dx/dy` 計算誤判為「使用者正在手動操作遊戲」，進而觸發虛假的 3 秒防搶暫停，導致掛機頻繁中斷。
2. **邏輯冗餘與過渡變數殘留**：
   系統已具備成熟且精準的 `[Ctrl + Space]` 全域快捷鍵監聽（限定 Terminal 與 Game 視窗聚焦），舊有的滑鼠位移猜測代碼（約 40 行）與 `user_operating`、`last_user_operation_time` 成為多餘且脆弱的包袱。

---

## 2. Action (架構重構與具體行動)

### 2.1 主迴圈極簡瘦身 (`main.py`)
- 徹底移除主迴圈中每幀測量滑鼠游標位移、計算矩形範圍與倒數 3 秒的冗餘代碼。
- 主迴圈精簡為「檢查 `is_paused` ➔ 休眠或直行 `step()`」的極簡單一職責模式。

### 2.2 點擊控制器雙層防護純淨化 (`actions/mouse.py`)
- `check_user_intervention()` 純淨化為直接檢驗 `state_machine.is_paused`。
- 保留底層保險絲機制：當使用者在連點間隙按下 `[Ctrl + Space]` 時，`mouse.click()` / `mouse.drag()` 於發射前 100% 毫秒級熔斷攔截。

### 2.3 防卡死 Watchdog 豁免與時間補償完全統一 (`states/`)
- `ExceptionWatchdog` 豁免直接綁定 `is_paused`。
- 暫停期間的所有秒數統一透過 `state_machine.resume()` 呼叫 `compensate_internal_timers(pause_duration)` 原子化加回內部計時器，杜絕超時誤判。

---

## 3. Result (成果驗證)

1. **單螢幕後台體驗徹底解放**：
   使用者在前景自由工作、瀏覽網頁與看影片，後台掛機全速平穩運行，零誤觸、零中斷。
2. **代碼大幅瘦身**：淨減少 128 行冗餘邏輯。
3. **測試全面綠燈**：
   `test_behavior_pause_resume`、`test_user_intervention_time_compensation`、`test_mouse_coordinates` 等單元測試 100% 通過。

---

## 4. So What (架構價值)

貫徹了 **AI Agent 極簡架構原則**：用明確的主動指令（快捷鍵）取代猜測性的被動狀態偵測，徹底消除了跨視窗重疊時的誤判邊界。

---

## 5. Influence & Maintenance Guidelines (後續維護指引)

- 暫停與恢復統一透過 `state_machine.pause()` / `resume()` / `toggle_pause()`（或按鍵監聽 `PauseController`）控制。
- 嚴禁在主流程中重新引入輪詢實體游標位置的猜測式邏輯。
