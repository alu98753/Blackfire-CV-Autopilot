# 📜 懸賞任務與 CLI 指令一對一對照分析報告 (最新修正版)

本報告詳細記錄懸賞任務映射系統的對照規則與處理架構。
- 核心對照程式碼：[utils/quest_mapper.py](file:///e:/Side_Project/BlackfireCrusade_tool/utils/quest_mapper.py#L84)
- 日常狀態管理員：[utils/daily_manager.py](file:///e:/Side_Project/BlackfireCrusade_tool/utils/daily_manager.py#L300)
- 硬碟持久化檔案：[user_data/daily_status.json](file:///e:/Side_Project/BlackfireCrusade_tool/user_data/daily_status.json)
- 全域 AI 行為規範：[.agents/AGENTS.md](file:///e:/Side_Project/BlackfireCrusade_tool/.agents/AGENTS.md#L45)


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

### 3. 🚫 顯式忽略/跳過執行的任務 (`IGNORED_QUESTS`)
- **機制**：使用者指示不打的任務。告示牌掃描時直接跳過不接取，不上報至 `unknown_quests`，亦不加入 `accepted_quests` JSON 佇列。
- **完整任務名稱清單**：
  1. `"獵金之蟲"`
  2. `"完成任何地下城"`
  3. `"敵人剿滅"`

---


## 🛡️ OCR 錯別字自動加強防護
不論是告示牌讀取還是完成彈窗，輸入的標題均會自動經過 `normalize_quest_title()` 清洗（如 `野瀦`➔`野豬`、`毀減`➔`毀滅`、`肇敗`➔`擊敗`、`枯樓`➔`骷髏`），確保精確命中上述字典。


## 🔍 未來發現 unknown_quests 時的檢查與處理 SOP
📌 具體三種處置方式：
情況 A：要打的新任務 開啟 

utils/quest_mapper.py
：
若打地下城 ➔ 加入 self.dungeon_rules（指定 0~4 索引）。
若打普通關卡 ➔ 加入 self.stage_rules（指定 1~6 等級與 first/middle/final 子關卡）。
情況 B：不要打的任務（如敵人剿滅、獵金之蟲） 開啟 

utils/quest_mapper.py
：
加入 self.ignored_rules 正則匹配，系統會識別為 ignored 模式，直接跳過不接取，且不上報 unknown_quests。
情況 C：EasyOCR 錯別字誤判（如 野猾 ➔ 野豬） 開啟 

utils/quest_mapper.py
：
加入 OCR_TYPO_MAP 對照字典，自動清洗為標準繁體字。