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
   * 退避目標時間由配置檔 `stamina_retreat_duration` 決定（`collect_only` 預設 7 小時）。
3. **恢復執行**：
   * 當 `elapsed >= retreat_seconds` 時，觸發恢復。
   * 還原原配置：`state_machine.config = state_machine.original_config`。
   * 重置 `state_machine.original_config = None` 與 `state_machine.stamina_retreat_start_time = None`。
   * 將狀態切換至 `STATE_UNKNOWN` 觸發全域重新定位。

---

## 5. 多模式相容性與防呆機制

### 5.1 普通關卡模式 (`stage`)
* 退避恢復後，自動於大廳重新定位並繼續進行 Stage 尋路與刷關。

### 5.2 地下城模式 (`dungeon`)
* 退避恢復後，自動進入地下城選單，繼續進行地下城探索。

### 5.3 混合模式 (`mix`) / 每日任務 (`daily`)
* `original_config` 保存體力耗盡當下被中斷的執行路由；若當時正在跑 Stage 懸賞，它可以是沒有地下城策略欄位的臨時 Stage 配置。
* Daily 的長期活動策略持續保存在 `primary_config`。`CollectOnlyHandler` 判斷 `auto_resume_dungeon_on_cd`、`greedy_dungeon` 與允許副本時，以這份策略為準，不會被臨時懸賞路由遮蔽。
* 地下城冷卻結束後建立獨立的 active dungeon route；`original_config`、未完成懸賞排程器與 `stamina_retreat_start_time` 均保持不變。
* 退避恢復後，`mix` / `daily` 導航邏輯會重新檢測全地下城 CD：
  * 若有可刷地下城（`has_available_dungeon()` 為 True），優先前往地下城。
  * 若地下城全在冷卻中，自動進入 Stage 普通關卡。

### 5.4 安全防呆過濾 (`has_available_dungeon`)
* 支援 `has_available_dungeon(target_config=...)` 帶入評估配置。
* **智慧自動備援**：仍停在 `collect_only` 且處於體力退避狀態時，未傳參數會回退讀取 `original_config`；scheduler 提交 dungeon resume route 後，改以 active route 評估，避免被中斷前的 Stage 配置遮蔽。
* **非地下城模式隔離**：若評估配置之 `type` 為非地下城模式（如純 `collect_only` 或 `stage`），安全回傳 `False`，避免誤拋 `ValueError` 中斷程式。

### 5.5 純領取模式 (`collect_only`) 大廳退回城鎮修復
* 於 `--mode collect_only` 領完體力視窗關閉後（狀態轉為 `NAVIGATING`）：
* 因為 `collect_only` 配置之 `navigation_path` 為空 `[]`，系統會自動在畫面上搜尋 `goback_town.png`（返回城鎮按鈕），點擊退回城鎮並轉移至 `STATE_COLLECT_ONLY` 待機，避免在 `NAVIGATING ↔ LOBBY` 之間發生死迴圈跳轉。

### 5.6 體力退避期間常規關卡禁絕律與地下城喚醒契約 (Stamina Retreat Supremacy Invariant)
* **常規關卡絕對禁用**：當系統處於體力退避期間 (`stamina_retreat_start_time is not None`)，常規關卡打怪 (`enable_stage_farming`) 必須被絕對禁用 (`False`)。
* **臨時喚醒路由純潔性 (`build_dungeon_resume_route`)**：從 `COLLECT_ONLY` 因地下城冷卻結束而喚醒的執行路由，其能力邊界僅限於該特定地下城本身。路由明確設定 `enable_stage_farming = False`、`tier4_mode = "none"`、`is_dungeon_temporary_resume = True`，並完全移除普通關卡尋路路徑 (`stage_entry`, `stage_navigation_path`)。
* **冷卻耗盡即時歸位律**：當臨時喚醒之地下城通關或所有允許之地下城再度進入冷卻時，活動調度器 (`evaluate_next_activity`) 與導航器 (`NavigationHandler`) 必定點擊 `goback_town.png` 返回城鎮並轉移至 `STATE_COLLECT_ONLY`，絕不切換至普通關卡頁籤。


## 6. 模組關聯與組件索引

| 組件名稱 | 檔案路徑 | 職責 |
| :--- | :--- | :--- |
| **全域攔截處** | `states/state_machine.py` | 於 `step()` 開頭呼叫體力不足檢測與 `has_available_dungeon` 備援過濾 |
| **退避邏輯** | `states/stamina_flow.py` | 關閉彈窗、退回城鎮、備份與切換模式 |
| **恢復與待機** | `states/handlers/collect_only.py` | 監測退避時間、冷卻結束自動切回 (`auto_resume_dungeon_on_cd`) 與還原配置 |
| **導航與再退避** | `states/handlers/navigation.py` | 全冷卻再退避轉移、大廳退回城鎮離場 |
| **全域配置** | `config.py` | 定義 `stamina_retreat_duration` 與 `auto_resume_dungeon_on_cd` 參數 |
| **單元測試** | `tests/test_daily_pipeline_stamina_retreat.py` | 驗證觸發、備份、Daily policy 喚醒、定時恢復與模式切換 |
