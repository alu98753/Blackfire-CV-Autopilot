# 系統組件與架構要素清單 (System Architecture Components Index) 🧩

本文件列出專案中所有的 **Entity (靜態實體)**、**State (業務狀態)**、**Data (動態數據 & 對應 Entity/State)** 與 **Exception (閉環自癒)** 之極簡名詞與模組對照清單。

---

## 1. Entity (靜態實體 / 畫面與特徵)

### 🏰 `TOWN_MAIN`: 城鎮主畫面 / 大門 (Town Main Scene)
* **建築門牌與地圖圖示 (Buildings & Nav Icons)**:
  * `door.png`: [common/door.png](../templates/common/door.png) - 城鎮大門 / 冒險入口 (傳送門)
  * `blood_altar`: [town_building/Blood_Altar/Blood_Altar.png](../templates/town_building/Blood_Altar/Blood_Altar.png) - 血之祭壇門牌
  * `jewelry_workshop`: [town_building/Jewelry_workshop/Jewelry_workshop.png](../templates/town_building/Jewelry_workshop/Jewelry_workshop.png) - 珠寶加工廠門牌
  * `tavern`: [town_building/Tavern/Tavern.png](../templates/town_building/Tavern/Tavern.png) - 酒館門牌 (抽英雄)
  * `bulletin_board`: [town_building/bulletin_board/bulletin_board.png](../templates/town_building/bulletin_board/bulletin_board.png) - 懸賞告示牌門牌
  * `chest`: [town_building/mysterious_treasure/mysterious_treasure.png](../templates/town_building/mysterious_treasure/mysterious_treasure.png) - 神秘寶箱門牌
  * `exit_house`: [town_building/exitfromhouse_and_to_town.png](../templates/town_building/exitfromhouse_and_to_town.png) - 建築屋內返回城鎮圖示
* **UI 互動與功能圖示 (UI Controls)**:
  * `bread.png`: [common/bread.png](../templates/common/bread.png) - 體力/麵包對話框發射按鈕
  * `diamond.png`: [diamond.png](../templates/diamond.png) - 鑽石對話框發射按鈕
  * `bag.png`: [common/bag.png](../templates/common/bag.png) - 背包打開按鈕
  * `wheel_of_fortune_popup`: [exceptions/Wheel_of_Fortune.png](../templates/exceptions/Wheel_of_Fortune.png) - 幸運輪盤彈窗

### ⚔️ `DUNGEON_SCENE`: 地下城探索畫面 (Dungeon Scene)
* **關卡與事件特徵 (Cards & Events)**:
  * `dungeon_cards`: 地下城探索關卡卡片範本
    * `Slime`: [dungeons/Slime_entry.png](../templates/dungeons/Slime_entry.png) (黏糊糊的石窟)
    * `Ghost`: [dungeons/Ghost_entry.png](../templates/dungeons/Ghost_entry.png) (幽影地穴)
    * `Forest`: [dungeons/Forest_entry.png](../templates/dungeons/Forest_entry.png) (森林迷宮)
    * `Ruins`: [dungeons/Ruins_entry.png](../templates/dungeons/Ruins_entry.png) (神秘遺跡)
    * `Ice`: [dungeons/Ice_entry.png](../templates/dungeons/Ice_entry.png) (冰雪洞窟)
  * `cooldown_sign`: [dungeons/cooldown_left.png](../templates/dungeons/cooldown_left.png) & [dungeons/cooldown_right.png](../templates/dungeons/cooldown_right.png) - 卡片冷卻木牌
  * `dungeon_bless`: [dungeons/dungeon_bless.png](../templates/dungeons/dungeon_bless.png) & [dungeons/bless_combat.png](../templates/dungeons/bless_combat.png) - 祝福選擇畫面
  * `gungeon_godown`: [dungeons/gungeon_godown.png](../templates/dungeons/gungeon_godown.png) - 下樓/進入下層圖示
  * `Treasure`: [dungeons/Treasure.png](../templates/dungeons/Treasure.png) - 寶箱特徵圖示
* **操作按鈕 (Buttons)**:
  * `dungeon_fight`: [dungeons/dungeon_fight.png](../templates/dungeons/dungeon_fight.png) - 地下城備戰/開始挑戰按鈕
  * `leave`: [dungeons/leave.png](../templates/dungeons/leave.png) - 離開地下城按鈕

