Viewed mode_setup.py:1-150
Searched for "set_active_profile"
Searched for "set_active_profile"
Viewed config.py:300-460
Searched for "exception_features"
Viewed exception_subsystem_architecture.md:1-131
Viewed loop.py:1-82
Viewed incident_journal.py:1-150
Viewed incident_journal.py:151-240
Viewed watchdog.py:1-150
Viewed watchdog.py:151-172
Viewed handler.py:1-142
Viewed game_relaunch.py:1-78
Viewed generic_anti_stuck.py:1-59
Viewed raid_box.py:1-115
Viewed wheel_of_fortune.py:1-150
Viewed profile_updates.py:1-10
Viewed mode_setup.py:140-196
Viewed stage_setup.py:1-60
Viewed stage_setup.py:61-86
Viewed dungeon_setup.py:1-80
Viewed tier4_setup.py:1-77
Viewed game_process.py:1-60
Viewed window.py:1-60
Viewed window.py:80-155

針對您提出的兩個核心問題，以下為目前架構的運作機制確認與所有例外處理的精確列點說明：

---

# 一、 重開機制與 Config / main 載入確認

### 結論：**您的理解完全正確！目前確實是「寫入 TOML ➔ 重開帶 `--resume` ➔ 零交談無縫重開」。**

### 1. main 與 config 是否會重新讀取？
* **外部監控重開（Supervisor Watchdog）**：
  當遇到心跳逾時（>180s）、Python 未捕獲異常崩潰、Ctrl+C 強制復原、或每日 08:00 定期維護時，外部守門員 [runtime/supervisor.py](file:///e:/Side_Project/BlackfireCrusade_tool/runtime/supervisor.py) 會透過 `subprocess.Popen` 開啟**全新的 Python 子進程**。此時 Python 直譯器、[main.py](file:///e:/Side_Project/BlackfireCrusade_tool/main.py) 的 `main()` 入口、以及 [config.py](file:///e:/Side_Project/BlackfireCrusade_tool/config.py) 都會**全新載入並從硬碟重新讀取**。
* **內部遊戲自癒重開（GameRelaunchSubflow）**：
  若是卡死 5 次未果觸發的遊戲級重開，Python 進程**不退出**，只強制終止遊戲進程並透過 Steam 重啟遊戲，記憶體中的 config 與 TOML 依然保持最新。

### 2. 為什麼重開不會詢問使用者偏好？（無縫重開作法）
整個「無縫重開 (Zero-Prompt Seamless Resume)」由以下機制閉環保證：

1. **第一次選擇即持久化寫入**：
   使用者在第一次啟動時於 CLI 選單所選的設定（例如：大關/小關、地下城類型或貪婪挑選、待機時是否打 Boss、裝備保留與大量分解品質等），在選擇當下即透過 [persist_mode_updates](file:///e:/Side_Project/BlackfireCrusade_tool/cli/profile_updates.py) 與 [update_profile_config](file:///e:/Side_Project/BlackfireCrusade_tool/config.py#L355) **以增量 Deep-Merge 方式即時寫入使用者的 `user_data/<profile>/config.toml`**。
2. **Supervisor 自動注入 `--resume`**：
   重開時，Supervisor 的 `prepare_resume_command()` 會自動保留原命令參數，並固定追加 `--resume`、`--target <target>`、`--profile <profile>`。
3. **main.py 的四道免交談閘門**：
   * **視窗鎖定**：`select_game_window(..., auto_prompt=not is_resume)` 偵測到 `is_resume=True`，直接依 target 鎖定視窗，**完全不彈出視窗選擇提示**。
   * **Profile 覆蓋載入**：`set_active_profile(profile_name)` 重新讀取 `defaults.toml` 並疊加剛剛寫入的 `user_data/<profile>/config.toml`。
   * **關卡與模式選單**：[cli/mode_setup.py](file:///e:/Side_Project/BlackfireCrusade_tool/cli/mode_setup.py#L41) 偵測到 `resume=True`，以 `interactive=False` 呼叫各 setup 模組，內部的 `prompt_choice` 改寫為 `lambda _prompt, default: default`，直接採用 TOML 的持久化數值，**不讀取 `stdin`**。
   * **裝備分解選單**：[main.py:L53](file:///e:/Side_Project/BlackfireCrusade_tool/main.py#L53) 由 `if not is_resume: setup_equipment_config(config)` 守衛，**直接略過裝備選單**。
4. **遊戲重置對齊**：
   若附帶 `--restart-game`（或視窗處於未回應狀態），[SteamGameLauncher](file:///e:/Side_Project/BlackfireCrusade_tool/utils/steam_launcher.py) 自動重啟遊戲並置頂校準為標準 1080p，狀態機切換至 `STATE_NAVIGATING` / `STATE_UNKNOWN` 無縫繼續掛機。

---

# 二、 目前所有例外處理做法（分類精確列點）

專案內的例外防禦採 **「感知分層 ➔ 雙層輕量自癒 ➔ 遊戲重啟 ➔ 進程監控兜底」** 的架構設計：

---

### 1. UI 阻擋與意外彈窗類例外 (UI Blockers & Modal Dialogs)

* **1.1 懸賞 / 掃蕩結算彈窗阻礙 (`Raid_Box.png`)**
  * **情境**：在非預期時刻出現掃蕩或懸賞結算視窗阻礙主流程。
  * **做法**：[RaidBoxSubflow](file:///e:/Side_Project/BlackfireCrusade_tool/states/exceptions/subflows/raid_box.py) 進行三段式救援：
    1. 全圖鎖定 `Raid_Box.png` 取得 ROI。
    2. 切割 ROI 內部優先比對 `exceptions/cancel.png`（寬鬆門檻 0.65 容忍半透明背景）並點擊。
    3. 若 ROI 未中則全圖比對關閉按鈕（門檻 0.70）；若仍未中則點擊右上方預設關閉座標 `(box_x + 360, box_y + 35)`。
    4. 處置完成後調用 `restore_stashed_state()` 復原被中斷的業務狀態。

* **1.2 幸運輪盤介面阻礙 (`Wheel_of_Fortune.png`)**
  * **情境**：遊戲隨機彈出幸運輪盤活動介面。
  * **做法**：[WheelOfFortuneSubflow](file:///e:/Side_Project/BlackfireCrusade_tool/states/exceptions/subflows/wheel_of_fortune.py) 進行處置：
    1. 匹配 `exceptions/Wheel_of_Fortune.png` 定位輪盤。
    2. 於輪盤內部比對 `common/quit.png`（門檻 0.75 防誤觸），未中則全圖備援比對，最後備援點擊右上角 `(box_x + 500, box_y + 40)`。
    3. 檢測是否回到城鎮門口 (`common/door.png`) 確認阻礙已排除，隨後復原狀態。

* **1.3 未知彈窗與暗色遮罩 (Generic Anti-Stuck & Dimming Overlay)**
  * **情境**：無專屬 Subflow 圖案匹配，但畫面出現未登錄之彈窗，或 [handler.py:L47](file:///e:/Side_Project/BlackfireCrusade_tool/states/exceptions/handler.py#L47) 分析出暗色遮罩（中央與邊框亮度差 > 15 且邊框 < 120）。
  * **做法**：觸發 **優先級 2 通用防卡死** [GenericAntiStuckSubflow](file:///e:/Side_Project/BlackfireCrusade_tool/states/exceptions/subflows/generic_anti_stuck.py)。依序掃描點擊通用全域按鈕：`common/confirm.png`, `common/continue.png`, `common/quit.png`, `common/ok.png`, `exceptions/cancel.png`, `cancel.png`（門檻 0.80），清除對話框後回復原狀態。

* **1.4 彈窗處置超限降級 (Max Retries Fallback)**
  * **情境**：輕量彈窗處置嘗試累計達 **5 次** 仍無法消除畫面阻礙。
  * **做法**：[UnexpectedPopupRecoveryHandler](file:///e:/Side_Project/BlackfireCrusade_tool/states/exceptions/handler.py#L135) 判定輕量救援失效，直接調用 [GameRelaunchSubflow](file:///e:/Side_Project/BlackfireCrusade_tool/states/exceptions/subflows/game_relaunch.py) 進入遊戲強制重開自癒。

---

### 2. 狀態逾時與邏輯卡死類例外 (Watchdog & Timeout Stuck)

* **2.1 常規短狀態逾時 (30 秒)**
  * **情境**：大廳 (`STATE_LOBBY`)、戰鬥結算 (`STATE_VICTORY`/`STATE_DEFEAT`) 等短暫狀態停滯超過 30 秒未變動。
  * **做法**：[ExceptionWatchdog](file:///e:/Side_Project/BlackfireCrusade_tool/states/exceptions/watchdog.py) 觸發：
    * **第 1 次逾時**：呼叫 `stash_current_state()` 暫存當前狀態與上下文，轉移至 `STATE_POPUP_RECOVERY` 啟動彈窗掃描與輕量恢復。
    * **第 2 次連續逾時**：若同一狀態再次卡死超過 30 秒（代表第 1 次輕量處置無效），直接呼叫 `GameRelaunchSubflow` 終止遊戲重開。

* **2.2 長流程任務逾時 (90 秒) 與進度防誤判**
  * **情境**：導航 (`STATE_NAVIGATING`)、戰鬥中 (`STATE_BATTLE`)、地下城 (`STATE_DUNGEON_EXPLORING`)、背包銷毀 (`STATE_BAG_CLEANING`)、城鎮子任務（抽卡/Boss/祭壇/珠寶/寶箱）等長流程任務給予 90 秒寬鬆門檻。
  * **防誤判機制**：在長作業中（如批次分解背包或出售珠寶），每推進一筆項目或 Phase 推進時，主動呼叫 `self.machine.notify_ui_progress()` 刷新 `last_state_change`，確保正常長作業絕不誤觸卡死。若真卡死逾時滿 90 秒，同樣走「第 1 次彈窗救援 ➔ 第 2 次遊戲重開」。

* **2.3 待機模式專屬動態 CD 逾時 (`STATE_COLLECT_ONLY`)**
  * **情境**：掛機待機冷卻時間超限（大於 `max(diamond_cd, bread_cd) + 60s`），代表計時已到卻未正常喚醒發起領取。
  * **做法**：Watchdog 判定待機定時器卡死，立即調用 `GameRelaunchSubflow` 重開遊戲並重新校準定時器。

* **2.4 狀態假切換與防抖保護**
  * **情境**：Handler 若重複執行無效的 `transition_to(current_state)`，可能惡意刷新時間戳導致 Watchdog 永遠無法累積到 30s/90s。
  * **做法**：在 [GameStateMachine.transition_to](file:///e:/Side_Project/BlackfireCrusade_tool/states/state_machine.py) 入口處加入 `if self.current_state != new_state:` 防抖檢查，非狀態實質變動絕不重置逾時計時器。

---

### 3. 遊戲視窗與作業系統層級例外 (Window & OS Level)

* **3.1 遊戲視窗無回應 (Hung Window)**
  * **情境**：遊戲主線程卡死（Windows 出現「沒有回應 / Not Responding」）。
  * **做法**：調用 Win32 API `IsHungAppWindow(hwnd)`（定義於 [utils/game_process.py](file:///e:/Side_Project/BlackfireCrusade_tool/utils/game_process.py#L14)）。在啟動檢測時若發現無回應，自動升級為 `force_relaunch = True`，立即強制結束進程並重新啟動遊戲。

* **3.2 遊戲視窗崩潰消失 (HWND Lost)**
  * **情境**：遊戲在待機或戰鬥中崩潰閃退，`capturer.get_window_rect()` 回傳 `None`。
  * **做法**：Watchdog 於 [watchdog.py:L50](file:///e:/Side_Project/BlackfireCrusade_tool/states/exceptions/watchdog.py#L50) 偵測到 HWND 不存在，記錄日誌後立即觸發 `GameRelaunchSubflow`，重新透過 Steam 拉起遊戲。

* **3.3 進程終止安全守衛 (Self-Termination Guard)**
  * **情境**：腳本在終止遊戲進程時可能誤殺自身。
  * **做法**：[utils/game_process.py](file:///e:/Side_Project/BlackfireCrusade_tool/utils/game_process.py#L59) 的 `terminate_game_process()` 內部核驗目標 PID，明確排除 `current_script_pid = os.getpid()`，保證絕不自我誤殺。

---

### 4. Python 進程監控與崩潰自癒 (External Supervisor)

* **4.1 心跳逾時死鎖 (Heartbeat Stale > 180 秒)**
  * **情境**：Python 腳本內部因底層 C 模組/DLL 阻塞、死鎖或未捕捉之無窮迴圈，導致超過 180 秒未寫入心跳檔（[runtime/heartbeat.py](file:///e:/Side_Project/BlackfireCrusade_tool/runtime/heartbeat.py)）。
  * **做法**：外部監控進程 [runtime/supervisor.py](file:///e:/Side_Project/BlackfireCrusade_tool/runtime/supervisor.py#L240) 強行 `terminate()` / `kill()` 該 Python 子進程，記錄 `HEARTBEAT_TIMEOUT` 事件至 Incident 日誌，並以指數退避（2s ~ 60s）自動重啟 Python 進程（帶入 `--resume --restart-game`）。

* **4.2 未捕獲之 Python 運行期異常 (Unhandled Exception Crash)**
  * **情境**：主迴圈發生非預期之 Python Exception（例如 OpenCV 矩陣例外、未預期的 NoneType 等）。
  * **做法**：[runtime/loop.py](file:///e:/Side_Project/BlackfireCrusade_tool/runtime/loop.py#L72) 的全域 `try...except Exception as exc:` 捕捉：
    1. 呼叫 `record_unhandled_exception(state_machine, exc)` 將 Traceback、異常型態、當前狀態與 Run Count 寫入 `user_data/<profile>/runtime/incidents/YYYY-MM-DD.jsonl`，並產生原子交接檔 `latest_child_termination.json`。
    2. 重新拋出異常使進程退出。
    3. 外部 Supervisor 讀取交接檔，記錄 `CRASH` 事件，並自動無縫重啟子進程。

* **4.3 每日 08:00 定期維護重啟 (Daily Scheduled Maintenance)**
  * **情境**：每天早上 08:00（遊戲伺服器換日重置），長時間掛機需要清理記憶體。
  * **做法**：Supervisor 在每日 08:00 到達時，記錄 `SCHEDULED_MAINTENANCE`，優雅關閉 Python 子進程，並帶入 `--resume --restart-game` 重開遊戲與腳本，重新載入每日任務。

* **4.4 使用者熱鍵例外控制**
  * **`Ctrl + Space`（暫停/繼續）**：主迴圈進入休眠並持續 touch heartbeat；恢復時自動計算並扣抵暫停秒數（`pause_duration`），補償內部 Watchdog 計時器，防止恢復後被誤判卡死。
  * **`Ctrl + Shift + Q`（手動安全退出）**：拋出專屬退出代碼 `SystemExit(75)` (`MANUAL_EXIT_CODE`)，Supervisor 識別後判定為正常手動退出，乾淨關閉監控並返回 `run.bat` 選單。
  * **`Ctrl + C`**：在 Supervisor 託管下，Supervisor 將 Ctrl+C 攔截為「使用者要求重開復原 (`interrupt_recovery_requested`)」，重啟子進程而非直接崩潰中斷。

---

### 5. 設定檔與資料損毀例外 (Config & Data Fail-safe)

* **5.1 設定檔語法損毀 (Malformed TOML / JSON)**
  * **情境**：使用者手動編輯 `config.toml` 或 `exception_features.json` 時打錯語法（格式損毀）。
  * **做法**：[JsonConfigManager](file:///e:/Side_Project/BlackfireCrusade_tool/config.py#L425) 與 TOML 載入器實作「交易式快照驗證」：檔案讀取或解析失敗時，發出 Warning Log，**自動保留並繼續使用上一份合法有效的記憶體快照 (Last Valid Snapshot)**，保證腳本絕不中斷崩潰。

* **5.2 敏感個資洩漏防護 (Incident Redaction)**
  * **情境**：在崩潰或復原寫入 Incident 日誌時，避免 Context 包含敏感資料。
  * **做法**：[runtime/incident_journal.py](file:///e:/Side_Project/BlackfireCrusade_tool/runtime/incident_journal.py#L71) 透過 `_redact()` 正則表達式，自動將含有 `token`, `password`, `secret`, `api_key`, `Bearer` 等數值遮蔽為 `[REDACTED]`。

---

### 6. 遊戲業務邏輯例外 (Gameplay State Transitions)

* **6.1 背包已滿例外 (Backpack Full)**
  * **情境**：戰鬥結束或大廳檢測到背包已滿提示。
  * **做法**：狀態機不拋錯，轉移至 `STATE_BACKPACK_FULL_SORTING` 或 `STATE_BAG_CLEANING`，自動切換至背包頁面，依據 TOML 設定之品質進行大量分解或保留，清理完畢後返回原流程。
* **6.2 體力耗盡與地下城冷卻 (Stamina Out / Dungeon CD)**
  * **情境**：進關提示體力不足，或地下城卡片帶有冷卻木牌。
  * **做法**：狀態機轉移至退守等待 (`STATE_RETREAT_WAIT`) 或回城待機 (`STATE_COLLECT_ONLY`)，停止發起進關點擊，進入低資源休眠。
* **6.3 視覺與 OCR 比對失效率防護**
  * **情境**：辨識字串模糊、模板未達門檻。
  * **做法**：所有圖像比對統一由 `safe_match` 防護，未達門檻時回傳 `None, 0.0`，Handler 進入下一幀安全輪詢，絕不拋出未處理之 Python 異常。

Edited result_todo.md
Viewed exceptionlist.md