# Blackfire Crusade 圖像匹配亮度診斷工具使用手冊

本目錄專門放置與本專案圖像匹配（DPI 縮放、亮度偏差、背景遮罩過濾）相關的調試診斷工具與說明文件。

---

## 🔍 1. 自動背景調暗過濾與存檔機制

為了防止遊戲在彈出前景彈窗時，程式誤匹配背景已被調暗的按鈕（例如背景變暗的「繼續」按鈕），我們在 `vision/matcher.py` 內置了**自適應亮度比例過濾器**：

* **運作機制**：
  * 當相似度達標且啟用 `check_brightness=True` 時，底層 `match` 方法會自動比對「匹配到的切片」與「模板」的平均灰度亮度比例。
  * **當亮度比例低於 0.8**（即匹配區亮度不到模板的 80%）時，程式會判定其為背景調暗按鈕並予以過濾。
  * **自動診斷存檔**：被過濾的瞬間，`Matcher` 會**自動**在專案根目錄下存檔以下兩張圖片：
    1. **`debug_{template_name}_dim_full.png`**：標記有紅色定位框、Confidence 和 Ratio 數據的全螢幕截圖。
    2. **`debug_{template_name}_dim_crop.png`**：匹配到的局部按鈕切片圖片。
  * **快速排查**：當您在掛機日誌中看到警告時，可以直接打開這兩張圖片，一眼看清當時是否有前景按鈕、還是誤判了背景。

---

## 📊 2. 圖像匹配與亮度分析工具

我們在 `tools/` 目錄下提供了一款獨立的可重用診斷工具：

### 🛠️ 啟動指令

如果您手動保存了某些特定影格的遊戲截圖，或者想要手動比對 `debug_click.png` 與模板之間的亮度數據，可隨時運行：

```powershell
# 預設診斷最近一次點擊的 debug_click.png 與 continue.png
.\.venv\Scripts\python tools/analyze_template_brightness.py

# 指定自訂的截圖路徑與模板路徑進行診斷
.\.venv\Scripts\python tools/analyze_template_brightness.py -s <截圖檔案路徑> -t <模板圖片路徑>
```

### 📋 輸出數據意義

* **Confidence (匹配相似度)**：OpenCV 的 `cv2.TM_CCOEFF_NORMED` 匹配度，介於 0.0 ~ 1.0 之間。
* **Ratio (實質亮度比例)**：`切片平均亮度 / 模板平均亮度`。
  * `Ratio >= 0.8`：屬於正常的前景高亮按鈕，程式會進行點擊。
  * `Ratio < 0.8`：屬於被黑色遮罩調暗的背景，程式會自動過濾。
* 工具會在本地輸出標記有紅框和數值的 `debug_analyze_full.png` 和 `debug_analyze_crop.png` 用於視覺化分析。
