# Runtime Incident Recording Spec（v1）

> 狀態：v1 已實作  
> 範圍：Supervisor、bot 子程序與遊戲內自癒流程的異常／重啟可觀測性。

## 1. 目的

長時間掛機後，能以**持久化、可統計且可回查**的資料回答：

1. 此 profile 從啟動至今，bot 曾被重啟幾次？
2. 每次重啟是正常維護，還是故障？若為故障，確切原因是什麼？
3. 未處理的 Python exception 是什麼型別、訊息、stack trace，以及發生前處於哪個 state？
4. 遊戲內自癒（彈窗恢復、遊戲重啟）發生了幾次、成功率如何、是否最後升級成整個 bot 重啟？

本系統是診斷紀錄，不得改變既有恢復判斷、阻塞主迴圈，或因寫檔失敗使 bot 結束。

## 2. 現況與問題

目前的責任鏈：

```text
run.bat → runtime.supervisor（父程序） → main.py（bot 子程序）
                                          └─ ExceptionWatchdog / GameRelaunchSubflow
```

- 子程序會在未處理 exception 時輸出 stack trace 後結束。
- Supervisor 可辨識 heartbeat 逾時、排程重啟與子程序退出，但子程序的 exit code 本身不能表達 exception 類型與理由。
- `scratch/runtime/heartbeat_<profile>.json` 是短期 liveness 通訊，會在下一次啟動覆蓋；它不是歷史紀錄。
- 既有遊戲內例外系統可能已成功修復問題，不能把它與「bot crash」混成同一個 exception 計數。

## 3. 檔案與程式位置

### 3.1 程式碼

新增 `runtime/incident_journal.py`，作為唯一的事件 schema、路徑計算、安全寫入與讀取介面。

選擇 `runtime/` 的理由：它同時被 `runtime.supervisor`（父程序）與 `main.py`／`runtime.loop`（子程序）使用，且與 `heartbeat.py` 的跨程序責任一致；不應放在 `states/exceptions/`，因為事件範圍包含 Supervisor 與 Python crash，而不只是遊戲內例外。

預計整合點：

| 來源 | 事件責任 |
| --- | --- |
| `main.py` | 建立子程序 session context，並清除上一輪的 child termination handoff。 |
| `runtime/loop.py` | 未處理 exception 時，先寫入 crash 記錄，再 re-raise。 |
| `states/exceptions/watchdog.py` | 記錄偵測到卡住、轉交 popup recovery、請求遊戲重啟。 |
| `states/exceptions/subflows/game_relaunch.py` | 記錄遊戲重啟開始、成功或失敗。 |
| `runtime/supervisor.py` | 記錄其重啟判斷、讀取子程序最後終止資訊並寫入結果。 |

### 3.2 持久化資料

```text
user_data/
  <profile>/
    config.toml                         # 既有設定
    daily_status.json                   # 既有每日進度
    runtime/
      incidents/
        2026-08-30.jsonl                # 當日事件歷史（append-only）
      latest_child_termination.json     # 子程序最後一次終止的 handoff
```

選擇 `user_data/<profile>/runtime/` 的理由：

- `user_data/` 已是本專案給 profile 專屬設定與進度使用的持久化區，且已被 gitignore。
- Native 與 Sandbox 的資料必須隔離，不能放共用的 `scratch/runtime/`。
- 使用者需要跨重啟保留事故歷史；`scratch/` 只適合 heartbeat、臨時測試輸出與可丟棄 debug artifact。

`latest_child_termination.json` 是父子程序的短期交接檔：子程序每次啟動先清除舊檔；若異常結束則原子寫入。Supervisor 重啟前讀取它，以避免僅憑 exit code 猜測原因。v1 不建立 `sessions/` 小檔案；當日或指定期間的統計直接由 JSONL 掃描得出。

**Supervisor 啟動契約**：受 Supervisor 管理的 child command 必須在啟動前含有**剛好一個、非空白**的 `--profile <name>`。Supervisor 不可依 child 之後才從互動式選窗取得的 title 推測 profile；缺少、空白或重複此參數時，會在建立 child 前以 `ValueError` 拒絕啟動。正式 `run.bat` 入口已固定傳入 `--profile native` 或 `--profile sandbox`。

Profile 名稱只允許小寫英文字母、數字、`_`、`-`；任何路徑片段均會拒絕，以保證所有 runtime 資料都位於 `user_data/<profile>/`。

### 3.3 截圖

