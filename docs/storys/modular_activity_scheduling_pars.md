# 🏛️ 模組化遊戲模式與基底待機調度重構開發故事 (PARS Framework)

> 本故事記錄掛機系統如何將死板互斥的模式調度，重構為「以 `COLLECT_ONLY` 為基底待機、自由疊加啟用週期性任務 (Boss / 地下城 / 城鎮日常)、並將普通關卡打怪解耦為可選模組」之高彈性架構。

---

## 🎯 一、Purpose (目的與痛點)

### 1. 歷史痛點
* **模式僵化綁定**：過去若選擇 `collect_only` (純定時領取)，即使 Boss (首領討伐) 或地下城冷卻結束，腳本也永遠不會去打；而若選擇 `mix` 或 `daily`，當地下城或 Boss 冷卻時，系統會強制 Fallback 前往普通關卡 (如 6-1)「一般打怪」，將所有體力全部耗光。
* **無法滿足「養老打王」或「週期高收益」需求**：使用者希望「平時在城鎮待機領體/鑽，Boss 好了就去打 Boss，地下城好了就去刷地下城，但**絕對不要去打小怪浪費體力**」，過去架構無法支援此組合。

### 2. 核心目標
* **基底化待機 (Collect Only Baseline)**：將定時領鑽/體力與城鎮待機作為系統最低優先級的基底守護狀態。
* **可選週期性任務 (Enableable Activities)**：首領討伐 (`enable_lord_boss`)、地下城 (`enable_dungeon`)、城鎮日常 (`enable_town_daily`) 可自由勾選啟用。
* **打怪開關獨立 (`enable_stage_farming`)**：普通關卡打怪僅在使用者明確開啟時才執行，預設關閉以保護體力。

---

## 🛠️ 二、Action (行動與核心架構實作)

### 1. 全域配置規範化與活動開關矩陣 ([config.py](../config.py))
在中央配置中定義 `DEFAULT_ACTIVITIES`，並透過 `normalize_config` 注入所有模式配置：
```python
DEFAULT_ACTIVITIES = {
    "auto_diamond": True,          # 內建定時領鑽石
    "auto_bread": True,            # 內建定時領體力
    "enable_lord_boss": True,      # 啟用首領領主討伐 (lord_boss)
    "enable_dungeon": True,        # 啟用地下城探索 (dungeon)
    "enable_town_daily": True,     # 啟用每日城鎮速領 (chest, hero, altar, jewelry)
    "enable_quests": False,        # 啟用懸賞告示牌與動態任務
    "enable_stage_farming": False, # 是否在週期性任務冷卻時去刷普通關卡 (預設關閉)
}
```

### 2. 全域活動調度器 ([GameStateMachine](../states/state_machine.py))
實作 `evaluate_next_activity()`，統一掌管活動優先級轉移：
$$\text{城鎮日常 (Tier 1)} \rightarrow \text{首領 Boss (Tier 2)} \rightarrow \text{地下城 (Tier 3)} \rightarrow \text{普通關卡打怪 (若啟用)} \rightarrow \mathbf{COLLECT\_ONLY\ 待機 (Tier 0)}$$

### 3. 主動式待機巡邏與喚醒機制 ([CollectOnlyHandler](../states/handlers/collect_only.py))
在待機期間除了定時領體/鑽外，加入週期性活動冷卻監聽：
- 若 `enable_lord_boss` 且 `has_available_lord_boss()` $\rightarrow$ 自動喚醒並發起 Boss 討伐。
- 若 `enable_dungeon` 且 `has_available_dungeon()` $\rightarrow$ 自動喚醒並轉移至 `STATE_NAVIGATING` 前往地下城。
- 若 `enable_town_daily` 且有待完成城鎮任務 $\rightarrow$ 自動喚醒並發起城鎮佇列。

### 4. 導航與大廳處理器退避適配 ([NavigationHandler](../states/handlers/navigation.py), [LobbyHandler](../states/handlers/lobby.py))
- 當地下城全冷卻時，若 `enable_stage_farming == False`，點擊 `goback_town.png` 返回城鎮並轉入 `STATE_COLLECT_ONLY` 待機，不再強制切換關卡頁籤。

### 5. CLI 與互動選單介面 ([main.py](../main.py))
- 新增 `--boss` / `--no-boss`、`--dungeon` / `--no-dungeon`、`--stage` / `--no-stage` 等模組化參數，並提供直觀的啟動問答推薦。

---

## 📊 三、Result (成效與驗證)

1. **全新行為測試集全綠通過**：
   * 建立獨立測試檔 [test_behavior_modular_activities.py](../tests/test_behavior_modular_activities.py)，5 大真實場景 100% 通過：
     * `test_scenario_1_pure_collect_only_no_periodic_triggers` (純領取養老)
     * `test_scenario_2_boss_and_collect_only_lifecycle` (Boss + 待機喚醒)
     * `test_scenario_3_dungeon_and_boss_cooldown_to_collect_only_and_wake_up` (地下城 + Boss + 待機喚醒)
     * `test_scenario_4_full_auto_with_stage_farming_fallback` (全自動推圖)
     * `test_scenario_5_daily_reset_awakening_in_collect_only` (08:05 跨日喚醒)
2. **全域無 Regression**：所有關聯模組行為測試與全域測試 100% 綠燈。

---

## 💡 四、So What (價值與效益)

1. **體力精準控管**：不再被迫消耗體力於非必要的普通關卡，可將體力完全保留給高回報活動或特定刷裝時段。
2. **架構擴充性大增**：未來若有新週期性活動（如限時活動、公會 Boss 等），只需在調度器中新增單一判斷條件，即可自動獲得待機與喚醒能力。

---

## 🌐 五、Influence (影響範圍)

* **核心模組**：`config.py`, `main.py`, `states/state_machine.py`, `states/handlers/collect_only.py`, `states/handlers/navigation.py`, `states/handlers/lobby.py`
* **規格文件**：`docs/mix_mode_architecture.md`, `README.md`
* **測試檔案**：`tests/test_behavior_modular_activities.py`, `tests/test_daily_pipeline_orchestration.py`, `tests/test_behavior_dungeon_cards.py`
