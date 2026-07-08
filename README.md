# Blackfire Crusade 自動化副本掛機輔助工具

本專案是一個基於 OpenCV 圖像模板匹配與 PyAutoGUI 自動化點擊開發的 《Blackfire Crusade》 副本自動掛機輔助腳本。專為 PC 視窗模式（如 Steam 版本）設計，通過視覺偵測自動完成遊戲大廳、戰鬥、結算、下樓、清理背包及定時獎勵領取的完整閉環掛機流程。

---

## 🚀 主要功能特點

1. **模組化狀態機調度 (State Pattern)**：
   * 採用狀態模式設計，將大廳 (`LOBBY`)、戰鬥 (`BATTLE`)、探索 (`EXPLORING`)、結算 (`RESULT`)、領體力/鑽石導航 (`NAVIGATING`)、背包清理 (`BAG_CLEANING`) 及背包滿自適應分選 (`BACKPACK_FULL_SORTING`) 拆分為獨立處理器類別，由主調度器分配執行。
2. **自動戰鬥啟用與 CD 控制**：
   * 進入戰鬥後，偵測「自動戰鬥」按鈕是否為未啟用狀態，若是則執行點擊啟用。內置 3 秒冷卻時間，防止因延遲重複點選而關閉已啟用的自動戰鬥。
3. **多段結算 PK 比對 (Multi-Stage Result)**：
   * 搜尋並加載所有結算繼續按鈕模板（`templates/common/continue*.png`）。比對時僅點選相似度最高的有效前台按鈕，完全無視背景殘留變暗按鈕的干擾，順暢通過多重結算頁面。
4. **自動定時領體力與鑽石 (Timer Claiming)**：
   * **領體力**：每隔 30 分鐘自動攔截尋路，點擊體力入口圖示並領取，具備體力已滿提示自動關閉的容錯處理。
   * **領鑽石**：每隔 2 小時自動點選 `goback_town` 返回城鎮並點擊鑽石入口。
   * **鑽石安全保護**：開啟鑽石視窗後，程序會鎖定在視窗內，只匹配 `diamond_free.png` (閥值 0.90) 或關閉按鈕，避免點擊到背景圖標或付費禮包。若鑽石處於冷卻時間（無免費領取按鈕），會點擊關閉按鈕安全退出。
   * **優先級**：體力與鑽石定時器同時到期時，優先執行領鑽石流程，隨後執行領體力。
5. **地圖探索事件記憶與下樓冷卻**：
   * 地下城隨機事件（開寶箱、選技能卡、接受祝福）被點擊後，立即標記為本層已完成，後續畫面比對中予以跳過，防止重複點擊。
   * 點選下樓按鈕後開啟 6 秒過渡期冷卻計時，防止載入下一層的時間差內重複點選舊圖示。
6. **滑鼠手動介入偵測 (Manual Interruption)**：
   * 當手動移動滑鼠（位移大於 5 像素）且距離腳本上次操作超過 1.2 秒時，腳本自動暫停並鎖定當前狀態，方便玩家臨時手動操作。
   * 滑鼠靜止達 3 秒後，腳本自動恢復運行。此機制僅檢測滑鼠移動，玩家使用鍵盤操作（如打字聊天）不會觸發暫停。
7. **背包滿自適應分選與低稀有度銷毀 (Smart Sorting)**：
   * 當彈出「無法容納的物品 (背包已滿)」彈窗 (`backpack_full.png`) 時，立即進入分選狀態：
     * **稀有度識別**：提取左側溢出格與右側背包格（內圈環狀取樣區 offset 10~20，標準差篩選：左側 > 40.0，右側 > 20.0）並在 HSV 色彩空間中判定裝備稀有度。
     * **銷毀與收納**：若左側有藍色及以上物品（紫、黃、橘、紅邊框），點選右側的低稀有度物品（綠色或灰色），點擊 `destroy.png` ➔ `confirm.png` 進行銷毀，隨後點選左側貴重物品 ➔ 點擊 `collect.png` 領取。
     * **滾動搜尋與安全關閉**：右側無低稀有度物品時，自動向下滾動（最多 3 次）。若仍無可銷毀物件，或左側已無貴重物品，則點擊關閉按鈕（精準座標 offset 1228, 50），並比對點擊二次確認彈窗，返回 `STATE_UNKNOWN`。