### 🚩 `LOBBY_PANEL`: 關卡準備大廳 (Lobby Stage/Dungeon Panel)
* **頁籤與導航 (Tabs & Nav)**:
  * `stage_tab`: [dungeons/stage.png](../templates/dungeons/stage.png) & [dungeons/stage_after.png](../templates/dungeons/stage_after.png) - 一般關卡頁籤
  * `dungeon_tab`: [dungeons/dungeon.png](../templates/dungeons/dungeon.png) & [dungeons/dungeon_after.png](../templates/dungeons/dungeon_after.png) - 地下城頁籤
  * `Lord_entry.png`: [load/Lord_entry.png](../templates/load/Lord_entry.png) & [load/Lord_entry_after.png](../templates/load/Lord_entry_after.png) - 首領大廳頁籤 (Before/After)
  * `goback_town`: [goback_town.png](../templates/goback_town.png) - 返回城鎮按鈕
* **操作按鈕 (Buttons)**:
  * `start.png`: [stages/start.png](../templates/stages/start.png) - 開始戰鬥按鈕
  * `raid_box_popup`: [exceptions/Raid_Box.png](../templates/exceptions/Raid_Box.png) - 掃蕩 / 寶箱獎勵彈窗
  * `task_complete_popup`: [task_complete.png](../templates/task_complete.png) - 任務完成彈窗

### ⚔️ `BATTLE_SCENE`: 戰鬥進行中畫面 (Battle Scene)
* **狀態與操作元件 (Battle Controls)**:
  * `auto.png`: [common/auto.png](../templates/common/auto.png) - 自動戰鬥啟用/切換按鈕
  * `battle_features`: [battle/battle_features_1.png](../templates/battle/battle_features_1.png) & [battle/battle_features_2.png](../templates/battle/battle_features_2.png) - 戰鬥介面特徵
  * `defeat.png`: [defeat.png](../templates/defeat.png) - 戰鬥失敗標題
  * `exit_battle`: [exit_battle.png](../templates/exit_battle.png) - 退出戰鬥按鈕
* **結算按鈕 (Result Buttons)**:
  * `continue.png`: [common/continue.png](../templates/common/continue.png) / [common/continue1.png](../templates/common/continue1.png) / [common/continue2.png](../templates/common/continue2.png) - 戰鬥結算繼續按鈕
  * `retry.png`: [stages/retry.png](../templates/stages/retry.png) / [defeat_retry.png](../templates/defeat_retry.png) - 再次挑戰按鈕

### 🎒 `BACKPACK_PANEL`: 背包介面 (Backpack Sorting & Cleaning Panel)
* **網格與裝備品質 (Grids & Tiers)**:
  * `backpack_full.png`: [backpack_full.png](../templates/backpack_full.png) - 背包已滿告示按鈕/標題
  * `bag_text.png`: [common/bag_text.png](../templates/common/bag_text.png) - 背包標題列錨點
  * `backpack_grid_18`: 背包 18 格掃描辨識區域 (`R0C0` ~ `R2C5`)
  * `equipment_tier_colors`: 裝備品質框色 (紫 `purple` / 藍 `blue` / 綠 `green` / 紅 `red` / 橙黃 `orange_yellow` / 灰 `gray_or_empty`)
* **處置按鈕 (Action Buttons)**:
  * `select_all.png`: [common/select_all.png](../templates/common/select_all.png) - 一鍵全選按鈕
  * `Disassembly.png`: [common/Disassembly.png](../templates/common/Disassembly.png) - 裝備分解按鈕
  * `destroy.png`: [common/destroy.png](../templates/common/destroy.png) - 裝備/道具銷毀按鈕
  * `tidy.png`: [common/tidy.png](../templates/common/tidy.png) - 整理背包按鈕

