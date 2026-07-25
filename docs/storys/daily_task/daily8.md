# Daily 8: 每日任務自動化與 08:05 定時觸發架構 📋

## 🎯 核心宗旨與設計目標

1. **08:05 定時自動觸發與中斷切換**：
   - 每日早上 08:05 自動觸發日常任務流程。
   - 觸發時無論腳本處於何種模式（如 `collect_only`、關卡或地下城），均自動切換至城鎮日常佇列；若正處於戰鬥中，則等待該場戰鬥結束（結算完畢退回城鎮/大廳）再行切換。

2. **獨立狀態持久化與跳過機制**：
   - 每個日常子任務（包含開寶箱、抽英雄、領血、告示牌、Boss 討伐）均維護獨立的完成狀態 (`completed_today`)，並持久化寫入 `user_data/daily_status.json`。
   - 腳本啟動時自動讀取檔態，跳過今日已完成的子任務，避免重複執行。

3. **08:05 每日重置與連動觸發**：
   - 每日早上 08:05 由 `DailyManager` 自動將所有子任務狀態重置為 `completed_today = False`，並自動觸發城鎮日常連動佇列 (`pop_and_next_town_subflow`)。

---

## 📋 每日子任務與執行規格



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

3. 領血 (血之祭壇 `blood_altar`)
   - **城鎮自動導航與進入**：若處於大廳畫面，優先點擊 `goback_town.png` 退回城鎮；於城鎮中掃描並點擊 `town_building/Blood_Altar/Blood_Altar.png` 進入祭壇。
   - **領水與領取按鈕**：進入建築後點擊領水頁籤 `town_building/Blood_Altar/receive_entry.png` ➔ 點擊每日免費領血按鈕 `town_building/Blood_Altar/receive_daily.png`。
   - **彈窗處理與離場**：連續處理領取與確認彈窗 (`common/confirm.png` / `common/ok.png` / `common/quit.png`)；彈窗關閉後點擊 `town_building/exitfromhouse_and_to_town.png` 返回城鎮。
   - **狀態持久化與 08:30 重置**：透過 `DailyManager` 記錄 `blood_altar` 的 `completed_today = True`（於 `user_data/daily_status.json` 中保存），每日 08:30 自動重置。
   - **連動佇列與 (選用) 獻祭續行**：領取完成後呼叫 `pop_and_next_town_subflow()` 消費下一個城鎮任務。


4. 領任務 (每日懸賞告示牌 `bulletin_board`)
   - **大廳退回與左上 1/4 ROI 鎖定**：若處於大廳 (`goback_town.png`) 點擊返回城鎮；於城鎮對螢幕左上 $1/4$ 區域 (`screen_img[0:h//2, 0:w//2]`) 進行 `town_building/bulletin_board/bulletin_board.png` 匹配與點擊。
   - **開窗憑據與條件式重置**：等待並確認 `common/quit.png` 出現證明成功開窗；掃描 `town_building/bulletin_board/reset.png`，若存在則點擊重置，若無則自動跳過。
   - **相對優勢過濾 (`task_after.png`)**：比對左半邊 ($X < W/2$) 任務卡片錨點 `task.png`。對每個錨點 ROI 同時比對 `task_after.png`；若 `conf(task_after) >= conf(task) - 0.02` 判定為已接取並自動過濾。若全數過濾（無未接任務），直接轉移至退出離場。
   - **Scale 自適應與 OCR 預處理**：
     - 依 `template_scale`（或視窗寬度比）動態計算 `icon_w` 與標題 ROI 起始點 `crop_x`。
     - 對標題 ROI 裁切上半部 $55\%$（避開下方副標與橫線），放大 2 倍 (`cv2.resize fx=2, fy=2`)。
     - 使用 EasyOCR 繁中與英文雙語模型 (`['ch_tra', 'en']`) 提取標題。
   - **逐列接取與 1 秒點擊延遲**：鎖定最上方 ($Y$ 最小) 未接任務點擊，並點擊右半邊 `accept_task.png`；點擊後強制等待 1 秒 (`time.sleep(1.0)`) 供系統響應與彈窗判斷。
   - **任務已滿防護 (`task_already_full.png`)**：若點擊後彈出 `task_already_full.png`，點擊 `confirm.png` 確認，寫入已抓取之標題至 JSON 並轉移至退出。
   - **離場與 JSON 持久化**：點擊 `common/quit.png` 關閉視窗；將標題陣列 `accepted_quests` 寫入 `user_data/daily_status.json` 並記錄 `completed_today = True`（每日 08:05 自動重置）。


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
python main.py --backend --subflow bulletin_board

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
    "bulletin_board": { "completed_today": true, "last_executed_at": "2026-07-25 08:34:00" },
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
    "bulletin_board": { ... },
    "lord_boss": { ... }
}

# 3. 向後相容全域匯出 (GAME_CONFIGS)
GAME_CONFIGS = {**PRIMARY_MODES, **SUBFLOW_CONFIGS}
```

#### CLI 參數解析對應 (`main.py`)：
- `--mode`: `choices=list(PRIMARY_MODES.keys())`（用戶在命令列幫助中只會看到 4 個乾淨的主模式）。
- `--subflow`: `nargs="+", choices=list(SUBFLOW_CONFIGS.keys())`（Dev 測試時可帶一個或多個子流程名稱，直接發起單體測試）。