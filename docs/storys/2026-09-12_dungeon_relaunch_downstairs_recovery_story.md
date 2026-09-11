# 地下城重啟下樓死循環修復與前置意圖鎖定開發故事 (PARS Story) 📜

本篇記錄於 `fix/dungeon_go_down` 分支中，修復遊戲在地下城內部重啟後無法推進下樓、造成尋路死循環的問題與收斂過程。

---

## 1. Problem (問題背景)

在地下城探索過程中發生遊戲重啟或異常恢復時，系統在 `login_flow` 登入載入完成後正確辨識到起點錨點 `dungeons/leave.png` 並轉移至 `SceneId.DUNGEON_EXPLORING`。然而在移交主狀態機後，發生以下異常現象：

1. **配置意圖未滿足 Dispatch 前置條件**：重啟後若當前配置為非地下城路線（例如普通關卡 `stage`、領地探索 `domain` 或城鎮速領），其 `explore_priorities` 缺少地下城下樓按鈕 `dungeons/gungeon_godown.png`，導致 `ExploreHandler` 無法匹配下樓標記。
2. **全域狀態感知誤判尋路**：`detect_current_state` 在 `config["type"] == "stage"` 或非 `dungeon` 模式下，因 `is_dungeon_mode_type()` 限制，只檢查最小復原特徵，而後續步驟比對大廳關卡按鈕造成狀態在 `NAVIGATING` 與 `DUNGEON_EXPLORING` 間震盪。
3. **`dungeon_fight.png` 職責邊界混淆**：舊實作誤將大廳出擊備戰按鈕 `dungeons/dungeon_fight.png` 視為地下城內部特徵與探索優先級，使內部決策與大廳導航邊界重疊。

---

## 2. Approach (架構方案與契約)

依據 [Precondition Contracts](../architecture/precondition_contracts.md) 第 7.1 與 7.2 節（物理狀態優先於目標意圖）與 [Lobby Scene Contract](../features/navigation/lobby_scene_contract.md) Invariant 6，制定長效架構契約 [Dungeon Relaunch Recovery Contract](../features/navigation/dungeon_relaunch_recovery_contract.md)：

1. **客觀場景主導 (Perceptual Scene Primacy)**：全域定位無論當前目標為關卡或領地，只要在畫面上觀測到地下城物理錨點（`leave.png`、`gungeon_godown.png`、`dungeons_complete.png`），立即鎖定為地下城內部，嚴禁被目標意圖遮蔽。
2. **目標意圖鎖定 (Intent Latching)**：肉身處於地下城時，關卡/領地目標意圖的 dispatch precondition 尚未成立。狀態機將原目標意圖複製並鎖定於 `dungeon_recovery_return_config`，並注入最小前置地下城離場路由（`EMERGENCY_DUNGEON_EXIT_PRIORITIES`）。
3. **通關離場閉環還原**：`ExploreHandler` 探索打通當前副本後，在確認大廳或城鎮錨點時，100% 原樣還原鎖定之目標配置，無縫恢復原目標執行。
4. **探索處理器領域自治**：`ExploreHandler` 自主驗證 `explore_priorities`，若傳入配置缺少有效地下城標記，自主回退至標準離場順序，並將 `dungeons/dungeon_fight.png` 徹底移出內部特徵庫。

---

## 3. Resolution (具體落實)

1. **配置層更新**：
   - [`config/defaults.toml`](../../config/defaults.toml)：於每日模式地下城優先級列表補入 `"dungeons/leave.png"`。
2. **狀態機核心強化**：
   - [`states/state_machine.py`](../../states/state_machine.py)：
     - 擴充 `DUNGEON_RECOVERY_MODE_TYPES` 包含 `domain` 與 `collect_only`。
     - 實作 `is_dungeon_explore_config` 靜態檢驗器。
     - 重構 `ensure_explore_config()`：在偵測到非地下城目標意圖時發動 Intent Latching，注入 `EMERGENCY_DUNGEON_EXIT_PRIORITIES`。
     - 從 `DUNGEON_SCENE_FEATURES`、`EMERGENCY_DUNGEON_EXIT_PRIORITIES` 與 `detect_current_state()` 中徹底移除 `dungeon_fight.png`。
3. **探索處理器防禦**：
   - [`states/handlers/explore.py`](../../states/handlers/explore.py)：移除非內部特徵之 `dungeon_fight.png`，健全自主回退安全機制。
4. **驗證測試與既有測試修復**：
   - [`tests/test_dungeon_relaunch_recovery.py`](../../tests/test_dungeon_relaunch_recovery.py)：新增 9 個情境驗證測試。
   - [`tests/test_town_subflow_precondition_navigation.py`](../../tests/test_town_subflow_precondition_navigation.py)：將舊測試中誤用的 `dungeon_fight.png` 更新為合法的地下城物理錨點 `leave.png`。

---

## 4. Status & Verification (驗證結果)

- **專屬行為測試**：`tests.test_dungeon_relaunch_recovery` 9 項測試全數通過（OK）。
- **前置條件導航測試**：`tests.test_town_subflow_precondition_navigation` 30 項測試全數通過（OK）。
- **雙工作樹全套測試比對**：
  - `MAIN BASELINE` (998 tests)：38 failures/errors。
  - `HEAD BASELINE` (1004 tests)：36 failures/errors。
  - 迴歸分類判定：`BRANCH_REGRESSION = 0`，既有失敗皆屬基準線問題，無引入任何新迴歸。
- **長效契約歸檔**：已於 [`docs/features/navigation/dungeon_relaunch_recovery_contract.md`](../features/navigation/dungeon_relaunch_recovery_contract.md) 建立正式規範；臨時性檔案 [`docs/todos/fix_dungeon_go_town.md`](../todos/fix_dungeon_go_town.md) 已完成刪除清理。
