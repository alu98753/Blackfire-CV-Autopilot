# 輕量化行為測試防護網建構計畫 (Google Software Dev Standard) 🧪

依據 Google 軟體工程規範與 `AGENTS.md` 第 6 條測試設計要求，本文件定義重構前的**行為測試開發矩陣**。
測試原則：**測試公開行為與契約（Given 畫面情境 ➔ When 觸發 handle ➔ Then 斷言點擊與轉移），不測試內部實作與私有方法。**

先了解該部分的code 與我核對行為 沒問題才寫測試

---

## 🎯 輕量化領域行為測試模組切分

### 1. `tests/test_behavior_navigation.py` (導航與畫面辨識轉移行為)
- [x] **1.1 城鎮畫面識別與導航行為**：當畫面出現 `common/door.png` 或 `diamond.png`，觸發領體力/領鑽石或跳轉大廳行為。
- [x] **1.2 大廳頁籤互斥與切換行為**：當在活動大廳時，正確辨識關卡頁籤 (`select_stage_after.png`) vs 地下城頁籤 (`dungeon_after.png`) 並發射頁籤切換點擊。
- [x] **1.3 地下城內部與備戰跳轉行為**：當畫面出現 `dungeons/leave.png` 或內部物件時，自動轉移至 `DUNGEON_EXPLORING`；出現 `dungeons/dungeon_fight.png` 時觸發進入戰鬥。
- [x] **1.4 全域任務完成彈窗攔截行為**：當尋路過程中出現 `task_complete.png`，中斷尋路並調用領獎子流程。
- [x] **1.5 鑽石與體力全域圖示自動跳轉**：尋路過程中若直接出現 `diamond.png` (且 `need_diamond_collection=True`) 或 `bread.png`，自動切換至對應領取狀態。
- [x] **1.6 關卡模式預設子關卡退守路徑**：當 `config_type == "stage"` 且 `sub_stage` 未指定時，預設載入 `stages/first_stage.png` 為尋路標的。
- [x] **1.7 關卡選擇多次滑動未果點擊返回重置**：在關卡選擇介面，當 `horizontal_scroll_count >= 8` 仍未見目標小島時，點擊 `goback_town.png` 退回城鎮並重置計數。
- [x] **1.8 關卡細節背景向下拖曳滾動尋找魔王關**：當偵測到關卡背景 `stages/stage_label.png` 但魔王關按鈕尚未出現時，經過 1.5 秒緩衝後觸發 `mouse.drag` 向下滾動。

### 2. `tests/test_behavior_dungeon_cards.py` (地下城卡片掃描與冷卻退避行為)
- [x] **2.1 地下城卡片定位與對齊行為**：正確定位多解析度下卡片位置，若無解鎖卡片觸發 `CardListNavigator.reset_to_left` 防呆滑動。
- [x] **2.2 冷卻木牌 OCR 解析與退避行為**：比對出 `cooldown_left.png` 時，解析剩餘秒數並更新冷卻緩衝字典。
- [x] **2.3 亮骨頭未解鎖過濾行為**：比對出 `light_skull.png` 相似度 < 0.75 時，設定無限冷卻防呆並切換頁籤/回城。
- [x] **2.4 全冷卻混合模式防死鎖切換**：地下城貪婪模式下若所有允許地下城均在冷卻中且模式為 `mix`，觸發 `_switch_to_stage_or_back` 切換關卡頁籤。
- [x] **2.5 全冷卻且無關卡頁籤時退回城鎮**：切換頁籤時若畫面上無 `select_stage.png` 但看得到 `goback_town.png`，點擊 `goback_town.png` 退回城鎮。
- [x] **2.6 地下城多次滑動無卡片極限退回城鎮**：單一模式下當 `card_alignment_attempts >= 7` 且無可打卡片時，點擊 `goback_town.png` 重置計數並退回城鎮。

### 3. `tests/test_behavior_stamina_retreat.py` (體力退避與狀態切換行為)
- [x] **3.1 地下城全冷卻切換 Collect Only**：混合/地下城模式下全冷卻時，自動退回 `STATE_COLLECT_ONLY`。
- [x] **3.2 collect_only 模式下領完體力返回城鎮**：解決大廳領完體力無路徑時點擊 `goback_town.png` 退回城鎮，防死迴圈。

### 4. `tests/test_behavior_town_subflows.py` (城鎮獨立子流程行為)
- [x] **4.1 酒館分解英雄行為**：辨識 `deassemble_hero.png` 並發射點擊領取碎片，確認退場機制。
- [x] **4.2 血之祭壇領血與獻祭離散狀態閉環**：驗證單向離散鏈領血與獻祭流程點擊與退出。
- [x] **4.3 懸賞告示牌與動態調度行為**：驗證字典 + difflib 正名管道與 4 場關卡懸賞離場核銷。

### 5. `tests/test_behavior_bag_cleaning.py` (背包銷毀與品質分類行為)
- [x] **5.1 單個裝備滿時預設銷毀行為**：預設限定 `['gray_or_empty']` 銷毀防誤刪高階裝備。
- [x] **5.2 大量分解高品質允許行為**：分解最高允許放寬至紫色史詩品質。

---

## 📈 執行與驗證流程

### 增量覆蓋率流程
當針對性開發或補充單一測試檔時，**使用 `-a` 增量模式與既有數據庫求聯集 (Union)**：

1. **增量執行**：
   ```bash
   .venv\Scripts\python -m coverage run -a -m unittest tests.test_behavior_navigation
   ```
2. **報表**：
   ```bash
   .venv\Scripts\python -m coverage report --include="states/handlers/navigation.py,utils/scene_detector.py" -m
   ```

3. **全域驗證** (Commit 前)：
   ```bash
   .venv\Scripts\python -m unittest discover tests
   ```
當所有 `test_behavior_*.py` 全部 PASS 且覆蓋率達標後，方可進行 `SceneDetector` 重構，確保重構過程無任何行為破壞。