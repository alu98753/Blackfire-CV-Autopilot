# 📜 懸賞任務與 CLI 指令一對一對照分析報告 (最新修正版)

本報告詳細記錄懸賞任務映射系統的對照規則與處理架構。
- 核心對照程式碼：[utils/quest_mapper.py](file:///e:/Side_Project/BlackfireCrusade_tool/utils/quest_mapper.py#L84)
- 日常狀態管理員：[utils/daily_manager.py](file:///e:/Side_Project/BlackfireCrusade_tool/utils/daily_manager.py#L300)
- 硬碟持久化檔案：[user_data/daily_status.json](file:///e:/Side_Project/BlackfireCrusade_tool/user_data/daily_status.json)
- 全域 AI 行為規範：[.agents/AGENTS.md](file:///e:/Side_Project/BlackfireCrusade_tool/.agents/AGENTS.md#L45)


---

## 🚫 1. 顯式忽略/跳過執行的任務 (`ignored_rules`)
- **機制**：已剔除不執行的任務（如 `敵人剿滅` 與 `獵金之蟲`）屬於已知且使用者選擇**顯式跳過 (ignored)** 的任務，**絕不上報至 `unknown_quests`**。
- **對照規則**：`self.ignored_rules = [r"(敵人剿滅|獵金之蟲)"]`
- **行為處理**：在告示牌掃描時，解析為 `mode_type = "ignored"` 的 `TaskNode`，直接跳過不安裝至執行佇列，且 `DailyManager.record_unknown_quest()` 亦不會將其寫入 `unknown_quests` 歷史清單。

---

## 🏰 2. 地下城任務字典 (`dungeon_rules`) 一對一對照表

地下城任務內部以 0-indexed 索引 (`0~4`) 表示，對應 `greedy_allowed_indices` 的 `[0, 1, 2, 3, 4]`，轉換成 CLI 指令時自動 `+1` 轉為 `--dungeon 1~5`。

| 懸賞任務名稱 / 關鍵字 | 對應 greedy_allowed_indices | 對應地下城名稱 | 產生的 CLI 自動掛機指令 |
| :--- | :---: | :--- | :--- |
| **`史萊姆王`** (史萊姆王的毀滅)<br>**`史萊姆`** (清除史萊姆)<br>**`黏糊糊的石窟`** | **0** | 地下城 #1<br>【黏糊糊的石窟】 (Slime) | `.venv\Scripts\python main.py --backend --mode dungeon --dungeon 1` |
| **`幽影地穴`**<br>**`鬼魂`** (清除鬼魂) | **1** | 地下城 #2<br>【幽影地穴】 (Ghost) | `.venv\Scripts\python main.py --backend --mode dungeon --dungeon 2` |
| **`破除森林的枷鎖`**<br>**`樹人`** (清除樹人)<br>**`森林迷宮`** | **2** | 地下城 #3<br>【森林迷宮】 (Forest) | `.venv\Scripts\python main.py --backend --mode dungeon --dungeon 3` |
| **`骷髏`** (清除骷髏)<br>**`枯樓`**<br>**`神秘遺跡`** (破除遺跡/遺跡的詛咒) | **3** | 地下城 #4<br>【神秘遺跡】 (Ruins) | `.venv\Scripts\python main.py --backend --mode dungeon --dungeon 4` |
| **`完成任何地下城`**<br>**`冰雪洞窟的暴君`**<br>**`終結寒冰獸王`**<br>**`冰雪洞窟`** | **4** | 地下城 #5<br>【冰雪洞窟】 (Ice) | `.venv\Scripts\python main.py --backend --mode dungeon --dungeon 5` |

---

## ⚔️ 3. 普通關卡怪物字典 (`stage_rules`) 一對一對照表

普通關卡任務會指定大關等級 `--stage 1~6` 與子關卡種類 `--sub first/middle/six/final`。

| 懸賞任務名稱 / 關鍵字 | 關卡等級 (`--stage`) | 子關卡類型 (`--sub`) | 對應普通關卡名稱 | 產生的 CLI 自動掛機指令 |
| :--- | :---: | :---: | :--- | :--- |
| **`野豬`** (清除野豬) | **Level 1** | `final` | 蒼穹平原 (魔王關) | `.venv\Scripts\python main.py --backend --mode stage --stage 1 --sub final` |
| **`熊`** (清除熊) | **Level 3** | `final` | 古樹森林 (魔王關) | `.venv\Scripts\python main.py --backend --mode stage --stage 3 --sub final` |
| **`沙蟲`** (清除沙蟲) | **Level 4** | `middle` | 沙漠廢墟 (中間關) | `.venv\Scripts\python main.py --backend --mode stage --stage 4 --sub middle` |
| **`蛙人`** (清除蛙人) | **Level 5** | `first` | 幽暗沼澤 (第一關) | `.venv\Scripts\python main.py --backend --mode stage --stage 5 --sub first` |
| **`冰元素`** (擊敗冰元素) | **Level 6** | `first` | **冰凍峽谷** (第一關) | `.venv\Scripts\python main.py --backend --mode stage --stage 6 --sub first` |

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