### 🩸 `BLOOD_ALTAR_PANEL`: 血之祭壇介面 (Blood Altar Panel)
* **互動元件 (Altar Controls)**:
  * `Blood_Altar.png`: [town_building/Blood_Altar/Blood_Altar.png](../templates/town_building/Blood_Altar/Blood_Altar.png) - 血之祭壇標題列錨點
  * `alter.png`: [town_building/Blood_Altar/alter.png](../templates/town_building/Blood_Altar/alter.png) - 祭壇頁籤
  * `Sacrifice.png`: [town_building/Blood_Altar/Sacrifice.png](../templates/town_building/Blood_Altar/Sacrifice.png) - 獻祭按鈕
  * `receive_entry.png`: [town_building/Blood_Altar/receive_entry.png](../templates/town_building/Blood_Altar/receive_entry.png) - 領取頁籤入口
  * `receive_daily.png`: [town_building/Blood_Altar/receive_daily.png](../templates/town_building/Blood_Altar/receive_daily.png) - 領取每日獎勵按鈕

### 💎 `JEWELRY_WORKSHOP_PANEL`: 珠寶加工廠介面 (Jewelry Workshop Panel)
* **道具與出售元件 (Goods & Trade)**:
  * `Jewelry_workshop.png`: [town_building/Jewelry_workshop/Jewelry_workshop.png](../templates/town_building/Jewelry_workshop/Jewelry_workshop.png) - 珠寶加工廠標題列錨點
  * `goods_items`: 材料/道具範本 (例如 [Scorpion_Shell.png](../templates/town_building/Jewelry_workshop/goods/green/Scorpion_Shell.png), [Toad_Venom.png](../templates/town_building/Jewelry_workshop/goods/green/Toad_Venom.png), [Dead_Soul_Core.png](../templates/town_building/Jewelry_workshop/goods/green/Dead_Soul_Core.png) 等)
  * `sell.png`: [town_building/sell.png](../templates/town_building/sell.png) - 出售按鈕
  * `sell_max.png`: [town_building/sell_max.png](../templates/town_building/sell_max.png) - 最大數量出售按鈕

### 👹 `LORD_BOSS_PANEL`: 首領領主介面 (Lord Boss Panel)
* **首領卡片與冷卻 (Boss Cards & Cooldown)**:
  * `lord_spider`: [load/lord_spider.png](../templates/load/lord_spider.png) (育母蜘蛛麗拉西亞卡片)
  * `lord_spectre`: [load/lord_spectre.png](../templates/load/lord_spectre.png) (古代惡靈伊瑟倫卡片)
  * `cooldown_sign`: [load/cooldown_sign.png](../templates/load/cooldown_sign.png) - 首領冷卻木牌

### 🍺 `HERO_DRAW_PANEL`: 酒館招募介面 (Hero Draw Panel / Tavern)
* **招募元件 (Draw Controls)**:
  * `Tavern.png`: [town_building/Tavern/Tavern.png](../templates/town_building/Tavern/Tavern.png) - 酒館標題列錨點
  * `free_recruitment.png`: [town_building/Tavern/free_recruitment.png](../templates/town_building/Tavern/free_recruitment.png) - 免費招募按鈕
  * `deassemble_hero.png`: [town_building/Tavern/deassemble_hero.png](../templates/town_building/Tavern/deassemble_hero.png) - 英雄解雇/分解按鈕

### 🎁 `CHEST_PANEL`: 神秘寶箱介面 (Chest Panel)
* **寶箱元件 (Chest Controls)**:
  * `mysterious_treasure.png`: [town_building/mysterious_treasure/mysterious_treasure.png](../templates/town_building/mysterious_treasure/mysterious_treasure.png) - 神秘寶箱標題列錨點
  * `free_treasure.png`: [town_building/mysterious_treasure/free_treasure.png](../templates/town_building/mysterious_treasure/free_treasure.png) - 免費開啟寶箱按鈕

### 📋 `BULLETIN_BOARD_PANEL`: 懸賞告示牌介面 (Bulletin Board Panel)
* **任務與調度元件 (Quests & Schedule)**:
  * `bulletin_board.png`: [town_building/bulletin_board/bulletin_board.png](../templates/town_building/bulletin_board/bulletin_board.png) - 懸賞告示牌標題列錨點
  * `task.png`: [town_building/bulletin_board/task.png](../templates/town_building/bulletin_board/task.png) & [town_building/bulletin_board/task_after.png](../templates/town_building/bulletin_board/task_after.png) - 任務頁籤 (Before/After)
  * `reset.png`: [town_building/bulletin_board/reset.png](../templates/town_building/bulletin_board/reset.png) - 刷新任務按鈕
  * `accept_task.png`: [town_building/bulletin_board/accept_task.png](../templates/town_building/bulletin_board/accept_task.png) - 接取任務按鈕
  * `task_already_full.png`: [town_building/bulletin_board/task_already_full.png](../templates/town_building/bulletin_board/task_already_full.png) - 任務已滿告示