v1 **不自動新增事故截圖**。現有 debug 圖片仍維持 `scratch/debug/`，且只能經 `utils.debug_artifacts.write_debug_image()` 寫入。日後若需要「每個 incident 的畫面」，另立 v2：事件只保存檔名參照，圖片仍是可清理、不可作為唯一證據的 `scratch/debug/` artifact。

## 4. 名詞與分類

| 名詞 | 定義 | 計入「bot exception／重啟」 |
| --- | --- | --- |
| incident | 一筆值得診斷的 runtime 事件。 | 視分類而定 |
| reason code | 同一大類下、可統計的具體原因。 | 不適用 |
| child handoff | 子程序留下、供 Supervisor 讀取的最後終止資訊。 | 不適用 |
| session | 一個 bot 子程序從啟動到結束的生命週期，以 `session_id` 關聯事件，不另存摘要檔。 | 不適用 |

v1 的頂層 `category` 固定為四類，這是使用者第一眼應看的摘要：

| category | 意義 | 計入 exception |
| --- | --- | --- |
| `CRASH` | bot 子程序未預期結束，或 Python 未處理 exception。 | 是 |
| `HEARTBEAT_TIMEOUT` | Supervisor 判定子程序失去 liveness 後終止。 | 是 |
| `SCHEDULED_MAINTENANCE` | 正常每日維護、明確手動退出，或 Ctrl+C 要求恢復重啟。 | 否 |
| `IN_GAME_RECOVERY` | 遊戲內偵測問題並嘗試修復或重啟遊戲。 | 否；失敗後若導致 bot 結束，另有 `CRASH` 事件 |

**4 × 10 閱讀模型**：先顯示四類的件數；選定其中一類後，再顯示該類最近期間內按次數排序的前十個 `reason_code`；需要證據時才開啟對應 JSONL 事件。這是檢視方式，不是 schema 的硬性上限，因此新原因不會因為超過十種而遺失。

## 5. 事件資料契約

`incidents/YYYY-MM-DD.jsonl` 每行是一個獨立 JSON object。採 JSON Lines 是因為可追加、不必整份讀入，並可用簡單腳本或人工查詢。

所有事件必備欄位：

```json
{
  "schema_version": 1,
  "event_id": "uuid",
  "occurred_at": "2026-08-30T20:15:43.123+08:00",
  "category": "CRASH",
  "reason_code": "unhandled_python_exception",
  "profile": "native",
  "session_id": "uuid",
  "pid": 12345,
  "state": "STATE_BATTLE",
  "run_count": 42,
  "details": {}
}
```

規則：

- `category` 固定使用上述四個大寫值；`reason_code` 使用穩定的英文 snake_case，供統計與測試；人可讀中文放在 `message` 或 `details`。
- 啟動初期尚未建立狀態機時，`state` 必須為 `null`，`run_count` 必須為 `0`；兩者不是寫檔失敗的理由。
- 不可把 traceback、完整 command line 或畫面資料塞進 `reason_code`。
- 不可記錄 token、帳密或遊戲帳號敏感資料；所有 `details`（包含 exception message 與 traceback）在持久化前必須經集中式遮罩。
- 每日 JSONL 歷史檔不使用跨程序 lock。每次寫入必須把單筆 compact JSON（含換行）以 append 模式的一次底層 write 寫出；事件頻率低，這可避免 Windows lock 的額外故障模式。`latest_child_termination.json` 採 temporary file + replace。所有 `incident_journal` 公開方法必須在內部捕捉寫檔相關的 `Exception`、寫 warning log 並回傳失敗結果，絕不改變主流程。

### 5.1 v1 原因碼目錄

| category | reason_code | 主要欄位 |
| --- | --- | --- |
| `CRASH` | `unhandled_python_exception` | `exception_type`, `exception_message`, `traceback` |
| `CRASH` | `child_exit_without_handoff` | `exit_code`, `started_at`, `last_heartbeat` |
| `CRASH` | `unexpected_clean_exit` | `exit_code` |
| `HEARTBEAT_TIMEOUT` | `heartbeat_stale` | `heartbeat_age_seconds`, `timeout_seconds`, `last_heartbeat` |
| `SCHEDULED_MAINTENANCE` | `daily_scheduled_restart` | `scheduled_hour`, `last_scheduled_restart_date` |
| `SCHEDULED_MAINTENANCE` | `manual_exit_hotkey` | `exit_code` |
| `SCHEDULED_MAINTENANCE` | `interrupt_recovery_requested` | `restart_number` |
| `IN_GAME_RECOVERY` | `watchdog_timeout_detected` | `state_duration_seconds`, `timeout_seconds`, `consecutive_count` |
| `IN_GAME_RECOVERY` | `popup_recovery_requested` | 頂層 `state`、`matched_subflow`, `match_confidence` |
| `IN_GAME_RECOVERY` | `game_relaunch_started` / `game_relaunch_succeeded` / `game_relaunch_failed` | `trigger_reason_code`, `game_title`, `is_sandbox`, `exception_type`（失敗時） |

