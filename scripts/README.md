# 專案維運與診斷工具手冊 (Scripts & Diagnostics Index) 🛠️

本目錄 (`scripts/`) 集中收納《黑火遠征》專案的所有**開發維護、圖像裁剪、座標校準、OCR 診斷、倍速熱注入與狀態除錯腳本**。

---

## 📂 工具清單與用途索引

| 腳本名稱 | 核心職責與用途 | 常用啟動指令 |
| :--- | :--- | :--- |
| **[crop_tool.py](crop_tool.py)** | 視覺模板交互式裁剪工具 (截圖選區並產生標準 1080p 模板) | `.\.venv\Scripts\python scripts/crop_tool.py` |
| **[list_windows.py](list_windows.py)** | 列出當前系統所有開啟之遊戲視窗與控制代碼 (HWND, PID, 標題) | `.\.venv\Scripts\python scripts/list_windows.py` |
| **[set_battle_settings.py](set_battle_settings.py)** | 戰鬥時鐘倍速破解與存檔唯讀鎖定工具 | `.\.venv\Scripts\python scripts/set_battle_settings.py --speed 5.0` |
| **[test_single_click.py](test_single_click.py)** | 單一模板圖像比對與後台模擬點擊獨立診斷工具 | `.\.venv\Scripts\python scripts/test_single_click.py -t common/quit.png --click` |
| **[analyze_template_brightness.py](analyze_template_brightness.py)** | 模板與截圖之灰度亮度比例 (Ratio) 與相似度 (Confidence) 分析 | `.\.venv\Scripts\python scripts/analyze_template_brightness.py` |
| **[calibrate_grid.py](calibrate_grid.py)** | 背包已滿 18 格溢出區與背包區網格起點微調工具 | `.\.venv\Scripts\python scripts/calibrate_grid.py` |
| **[calibrate_bag_cleaning_grid.py](calibrate_bag_cleaning_grid.py)** | 背包大量分解 (134x139.5) 裝備網格錨點校準工具 | `.\.venv\Scripts\python scripts/calibrate_bag_cleaning_grid.py` |
| **[diagnose_bulletin_board_ocr.py](diagnose_bulletin_board_ocr.py)** | 懸賞告示牌 OCR 文字提取與字串正規化診斷 | `.\.venv\Scripts\python scripts/diagnose_bulletin_board_ocr.py` |
| **[diagnose_quest_ocr.py](diagnose_quest_ocr.py)** | 懸賞任務條目未接/已接互斥比對與文字辨識診斷 | `.\.venv\Scripts\python scripts/diagnose_quest_ocr.py` |
| **[diagnose_task_complete_ocr.py](diagnose_task_complete_ocr.py)** | 任務完成全域彈窗文字與領取按鈕檢測診斷 | `.\.venv\Scripts\python scripts/diagnose_task_complete_ocr.py` |
| **[diagnose_dpi_clicks.py](diagnose_dpi_clicks.py)** | 視窗縮放與 DPI 點擊偏差深度診斷工具 | `.\.venv\Scripts\python scripts/diagnose_dpi_clicks.py` |

---

## 🔍 圖像匹配與亮度診斷說明

為了防止遊戲在彈出前景彈窗時，程式誤匹配背景已被調暗的按鈕（例如背景變暗的「繼續」按鈕），底層 `TemplateMatcher` 內置了**自適應亮度比例過濾器**：
* **Confidence (匹配相似度)**：OpenCV 的 `cv2.TM_CCOEFF_NORMED` 匹配度（0.0 ~ 1.0）。
* **Ratio (實質亮度比例)**：`切片平均亮度 / 模板平均亮度`。
  * `Ratio >= 0.8`：屬於正常的前景高亮按鈕，程式會進行點擊。
  * `Ratio < 0.8`：屬於被黑色遮罩調暗的背景，程式會自動過濾。
