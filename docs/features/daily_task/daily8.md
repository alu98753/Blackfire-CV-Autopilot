# Daily 8: 每日任務自動化與 08:05 定時觸發架構 📋

## 🎯 核心宗旨與設計目標

1. **每日主模式 (`--mode daily`) 全自動四階梯流水線**：
   - 使用 `python main.py --mode daily` 作為全自動日常掛機的唯一主入口。
   - 啟動後由 `Daily Master Pipeline` 全自動依照動態優先級連貫執行：城鎮速領 ➔ 領主 Boss 討伐 ➔ 懸賞任務 ➔ 玩家指定的 Tier 4 長駐模式。

2. **08:05 定時自動觸發與中斷切換**：
   - 每日早上 08:05 由 `DailyManager` 自動觸發日常任務重置與連動。
   - 觸發時無論腳本處於何種狀態（如 `collect_only`、關卡或地下城），均自動切換至城鎮日常佇列；若正處於戰鬥中，則等待該場戰鬥結束（結算完畢退回城鎮/大廳）後搶先插隊切換。

3. **獨立狀態持久化與跳過機制**：
   - 每個日常子任務（包含開寶箱 `chest`、抽英雄 `hero_draw`、領血 `blood_altar`、告示牌 `bulletin_board`、Boss 討伐 `lord_boss`）均維護獨立的完成狀態 (`completed_today`)，並持久化寫入 `user_data/daily_status.json`。
   - 腳本啟動時自動讀取狀態，跳過今日已完成的子任務，避免重複執行。

---

## 📋 全域四階梯優先級與子任務規格 (Master Priority Hierarchy)

```
🥇 Tier 1: 一極優先 (每日一次性城鎮速領)
   👉 chest (寶箱) ➔ hero_draw (抽卡) ➔ blood_altar (祭壇獻祭 + 珠寶賣裝)
   (只要當天 completed_today == False，啟動即優先連貫做完)
                             │
                             ▼
🥈 Tier 2: 二極優先 (領主 Boss 討伐 lord_boss 包含計時器調度)
   👉 優先級 > bulletin_board (懸賞任務)！
   👉 檢查 DailyManager.get_available_lord_bosses() (蜘蛛 1hr / 惡靈 2hr CD, 5 次上限，每次戰鬥需 5 點體力/麵包)
   👉 只要有 Boss CD 結束且今日場次 < 5 次 ➔ 戰鬥結束回到大廳時發起討伐（體力不足 5 點時將轉入 collect_only 待機領體力）！
                             │
                             ▼
🥉 Tier 3: 三極優先 (懸賞告示牌與動態任務 bulletin_board)
   👉 告示牌取卡與 accepted_quests 多階梯排序 (地下城懸賞優先 ➔ 關卡懸賞 ➔ 確定性/Level大者優先)
   👉 依據 QuestScheduler 產出最高優先懸賞目標 (破除森林的枷鎖/清除骷髏/蛙人...)
   ⚡ 戰鬥途中若 Tier 2 Boss 冷卻結束 ➔ 打完該場戰鬥後立刻搶先切回打 Boss！
                             │
                             ▼
🎖️ Tier 4: 四極長駐 (玩家可選 stage / domain，預設: 冰凍峽谷 6-1)
   👉 地下城與 Lord 屬於定時活動，預設啟用並在就緒時插隊；可由 Profile TOML 個別停用。
   👉 stage 子選單選擇大關與小關；domain 子選單目前支援黃金古國。
   👉 CLI 選擇持久化至 user_data/<profile>/config.toml，native / sandbox / 其他帳號互不影響。

   ⚡ 刷關期間若 Tier 2 Boss 冷卻結束 ➔ 自動切回打 Boss！
```

---

## 📋 子任務執行詳細規格

1. **開寶箱 (神秘寶箱 `chest`)**
   - **城鎮自動導航**：若處於大廳等非城鎮畫面，自動點擊 `goback_town.png` 退回城鎮。
   - **寶箱比對與領取**：於城鎮掃描並點擊 `town_building/mysterious_treasure/mysterious_treasure.png` 領取。
   - **狀態持久化**：透過 `DailyManager` 記錄 `chest` 的 `completed_today = True`（於 `user_data/daily_status.json` 中保存），每日 08:05 自動重置。

2. **抽英雄 (酒館免費招募 `hero_draw`)**
   - **進入酒館與招募**：於城鎮點擊 `town_building/Tavern/Tavern.png` 進入，點擊 `free_recruitment.png` 免費招募。
   - **領取與退出**：確認領取後點擊退出返回城鎮，紀錄 `hero_draw` 的 `completed_today = True`。

