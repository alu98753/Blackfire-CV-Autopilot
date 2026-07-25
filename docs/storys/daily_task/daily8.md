現在我這個分之 想要做每天8點05 要自己去做的任務( 假設在collect only , 或戰鬥 任何情況都要跳轉 戰鬥的話舊等戰鬥結束後

然後要有config 判斷今天領了沒(每個子任務都設定 因為可能有些可以一次做完 有些不行) 避免腳本每次開的時候都重新判斷
具體而言 每天早上8:05 把config 重製為false, 然後每天8:05 trigger他

以下是要做的事情 接著 因為某些圖片還沒辦法截圖 所以 先暫時把大家的功能做個半成品出來

1. 開寶箱 (神秘寶箱 `chest`)
   - **城鎮自動導航**：若處於大廳等非城鎮畫面，自動比對並點擊 `goback_town.png` 退回城鎮。
   - **寶箱比對與領取**：於城鎮掃描並點擊 `town_building/mysterious_treasure/mysterious_treasure.png`；若有確認彈窗自動點擊領取。
   - **狀態持久化與 08:05 重置**：透過 `DailyManager` 記錄 `chest` 的 `completed_today = True`（於 `user_data/daily_status.json` 中保存），每日 08:05 自動重置。
   - **連動佇列**：完成領取後自動呼叫 `pop_and_next_town_subflow()` 續行下一個城鎮任務。

2. 抽英雄 (酒館免費招募 `hero_draw`)
   - **進入酒館**：於城鎮掃描並點擊 `town_building/Tavern/Tavern.png` 進入酒館。
   - **免費招募**：進入酒館後比對並點擊 `town_building/Tavern/free_recruitment.png` 進行免費招募。
   - **領取與退出**：點擊 `common/confirm.png` / `common/ok.png` 確認領取 ➔ 點擊 `common/quit.png` / `exitfromhouse_and_to_town.png` 退出酒館。
   - **狀態持久化與 08:05 重置**：透過 `DailyManager` 記錄 `hero_draw` 的 `completed_today = True`，每日 08:05 自動重置。
   - **連動佇列**：招募完成後自動呼叫 `pop_and_next_town_subflow()` 續行下一個城鎮任務。

3. 領血
[Blood_Altar.png](file;file:///e%3A/Side_Project/BlackfireCrusade_tool/templates/town_building/Blood_Altar/Blood_Altar.png) 

[receive.png](file;file:///e%3A/Side_Project/BlackfireCrusade_tool/templates/town_building/Blood_Altar/receive.png) 


4. 領任務 (每日懸賞告示牌自動化與動態排程)
   - **詳細架構報告與研究**：參見 [daily_task_architecture_report.md](file:///e:/Side_Project/BlackfireCrusade_tool/docs/storys/daily_task/daily_task_architecture_report.md)
   - **懸賞任務模板圖片**：[templates/town_building/bulletin_board/Daily_task/](file:///e:/Side_Project/BlackfireCrusade_tool/templates/town_building/bulletin_board/Daily_task/)


===

5. 打boss (首領領主討伐)
   - **規則與冷卻**：每個 Boss 每日上限 5 次，戰鬥完成後寫入獨立 CD（08:05 自動清零）。
     - **古代惡靈伊瑟倫** (`lord_spectre`): 冷卻時間 2 小時 (7200 秒)。
     - **育母蜘蛛麗拉西亞** (`lord_spider`): 冷卻時間 1 小時 (3600 秒)。
   - **討伐優先權策略**：依 CD 秒數降序排序 ($7200s > 3600s$)，系統優先鎖定挑戰難度更高、CD 更長的 Boss，匹配並點擊後立刻 `break` 鎖定。
   - **極致省電 08:05 重置**：進度與時間戳紀錄於 `user_data/daily_status.json`（已 gitignore 隔離）。主迴圈具備 60 秒限流與浮點數時間戳預算，對 CPU/電量 0 負擔。
   - **UI 頁籤與原模式自動回歸**：採用 `match_mutually_exclusive_tabs` 比對 `load/Lord_entry_after.png`；討伐完畢自動恢復 `primary_config` 回歸原模式 (`mix` / `stage` / `dungeon` / `collect_only`) 繼續刷怪。

---

## 🏛️ 架構設計與 Dev 階段獨立測試方案 (Architecture Design)

### 1. 痛點解法：雙層觸發設計 (Two-Tier Trigger Architecture)
為避免 CLI `--mode` 爆炸（原本每個小功能都加一個 `--mode`），我們將模式解耦為兩層：

- **主運作模式 (Primary Modes)**：保持極簡乾淨，只保留代表長途掛機行為的 4 個主模式（`mix`, `dungeon`, `stage`, `collect_only`）。
- **子流程測試旗標 (`--subflow`)**：專為 **Dev 開發與單體測試** 設計！允許開發者在命令列直接呼叫單個或多個子流程，無需為每個子功能新增獨立的 `--mode`。

#### Dev 階段 CLI 獨立測試指令 (單獨測試小功能)：
```bash
# 獨立測試：開寶箱
python main.py --backend --subflow chest

# 獨立測試：抽英雄
python main.py --backend --subflow hero_draw

# 獨立測試：領血
python main.py --backend --subflow blood_altar

# 獨立測試：領懸賞任務
python main.py --backend --subflow bounty

# 獨立測試：打 Boss (預設輪巡所有獨立 Boss)
python main.py --backend --subflow lord_boss

# 獨立測試：指定單獨打「育母蜘蛛」
python main.py --backend --subflow lord_boss:lord_spider

# 組合測試：一次測試開寶箱 + 領血 + 打 Boss
python main.py --backend --subflow chest blood_altar lord_boss
```

#### Prod 長掛機階段 (自動化排程)：
主模式 (如 `mix`) 正常運行，在每隔幾分鐘回到城鎮時，自動由 `DailyManager` 檢查 `daily_status.json`：
- 若跨過 08:30，自動重置今日所有 Boss 與 Daily 子任務狀態。
- 若有任何 Boss CD 滿 2hr 且 `today_count < 5`，自動注入相應的 Boss 討伐任務至城鎮佇列！

---

### 2. 狀態持久化 JSON 結構 (`user_data/daily_status.json`)
```json
{
  "last_daily_reset_date": "2026-07-25",
  "subflows": {
    "chest": { "completed_today": true, "last_executed_at": "2026-07-25 08:31:00" },
    "hero_draw": { "completed_today": true, "last_executed_at": "2026-07-25 08:32:00" },
    "blood_altar": { "completed_today": true, "last_executed_at": "2026-07-25 08:33:00" },
    "bounty": { "completed_today": true, "last_executed_at": "2026-07-25 08:34:00" },
    "lord_boss": {
      "completed_today": false,
      "bosses": {
        "lord_spider": {
          "name": "育母蜘蛛麗拉西亞",
          "today_count": 2,
          "max_daily_count": 5,
          "cooldown_seconds": 7200,
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

### 3. Clean Code `config.py` 分層重構方案

在 `config.py` 中，依據 SRP (單一職責原則) 與 職責分離原則，將原本全平鋪的 `GAME_CONFIGS` 分為兩層配置：

```python
# 1. 主掛機大局模式 (PRIMARY_MODES - 僅限 4 個)
PRIMARY_MODES = {
    "mix": { ... },
    "dungeon": { ... },
    "stage": { ... },
    "collect_only": { ... }
}

# 2. 城鎮子流程獨立配置 (SUBFLOW_CONFIGS - 可供 Dev 單體測試或日常觸發)
SUBFLOW_CONFIGS = {
    "bag_clean": { ... },
    "blood_altar": { ... },
    "jewelry_workshop": { ... },
    "chest": { ... },
    "hero_draw": { ... },
    "bounty": { ... },
    "lord_boss": { ... }
}

# 3. 向後相容全域匯出 (GAME_CONFIGS)
GAME_CONFIGS = {**PRIMARY_MODES, **SUBFLOW_CONFIGS}
```

#### CLI 參數解析對應 (`main.py`)：
- `--mode`: `choices=list(PRIMARY_MODES.keys())`（用戶在命令列幫助中只會看到 4 個乾淨的主模式）。
- `--subflow`: `nargs="+", choices=list(SUBFLOW_CONFIGS.keys())`（Dev 測試時可帶一個或多個子流程名稱，直接發起單體測試）。