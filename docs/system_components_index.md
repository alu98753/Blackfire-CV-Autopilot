# 系統組件與架構要素清單 (System Architecture Components Index) 🧩

本文件列出專案中所有的 **Entity (靜態實體)**、**State (業務狀態)**、**Data (動態數據 & 對應 Entity/State)** 與 **Exception (閉環自癒)** 之極簡名詞與模組對照清單。

---

## 1. Entity (靜態實體 / 畫面與特徵)

### 畫面與介面 (Scenes & Panels)
* `TOWN_MAIN`: 城鎮主畫面 / 大門
* `BATTLE_SCENE`: 戰鬥進行中畫面
* `DUNGEON_SCENE`: 地下城探索畫面
* `LOBBY_PANEL`: 關卡準備大廳
* `BACKPACK_PANEL`: 背包介面
* `BLOOD_ALTAR_PANEL`: 血之祭壇介面
* `JEWELRY_WORKSHOP_PANEL`: 珠寶加工廠介面
* `LORD_BOSS_PANEL`: 首領領主介面
* `HERO_DRAW_PANEL`: 酒館招募介面
* `CHEST_PANEL`: 神秘寶箱介面
* `BULLETIN_BOARD_PANEL`: 懸賞告示牌介面

### 建築門牌與地圖圖示 (Buildings & Nav Icons)
* `gate`: 城鎮大門 / 冒險入口
* `blood_altar`: 血之祭壇門牌
* `jewelry_workshop`: 珠寶加工廠門牌
* `lord_boss`: 首領領主門牌
* `tavern`: 酒館門牌 (抽英雄)
* `bulletin_board`: 懸賞告示牌門牌
* `chest`: 神秘寶箱門牌

### 卡片與互動物件 (Cards & Interactive Templates)
* `lord_boss_cards`: 首領卡片 (`lord_spider`, `lord_spectre` 等)
* `dungeon_cards`: 地下城/關卡卡片
* `cooldown_sign`: 冷卻木牌 (`cooldown_left.png`, `cooldown_right.png`)
* `dungeon_leave_btn`: 地下城離開按鈕 (`dungeons/leave.png`)

### 核心操作按鈕 (Action Buttons)
* `start_btn`: 開始按鈕
* `continue_btn`: 繼續按鈕
* `retry_btn`: 再次挑戰按鈕
* `auto_battle_btn`: 自動戰鬥按鈕
* `select_all_btn`: 全選按鈕 (背包/獻祭)
* `disassemble_btn`: 分解按鈕
* `destroy_btn`: 銷毀按鈕
* `receive_btn`: 領取按鈕
* `refresh_btn`: 刷新按鈕 (告示牌)

### 彈窗與覆蓋物 (Popups & Overlays)
* `wheel_of_fortune_popup`: 幸運輪盤彈窗
* `raid_box_popup`: 掃蕩 / 寶箱獎勵彈窗
* `ad_unexpected_popup`: 廣告與各類通用意外彈窗

---

## 2. State (業務狀態 & 對應 Handler)