8. **背包自動清理分解與貴重保留 (Bag Cleaning & Reservation)**：
   * 當從自適應分選退出，或在戰鬥結算後回到大廳且 `need_bag_cleaning` 為 True 時，狀態機會自動轉移至 `BAG_CLEANING` 狀態。
   * **貴重保留流程**：點擊打開背包 ➔ 點擊大量分解 ➔ 點擊全選 ➔ **使用自適應環狀遮罩色彩分類法，自動掃描網格並反選保留藍、紫、橘黃、紅等稀有貴重裝備** ➔ 點擊分解 ➔ 確認彈窗 ➔ 點擊整理 ➔ 點擊退出關閉背包。
9. **貴重裝備色彩分類特徵工程 (Rare Gear Color Classification)**：
   * 內置獨立的色彩判定特徵工程（環帶採樣遮罩避開中心打勾與邊緣發光），並為紫、藍、橘黃、紅等各品質顏色設置了專屬的飽和度 $S$ 與亮度 $V$ 閾值。
   * 詳細算法與防禦大石棒等灰色裝備的過濾參數請參閱專屬文件：[bag_color_classification.md (色彩特徵說明文件)](file:///e:/Side_Project/BlackfireCrusade_tool/docs/bag_color_classification.md)。
10. **通用戰敗重新開始 (Defeat Retry)**：
    * 當自動戰鬥失敗並跳轉到戰敗結算畫面（`defeat.png`）時，程式會自動識別，並以「雙保險」機制點選重新開始：
      * 優先搜尋匹配 `defeat_retry.png` 或 `stages/retry.png` 按鈕進行精準點擊；
      * 若無匹配，則以戰敗大圖的中心點進行左下角相對座標 `(X - 140, Y + 250)` 的防禦性點擊重啟，確保不卡死並順暢累加戰鬥場次。

---

## 🛠️ 環境配置與安裝指引 (How to Build & Setup)

1. **建立 Python 虛擬環境**：
   在專案根目錄下打開終端機執行：
   ```powershell
   python -m venv .venv
   ```
2. **啟動虛擬環境並安裝依賴套件**：
   ```powershell
   # 啟動虛擬環境 (PowerShell 執行 .\.venv\Scripts\Activate.ps1 / CMD 執行 .\.venv\Scripts\activate.bat)
   .\.venv\Scripts\activate
   # 安裝 OpenCV, PyAutoGUI, mss 等依賴套件
   pip install -r requirements.txt
   ```
3. **確認遊戲視窗**：
   開啟遊戲（必須保持前台可見，不能最小化），執行視窗偵測腳本：
   ```powershell
   .\.venv\Scripts\python list_windows.py
   ```
   確認輸出中包含遊戲視窗標題 `Blackfire Crusade`。
4. **裁剪自定義範本圖片 (選用)**：
   若因解析度差異需重新裁剪模板，可執行模板裁剪工具：
   ```powershell
   .\.venv\Scripts\python crop_tool.py
   ```
   * 程式倒數 5 秒後擷取視窗，在畫面上拖曳滑鼠框選按鈕，按 `Enter` 鍵確認選取，輸入檔名並儲存到 `templates/` 下的對應文件夾中。

---

## 📖 啟動指令與模式指南 (Usage & Modes Guide)

本工具支援多種執行模式與靈活的指令參數，可完美適配前台實體操作與後台不搶占掛機需求。

### 1. 指令參數說明 (Command-Line Arguments)

啟動腳本時，您可以搭配以下參數：

| 參數 | 類型 | 預設值 | 說明 |
| :--- | :--- | :--- | :--- |
| `--mode` | 字串 | `dungeon_slime` | **掛機模式**：可選 `stage` (一般關卡)、`dungeon_slime` (史萊姆地下城)、`bag_clean` (單次背包整理分解)。 |
| `--backend` | 切換旗標 | 關閉 | **啟用後台掛機模式**。滑鼠不會被腳本強行移動，您可以將遊戲放置在延伸大螢幕（DPI=1.0）背景，並在主螢幕繼續您的日常辦公、瀏覽網頁或遠端遙控，點擊完全獨立且不干涉。 |
| `--interval` | 浮點數 | `0.05` | 畫面偵測的間隔時間（秒）。預設 `0.05` 確保最高回饋速度，若想降低 CPU 佔用可調高（如 `0.2` 或 `0.3`）。 |
| `--title` | 字串 | `Blackfire Crusade` | 遊戲視窗名稱。如果多開或標題不同時可手動指定。 |
| `--human` | 切換旗標 | 關閉 | **模擬人類操作**（僅在前台模式有效）。滑鼠會以隨機二次曲線（EaseOutQuad）移動，並在點擊間隙產生防作弊隨機微小時間偏移。 |

---

### 2. 核心模式執行方法

#### 🔹 模式 A：史萊姆地下城自動探索 (`--mode dungeon_slime`)
* **功能**：自動在大廳進入地下城、下樓、貪婪模式挑選、接受祝福/開啟寶箱、戰鬥、背包滿時自動銷毀垃圾並收集貴重物、定時自動回城領鑽石與體力。
* **前置要求**：將遊戲畫面停留在**最外層的大廳/城鎮畫面（能看到右下角 `common/door.png` 傳送門圖標）**。
* **啟動指令（後台不搶滑鼠模式，推薦）**：
  ```powershell
  .\.venv\Scripts\python main.py --mode dungeon_slime --backend
  ```
* **啟動指令（前台實體滑鼠移動模式）**：
  ```powershell
  .\.venv\Scripts\python main.py --mode dungeon_slime
  ```

#### 🔹 模式 B：普通關卡自動刷關 (`--mode stage`)
* **功能**：自動點擊開始關卡、戰鬥、結算（識別 continue 並點擊）、戰敗自動重新開始（雙保險防禦點擊）。
* **前置要求**：手動選好關卡，並將遊戲停留在**關卡準備去戰鬥畫面（能看見右下角黃色 `stages/start.png` 按鈕）**。
* **啟動指令**：
  ```powershell
  .\.venv\Scripts\python main.py --mode stage --backend
  ```

#### 🔹 模式 C：單次自動分解與整理背包 (`--mode bag_clean`)
* **功能**：啟動後會主動打開背包、大量分解、全選、**逐格反選貴重保留品質（依據您在啟動問答時的選擇，不會誤分解貴重物）**、點擊分解與二次確認、整理背包，最後關閉退出背包並**自動關閉終端機程序**。
* **前置要求**：將遊戲畫面停留在**最外層的大廳/城鎮畫面（能看到底部 `common/bag_text.png` 背包文字按鈕）**。
* **啟動指令**：
  ```powershell
  .\.venv\Scripts\python main.py --mode bag_clean --backend
  ```

---

### 3. 視覺化調試輔助：`debug_click.png`

在啟用 `--backend`（後台模式）時，程式在送出每次點擊前都會在當前視窗畫面上繪製標記：
* **標記樣式**：點擊的物理相對座標處會畫上 **紅色圓圈與十字準星**，並標註 `Click: (X, Y)` 物理座標。
* **儲存檔案**：輸出為專案根目錄下的 **`debug_click.png`**。
* **用途**：此功能為純視覺排查工具，對掛機無任何負擔。如果您發現程式點擊了錯誤的按鈕（例如點偏），可以隨時打開 `debug_click.png`，一眼看清紅圈有沒有準確覆蓋在您的目標按鈕中心，協助您極速核對位置。

---

### 4. 安全暫停與終止
* **手動介入暫停**：掛機時若手動移動滑鼠，程式會偵測到使用者介入並自動暫停（鎖定當前狀態），滑鼠靜止 3 秒後自動恢復。
* **安全終止**：在 PowerShell 視窗中隨時按下 `Ctrl + C`，即可安全退出掛機並在畫面輸出本次掛機的戰鬥場次統計資訊。

---

## 🤖 AI 開發者指南 (AI Developer Guide)

如果您是協同開發的 AI Coding Agent：
1. **工作規範**：在進行任何代碼修改前，請務必先閱讀工作區自訂技能規範檔案：[.agents/skills/state_machine_development/SKILL.md (開發規範)](file:///e:/Side_Project/.agents/skills/state_machine_development/SKILL.md)。
2. **決策樹文件**：可透過讀取 [docs/dungeon_flow.md (流程圖)](file:///e:/Side_Project/BlackfireCrusade_tool/docs/dungeon_flow.md) 來快速了解地下城探索與體力領取的比對決策邏輯。
3. **圖像亮度與背景過濾診斷**：若遇到按鈕因為大廳/關卡背景變暗而導致誤匹配（例如將背景調暗的 continue 按鈕誤判為前景按鈕點擊），可使用我們提供的專屬分析工具進行診斷：
   ```powershell
   # 預設診斷最近一次後台點擊截圖 (debug_click.png) 與繼續按鈕 (continue.png) 之間的亮度比例
   .\.venv\Scripts\python tools/analyze_template_brightness.py
   
   # 或指定自訂的截圖與模板進行高精確匹配與亮度比例分析
   .\.venv\Scripts\python tools/analyze_template_brightness.py -s <截圖路徑> -t <模板路徑>
   ```
   * **輸出結果**：工具會自動在根目錄輸出標記有相似度與亮度比例的 `debug_analyze_full.png` 全螢幕圖與 `debug_analyze_crop.png` 匹配切片，並給出是否屬於背景暗區的建議，便於微調過濾閾值。
4. **迴歸測試**：重構或修改狀態機代碼後，請**必須執行**以下測試以確保邏輯無損：
```powershell
.\.venv\Scripts\python tests/test_state_machine_logic.py
```


## 開發中與待辦功能 (TODOs)

- **[待辦] 自動掏選不同地下城** (支援第一個、第二個等模式選擇)。
- **[待辦] 多顯示器/跨延伸螢幕 DPI 縮放自適應對齊（暫緩開發）**：
  * **背景現象**：當遊戲視窗置於具有 DPI 縮放（如 1.25 倍或 1.5 倍）的延伸小螢幕（筆電螢幕）時，前台（pyautogui）與後台（PostMessage）點擊皆會產生偏置（例如點鑽石時偏右點到排行榜）；而當視窗置於無縮放（1.0 倍，DPI=96）的外接大螢幕時，前台點擊可精準運行，但後台點擊若未正確處理座標系亦會產生偏差。
  * **原因剖析**：
    1. 腳本進程在 `main.py` 開頭宣告為 DPI Aware 自適應後，OpenCV 的圖像匹配與 `win32gui` 回傳的皆為真實的 **物理像素座標**。
    2. 然而，作業系統在處理 `pyautogui` 移動或後台 `PostMessage` 時，接收的引數皆為 **邏輯座標 (Logical Pixels / Client Coordinates)**。
    3. 在有 DPI 縮放的顯示器中，`物理座標 = 邏輯座標 * DPI 縮放比例`。如果沒除以縮放比例直接將物理像素（例如 1392）發送過去，系統會將其當作邏輯像素（邏輯 1392 * 1.5 = 物理 2088），導致點擊位置偏離到極右方。
  * **解決方案思路**：
    * **後台模式 (PostMessage)**：使用 `ctypes.windll.user32.GetDpiForWindow(hwnd)` 獲取視窗當前螢幕的 DPI 值，除以 96 得到 `dpi_factor`。發送點擊前，將相對於視窗左上角的物理座標除以該因子轉換為邏輯相對座標：`lParam = MAKELONG(rx_physical / dpi_factor, ry_physical / dpi_factor)`。
    * **前台模式**：棄用 pyautogui (邏輯座標)，改用 `win32api.SetCursorPos((abs_x, abs_y))` (物理座標) 與 `win32api.mouse_event` 發送點擊，可完全免除 DPI 縮放換算。
- **[已擱置] 為了讓稀有戰利品不被誤分解(即使現在可以判斷顏色了),我希望在戰鬥結束畫面(也就是continue處) 判斷到"獲得戰利品"這五個字  跟continue同時存在(可能在不同位置 圖片供你參考)時 去紀錄有哪些要鎖定 如果有 就接著去背包鎖定(如果已經鎖定(只有解鎖的字樣沒有鎖定的字樣) 就退出 (不要再繼續按了))) 如果沒有就再戰鬥 retry

這個在一般關卡 跟地下城 探索但背包滿了 或是 bag_clean 時候 是都要 觸發的 通用的邏  先思考你需要什麼圖片資源 與計畫