### ⚠️ `POPUPS_AND_OVERLAYS`: 通用彈窗與覆蓋物 (Popups & Overlays)
* `cancel.png`: [exceptions/cancel.png](../templates/exceptions/cancel.png) - 彈窗關閉/取消按鈕
* `quit.png`: [common/quit.png](../templates/common/quit.png) - 視窗離開按鈕

---

## 2. State (業務狀態 & 對應 Handler)

* `STATE_UNKNOWN`: 未知狀態 (`BaseStateHandler`)
* `STATE_NAVIGATING`: 尋路與導航中 ([NavigationHandler](../states/handlers/navigation.py))
* `STATE_LOBBY`: 關卡準備大廳 ([LobbyHandler](../states/handlers/lobby.py))
* `STATE_BATTLE`: 戰鬥進行中 ([BattleHandler](../states/handlers/battle.py))
* `STATE_RESULT`: 戰鬥結算 ([ResultHandler](../states/handlers/result.py))
* `STATE_DUNGEON_EXPLORING`: 地下城探索 ([ExploreHandler](../states/handlers/explore.py))
* `STATE_BAG_CLEANING`: 背包基礎清理 ([BagCleaningHandler](../states/handlers/bag_cleaning.py))
* `STATE_BACKPACK_FULL_SORTING`: 背包滿格銷毀 ([BackpackFullSortingHandler](../states/handlers/backpack_full_sorting.py))
* `STATE_BREAD_COLLECTION`: 麵包體力領取 ([BreadCollectionHandler](../states/handlers/bread_collection.py))
* `STATE_DIAMOND_COLLECTION`: 鑽石領取 ([DiamondCollectionHandler](../states/handlers/diamond_collection.py))
* `STATE_COLLECT_ONLY`: 體力退避待機 ([CollectOnlyHandler](../states/handlers/collect_only.py))
* `STATE_LOADING`: 畫面過渡載入 ([LoadingHandler](../states/handlers/loading.py))
* `STATE_BLOOD_ALTAR`: 血之祭壇獻祭 ([BloodAltarHandler](../states/handlers/blood_altar.py))
* `STATE_JEWELRY_WORKSHOP`: 珠寶加工廠出售 ([JewelryWorkshopHandler](../states/handlers/jewelry_workshop.py))
* `STATE_LORD_BOSS`: 首領領主討伐 ([LordBossHandler](../states/handlers/lord_boss.py))
* `STATE_CHEST`: 神秘寶箱開啟 ([ChestHandler](../states/handlers/chest.py))
* `STATE_HERO_DRAW`: 酒館招募 ([HeroDrawHandler](../states/handlers/hero_draw.py))
* `STATE_BULLETIN_BOARD`: 懸賞告示牌任務 ([BulletinBoardHandler](../states/handlers/bulletin_board.py))
* `STATE_POPUP_RECOVERY`: 意外彈窗恢復 ([UnexpectedPopupRecoveryHandler](../states/exceptions/handler.py))

---

## 3. Data (動態數據 & 記憶架構) 🧠

本專案的 Data 分為 **「硬碟實體檔案 (Disk Files)」** 與 **「記憶體即時變數 (RAM Runtime Data)」** 兩大層級：

---

### 💾 類別 A：硬碟實體檔案 (Disk Files)
永久寫入硬碟的設定指南與狀態記憶，即使遊戲關閉或腳本重啟也不會遺失。

