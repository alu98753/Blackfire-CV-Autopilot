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

---

## 🛠️ 環境配置與安裝指引 (How to Build & Setup)

1. **建立 Python 虛擬環境**：
   在專案根目錄下打開終端機執行：
   ```powershell
   python -m venv .venv
   ```
2. **啟動虛擬環境並安裝依賴套件**：
   ```powershell
   # 啟動虛擬環境
   .\.venv\Scripts\Activate.ps1
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

## 📖 啟動掛機說明

1. **普通關卡模式**：
   手動選好關卡，並將遊戲畫面停留在**去戰鬥 (能看見 `stages/start.png` 的準備畫面)**：
   ```powershell
   .\.venv\Scripts\python main.py --mode stage
   ```
2. **史萊姆地下城模式**：
   將遊戲畫面停留在**最外層的大廳/城鎮畫面 (能看到 `common/door.png` 入口圖標的畫面)**：
   ```powershell
   .\.venv\Scripts\python main.py --mode dungeon_slime
   ```
   * **自訂參數**：
     * `--title "自訂標題"`：變更要匹配的視窗名稱。
     * `--interval 秒數`：調整畫面偵測間隔。預設為 `0.3` 秒。
     * *範例*：`.\.venv\Scripts\python main.py --mode dungeon_slime --interval 0.5`
3. **安全終止**：
   在終端機按 `Ctrl + C` 可安全終止腳本並輸出掛機統計資訊（如啟動戰鬥場次）。

---

## 🤖 AI 開發者指南 (AI Developer Guide)

如果您是協同開發的 AI Coding Agent：
1. **工作規範**：在進行任何代碼修改前，請務必先閱讀工作區自訂技能規範檔案：[.agents/skills/state_machine_development/SKILL.md (開發規範)](file:///e:/Side_Project/.agents/skills/state_machine_development/SKILL.md)。
2. **決策樹文件**：可透過讀取 [docs/dungeon_flow.md (流程圖)](file:///e:/Side_Project/BlackfireCrusade_tool/docs/dungeon_flow.md) 來快速了解地下城探索與體力領取的比對決策邏輯。
3. **迴歸測試**：重構或修改狀態機代碼後，請**必須執行**以下測試以確保邏輯無損：
```powershell
.\.venv\Scripts\python tests/test_state_machine_logic.py
```


## 開發中與待辦功能 (TODOs)

- **[待辦] 自動掏選不同地下城(支援第一個 第二個等模式選擇
- **[待辦] 現在不知道為何背包滿了要清理的情況會等很久才按下開啟背包
- **[待辦] 為了讓稀有戰利品不被誤分解(即使現在可以判斷顏色了),我希望在戰鬥結束畫面(也就是continue處) 判斷到"獲得戰利品" 跟continue同時存在時 去紀錄有哪些要鎖定 如果有 就接著去背包鎖定(如果已經鎖定(只有解鎖的字樣沒有鎖定的字樣) 就退出 (不要再繼續按了))) 如果沒有就再戰鬥 retry