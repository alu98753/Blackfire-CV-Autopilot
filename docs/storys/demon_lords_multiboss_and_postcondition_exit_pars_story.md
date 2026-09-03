# PARS Story: 深淵魔王多 Boss 清單循序調度、插槽無反應判定與優雅導航退出

## Purpose
深淵魔王 (Demon Lords) 挑戰先前僅支援單一固定 Boss (`target_boss = "voidborn_elres"`)，且在次數耗盡或已打完時，缺乏明確的後置條件 (Postcondition) 判定，容易在準備彈窗中反覆點擊空插槽。此外，戰鬥勝利過場中的經驗值繼續按鈕曾與地下城恢復錨點發生相似度衝突，導致狀態機誤判並劫持至地下城探索狀態。

本重構目的在於：
1. 將深淵魔王升級為多 Boss 清單 (`targets = ["boss_key", ...]`) 循序調度架構，與 `lord_boss` 統一規範。
2. 依據 Greenfield-lite v1 架構標準，為空插槽點擊建立明確的 Postcondition（開彈窗 / 出現 `choose.png`）與有界重試上限（2 次），確鑿判定次數耗盡並點擊 `quit.png` 優雅關閉彈窗，返回卡片介面切換下一隻魔王或退回流水線自由導航（Town / Stage / Dungeon）。
3. 根除戰鬥勝利畫面誤觸地下城恢復錨點之轉移劫持問題。

## Action
1. **多 Boss 持久化結構與排程 API**：
   - 在 [defaults.toml](../../config/defaults.toml) 中配置 `targets = ["voidborn_elres"]` 陣列。
   - 在 [daily_manager.py](../../utils/daily_manager.py) 中將 `demon_lords` 升級為包含 `bosses` 字典的結構，提供 `_ensure_demon_lords_structure()` 自動遷移相容舊格式。
   - 實作 `get_available_demon_lords()`、`is_demon_lords_available()`、`record_demon_lords_fight()` 與 `mark_demon_lord_completed()`。
2. **Postcondition 核驗與無反應有界退出**：
   - 在 [demon_lords.py](../../states/handlers/demon_lords.py) 中追蹤 `slot_no_reaction_count`。點擊 `slot.png` 後若連續 2 次未能觸發選石視窗，判定當前魔王挑戰次數已耗盡。
   - 觸發退出子流程：標記魔王完成，匹配並點擊 `common/quit.png` 關閉彈窗返回卡片介面。若尚有其他可用魔王則選取下一張，若全部完成則呼叫 `pop_and_next_town_subflow()` 自動流轉至下一任務。
   - 透過簡化感知判定與重構方法，將 `demon_lords.py` 總行數嚴格壓制在 295 行（符合 AGENTS.md 檔案 <= 300 行與單一方法 <= 60 行規範）。
3. **修復戰鬥勝利轉移劫持**：
   - 在 [battle.py](../../states/handlers/battle.py) 中將地下城恢復錨點相似度門檻由 `0.80` 提升至 `0.88`，並加入 `continue1.png` / `continue2.png` 備援。
   - 在 [state_machine.py](../../states/state_machine.py) 中自 `DUNGEON_RECOVERY_FEATURES` 移除 `gungeon_godown_confirm.png`，並在 `has_dungeon_context()` 中排除魔王戰鬥情境。

## Result
1. 深淵魔王支援動態配置多隻魔王並依序討伐，打完一隻自動切換下一隻。
2. 點擊插槽無反應時能在 2 次嘗試後迅速識別，點擊 `quit.png` 關閉彈窗並自動接力推進日常流水線，徹底告別準備介面卡死風險。
3. 戰鬥獲勝後的經驗值與 V 旗幟彈窗皆能 100% 正確匹配 `continue` 按鈕並轉入 `STATE_RESULT`，不再誤跳地下城。
4. 行為測試覆蓋率全綠：
   - `tests.test_demon_lords_subflow` 12 項測試全數通過。
   - `tests.test_daily_pipeline_orchestration` 29 項測試全數通過。

## So What
此變更使深淵魔王完全對齊 Greenfield-lite v1 的「感知與決策分離」以及「所有動作均需後置驗證與有界重試」之核心準則。透過統一的清單式多 Boss 抽象，未來新增深淵魔王只需在 `defaults.toml` 的 `bosses` 與 `targets` 增添設定與卡片範本即可無縫擴展，無須改動任何狀態機或排程程式碼。

## Influence
- 核心調度邏輯維護於 [DemonLordsHandler](../../states/handlers/demon_lords.py)
- 持久化狀態與多 Boss 清單由 [DailyManager](../../utils/daily_manager.py) 管理
- 狀態轉移與 Tier 1.5 排程流轉於 [GameStateMachine](../../states/state_machine.py) 與 [ResultHandler](../../states/handlers/result.py)
- 測試規格鎖定於 [test_demon_lords_subflow.py](../../tests/test_demon_lords_subflow.py) 與 [test_daily_pipeline_orchestration.py](../../tests/test_daily_pipeline_orchestration.py)
