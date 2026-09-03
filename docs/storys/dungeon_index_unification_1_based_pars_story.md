# PARS 開發故事：地下城索引全面統一為 1-based 📐

## 📝 PARS 5 大要素

### 1. Purpose (目的)
在專案早期的歷史設計中，普通關卡 (Stage) 與魔王關皆採用直觀的 1-based 編號（`1 ~ 6`），而地下城 (Dungeon) 卻因歷史沿革而繼承了底層陣列的 0-based 編號（`0 ~ 5`）。
這導致整個系統長期承受雙重索引的隱患與認知撕裂：
1. **設定認知衝突**：`defaults.toml` 的 `[bounty_quests]` 出現 `max_stage = 6` 與 `max_dungeon = 5` 的詭異落差，使用者常常疑惑為何關卡有第 6 關但地下城只能填 5。
2. **Off-by-one 補釘散落**：CLI 介面、日誌印出、TaskNode 命令生成等至少 12 處被迫充斥 `+ 1` / `- 1` 的臨時轉換補釘，稍有不慎即引發陣列越界或冷卻索引對齊失敗（如 `AssertionError: 6 != 5` 或 `IndexError`）。
3. **冷卻字典與規則混亂**：`dungeon_cooldowns` 字典鍵值、`quest_rules.json` 中的 `dungeon_index` 與 `defaults.toml` 混雜 0-based 與 1-based，嚴重阻礙模組重構與維護。

為此，發起本項重大重構：**將地下城索引徹底統一為 1-based (`1 ~ 6`)，與關卡系統 100% 完全對齊，消除所有跨層轉換雜湊。**

---

### 2. Action (行動)

1. **設定檔與規則庫全面重構 (Config & Rules Layer)**：
   - **[config/defaults.toml](../../config/defaults.toml)**：將 `[bounty_quests]` 的 `max_dungeon` 預設值修正為 `6`；將所有模式的 `greedy_allowed_indices` 統一更新為 `[1, 2, 3, 4, 5, 6]`；將 `cooldown_map` 字典鍵值由 `0..5` 統一改為 `1..6`（`1=0.0s, 2=300.0s, ..., 6=1800.0s`）。
   - **[config/quest_rules.json](../../config/quest_rules.json)**：將 10 個 `dungeon_rules` 項目的 `dungeon_index` 全面由 `0..5` 平移至 `1..6`（1: 黏糊糊的石窟, 2: 幽影地穴, 3: 森林迷宮, 4: 神秘遺跡, 5: 幽暗監獄, 6: 冰雪洞窟）。
   - **[user_data/native/config.toml](../../user_data/native/config.toml)**：同步更新 `tier4_dungeon_index = 6` 與 `max_dungeon = 6`。

2. **核心領域邏輯與排程器去補釘化 (Domain & Scheduler Layer)**：
   - **[utils/quest_mapper.py](../../utils/quest_mapper.py)**：`TaskNode` 的 `dungeon_index` 嚴格定義為 `1..6`；`to_cli_args()` 移除 `+ 1` 補釘，直接使用 `str(self.dungeon_index)`；`to_config_dict()` 依 `dungeon_entries[idx - 1]` 安全映射名稱。
   - **[utils/quest_scheduler.py](../../utils/quest_scheduler.py)**：`print_task_summary()` 移除 `+ 1` 補釘，直接輸出 `地下城 #{t.dungeon_index}`。
   - **[cli/dungeon_setup.py](../../cli/dungeon_setup.py)**：移除所有 `int(choice) - 1` 與 `index + 1` 運算，輸入選項 `1 ~ 6` 直接對應儲存為 `1 ~ 6`。