3. **領血與獻祭 (血之祭壇 `blood_altar` & 珠寶賣裝 `jewelry_workshop`)**
   - **領水與賣裝連鎖**：進入血之祭壇點擊每日免費領血 ➔ 完成後自動連帶執行 `jewelry_workshop` (珠寶加工廠出售)。
   - **狀態持久化**：紀錄 `blood_altar` 的 `completed_today = True`。

4. **領任務 (每日懸賞告示牌 `bulletin_board`)**
   - **告示牌點擊與相對優勢過濾**：於城鎮點擊告示牌，相對比對 `task_after.png` 自動過濾已接任務。
   - **EasyOCR 解析與接取**：EasyOCR 繁中/英文解析任務標題，自動寫入 `accepted_quests` 並由 `QuestScheduler` 動態排程。

5. **打 Boss (首領領主討伐 `lord_boss`)**
   - **CD 與計時器維護**：古代惡靈 (`lord_spectre`, 2hr CD) / 育母蜘蛛 (`lord_spider`, 1hr CD)，每日上限各 5 次。
   - **即時搶先插隊**：優先級大於懸賞任務與退守刷關。任何戰鬥結束回到大廳時，若 Boss 冷卻到期，立刻搶先切回討伐 Boss。

---

## 🏛️ CLI 運作模式與 Dev 獨立測試方案

### 1. 正式生產主模式 (`--mode daily`) 🚀
**日常長途掛機運作唯一主入口**。啟動後由 Daily Master Pipeline 全自動運作：
```bash
python main.py --backend --mode daily
```

啟動時會先顯示 Tier 4 模式選單，再進入 `stage` 或 `domain` 子選單。對應的玩家設定範例如下：

```toml
[primary_modes.daily]
enable_dungeon = true
enable_lord_boss = true
tier4_mode = "stage" # 或 "domain"
tier4_domain = "golden_empire"
tier4_stage_level = 6
tier4_sub_stage = "first"
```

---

### 2. Dev 階段獨立測試指令 (`--subflow`) 🧪
**`--subflow` 僅供開發與單體測試獨立模組使用**，不作為日常長掛機模式：

```bash
# 獨立測試：開寶箱
python main.py --backend --subflow chest

# 獨立測試：抽英雄
python main.py --backend --subflow hero_draw

# 獨立測試：領血
python main.py --backend --subflow blood_altar

# 獨立測試：領懸賞任務
python main.py --backend --subflow bulletin_board

# 獨立測試：打 Boss (預設輪巡所有可用 Boss)
python main.py --backend --subflow lord_boss

# 組合測試：獨立測試開寶箱 + 領血 + 珠寶賣裝
python main.py --backend --subflow chest blood_altar jewelry_workshop
```

---

### 3. 狀態持久化 JSON 結構 (`user_data/daily_status.json`)
```json
{
  "last_daily_reset_date": "2026-07-25",
  "subflows": {
    "chest": { "completed_today": true, "last_executed_at": "2026-07-25 08:31:00" },
    "hero_draw": { "completed_today": true, "last_executed_at": "2026-07-25 08:32:00" },
    "blood_altar": { "completed_today": true, "last_executed_at": "2026-07-25 08:33:00" },
    "bulletin_board": { "completed_today": true, "last_executed_at": "2026-07-25 08:34:00" },
    "lord_boss": {
      "completed_today": false,
      "bosses": {
        "lord_spider": {
          "name": "育母蜘蛛麗拉西亞",
          "today_count": 2,
          "max_daily_count": 5,
          "cooldown_seconds": 3600,
          "last_fight_timestamp": 1784920000,
          "completed_today": false
        },
        "lord_spectre": {
          "name": "古代惡靈伊瑟倫",
          "today_count": 0,
          "max_daily_count": 5,
          "cooldown_seconds": 7200,
          "last_fight_timestamp": 0,
          "completed_today": false
        }
      }
    }
  }
}
```

---

### 4. Clean Code `config.py` 配置架構

```python
# 1. 主掛機大局模式 (PRIMARY_MODES)
PRIMARY_MODES = {
    "daily": { "name": "每日懸賞任務 (Daily Master Pipeline)", "type": "mix", ... },
    "mix": { ... },
    "dungeon": { ... },
    "stage": { ... },
    "collect_only": { ... }
}

# 2. 城鎮子流程獨立配置 (SUBFLOW_CONFIGS - 僅供 Dev 單體測試)
SUBFLOW_CONFIGS = {
    "bag_clean": { ... },
    "blood_altar": { ... },
    "jewelry_workshop": { ... },
    "chest": { ... },
    "hero_draw": { ... },
    "bulletin_board": { ... },
    "lord_boss": { ... }
}

# 3. 向後相容全域匯出
GAME_CONFIGS = {**PRIMARY_MODES, **SUBFLOW_CONFIGS}
```