* `STATE_UNKNOWN`: 未知狀態 (`BaseStateHandler`)
* `STATE_NAVIGATING`: 尋路與導航中 ([NavigationHandler](file:///e:/Side_Project/BlackfireCrusade_tool/states/handlers/navigation.py))
* `STATE_LOBBY`: 關卡準備大廳 ([LobbyHandler](file:///e:/Side_Project/BlackfireCrusade_tool/states/handlers/lobby.py))
* `STATE_BATTLE`: 戰鬥進行中 ([BattleHandler](file:///e:/Side_Project/BlackfireCrusade_tool/states/handlers/battle.py))
* `STATE_RESULT`: 戰鬥結算 ([ResultHandler](file:///e:/Side_Project/BlackfireCrusade_tool/states/handlers/result.py))
* `STATE_DUNGEON_EXPLORING`: 地下城探索 ([ExploreHandler](file:///e:/Side_Project/BlackfireCrusade_tool/states/handlers/explore.py))
* `STATE_BAG_CLEANING`: 背包基礎清理 ([BagCleaningHandler](file:///e:/Side_Project/BlackfireCrusade_tool/states/handlers/bag_cleaning.py))
* `STATE_BACKPACK_FULL_SORTING`: 背包滿格銷毀 ([BackpackFullSortingHandler](file:///e:/Side_Project/BlackfireCrusade_tool/states/handlers/backpack_full_sorting.py))
* `STATE_BREAD_COLLECTION`: 麵包體力領取 ([BreadCollectionHandler](file:///e:/Side_Project/BlackfireCrusade_tool/states/handlers/bread_collection.py))
* `STATE_DIAMOND_COLLECTION`: 鑽石領取 ([DiamondCollectionHandler](file:///e:/Side_Project/BlackfireCrusade_tool/states/handlers/diamond_collection.py))
* `STATE_COLLECT_ONLY`: 體力退避待機 ([CollectOnlyHandler](file:///e:/Side_Project/BlackfireCrusade_tool/states/handlers/collect_only.py))
* `STATE_LOADING`: 畫面過渡載入 ([LoadingHandler](file:///e:/Side_Project/BlackfireCrusade_tool/states/handlers/loading.py))
* `STATE_BLOOD_ALTAR`: 血之祭壇獻祭 ([BloodAltarHandler](file:///e:/Side_Project/BlackfireCrusade_tool/states/handlers/blood_altar.py))
* `STATE_JEWELRY_WORKSHOP`: 珠寶加工廠出售 ([JewelryWorkshopHandler](file:///e:/Side_Project/BlackfireCrusade_tool/states/handlers/jewelry_workshop.py))
* `STATE_LORD_BOSS`: 首領領主討伐 ([LordBossHandler](file:///e:/Side_Project/BlackfireCrusade_tool/states/handlers/lord_boss.py))
* `STATE_CHEST`: 神秘寶箱開啟 ([ChestHandler](file:///e:/Side_Project/BlackfireCrusade_tool/states/handlers/chest.py))
* `STATE_HERO_DRAW`: 酒館招募 ([HeroDrawHandler](file:///e:/Side_Project/BlackfireCrusade_tool/states/handlers/hero_draw.py))
* `STATE_BULLETIN_BOARD`: 懸賞告示牌任務 ([BulletinBoardHandler](file:///e:/Side_Project/BlackfireCrusade_tool/states/handlers/bulletin_board.py))
* `STATE_POPUP_RECOVERY`: 意外彈窗恢復 ([UnexpectedPopupRecoveryHandler](file:///e:/Side_Project/BlackfireCrusade_tool/states/exceptions/handler.py))

---

## 3. Data (動態數據 & 對應 Entity / State 映射)

| 數據名稱 / 結構 | 對應 Entity / State | 說明 / 職責 |
| :--- | :--- | :--- |
| `SceneInfo` | Scenes, Panels, Buttons | `SceneDetector` 的視覺辨識輸出 (包含當前場景、匹配按鈕與座標) |
| `goods_settings` | `BACKPACK_PANEL`, `STATE_BACKPACK_FULL_SORTING` | 背包裝備/道具銷毀授權與品質門檻的單一權威來源 (SSOT) |
| `daily_status.json` / `DailyManager` | Buildings, Panels, Daily Tasks | 每日懸賞、建築狀態、首領 CD 及跨日 08:05 Date Tag 的持久化記憶 |
| `QuestScheduler` / `QuestMapper` | `bulletin_board`, `STATE_BULLETIN_BOARD` | 告示牌任務名稱匹配規則與優先級動態調度隊列 |
| `dungeon_cooldowns` | `dungeon_cards`, `cooldown_sign` | 各地下城關卡的 OCR 冷卻剩餘秒數記憶 |
| `lord_boss_cooldowns` | `lord_boss_cards`, `cooldown_sign` | 首領討伐各 Boss 的 OCR 冷卻剩餘秒數記憶 |
| `town_subflow_queue` | Buildings, Town States | 進入城鎮後待執行的子流程佇列 (`BLOOD_ALTAR`, `HERO_DRAW` 等) |
| `stamina_retreat_start_time` | `STATE_COLLECT_ONLY` | 體力耗盡退避開始時間與 1 小時待機輪詢冷卻記憶 |
| `user_intervention_time` | All States, Exceptions | 使用者手動介入的時間戳與累計補償時長 |

---

## 4. Exception (閉環自癒與異常處理)

### Watchdog 監控器
* `ExceptionWatchdog`: 全局卡死監控 (常規 State 30 秒 / `NAVIGATING` 90 秒逾時門檻)

### 救援 Handler
* `UnexpectedPopupRecoveryHandler`: 意外彈窗與未預期畫面救援 Handler (`STATE_POPUP_RECOVERY`)

### Exception Subflows (自癒子流程)
* `GameRelaunchSubflow`: 遊戲崩潰 / 卡死重啟與 Steam 連線恢復
* `WheelOfFortuneSubflow`: 幸運輪盤彈窗自動關閉 / 領取
* `RaidBoxSubflow`: 掃蕩與寶箱獎勵彈窗處理
* `GenericAntiStuckSubflow`: 通用防卡死盲點點擊與隨機位移救援