#### 1. [config.py](../config.py)
* **檔案用途**：全域系統設定、自動化模式參數、裝備/材料銷毀 SSOT 與 OCR 裁切框像素偏移量。
* **主要變數與 Key 結構**：
  * `GAME_CONFIGS`: 遊戲模式定義字典（包含 `dungeon`, `stage`, `daily`, `collect_only` 之 `navigation_path`, `result_buttons`, `dungeon_name` 等）。
  * `goods_settings`: 裝備與材料銷毀/出售權限 SSOT（包含 `disassemble_colors`, `keep_colors`, `gray`, `green`, `blue`, `purple` 各品質品項，如 `"Scorpion_Shell": True`）。
  * `SUBFLOW_CONFIGS`: 08:05 城鎮子流程獨立配置（包含 `blood_altar`, `jewelry_workshop`, `lord_boss`, `chest`, `hero_draw`, `bulletin_board` 之門牌按鈕 `building_btn` 與首領卡片名冊 `bosses`）。
  * `TASK_BANNER_OCR_OFFSET` / `BULLETIN_BOARD_OCR_OFFSET`: 懸賞任務對話框與告示牌清單之 OCR 裁切框偏移量 (`offset_x`, `offset_y`, `box_width`, `box_height`)。
  * `DEFAULT_DISASSEMBLE_COLORS` / `DEFAULT_KEEP_COLORS`: 背包預設拆解與保留品階名單。

#### 2. [user_data/daily_status.json](../user_data/daily_status.json) (掌管類別: [DailyManager](../utils/daily_manager.py))
* **檔案用途**：每日懸賞任務完成度、首領冷卻與城鎮建築子流程今日執行狀態之持久化記憶檔案。
* **主要變數與 Key 結構**：
  * `date`: 跨日 Date Tag (格式如 `"2026-07-29"`)，每日 08:05 後觸發自動清空重置。
  * `daily_tasks`: 告示牌懸賞任務的當前接取與完成進度對照表。
  * `lord_boss_status`: 首領討伐各 Boss 今日剩餘次數 (每日上限 5 次) 與 OCR 冷卻解鎖時間戳。
  * `town_subflow_completed`: 今日城鎮子流程 (`blood_altar`, `jewelry_workshop`, `hero_draw` 等) 完成紀錄。

#### 3. [config/quest_rules.json](../config/quest_rules.json) (掌管類別: [QuestMapper](../utils/quest_mapper.py))
* **檔案用途**：告示牌懸賞任務辨識規則、EasyOCR 繁體中文錯別字清洗字典、忽略任務名冊，與任務名稱配對至地下城 (0~4) / 普通關卡 (1~6) 的對照數據。
* **主要變數與 Key 結構**：
  * `deterministic_quests`: 確定性可計數任務全名清單（通關每場 100% 累加進度）。
  * `banner_verify_quests`: 無法自動累計、僅憑彈窗核銷之任務全名清單。
  * `ignored_quests`: 顯式跳過不接取之任務關鍵字（不納入 unknown 統計）。
  * `typo_groups`: EasyOCR 錯別字自動清洗容錯對照表（例如 `"毀滅": ["致滅", "毀減"]`）。
  * `dungeon_rules`: 地下城任務關鍵字配對至 `dungeon_index` (0~4) 規則列表。
  * `stage_rules`: 普通關卡怪物關鍵字配對至 `stage_level` (1~6) 與 `sub_stage` (`first`, `middle`, `six`, `final`) 規則列表。

#### 4. [config/exception_features.json](../config/exception_features.json) (掌管類別: [UnexpectedPopupRecoveryHandler](../states/exceptions/handler.py) & [Watchdog](../states/exceptions/watchdog.py))
* **檔案用途**：自癒子流程 (Exception Subflow) 觸發特徵圖案對照表與全域 Watchdog 卡死逾時秒數門檻。
* **主要變數與 Key 結構**：
  * `non_battle_stuck_timeout_sec`: 常規狀態 Watchdog 卡死逾時門檻 (預設 `30.0` 秒)。
  * `battle_stuck_timeout_sec`: 導航與戰鬥狀態 Watchdog 卡死逾時門檻 (預設 `90.0` 秒)。
  * `subflow_feature_mapping`: Exception Subflow 觸發對照字典（包含 `wheel_of_fortune_subflow` ➔ `exceptions/Wheel_of_Fortune.png`、`raid_box_subflow` ➔ `exceptions/Raid_Box.png`、`generic_anti_stuck_subflow` ➔ `exceptions/cancel.png`）。


---

