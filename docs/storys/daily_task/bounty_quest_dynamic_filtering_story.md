# PARS 開發故事：懸賞任務動態篩選獨立配置與防誤排機制 🛡️

## 📝 PARS 5 大要素

### 1. Purpose (目的)
在多帳號 (本帳 vs 小帳) 掛機環境中，二號小帳戰力受限（約 1800，隊伍為 3 坦補 + 1 冰法），面對具備 476% 冰抗且每 20 回合自補 50% HP 的第 6 關魔王「霜凍巨獸」或高階地下城首領時必然滅團陷入死循環。
為解決小帳卡關問題，同時因應使用者可能在 `daily_status.json` 中手動調整 `accepted_quests`，必須建立完全獨立的 `[bounty_quests]` 配置表與多時機動態篩選防線，確保任何超標任務絕不被排入執行佇列。

---

### 2. Action (行動)

1. **獨立 TOML 配置與階層覆蓋 (Config Layer)**：
   - 於 [config/defaults.toml](../../../config/defaults.toml) 建立獨立區塊 `[bounty_quests]`，預設天花板為 `max_stage = 6` 與 `max_dungeon = 5`（全內容開放基準）。
   - 在 [config.py](../../../config.py) 加入 `_REQUIRED_DEFAULT_SETTING_PATHS` 強制校驗，導出 `BOUNTY_QUESTS_CONFIG` 與 `get_bounty_quest_config(profile)`。
   - 於二號帳號 `user_data/sandbox/config.toml` 配置 `max_stage = 4`、`max_dungeon = 4`；一號帳號 `user_data/native/config.toml` 配置 `max_stage = 6`、`max_dungeon = 5`，實現多 Profile 獨立隔離。

2. **Greenfield-lite 純判定函式 (Predicate Policy)**：
   - 於 [utils/quest_mapper.py](../../../utils/quest_mapper.py) 實作純函式 `is_quest_allowed(task_node, bounty_config)`，無副作用核驗 `stage_level <= max_stage` 與 `dungeon_index <= max_dungeon`。
   - 擴充 `QuestMapper.sort_quests(quest_titles, bounty_config=None)`，在多階梯排序前自動剔除超標任務。

3. **三時機防禦與磁碟熱重載 (Three-layer Defense & Hot Reload)**：
   - **防禦時機 1（告示牌接取與自癒清洗）**：於 [DailyManager.update_bulletin_board_quests()](../../../utils/daily_manager.py) 及載入清洗時，自動過濾超過上限之新舊任務，杜絕超標任務寫入 `daily_status.json`。
   - **防禦時機 2（磁碟熱重載感知）**：於 `DailyManager` 實作 `reload_status_if_modified()`，秒級偵測使用者手動編輯 JSON 的 `mtime` 變更並自動重新載入，避免過期記憶體快取覆蓋手動變更。
   - **防禦時機 3（排程派發即時門閥）**：於 [QuestScheduler.from_daily_status()](../../../utils/quest_scheduler.py) 與 `get_next_action_node()` 實施雙重過濾，即使存檔留有超標任務也絕不派發進場。

---

### 3. Result (結果)
- **單元測試全數通過**：
  - 新增專屬測試檔 `tests/test_bounty_quest_filtering.py`，7 項測試 100% 綠燈通過。
  - 回歸測試 `tests/test_quest_mapper_and_scheduler.py` (24 項) 與 `tests/test_subflow_and_daily_manager.py` (24 項) 全數通過。
- **實測行為符合預期**：
  - 小帳環境 (`max_stage=4, max_dungeon=4`) 下，「討伐惡魔」(Stage 6) 與「冰雪洞窟的暴君」(Dungeon 5) 成功被過濾，僅排程執行「破除遺跡的詛咒」(Dungeon 3) 與「清除沙蟲」(Stage 4)。
  - 本帳環境 (`max_stage=6, max_dungeon=5`) 完整執行所有 4 個懸賞任務。

---

### 4. So What (核心價值)
徹底解除了小帳在每日懸賞掛機時意外接取或執行無法戰勝的高難度關卡而滅團卡死的痛點，同時賦予使用者手動調配任務清單的自由度與系統安全性。

---

### 5. Influence (影響)
本實作確立了專案中「角色戰力邊界與動態任務調度解耦」的標準模式，未來的各類活動（如領主討伐白名單、魔王挑選）皆可依循此獨立 TOML + 階層覆蓋 + 純函式門閥的架構模式推展。
