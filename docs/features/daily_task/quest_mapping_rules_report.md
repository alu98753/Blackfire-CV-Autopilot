# 📜 懸賞任務與 CLI 指令一對一對照分析報告 (最新修正版)

本報告詳細記錄懸賞任務映射系統的對照規則與處理架構。
- 核心對照程式碼：[utils/quest_mapper.py](../../../utils/quest_mapper.py#L84)
- 日常狀態管理員：[utils/daily_manager.py](../../../utils/daily_manager.py#L300)
- 硬碟持久化檔案：[user_data/daily_status.json](../../../user_data/native/daily_status.json)
- 全域 AI 行為規範：[.agents/AGENTS.md](../../../.agents/AGENTS.md#L45)


---

## 📋 三大懸賞任務全名與計數策略對照清單 (`counting_policy`)

### 1. ✅ 確定性可計數任務 (`DETERMINISTIC_QUESTS`)
- **機制**：通關或擊殺 100% 必然累加進度。允許 `record_kill_event()` 在記憶體中自動算次數，達標即停止重複派發。
- **完整任務名稱清單**：
  1. `"清除沙蟲"` ➔ 普通關卡 Level 4 middle (沙漠廢墟 中間關)
  2. `"清除蛙人"` ➔ 普通關卡 Level 5 first (幽暗沼澤 第一關)
  3. `"清除骷髏"` ➔ 地下城 #4 【神秘遺跡】 (Ruins)
  4. `"清除史萊姆"` ➔ 地下城 #1 【黏糊糊的石窟】 (Slime)
  5. `"清除樹人"` ➔ 地下城 #3 【森林迷宮】 (Forest)

### 2. ❓ 僅彈窗/告示牌核銷任務 (`BANNER_VERIFY_QUESTS`)
- **機制**：Boss 隨機刷新或完成條件不透明。**絕對禁止**背景自動累加記憶體進度。唯有畫面跳出 `task_complete.png` 領獎彈窗（EasyOCR 辨識）或告示牌點擊 `task_after.png` 綠色勾勾時方可核銷剔除。
- **完整任務名稱清單**：
  1. `"冰雪洞窟的暴君"` ➔ 地下城 #5 【冰雪洞窟】 (Ice)
  2. `"史萊姆王的毀滅"` ➔ 地下城 #1 【黏糊糊的石窟】 (Slime)
  3. `"破除森林的枷鎖"` ➔ 地下城 #3 【森林迷宮】 (Forest)
  4. `"雪山詛咒"` ➔ 地下城 #5 【冰雪洞窟】 (Ice)

### 3. 🚫 顯式忽略/跳過執行的任務 (`IGNORED_QUESTS`)
- **機制**：使用者指示不打的任務。告示牌掃描時直接跳過不接取，不上報至 `unknown_quests`，亦不加入 `accepted_quests` JSON 佇列。
- **完整任務名稱清單**：
  1. `"獵金之蟲"`
  2. `"完成任何地下城"`
  3. `"敵人剿滅"`

---

## 🧮 懸賞任務多階梯優先級排序與自動持久化機制 (`sort_quests` & Persistence)

在 [utils/quest_mapper.py](../../../utils/quest_mapper.py#L145) 的 `QuestMapper` 中實作了 `sort_quests(quest_titles)` 方法，並於 [utils/daily_manager.py](../../../utils/daily_manager.py#L279) 的 `update_bulletin_board_quests()` 中自動調用。

### 1. 🥇 多階梯排序優先級規則 (Sorting Hierarchy)
當告示牌接取任務或更新佇列時，任務會依照四元組 Key `(policy_score, mode_score, idx_score, sub_score)` 進行排序：

- **第一梯隊：確定性優先 (`policy_score`)**
  `DETERMINISTIC_QUESTS` (確定性可計數) ➔ **最優先 (0)** > `BANNER_VERIFY_QUESTS` (僅憑彈窗核銷) ➔ **次之 (1)**
- **第二梯隊：模式優先 (`mode_score`)**
  `dungeon` (地下城) ➔ **優先 (0)** > `stage` (普通關卡) ➔ **次之 (1)** > `generic_boss` (通用 Boss) ➔ **(2)**
- **第三梯隊：索引與等級大者優先 (`idx_score`)**
  - **地下城 (`dungeon_index`)**：`index` 大者優先 (`dungeon 4 (冰雪洞窟)` > `dungeon 3 (神秘遺跡)` > `dungeon 2 (森林迷宮)` > `dungeon 1` > `dungeon 0 (黏糊糊的石窟)`).
  - **普通關卡 (`stage_level`)**：`level` 大者優先 (`Level 6 (冰凍峽谷)` > `Level 5 (幽暗沼澤)` > `Level 4 (沙漠廢墟)` > `Level 3` > `Level 1`).
  - **子關卡類型**：`final` (魔王關) > `middle` (中間關) > `first` (第一關).

---

### 2. 📋 排序示範與 JSON 硬碟寫入樣貌

當告示牌抓取到隨機任務佇列時，寫入 [user_data/daily_status.json](../../../user_data/native/daily_status.json) 的 `accepted_quests` 實際呈現順序為：

```json
"accepted_quests": [
  "清除骷髏",        // 1. DETERMINISTIC, 地下城 #4 (神秘遺跡)
  "清除樹人",        // 2. DETERMINISTIC, 地下城 #3 (森林迷宮)
  "清除史萊姆",      // 3. DETERMINISTIC, 地下城 #1 (黏糊糊的石窟)
  "清除蛙人",        // 4. DETERMINISTIC, 關卡 Level 5 (幽暗沼澤 第一關)
  "清除沙蟲",        // 5. DETERMINISTIC, 關卡 Level 4 (沙漠廢墟 中間關)
  "冰雪洞窟的暴君",  // 6. BANNER_VERIFY, 地下城 #5 (冰雪洞窟)
  "破除森林的枷鎖",  // 7. BANNER_VERIFY, 地下城 #3 (森林迷宮)
  "史萊姆王的毀滅"   // 8. BANNER_VERIFY, 地下城 #1 (黏糊糊的石窟)
]
```

*(註：`獵金之蟲`、`完成任何地下城` 與 `敵人剿滅` 命中 `IGNORED_QUESTS`，在排序寫入前已被自動剔除)*

---

## 🛡️ OCR 錯別字對照與 3-in-1 自動正名校正管道

為了解決 EasyOCR 將遊戲簡體/繁體字寫讀錯的問題（如 `野猾` ➔ `野豬`），系統在 [utils/quest_mapper.py](../../../utils/quest_mapper.py#L41) 採用了 **`TYPO_GROUPS` 結構** 與 **三合一自動正名校正管道**：

### 1. 錯字對照表 (`TYPO_GROUPS`)
以正確標準繁體字為 Key，常見 OCR 誤讀錯字清單為 Value：
- `"野豬"` ➔ `["野瀦", "野猾", "野豬"]`
- `"毀滅"` ➔ `["毀減", "毀滅"]`
- `"擊敗"` ➔ `["肇敗", "擎殺", "擊敗"]`
- `"骷髏"` ➔ `["枯樓", "骷樓", "骷髏"]`
- `"首領"` ➔ `["直領", "首領"]`
- `"惡魔"` ➔ `["忠魔", "惡魔"]`
- `"樹人"` ➔ `["樹入", "樹人"]`
- `"蛛後"` ➔ `["蛛俊", "蛛後"]`

### 2. 三合一自動正名校正管道 (`auto_correct_quest_title`)
當 EasyOCR 讀取標題文字後，會依序通過以下三道過濾防線：
1. **字典反向映射 (1.0 權重)**：查詢 `TYPO_GROUPS`，精確命中錯字直接正名。
2. **`difflib` 編輯距離 (2.0 權重)**：計算字串相似度（Cutoff ≥ 0.65）。
3. **筆畫與子字串比對 (2.5 權重)**：比對特有專有名詞與子字串，防止未知新任務誤判。

### 3. 告示牌灰色已接取任務 (`task_after.png`) 灰度比防誤殺
在 [bulletin_board.py](../../../states/handlers/bulletin_board.py#L195) 中，除了模板比對外，額外計算 ROI 灰度比 `ratio_after <= 0.88`：
- **灰度比 ≤ 0.88** ➔ 判定為灰色已接取任務 (`task_after.png`)，予以過濾。
- **鮮黃色區域 (灰度比 > 0.88)** ➔ 判定為待接取任務 (`task.png`)，方可進行點擊接取。


## 🔍 未來發現 unknown_quests 時的檢查與處理 SOP
📌 具體三種處置方式：
1. **情況 A：要打的新任務**
   開啟 [utils/quest_mapper.py](../../../utils/quest_mapper.py#L84)：
   - 若為確定性通關/擊殺 ➔ 加入 `DETERMINISTIC_QUESTS` 全名清單。
   - 若為不確定隨機 Boss ➔ 加入 `BANNER_VERIFY_QUESTS` 全名清單。
   - 若打地下城 ➔ 加入 `self.dungeon_rules`（指定 0~4 索引）。
   - 若打普通關卡 ➔ 加入 `self.stage_rules`（指定 1~6 等級與 `first/middle/final` 子關卡）。
2. **情況 B：不要打的任務**（如`敵人剿滅`、`獵金之蟲`、`完成任何地下城`）
   開啟 [utils/quest_mapper.py](../../../utils/quest_mapper.py#L86)：
   - 加入 `IGNORED_QUESTS` 全名清單與 `self.ignored_rules` 正則匹配，系統會識別為 `ignored` 模式，直接跳過不接取，且**不上報 `unknown_quests`**。
3. **情況 C：EasyOCR 錯別字誤判**（如 `直領` ➔ `首領`）
   開啟 [utils/quest_mapper.py](../../../utils/quest_mapper.py#L41)：
   - 於 `TYPO_GROUPS` 的 Key 下補充對應的 OCR 錯別字，系統自動進行清洗與正名。