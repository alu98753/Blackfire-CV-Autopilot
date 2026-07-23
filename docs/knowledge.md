# Blackfire Crusade 領域知識與介面規則指南 (Knowledge Base)

本文件紀錄《Blackfire Crusade》自動化腳本之畫面狀態判斷邊界、操作行為規則與模式導航之單一正確知識來源。

---

## 1. 城鎮 (Town)

城鎮為玩家登入遊戲後的初始主畫面。

### A. 領取鑽石 (`diamond.png`)
* **入口條件**：畫面偵測到 `diamond.png` 且冷卻倒數結束（預設 2 小時）。
* **執行流程**：
  1. 點擊 `diamond.png` 進入領取視窗。
  2. 匹配 `diamond_free.png`（免費領取按鈕）。
  3. 點擊後，遊戲會彈出獲得獎勵確認視窗，點擊 `common/confirm.png` 或 `common/ok.png`。
  4. 領取完畢或冷卻中時，點擊 `common/quit.png` 關閉視窗返回城鎮。

### B. 進入大廳 (`common/door.png`)
* 點擊城鎮大門 `common/door.png` 可進入大廳選關畫面。

---

## 2. 大廳與導航 (Lobby & Navigation)

僅有在這裡才能進行以下事情 ! 這是 去關卡(select_stage.png) 或地下城(dungeon.png)的地方,也可以在這裡領取體力(bread.png), 也可以從這裡回去城鎮(goback_town.png)

### A. 領取體力 (`common/bread.png`)
* **入口條件**：在大廳畫面偵測到 `common/bread.png` 且冷卻倒數結束。
* **執行流程**：
  1. 點擊 `common/bread.png` 開啟體力頁面。
  2. 匹配並點擊 `common/collect.png`。
  3. 若跳出體力已滿提示，點擊 `common/confirm.png` / `common/ok.png` 關閉。
  4. 點擊 `common/quit.png` 返回大廳。

### B. 模式選擇與導航路徑 (Navigation Modes)
1. **Stage 模式**：專門執行普通關卡挑戰，根據配置之 `stage_target` 滾動地圖選擇關卡與小關/魔王關。
2. **Dungeon 模式**：專門執行地下城探索，判斷冷卻木牌（`dungeons/cooldown_left.png` 等），依貪婪或自訂順序進入探索。
3. **Mix 混合模式（預設）**：
   * **優先級**：若有任意地下城冷卻結束且可挑戰，優先進入地下城。
   * **退守機制**：若所有允許地下城均在冷卻中，自動點擊 `common/select_stage.png` 轉入普通關卡刷關。
   * **即時恢復**：在 Stage 完成一輪戰鬥後，若檢測到地下城 CD 已結束，自動退出 Stage 並返回地下城。

---

## 3. 背包管理與防卡死處置 (Inventory & Exception Self-Healing)

### A. 背包分解與清理 (`STATE_BAG_CLEANING`)
* 戰鬥結束回到大廳或溢出時標記 `need_bag_cleaning = True`。
* 點擊 `bag.png` 進入背包 ➔ 點擊 `Backpack_Disassembly.png`（大量分解）➔ `select_all.png`（全選）➔ `Disassembly.png`（確認分解）➔ `tidy.png`（整理）➔ 點擊 `common/quit.png` 退出。

### B. 背包滿自適應分選 (`STATE_BACKPACK_FULL_SORTING`)
* 偵測到 `backpack_full.png` 時觸發。
* 掃描左側 4x4 溢出格，若包含高稀有度裝備（藍/紫/黃/橘/紅），則掃描右側背包 4x4 低稀有度裝備（灰/綠）並點擊 `destroy.png` 銷毀騰出空間，隨後領取左側貴重裝備。

### C. 全域體力退避 (`Stamina Retreat`)
* 偵測到 `no_bread/no_bread.png` 彈窗時，自動點擊 `cancel.png` 關閉彈窗。
* 點擊 `goback_town.png` 退回城鎮，模式自動切換至 `collect_only` 掛機 4.0 小時。
* 時間到達後，還原原模式並於大廳自動重新定位。