# 地下城探索決策優先級與冷卻機制 ⚔️

本文件記錄 `ExploreHandler` 在地下城探索過程中的按鈕匹配優先級與過渡冷卻規範。

---

## 1. 執行檔案
* `states/handlers/explore.py`
* `config.py`

## 2. 按鈕比對優先順序
在探索狀態中，比對順序嚴格區分為：
1. **高優先權（對話框/彈窗）**：
   - `dungeons_complete.png`
   - `choice_bless.png`
   - `Get_tresure_comfirm.png`
   - **目的**：優先處理彈窗，防止誤點背景圖像。
2. **低優先權（背景圖標）**：
   - `gungeon_godown.png` (下樓入口)
   - `Treasure.png` (寶箱)

---

## 3. 下樓冷卻過渡機制
- **下樓冷卻時間**：點選下樓按鈕後開啟 **4 秒過渡期冷卻計時** (`last_godown_time`)。
- **目的**：防止在載入下一層的時間差內重複點選舊圖示造成死迴圈。
