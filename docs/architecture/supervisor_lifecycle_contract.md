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

本節約束旗標消費、PID 安全、持久化順序與崩潰循環的可觀測安全結果。退出碼分類、時間窗口、次數預算、檔案格式與程序 API 均可在不改變義務及其驗證的情況下調整；聚焦驗證為 `tests/test_behavior_supervisor_lifecycle.py` 與 `tests/test_supervisor_alarm.py`。術語判讀見 [Canonical Invariant Registry](canonical_invariant_registry.md)。

### Invariant 1: 單次消費旗標保護 (Single-Use Flag Consumption)
- **Scope**：具一次性語意的子程序重啟要求。
- **Rule**：一次性重啟要求 MUST 只影響其所屬的一次子程序啟動，且 MUST NOT 污染後續非相同原因的重啟。
- **Observable consequence**：後續一般復原不會意外重複執行全量遊戲重啟。
- **Allowed variation**：旗標、退出碼、命令建構器與觸發來源可變更。
- **Verification**：`tests/test_behavior_supervisor_lifecycle.py`。

### Invariant 2: 呼叫者 PID 安全守護 (Self-PID Guard)
- **Scope**：Supervisor 執行任何目標程序終止時。
- **Rule**：程序終止 MUST 排除 Supervisor、其呼叫鏈與其他受保護的控制程序。
- **Observable consequence**：復原動作不會終止執行該復原的控制程序。
- **Allowed variation**：PID 傳遞方式、程序列舉 API 與受保護程序識別方式可變更。
- **Verification**：`tests/test_behavior_supervisor_lifecycle.py`。

### Invariant 3: 狀態持久化先於子程序終止 (State Persistence Before Child Termination)
- **Scope**：依賴持久化狀態去抑制重複執行的維護重啟。
- **Rule**：系統 MUST 在終止子程序前成功持久化該次維護的抑制狀態；持久化失敗時 MUST NOT 執行該終止。
- **Observable consequence**：儲存失敗不會造成無法記錄的重複終止循環。
- **Allowed variation**：狀態媒介、資料格式、交易機制與維護排程可變更。
- **Verification**：`tests/test_behavior_supervisor_lifecycle.py`。

### Invariant 4: 崩潰循環滑動窗口告警 (Crash-Loop Sliding Window Backoff)
- **Scope**：短時間重複失敗的子程序生命週期。
- **Rule**：系統 MUST 偵測有界時間內的不穩定重啟模式，並在達到升級條件時發出告警及降低重啟壓力。
- **Observable consequence**：崩潰循環可被通知，且不會無限制消耗系統資源。
- **Allowed variation**：窗口、計數條件、穩定性判準、通知事件與退避演算法可變更。
- **Verification**：`tests/test_behavior_supervisor_lifecycle.py` 與 `tests/test_supervisor_alarm.py`。

---

## 4. 相關模組與測試依歸

### Current policy / implementation reference

目前的旗標、狀態路徑、窗口、計數預算、事件名稱與程序 API 由 production code 與設定維護。這些是 AS-IS 策略，不是本章的 normative rule。

- 守護核心：[`runtime/supervisor.py`](../../runtime/supervisor.py)
- 進程操作：[`utils/game_process.py`](../../utils/game_process.py)
- 主啟動進入點：[`main.py`](../../main.py)
- 崩潰追蹤：[`runtime/crash_tracker.py`](../../runtime/crash_tracker.py)
- 事故日誌：[`runtime/incident_journal.py`](../../runtime/incident_journal.py)
- 行為驗證測試套件：[`tests/test_behavior_supervisor_lifecycle.py`](../../tests/test_behavior_supervisor_lifecycle.py)