### ⚡ 類別 B：記憶體即時變數 (RAM Runtime Data)
腳本執行期間隨畫面辨識與狀態流轉即時更新的記憶體變數，隨進程結束而釋放。

| 變數名稱 / 結構 | 存放位置 / 模組 | 檔案用途與變數內容 |
| :--- | :--- | :--- |
| `SceneInfo` | [utils/scene_detector.py](../utils/scene_detector.py) | 每次擷取螢幕後的即時視覺報告（包含 `scene_type`, `is_town`, `is_lobby`, `matched_elements` 按鈕與座標） |
| `town_subflow_queue` | [states/state_machine.py](../states/state_machine.py) | 進入城鎮後待依次執行的子流程佇列清單 (`list`，如 `["blood_altar", "hero_draw"]`) |
| `stamina_retreat_start_time` | [states/state_machine.py](../states/state_machine.py) | 體力耗盡轉入 `COLLECT_ONLY` 退避模式的起始時間戳 (`float`) |
| `dungeon_cooldowns` / `lord_boss_cooldowns` | [states/state_machine.py](../states/state_machine.py) | 透過 OCR 讀取卡片木牌獲得的即時剩餘冷卻秒數記憶 (`dict`) |
| `user_intervention_time` | [states/state_machine.py](../states/state_machine.py) | 偵測到使用者手動移動滑鼠時的即時時間戳與累計補償秒數 (`float`) |



---

## 4. Exception (閉環自癒與異常處理) 🛡️

> 💡 **核心概念**：Exception 體系是自動化腳本的**「緊急救援醫護隊」**。當 24/7 掛機期間畫面出現意外廣告彈窗、獎勵遮擋、卡死或遊戲崩潰時，救援體系會自動接管畫面並處理彈窗，成功清除障礙後自動恢復原狀態 (State Restore)，達成 100% 無人值守不斷線的自癒閉環。

---

### 🚨 1. 超時哨兵 (Watchdog 監控器)
* [ExceptionWatchdog](../states/exceptions/watchdog.py)
  * **職責**：全域狀態計時器。當同一 State 維持超過門檻（常規狀態 `30` 秒 / 導航與戰鬥狀態 `90` 秒）且無畫面進展時發起吹哨。
  * **動作**：暫存當前狀態 (`StateStash`)，並強制切換至救援狀態 `STATE_POPUP_RECOVERY`。

---

### 🏥 2. 救援隊長 (Recovery Handler)
* [UnexpectedPopupRecoveryHandler](../states/exceptions/handler.py) (`STATE_POPUP_RECOVERY`)
  * **職責**：接管卡死畫面，調度下屬專屬的 Subflows 進行特定特徵比對與障礙排除。
  * **動作**：比對成功並排除彈窗後，還原暫存狀態，將控制權交還給原 Handler。

---

### 🚑 3. 專屬救援隊員 (Exception Subflows)

| 子流程名稱 (Subflow) | 模組檔案位置 | 專屬處理障礙與行動 |
| :--- | :--- | :--- |
| `WheelOfFortuneSubflow` | [wheel_of_fortune.py](../states/exceptions/subflows/wheel_of_fortune.py) | 偵測 [exceptions/Wheel_of_Fortune.png](../templates/exceptions/Wheel_of_Fortune.png) 幸運輪盤彈窗，自動點擊關閉 / 領取 |
| `RaidBoxSubflow` | [raid_box.py](../states/exceptions/subflows/raid_box.py) | 偵測 [exceptions/Raid_Box.png](../templates/exceptions/Raid_Box.png) 掃蕩 / 寶箱獎勵彈窗，於 ROI 內部尋找 [cancel.png](../templates/exceptions/cancel.png) 自動點擊關閉 |
| `GenericAntiStuckSubflow` | [generic_anti_stuck.py](../states/exceptions/subflows/generic_anti_stuck.py) | 找不到特定圖片時的通用救援：針對 [exceptions/cancel.png](../templates/exceptions/cancel.png) 盲點或進行微幅位移解鎖死鎖 |
| `GameRelaunchSubflow` | [game_relaunch.py](../states/exceptions/subflows/game_relaunch.py) | 遊戲崩潰、黑屏或視窗消失時，透過 Steam Launcher 發起重啟並重新恢復進入遊戲狀態 |

