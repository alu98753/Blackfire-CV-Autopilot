# 混合模式 (Mix Mode) 動態瀑布流掛機架構規格書

## 1. 模式背景與設計哲學

`mix`（混合模式：關卡 + 地下城）為專案之預設執行模式。其核心哲學為**「地下城優先、普通關卡退守」**的瀑布流自動調度策略，旨在最大化地下城資源產出的同時，避免地下城進入全員冷卻時的閒置等待。

---

## 2. 瀑布流決策優先級 (Waterfall Priorities)

導航引擎在 `NAVIGATING` 狀態下，依以下優先級自動進行頁籤切換與關卡發起：

```
[NAVIGATING 導航]
   │
   ├── 1. 檢查地下城冷卻 (has_available_dungeon)
   │      ├── 有可用地下城 ──► 切換至地下城頁籤 (dungeon.png) ──► 挑戰地下城
   │      └── 無可用地下城 (全冷卻) ──► 轉入第 2 階段
   │
   └── 2. 轉入普通關卡退守
          └── 切換至關卡頁籤 (select_stage.png) ──► 地圖滾動/對齊 ──► 挑戰 Stage 關卡 (stage_target)
```

---

## 3. 頁籤狀態判定與防重入 (Tab State & Anti-Reentry)

為避免畫面加載動畫或連點造成的頁籤閃爍與重複觸發，系統引入雙向特徵對比判定：

1. **地下城選關介面 (`dungeon_select_open`)**：
   * 比對 `dungeons/dungeon_after.png` 或 `dungeons/cooldown_left.png` 或地下城解鎖卡片 (`Slime_entry`, `Ghost_entry` 等)。
   * 若 `dungeon_select_open == True`，防重入跳過 `dungeons/dungeon.png` 之點擊。
2. **普通關卡選關介面 (`stage_select_open`)**：
   * 比對 `stages/select_stage_after.png` 或關卡背景小島 (`level1` ~ `level6`)。
   * 若 `stage_select_open == True`，防重入跳過 `common/select_stage.png` 之點擊。

---

## 4. 冷卻監控與即時轉向

* **冷卻登記與 OCR 解析**：地下城通關或冷卻木牌讀取時，更新 `state_machine.dungeon_cooldowns`。
* **戰後即時切換**：Stage 戰鬥結束回到大廳或結算時，若檢測到有地下城 CD 已經結束，立即發出提示並點擊 `dungeons/dungeon.png` 優先切回地下城。
* **日誌透明化**：在每次切換頁籤與退守 Stage 時，輸出所有 5 個地下城的剩餘冷卻秒數與判定結果。

---

## 5. 相容性與測試保護

* 相關 Handler：`states/handlers/navigation.py`, `states/handlers/explore.py`, `states/handlers/result.py`
* 測試覆蓋：`tests/test_behavioral_scenarios.py` 之 `test_mix_mode_*` 系列測試案例，確保導航瀑布流邏輯 100% 覆蓋。