3. **狀態機與導航跳轉統一 (State Machine & Navigation Layer)**：
   - **[states/state_machine.py](../../states/state_machine.py)**：
     - `has_available_dungeon()` 全面採用 `enumerate(entry_templates, start=1)`，消除歷史 0-indexed 造成的冷卻誤判；
     - `_apply_tier4_dungeon_selection()` 邊界檢查修正為 `1 <= target_idx <= len(dungeon_entries)`，取得範本與名稱使用 `idx - 1`。
   - **[states/handlers/navigation.py](../../states/handlers/navigation.py)**：
     - `visible_dungeons` 字典鍵值由 `0..5` 統一重構為 `1..6`；
     - 貪婪選關迴圈由 `range(5, -1, -1)` 修正為 `range(len(entry_templates), 0, -1)`；
     - 地下城狀態核驗與名稱檢索統一使用 `dungeon_names[i - 1]`。

4. **全套業務領域單元測試更新與驗證 (Test Suite Overhaul)**：
   - 逐一更新 11 個相關單元測試檔案的斷言與測試 Fixture，確保全部適配 1-based：
     - `tests/test_bounty_quest_filtering.py` (10/10 通過)
     - `tests/test_quest_mapper_and_scheduler.py` (24/24 通過)
     - `tests/test_quest_statemachine_integration.py` (15/15 通過)
     - `tests/test_behavior_daily_dungeon_toggle.py` (5/5 通過)
     - `tests/test_dungeon_swipe_unit.py` (5/5 通過)
     - `tests/test_dungeon_runtime_context.py` (2/2 通過)
     - `tests/test_deadlock_risk_prevention.py` (4/4 通過)
     - `tests/test_daily_pipeline_stamina_retreat.py` (4/4 通過)
     - `tests/test_daily_pipeline_orchestration.py` (29/29 通過)
     - `tests/test_behavior_main_entrypoint.py` (15/15 通過)
     - `tests/test_behavior_runtime_config_refresh.py` (9/9 通過)
     - `tests/test_main_config.py` (9/9 通過)
     - `tests/test_behavior_dungeon_scenarios.py` (7/7 通過)
     - `tests/test_behavior_navigation.py` (16/16 通過)

5. **封裝領域目錄服務與消除重複手寫邏輯 (Domain Catalog & Code Integrity)**：
   - 建立 [utils/dungeon_catalog.py](../../utils/dungeon_catalog.py)，提供 `DungeonCatalog` 與不可變資料契約 `DungeonCooldownReport`。
   - 集中提供 1-based 名稱/模板查詢（`get_name`、`get_entry_template`）、路徑逆向解析（`resolve_index_from_nav_path`）與冷卻狀態報表格式化（`format_cooldown_report`）。
   - 修復 `states/handlers/navigation.py` 的 `IndexError` 與 `states/state_machine.py` 的 `ValueError`（越界崩潰點）。
   - 新增 `tests/test_dungeon_catalog.py` (9 項測試 100% 通過)。
   - 更新 `test_behavior_dungeon_cards.py`、`test_behavior_dungeon_state_machine.py` 與 `test_behavior_pause_resume.py` 測試套件，消除舊 0-based 遺留夾具與超時競爭。

---

### 3. Result (結果)
- **單元測試全數綠燈通過**，包含新增之 `test_dungeon_catalog.py` 與修復之 `test_behavior_dungeon_cards.py`、`test_behavior_dungeon_state_machine.py` 等。
- 專案程式碼與設定檔中徹底清除了數十處 `+ 1` / `- 1` 的 Off-by-one 轉換 gymnastics 與手寫重複迴圈。
- 使用者設定檔中 `max_stage = 6` 與 `max_dungeon = 6` 語意高度統一，徹底符合直覺。

---

### 4. So What (核心價值)
- **消除致命隱患**：排除了因地下城 0-based 與 1-based 混用導致冷卻檢查失效或點擊錯誤卡片的潛在死結。
- **大幅降低認知負荷**：無論是開發者編寫新 State Handler、撰寫測試，還是玩家透過 CLI / TOML 進行配置，所有關卡與地下城均遵循統一的 `1 ~ 6` 數學模型。

---

### 5. Influence (影響)
本次重構確立了專案領域實體索引的「全域 1-based 規範」。後續即將實作之黃金古國（第 7 關卡）、首領討伐編號或更高階活動，均嚴格遵守 1-based 實體設計，嚴禁在業務邏輯層引入任何 0-indexed 混雜。
