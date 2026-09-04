# 多進程 Supervisor 生命週期自癒與 S1~S7 遊戲重啟矩陣開發故事（PARS Framework）

## Purpose (目的)

1. **長時間 24/7 掛機的記憶體洩漏與渲染死鎖痛點**：舊架構下 Supervisor 在每日 08:00 定時維護重啟或心跳逾時（>180s）時，僅殺除並重啟 Python 子進程 (`main.py`)，而未重啟遊戲本體。導致累積 24 小時的 Unity 記憶體洩漏無法釋放；且當心跳逾時是由遊戲視窗未回應 (Hung)、白屏或 DXGI 截圖卡死引起時，僅重啟 Python 會再次 Attach 到卡死視窗，陷入惡性死循環。
2. **進程管理邏輯分散與 DRY 違規**：先前 `GameRelaunchSubflow` 散落著手寫 Win32 API 與 `taskkill` 字串，缺乏集中的進程生命週期管理模組與 PID 安全隔離。
3. **區分情境的快速 Attach vs 強制重開**：一般 Python 例外短暫閃退時不應盲目關閉遊戲，需保留秒級 Attach 能力以防打斷進行中的關卡；而維護或視窗卡死時則必須強制銷毀舊遊戲重啟。

## Action (行動)

1. **定義 S1 ~ S7 生命週期決策矩陣**：
   - **S1 (每日 08:00 維護)** 與 **S2 (心跳逾時 >180s)**：Supervisor 強制終止子進程後，注入單次消費之 `--restart-game` 旗標，清除舊遊戲進程並透過 Steam 直連重開登入。
   - **S3 (遊戲未回應視窗偵測)**：啟動時調用 `IsHungAppWindow(hwnd)`，若視窗無回應自動升級為強制重啟。
   - **S4 (執行期嚴重卡死)**：Watchdog 觸發重構後的 `GameRelaunchSubflow`。
   - **S5 (一般 Python 例外崩潰)** 與 **S6 (終端機 Ctrl+C)**：維持原樣快速 Attach（不帶 `--restart-game`），秒級接續。
   - **S7 (專屬手動退出 `Ctrl+Shift+Q`)**：子進程送出 Exit Code 75，Supervisor 正常結束且不重啟遊戲。
2. **抽離共用進程管理模組 ([utils/game_process.py](../../utils/game_process.py))**：
   - 實作 `is_window_hung(hwnd)` 檢查視窗健康度。
   - 實作 `terminate_game_process(game_title, hwnd, script_pid, timeout)`，內建呼叫者 PID 安全守護（防誤殺自己）、安全 taskkill 執行與輪詢銷毀確認。
3. **重構既有重啟子流程 ([states/exceptions/subflows/game_relaunch.py](../../states/exceptions/subflows/game_relaunch.py))**：
   - 移除內部重複的手寫 `taskkill` 與 Win32 Process ID 邏輯，改為調用 `utils.game_process.terminate_game_process`，恪守 DRY 原則。
4. **擴充 Steam 啟動器與進入點契約 ([utils/steam_launcher.py](../../utils/steam_launcher.py), [cli/arguments.py](../../cli/arguments.py), [main.py](../../main.py))**：
   - `SteamGameLauncher.ensure_game_ready(force_relaunch=False)` 支援重開遊戲。
   - CLI 新增 `--restart-game` 參數。
   - `main.py` 整合 `args.restart_game` 與 `is_window_hung` 自動升級重啟。
5. **Supervisor 支援單次消費旗標注入 ([runtime/supervisor.py](../../runtime/supervisor.py))**：
   - `prepare_resume_command` 支援 `restart_game: bool`，並自動清除舊殘留，確保重啟成功後後續的 S5 crash 不會永久殘留 `--restart-game`。
6. **建立 S1 ~ S7 專屬領域行為測試套件 ([tests/test_behavior_supervisor_lifecycle.py](../../tests/test_behavior_supervisor_lifecycle.py))**：
   - 編寫 9 個聚焦單元測試，100% 覆蓋 S1 ~ S7、單次消費保護與 PID 防誤殺機制。

## Result (結果)

- 測試套件執行耗時僅 0.033 秒，全數綠燈通過：
  - `test_scenario_s1_daily_scheduled_restart_injects_restart_game` (OK)
  - `test_scenario_s2_heartbeat_stale_injects_restart_game` (OK)
  - `test_scenario_s3_hung_window_auto_escalates_to_restart_game` (OK)
  - `test_scenario_s4_runtime_capture_failure_triggers_game_relaunch` (OK)
  - `test_scenario_s5_unhandled_crash_fast_resumes_without_restart_game` (OK)
  - `test_scenario_s6_keyboard_interrupt_fast_resumes_without_restart_game` (OK)
  - `test_scenario_s7_manual_exit_stops_supervisor_without_restart` (OK)
  - `test_restart_game_flag_is_single_use_consumed` (OK)
  - `test_terminate_game_process_safety_guards_self_pid` (OK)
- 主進入點測試 `tests.test_behavior_main_entrypoint` 17 項全數綠燈 (0.061s)。
- 長時間韌性測試 `tests.test_long_run_resilience` 21 項全數綠燈 (1.666s)。

## So What (核心價值)

將「父進程守護排程（Supervisor）」與「子進程自癒執行（Worker）」的生命週期職責明確解耦：
- Supervisor 僅透過參數協議 (`--resume`, `--restart-game`) 宣告意圖，不跨進程侵入業務邏輯。
- Worker 集中於 `utils.game_process` 封裝 Windows 視窗與進程操作，兼顧安全性與乾淨度。
- 達成 24/7 掛機的真正閉環自癒：遇死鎖乾淨清空重開，遇小錯秒級無損接回。

## Influence (影響)

為多開沙盒（Sandbox）與本機（Native）實例提供了標準統一的進程管理接口；未來若引入其他遊戲版本或客戶端封裝，均可直接復用 `game_process` 與 Supervisor 參數協議。
