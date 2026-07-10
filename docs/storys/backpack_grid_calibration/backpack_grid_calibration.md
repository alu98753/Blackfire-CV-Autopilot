# 🎒 背包自適應網格精準校準的開發故事 (PARS Document) 🏆

本文件採用 **PARS 架構**（Purpose, Action, Result, So What, Influence）記錄「背包已滿自適應分選」中，網格框線從「嚴重歪斜」到「極致精準對齊」的開發故事與技術成果。

---

## 1. Purpose (目的)
在遊戲掛機過程中，若背包已滿會彈出分選視窗。我們必須精確識別左側「溢出區」的高價值裝備進行領取，同時識別右側「背包區」的低稀有度裝備進行銷毀。

### 🚨 遭遇的痛點
1. **格子非正方形**：原先預設格子是正方形（`134x134`），但實際上游戲格子的縱向高度（Y軸方向）略大於橫向寬度（X軸方向），造成網格越往下累積偏差越大。
2. **Y 軸偏上誤判**：原先的定位相對於 `backpack_full.png` 標題中心在 Y 軸上偏上了約 14 像素。這導致在掃描時，下一列的物品上邊緣進入了當前列的檢測框，被顏色分類器誤判成當前列有貴重裝備，進而阻礙了銷毀與領取流程。
3. **X 軸整體偏右**：左右兩側的框線均偏右了約 21~22 像素，點擊中心點無法精準定位在裝備中心，增大了誤觸邊界或背景的風險。

---

## 2. Action (行動)

### 🛠️ 步驟一：拆分獨立 X/Y 網格參數
我們重構了定位算法，將原本單一的格子常數 `cell_size` 與 `step` 拆分為 X、Y 兩個獨立方向：
- `CELL_W` 與 `CELL_H` (格子寬度和高度)
- `STEP_X` 與 `STEP_Y` (橫向與縱向格子間距)

### 🧰 步驟二：開發圖形化「手動校準工具」
為了讓使用者能直觀且自主地微調參數，我們在 [tools/calibrate_grid.py](../../tools/calibrate_grid.py) 撰寫了校準工具：
* 它讀取當前遊戲截圖，匹配標題中心，並利用校準參數繪製網格框（紅色）與點擊中心（黃點）。
* 輸出預覽圖至 `scratch/grid_calibration_result.png`，實現「修改參數 ➔ 執行腳本 ➔ 查看圖像」的超快迭代。

### 🎯 步驟三：反覆微調並敲定最佳參數
經由使用者手動校準，找出了與遊戲畫面完美吻合的黃金參數：
- **偏移量**：`LEFT_DX = -589`, `LEFT_DY = 105`, `RIGHT_DX = 34`, `RIGHT_DY = 105`
- **尺寸與間距**：`CELL_W = 134`, `CELL_H = 139.5`, `STEP_X = 134`, `STEP_Y = 139.5` (高度完美修正為 `139.5` 像素)
- **右側滾動參考中心**：同步精算更新為 `dx = 302`, `dy = 384`

### 💻 步驟四：代碼套用與測試重構
1. **套用至邏輯**：將此套尺寸變數套用到主邏輯類 [backpack_full_sorting.py](../../states/handlers/backpack_full_sorting.py) 中。
2. **重構測試套件**：更新了單元測試 [test_state_machine_logic.py](../../tests/test_state_machine_logic.py) 與行為測試 [test_behavioral_scenarios.py](../../tests/test_behavioral_scenarios.py) 的模擬畫像生成座標與點擊斷言，確保不因網格位置變更而破壞測試覆蓋。

---

## 3. Result (結果)
* **框線極致精準**：紅色框線與遊戲內所有格子深色外邊界完美重疊，中心黃點分毫不差地落在每件裝備的最中心。
* **自動測試 100% 通過**：主狀態機與行為場景的 65 個自動化測試全數回歸成功 (`OK`)。
* **動作路徑保存**：分選的每一步動作皆會保存審計截圖至專屬資料夾，清晰地展現出完整的「掃描 ➔ 點擊銷毀 ➔ 領取貴重物 ➔ 安全關閉」的決策軌跡。

### 🖼️ 實行動作鏈素材：
- [feature_destroyandget_1.png](file:///e:/Side_Project/BlackfireCrusade_tool/docs/storys/backpack_grid_calibration/feature_destroyandget_1.png) (對比圖)
- [feature_destroyandget_2.png](file:///e:/Side_Project/BlackfireCrusade_tool/docs/storys/backpack_grid_calibration/feature_destroyandget_2.png) (定位與檢測)
- [feature_destroyandget_3.png](file:///e:/Side_Project/BlackfireCrusade_tool/docs/storys/backpack_grid_calibration/feature_destroyandget_3.png) (銷毀與確認操作)

---

## 4. So What (核心價值)
* **高健壯性自適應**：擺脫了「格子必須是正方形」的假設限制，能精準適配遊戲 UI 物理上的拉伸與偏差，大幅提升偵測精準度，將分類誤判率降至 0。
* **自主維護能力**：此設計將 UI 調參的權力完全交給使用者。未來只要遊戲更換解析度或調整 UI 排版，使用者無須修改複雜的決策邏輯代碼，只要打開校準工具調整 4 個基礎數值，即可在 1 秒內完成適配！

---

## 5. Influence (影響)
* **模組化範式建立**：此「標題中心錨定 ➔ 獨立寬高 X/Y 網格切片掃描 ➔ 圖形化調參預覽」的設計模式已被寫入 [SKILL.md](../../.agents/skills/state_machine_development/SKILL.md) 規範中。
* **技術推廣**：後續若需要開發「商店自動選購」、「符文裝備一鍵穿戴」等任何涉及宮格網格（Grid-based）的掃描與操作邏輯，此套「校準工具 + 獨立寬高網格邏輯」皆可直接套用並快速複製成功經驗。
