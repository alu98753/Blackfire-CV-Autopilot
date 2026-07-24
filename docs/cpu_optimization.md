# 🔍 BlackfireCrusade_tool 架構審查與 CPU 耗能優化提案

此文件針對本專案的「畫面擷取」、「模板匹配」與「狀態機調度」三大核心模組進行深入的效能審查。參考了業界成熟的掛機助手（如 ALAS, MAA）的工程思路，提出具體的優化技術路線。

---

## 🛑 當前架構的三大 CPU 效能瓶頸

### 1. 後台截圖中 PrintWindow 與 BitBlt 的無謂重複嘗試 (I/O & GDI 資源消耗)
* **問題點**：在 [capture/screen.py](file:///e:/Side_Project/BlackfireCrusade_tool/capture/screen.py#L116-L176) 的 `_capture_backend` 中，每次擷取都會先呼叫 `PrintWindow`。如果該遊戲視窗的顯示引擎（如 DirectX/OpenGL 加速）導致 `PrintWindow` 傳回全黑或失敗，程式會拋出異常並進入 `except`，隨後**再次建立一組 GDI 物件並執行傳統的 `BitBlt` 複製**。
* **後果**：這導致每次截圖都要經歷一次異常捕獲、兩次 GDI 物件的頻繁創建與銷毀。

### 2. 氾濫的全螢幕模板匹配 (Full-Screen Template Matching)
* **問題點**：在 [vision/matcher.py](file:///e:/Side_Project/BlackfireCrusade_tool/vision/matcher.py#L78) 中，所有的 `match` 調用均是在整張遊戲畫面（通常是 1920x1080）中滑動尋找模板。在 [state_machine.py](file:///e:/Side_Project/BlackfireCrusade_tool/states/state_machine.py#L180-L244) 的主迴圈中，每一幀都會同時比對：
  * 卡死清除（confirm, ok, continue, quit - 共 4 次）
  * 背包已滿、任務完成（共 2 次）
  * 重新登入、體力檢測（共 2 次）
  * 當前狀態 Handler 的特定按鈕比對
* **後果**：每一幀進行高達 **8 ~ 10 次的全圖滑動窗口乘法運算**，直接讓單個核心的 CPU 被矩陣計算填滿。

### 3. 高頻率與低頻率事件「一視同仁」的輪詢頻率
* **問題點**：諸如「背包滿了」、「任務完成」、「重新登入」與「卡死清除」等事件，在遊戲運作中屬於**極低頻率發生的事件**。但在目前的狀態機 `step` 中，每一幀都在以高頻率（如每 0.5 秒）進行這些事件的全螢幕圖像比對。

---

## 💡 業界最佳實踐與優化路線 (Roadmap)

### 📌 優化一：局部感興趣區域 (Region of Interest, ROI) 限制比對
* **工程思路**：
  * 遊戲中的 UI 按鈕（如再戰按鈕、確定按鈕、返回城鎮等）絕大多數都出現在固定的比例座標區域。
  * 我們可以為 `GAME_CONFIGS` 中的各個模板或按鈕**定義對應的 ROI 矩形區域** (例如：`"common/confirm.png": {"left_pct": 0.4, "top_pct": 0.6, "width_pct": 0.2, "height_pct": 0.1}`)。
  * 在比對時，先根據當前視窗解析度裁切出該小區塊，僅對 **200x100 像素** 的小圖進行 `matchTemplate`。
  * **預期效果**：運算矩陣面積減少 95% 以上，**匹配速度提升 10~20 倍，CPU 佔用率降至微乎其微**。

### 📌 優化二：後台截圖的自適應狀態記憶 (Adaptive Backend Strategy)(已經完成)
* **工程思路**：
  * 在 `ScreenCapturer` 初始化時，設定一個狀態標記 `self.use_printwindow = True`。
  * 如果在第一次截圖時 `PrintWindow` 失敗（例如回傳 None 或全黑），則將該標記設為 `False`。
  * 在後續的生命週期中，**直接跳過 PrintWindow，改用傳統的 BitBlt**，消滅每一幀拋出 Exception 的 CPU 開銷。
  * 同時，快取 `saveDC` 與 `saveBitMap` 等 GDI 資源控制代碼，只有在視窗解析度改變時才重建。

### 📌 優化三：分級輪詢與低頻事件退避 (Tiered Polling Frequency)
* **工程思路**：
  * 將偵測事件分為兩類：
    1. **主流程事件（高頻輪詢）**：例如加載中、戰鬥結束、再戰按鈕等，維持當前 interval (如 0.5s) 偵測。
    2. **全域例外事件（低頻輪詢）**：例如背包滿、卡死檢查、任務完成、重新登入等。這些偵測加入時間戳限制，**每 3 ~ 5 秒才執行一次比對**。
  * **預期效果**：在 90% 的掛機時間內，每幀的圖像比對次數從 8 次減少到 1 次，大幅降低空轉時的能耗。

### 📌 優化四：金字塔下採樣匹配 (Image Pyramids Matching)(已經完成)
* **工程思路**：
  * 對於必須在全圖尋找的模板（如地下城隨機事件），在比對前先使用 `cv2.resize` 對來源圖與模板圖同步進行 **1/2 或 1/4 下採樣**。
  * 在縮小的圖上進行快速比對，定位到候選區域後，再將該區域映射回原圖進行小範圍的 1:1 精確對齊。
  * **預期效果**：對於大尺寸模板的匹配速度有 4 倍以上的效能提升。
