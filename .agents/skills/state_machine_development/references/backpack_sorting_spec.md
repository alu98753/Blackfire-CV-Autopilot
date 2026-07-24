# 背包滿自適應裝備分選技術規格 (Backpack Sorting Spec) 🎒

本文件包含 `BackpackFullSortingHandler` 的詳細演算邏輯與幾何網格座標定義。

---

## 1. 執行檔案
* `states/handlers/backpack_full_sorting.py`

## 2. 幾何網格點定義
當在畫面上匹配到 `backpack_full_sort.png` (基準座標 `pos_full`) 時，彈窗左上角為：
- `win_x = pos_full[0] - 630`
- `win_y = pos_full[1] - 37`

網格幾何參數：
- **左側溢出區起點**：`left_x0 = 77`, `left_y0 = 190`
- **右側背包區起點**：`right_x0 = 677`, `right_y0 = 190`
- **單個格子尺寸**：`cell_size = 108`
- **步長間距**：`step = 134`

---

## 3. 雙區域篩選過濾器演算法
1. **左側溢出格 (貴重物品保護)**：
   - 取樣標準差 `std > 40.0`。
   - 使用 HSV 色環取樣檢測到藍、紫、黃、橘、紅時，視為貴重裝備，觸發點擊挪入右側背包。
2. **右側背包格 (垃圾裝備銷毀)**：
   - 取樣標準差 `std > 20.0`。
   - 使用 HSV 色環檢測到綠或灰時，視為可銷毀的低稀有度裝備，觸發勾選與銷毀。

---

## 4. 退出與清理連鎖
- **二次確認關閉**：點擊關閉 X 按鈕（座標為彈窗左上角 + `X=1228, Y=50`）後，擷取畫面匹配並點擊 `common/confirm.png` 以成功退出。
- **清理連鎖**：狀態轉移至 `BACKPACK_FULL_SORTING` 時，自動設置 `self.need_bag_cleaning = True`。退出後會自動由 `ExploreHandler` 或 `LobbyHandler` 攔截進入 `STATE_BAG_CLEANING` 進行大量分解。
