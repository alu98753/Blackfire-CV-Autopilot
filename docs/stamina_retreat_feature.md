# 全域體力不足退避與自動恢復機制 (Stamina Retreat & Auto Recovery Feature)

## 1. 功能概述

本功能旨在處理遊戲中體力（麵包）耗盡並彈出 `no_bread.png` 視窗時的防卡死與自動退避掛機機制。當檢測到體力不足時，系統會自動關閉彈窗、退回城鎮、切換至 `collect_only`（定時領取）模式掛機，並於指定冷卻時間結束後自動恢復原設定繼續執行。

---

## 2. 觸發條件與作用狀態

* **觸發圖標**：`templates/no_bread/no_bread.png`（食物不足彈窗）。
* **作用狀態範圍**：僅在可能發起新戰鬥或關卡切換的狀態下進行偵測：
  * `STATE_NAVIGATING`（尋路選關）
  * `STATE_LOBBY`（準備大廳）
  * `STATE_LOADING`（關卡載入）
  * `STATE_RESULT`（結算再戰）
* **排除狀態**：戰鬥中 (`STATE_BATTLE`)、地下城探索中 (`STATE_DUNGEON_EXPLORING`)、背包整理中 (`STATE_BAG_CLEANING`, `STATE_BACKPACK_FULL_SORTING`)。

---

## 3. 處理流程與執行步驟

當觸發體力不足時，由 `states/stamina_flow.py` 之 `handle_insufficient_stamina()` 按下列順序執行：

1. **關閉彈窗**：
   * 搜尋並點擊 `templates/no_bread/cancel.png`（【取消】按鈕）。
   * 若無法定位【取消】按鈕，依據 `no_bread.png` 基準座標進行左下相對偏移點擊（防呆點擊）。
2. **清除殘留視窗與退回城鎮**：
   * 執行防呆輪詢，點擊 `common/quit.png` 或 `exit_battle.png` 關閉當前關卡選單。
   * 搜尋並點擊 `goback_town.png` 返回城鎮大廳。
3. **備份與模式切換**：
   * 將當前完整配置物件備份至 `state_machine.original_config`。
   * 記錄退避啟動時間 `state_machine.stamina_retreat_start_time = time.time()`。
   * 載入 `GAME_CONFIGS["collect_only"]` 配置。
   * 轉移至 `STATE_COLLECT_ONLY` 狀態。

---

## 4. 定時掛機與自動恢復協議

於 `STATE_COLLECT_ONLY`（`CollectOnlyHandler`）運作期間：

1. **城鎮待機與資源收集**：
   * 僅於鑽石或體力冷卻倒數結束時執行領取動作。
   * 每 60 秒於城鎮地圖執行微幅拖曳（心跳機制）防止閒置斷線。
2. **時間監測與恢復**：
   * 每次執行 `handle()` 時，計算累積退避時間：`elapsed = time.time() - stamina_retreat_start_time`。
   * 退避目標時間由配置檔 `stamina_retreat_duration` 決定（預設 4.0 小時）。
3. **恢復執行**：
   * 當 `elapsed >= retreat_seconds` 時，觸發恢復。
   * 還原原配置：`state_machine.config = state_machine.original_config`。
   * 重置 `state_machine.original_config = None` 與 `state_machine.stamina_retreat_start_time = None`。
   * 將狀態切換至 `STATE_UNKNOWN` 觸發全域重新定位。

---

## 5. 多模式相容性行為

### 5.1 普通關卡模式 (`stage`)
* 退避恢復後，自動於大廳重新定位並繼續進行 Stage 尋路與刷關。

### 5.2 地下城模式 (`dungeon`)
* 退避恢復後，自動進入地下城選單，繼續進行地下城探索。

### 5.3 混合模式 (`mix`)
* 退避啟動時，完整備份 `mix` 全量配置（含 `dungeon_names`, `greedy_dungeon`, `stage_target`）。
* 退避恢復後，`mix` 導航邏輯會重新檢測全地下城 CD：
  * 若有可刷地下城（`has_available_dungeon()` 為 True），優先前往地下城。
  * 若地下城全在冷卻中，自動進入 Stage 普通關卡。

---

## 6. 模組關聯與組件索引

| 組件名稱 | 檔案路徑 | 職責 |
| :--- | :--- | :--- |
| **全域攔截處** | `states/state_machine.py` | 於 `step()` 開頭呼叫體力不足檢測 |
| **退避邏輯** | `states/stamina_flow.py` | 關閉彈窗、退回城鎮、備份與切換模式 |
| **恢復邏輯** | `states/handlers/collect_only.py` | 監測退避時間與自動還原配置 |
| **全域配置** | `config.py` | 定義 `stamina_retreat_duration` 等參數 |
| **單元測試** | `tests/test_state_machine_logic.py` | 驗證觸發、備份、定時恢復與模式切換 |
