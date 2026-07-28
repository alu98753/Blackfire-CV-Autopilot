# 誤點擊意外彈窗恢復處理器與 Subflow 容納架構開發故事 (PARS Framework) 🛡️

## Purpose (目的)
在長跑自動掛機過程中，滑鼠偶爾可能因畫面座標偏移或動態 UI 觸發而誤點擊非預期區域，導致開啟未知視窗或**雙層疊加彈窗**（例如：最上層「突襲」對話框與襯底「關卡 VI」資訊視窗）。原本的排程器與狀態機無法感知視窗開錯，容易導致流程卡死。本工程旨在建立具備**狀態暫存 (State Stashing)**、**明暗度遮罩分析 (Dimming Detection)** 與**可擴充 Exception Subflow 容器**之自癒復原機制。

---

## Action (行動)

1. **狀態暫存與回復機制 (State Stashing & Restoration)**：
   - 於 [GameStateMachine](file:///e:/Side_Project/BlackfireCrusade_tool/states/state_machine.py#L160) 增設 `STATE_POPUP_RECOVERY` 狀態，並實作 `stash_current_state()` 與 `restore_stashed_state()`。
   - 觸發例外時自動備份原 `current_state` 及 phase context，待視窗徹底關閉後無痕還原原本流程。

2. **可擴充 Subflow 容器架構 (Exception Subflow Container)**：
   - 定義抽象介面 `BaseExceptionSubflow`，包含 `can_handle()` 與 `execute()` 兩大標準契約。
   - 實作通用關閉/取消 Subflow (`GenericCancelSubflow` 對應 `cancel.png`, `common/close.png` 等) 與 `RaidBoxSubflow`（對應 `Raid_Box.png`）。
   - 於 [UnexpectedPopupRecoveryHandler](file:///e:/Side_Project/BlackfireCrusade_tool/states/handlers/popup_recovery.py) 實現多 Subflow 迭代排程器，支援多層疊加彈窗之連續解鎖排除。

3. **明暗度遮罩與對比分析 (Modal Dimming Overlay Detection)**：
   - 實作 `analyze_dimming_overlay(screen_img)`，透過邊框與中央區域亮度方差，科學判斷遊戲畫面是否處於 Modal 遮罩狀態。

4. **單元測試與防呆保護**：
   - 撰寫 [test_behavior_popup_recovery.py](file:///e:/Side_Project/BlackfireCrusade_tool/tests/test_behavior_popup_recovery.py) 驗證狀態暫存、Subflow 容器調度及最大重試 Fallback 機制。

---

## Result (結果)
- **測試驗證**：全套 308 項單元測試 100% 綠燈通過 (OK)，耗時 223.9 秒，全域零 Regression。
- **實務測試**：針對 `debug_click.png` 雙層彈窗，系統能先後排除第一層「突襲 (cancel.png)」與第二層「關卡 (close.png)」，達成多階層自癒。

---

## So What (核心價值)
- **高強健性防護網**：將防錯與異常排除解耦為獨立 Handler 與 Subflow 閉環，提升系統面對亂點、誤觸彈窗時的強健性與 24/7 長跑穩定度。
- **低耦合擴充性**：未來遇到任何全新類型的意外視窗，僅需繼承 `BaseExceptionSubflow` 並註冊至 Handler，免修核心狀態機。

---

## Influence (影響)
- 確立了「意外視窗處置 = Subflow 容器 + 狀態暫存」的標準開發模式。
- 為後續其他彈窗、突發事件處理提供了標準擴充介面與降級處置標準。