`child_exit_without_handoff` 是保守的兜底名稱：它可能是 C/C++ extension 硬崩潰、OOM、Windows 工作管理員結束、啟動早期失敗，或交接檔無法寫入；不得僅憑它斷定為特定底層崩潰。

## 6. 父子程序交接流程

```text
子程序啟動
  → Supervisor 先建立 session_id，隨 child command 的內部參數傳入
  → child 使用此 session_id；清除本 profile 的 latest_child_termination.json
  → heartbeat 帶入 session_id，讓 Supervisor 事件可關聯目前 child；只有 PID、session_id 與本次啟動時間都吻合時，Supervisor 才採用 heartbeat 的 state/run count
  → 正常運作時記錄 recovery events
  → 未處理 exception：寫 unhandled_exception + latest_child_termination.json，然後 re-raise
  → Supervisor 偵測 child exit / heartbeat timeout / scheduled restart / Ctrl+C
  → Supervisor 寫對應四大分類事件，必要時安排重啟
  → 建立下一個子程序（相同 profile，--resume）
```

heartbeat timeout 的特殊處理：它是 Supervisor 主動終止子程序，可能沒有子程序終止紀錄。因此 Supervisor 必須自己成為該事故的權威來源，寫入 `HEARTBEAT_TIMEOUT/heartbeat_stale` 後再停止 child。

child exit 的兜底：若 exit code 不是明確 manual-exit code，且本次 child 沒有可讀、且 `pid` 等於目前 `Popen.pid` 的 handoff，Supervisor 必須寫 `CRASH/child_exit_without_handoff`。PID 比對可防止子程序在啟動極早期崩潰、來不及清除上一輪 handoff 時誤讀舊資料；這也涵蓋連 Python 都來不及執行 exception handler 的情況。

中斷語意：`Ctrl+Shift+Q`（專用 exit code 75）是 `SCHEDULED_MAINTENANCE/manual_exit_hotkey`，Supervisor 停止；`Ctrl+C` 是既有的 `SCHEDULED_MAINTENANCE/interrupt_recovery_requested`，Supervisor 仍會恢復重啟。不要把兩者合併成 generic manual exit。

## 7. v1 不做的事

- 不建立 UI、資料庫、雲端上傳或通知。
- 不改變 Supervisor 的 timeout、backoff、每日重啟或恢復決策。
- 不追溯舊 console log 以補齊歷史資料。
- 不在每個 `except Exception` 都寫 incident；只有會影響恢復路徑、程序生命週期，或需要統計的事件才記錄，避免噪音與大量 IO。
- 不自動截圖（見 3.3）。

## 8. 驗收條件

1. Native 與 Sandbox 寫入不同的 `user_data/<profile>/runtime/` 目錄。
2. 一次未處理 exception 在歷史中可找到 exception type、message、traceback、最後 state、session ID；Supervisor 可由 handoff 關聯到它。
3. heartbeat timeout 即使 child 沒有機會寫檔，也至少有一筆 `HEARTBEAT_TIMEOUT` 事件含 heartbeat age。
4. 子程序以非預期 exit code 離開、且未留下 handoff 時，Supervisor 記錄 `CRASH/child_exit_without_handoff` 與 exit code。
5. 啟動初期失敗時允許 `state: null` 與 `run_count: 0`。
6. 每日排程、`Ctrl+Shift+Q` 與 Ctrl+C 都能分別識別，且不被統計成 exception。
7. 寫入路徑不存在、唯讀或 JSON 損毀時，bot 的既有重啟／恢復行為仍正常。
8. 摘要可先顯示四大分類，且每類可列出前十個 reason code。
9. 測試覆蓋 schema、profile 隔離、append 寫入失敗、child→Supervisor 關聯、無 handoff 的 child exit 與統計分類。

## 9. 後續決策點（v2 候選）

- 保留天數與大小上限（例如事件保留 30 天）。
- 產生 CLI 摘要指令，例如「最近 24 小時依 reason_code 分組」。
- 事故截圖與前後 N 行 structured log 參照。
- crash loop 閾值與主動停止／通知策略；這必須另行確認，不能在 v1 自動加入。
