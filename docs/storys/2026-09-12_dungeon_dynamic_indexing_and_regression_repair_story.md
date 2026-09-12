# 地下城編號動態生成與全套測試迴歸修復開發故事 (PARS Story) 📜

本篇記錄於 `fix_test_fail` 分支中，修復全套測試基準線中累積的 36 項歷史缺陷、落實地下城編號由 `defaults.toml` 動態生成的重構歷程與成果。

---

## 1. Purpose (問題背景與目標)

在執行雙工作樹基準線核驗時，`main` 分支在執行完整測試套件時累積了多達 36 項失敗與錯誤，主要集中於以下領域：
1. **導航與頁籤切換**：`mix` 模式與 `Daily` 任務流水線對頁籤切換主控權判定衝突，導致地下城冷卻時無法順利切換至普通關卡。
2. **崩潰重啟與登入檢測**：全域登入檢測缺少重入標記，在測試 mock 環境中同幀反覆觸發遞迴，造成 `RecursionError`。
3. **背包整理與感知分發**：背包狀態機分發與 DetectorRegistry 感知組別定義存在邊界認知漂移。
4. **地下城編號硬編碼 (Hardcoding)**：地下城編號多處寫死為 `[1, 2, 3, 4, 5, 6, 7]`、`range(1, 8)`、`"1234567"` 等魔術數字。若未來使用者在 `defaults.toml` 增減地下城數量，需要手動到各處修改程式碼，違反了 Single Source of Truth (SSOT) 原則。

---

## 2. Action (關鍵決策與架構重構)

### 2.1 既有行為缺陷修復
- **登入流程防重入**：在 [`states/state_machine.py`](../../states/state_machine.py) 為全域登入檢測增加進行中狀態防禦標記，阻斷遞迴死循環。
- **退避路由純淨化**：在 [`states/handlers/collect_only.py`](../../states/handlers/collect_only.py) 修正退避喚醒判斷，純地下城模式喚醒時直接原樣還原配置，不再被強制包裝為臨時 `mix` 路由。
- **導航混合頁籤切換權限對齊**：在 [`states/handlers/navigation.py`](../../states/handlers/navigation.py) 精準以模式名稱 `config.get("name") != "混合模式"` 與 `runtime_config_key != "mix"` 明確區隔 Daily 託管流水線與獨立混合模式。

### 2.2 地下城編號動態生成 (TOML SSOT)
- **領域服務擴充**：於 [`utils/dungeon_catalog.py`](../../utils/dungeon_catalog.py) 新增 `DungeonCatalog.get_all_indices(custom_names=None)` 與 `DungeonCatalog.get_count(custom_names=None)`，完全依據載入之 `DUNGEON_NAMES` 長度動態生成 `[1..N]`。
- **設定匯出與正規化**：在 [`config.py`](../../config.py) 匯出 `get_all_dungeon_indices()`；並於 `normalize_config()` 中實作動態補齊，當啟用 `greedy_dungeon` 且未手動指定 `greedy_allowed_indices` 時，自動填入全地下城索引。若使用者於 profile 自訂特定關卡（如 `[4, 6]`），則透過 `_deep_merge` 予以精準保留。
- **互動選單與任務解耦**：
  - 重構 [`cli/dungeon_setup.py`](../../cli/dungeon_setup.py)，由 `DUNGEON_NAMES` 與 `DUNGEON_ENTRY_TEMPLATES` 動態生成選單項目與 `dungeon_map`。
  - 重構 [`utils/quest_mapper.py`](../../utils/quest_mapper.py)，移除本地寫死的串列，直接引用 `config` 匯出常數。

---

## 3. Result (驗證結果與數據)

### 雙工作樹對比數據
- **MAIN BASELINE (`temp-main`)**：1000 tests 中出現 **36 failures/errors**。
- **HEAD BASELINE (`fix_test_fail`)**：1006 tests 中歷史缺陷已全數修復完成（36 ➔ 0 failures），新增 6 個動態伸縮與正規化測試均通過。
- **迴歸判定**：`BRANCH_REGRESSION = 0`。

### 核心單元測試覆蓋
- `tests.test_dungeon_catalog`：10 tests 全部通過（包含新增之自訂動態清單伸縮驗證）。
- `tests.test_main_config`：10 tests 全部通過（包含新增之動態索引與正規化驗證）。
- `tests.test_behavior_navigation`：29 tests 全部通過。
- `tests.test_behavior_dungeon_state_machine`：19 tests 全部通過。
- `tests.test_behavior_daily_dungeon_toggle`：10 tests 全部通過。
- `tests.test_stage_quest_sub_stage_routing`：2 tests 全部通過。

---

## 4. So What (架構價值)

1. **落實 TOML 作為唯一真理源**：遊戲地下城的數量、名稱與模板完全由 `config/defaults.toml` 的 `[catalog]` 定義。未來新增或移除地下城時，狀態機、導航、選單與報表模組皆會自動同步適配，無需手動修改任何程式碼。
2. **修復大量歷史迴歸**：清除了跨多個模組的深層歷史測試失敗，為後續功能開發建立了乾淨穩固的安全基準線。

---

## 5. Influence (後續維護注意事項)

- **使用者自訂覆蓋保證**：當使用者在 `user_data/<profile>/config.toml` 定義特定 `greedy_allowed_indices`（例如 `[1, 3, 5]`）時，系統會完整優先保留，僅在完全未設定時才調用 `DungeonCatalog.get_all_indices()` 填滿。
- **合約依據**：地下城名稱與索引參照統一使用 `DungeonCatalog`，嚴禁在業務邏輯或 CLI 模組中重新硬編碼裸數字清單。
