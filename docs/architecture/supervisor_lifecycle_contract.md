# 多進程 Supervisor 生命週期自癒與進程管理契約 (Supervisor Lifecycle Contract) 🏛️

> 狀態：Canonical Architecture Contract（正式架構規範）  
> 適用範圍：`runtime/supervisor.py`、`runtime/loop.py`、`utils/game_process.py`、`main.py` 與外部看門狗架構。

---

## 1. 職責劃分與架構邊界 (Architecture Boundaries)

本系統採「外掛守護進程（Supervisor）」與「Worker 工作進程（`main.py`）」雙層架構：
1. **Supervisor（守護者）**：
   - 作為外部獨立進程運作，持有子進程控制權。
   - 負責監控心跳檔案時間戳 (`heartbeat_age_seconds`)、管理 08:00 定時維護排程、追蹤崩潰循環 (`CrashLoopTracker`)，並於崩潰時透過參數協議 (`--resume`, `--restart-game`) 宣告重啟意圖。
   - 絕不侵入遊戲畫面或執行任何 CV 業務決策。
2. **Worker（工作進程 `main.py`）**：
   - 執行狀態機主迴圈，負責遊戲感知與操作。
   - 定時回報存活心跳（`touch_heartbeat`）；在退出時留下 `latest_child_termination.json` handoff 診斷資訊。
   - 封裝 Win32 API 視窗健康度檢查 (`is_window_hung`) 與進程終止守護 (`terminate_game_process`)。

---

## 2. S1 ~ S7 生命週期決策矩陣 (Lifecycle Decision Matrix)

Supervisor 依據子進程退出碼（Exit Code）、心跳逾時與維護排程，執行具備嚴格不變量約束之 S1~S7 分流自癒：

| 情境代號 | 觸發條件 | Supervisor 行動 | Worker / 遊戲行為 | 事故類別 (Incident Category) |
| :--- | :--- | :--- | :--- | :--- |
| **S1 (每日定時維護)** | 本地時間達 08:00 且今日未重啟 | 終止 Worker 子進程；寫入排程事故；注入單次 `--restart-game` 與 `--resume` | 銷毀舊遊戲進程，透過 Steam 直連重開並重新登入 | `SCHEDULED_MAINTENANCE` |
| **S2 (心跳逾時死鎖)** | 心跳時間戳過期逾 180 秒 (`watchdog_timeout`) | 終止 Worker 子進程；寫入逾時事故；注入單次 `--restart-game` 與 `--resume` | 視為遊戲視窗無回應或渲染死鎖，銷毀舊進程並重開遊戲 | `HEARTBEAT_TIMEOUT` |
| **S3 (無回應視窗偵測)** | Worker 啟動時偵測到視窗無回應 | Supervisor 正常啟動 Worker | `is_window_hung(hwnd)` 成立，Worker 自動升級 `force_relaunch = True` 重開遊戲 | 由 Worker 記錄 `CRASH` / 自癒 |
| **S4 (執行期嚴重卡死)** | 遊戲內 Watchdog 重試耗盡 (5 次未消除) | Supervisor 維持監聽 | Worker 調用 `GameRelaunchSubflow` 殺進程並重啟遊戲 | `IN_GAME_RECOVERY` |
| **S5 (一般例外崩潰)** | Worker 未捕獲 Python 例外崩潰 (`exit != 0, 75, 42`) | 讀取 handoff 記錄事故；發起快速接續（**不帶** `--restart-game`） | 秒級 Attach 回既有遊戲視窗，無損接續當前關卡進度 | `CRASH` |
| **S6 (手動中斷 Ctrl+C)** | 操作員於終端按下 `Ctrl+C` | 終止 Worker 子進程；Supervisor 正常結束退出 | 遊戲本體維持運行，不強制銷毀 | 無（手動中止） |
| **S7 (專屬手動退出熱鍵)** | 操作員按下 `Ctrl+Shift+Q` (Exit Code 75) | 記錄手動維護事故；Supervisor 乾淨退出，**不重啟 Worker，不重啟遊戲** | 遊戲本體維持運行，交由操作員完全接管 | `SCHEDULED_MAINTENANCE` |
| **S-Restart (手動重啟熱鍵)** | 操作員按下 `Ctrl+Q` (Exit Code 42) | 發起快速接續重啟（**不帶** `--restart-game`） | 秒級 Attach 回遊戲視窗重新載入狀態機 | 無（操作員意圖重整） |

---

## 3. 核心不可變鐵律 (Core Invariants)

### Invariant 1: 單次消費旗標保護 (Single-Use Flag Consumption)
- `--restart-game` 旗標嚴格採「單次消費」語意。
- 僅在 S1 (定時維護) 或 S2 (心跳逾時) 觸發時由 Supervisor 動態追加。
- 下一次生成子進程指令時，`prepare_resume_command` 必須**主動濾除殘留的 `--restart-game`**。
- **守護意圖**：保證在重開遊戲後，若 Worker 後續遭遇 S5 (一般 Python 例外崩潰)，能維持「快速秒級 Attach」而不被污染為「再次強制關閉遊戲」，杜絕無限重開遊戲風暴。

### Invariant 2: 呼叫者 PID 安全守護 (Self-PID Guard)
- 在執行進程終止 (`terminate_game_process`) 時，必須明確傳入呼叫者自身之 PID。
- 若枚舉進程所取得之 PID 等於呼叫者 PID 或其父進程 PID，**嚴禁執行終止**。
- **守護意圖**：防止進程匹配邏輯誤殺正在執行救援的 Python 進程或 Supervisor 自身。

### Invariant 3: 狀態持久化先於子程序終止 (State Persistence Before Child Termination)
- 於 S1 觸發定時維護時，Supervisor 必須**先成功將今日維護標記寫入狀態檔案** (`daily_restart_state_path`)，方可向子進程發送終止訊號。
- 若狀態寫入遭遇 I/O 失敗，必須暫緩維護重啟，絕不盲目終止 Worker。
- **守護意圖**：防止在磁碟滿或權限不足時，因寫檔失敗而在同一小時內陷入反覆殺進程重啟的活鎖。

### Invariant 4: 崩潰循環滑動窗口告警 (Crash-Loop Sliding Window Backoff)
- `CrashLoopTracker` 以滑動時間窗口（預設 90 秒）統計子進程重啟次數。
- 當短時間內連續重啟超過閥值（預設 5 次），且累計運算時間不足以構成穩定運行時，觸發 `SUPERVISOR_CRASH_LOOP_EXCEEDED` 警報通知。
- 升級發送緊急告警並啟動指數退避（Backoff），保護系統資源不被高頻重啟耗盡。

---

## 4. 相關模組與測試依歸

- 守護核心：[`runtime/supervisor.py`](../../runtime/supervisor.py)
- 進程操作：[`utils/game_process.py`](../../utils/game_process.py)
- 主啟動進入點：[`main.py`](../../main.py)
- 崩潰追蹤：[`runtime/crash_tracker.py`](../../runtime/crash_tracker.py)
- 事故日誌：[`runtime/incident_journal.py`](../../runtime/incident_journal.py)
- 行為驗證測試套件：[`tests/test_behavior_supervisor_lifecycle.py`](../../tests/test_behavior_supervisor_lifecycle.py)
