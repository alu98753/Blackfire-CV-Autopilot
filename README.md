# Blackfire Crusade 自動化副本掛機輔助工具 🎮

這是一個基於 **電腦視覺（Computer Vision / OpenCV 模板匹配）** 與 **GUI 自動化（PyAutoGUI）** 技術開發的 2D 回合制遊戲《Blackfire Crusade》自動副本掛機腳本。

本工具專為 PC 視窗模式（如 Steam 版本）設計，能自動偵測遊戲狀態（準備大廳、戰鬥中、結算畫面）並執行對應的操作（點擊開始、開啟自動戰鬥、點擊繼續與再次挑戰），省去手動重複點擊的時間。

---

## ✨ 核心特色與技術

1. **極速與輕量化**：
   * 採用 `mss` 高效畫面擷取，單次截圖僅需 10~30ms，CPU 佔用率極低（$< 1\%$）。
   * 支援 `PIL ImageGrab` 作為備份截圖方案，確保系統相容性。
2. **閉環反饋與 CD 重試控制 (Auto Toggle)**：
   * 透過比對未啟用的「自動戰鬥」模板，並配合 3 秒冷卻時間，可確保遊戲在延遲或漏點時自動重試，同時絕不會發生「重複點擊而將已啟用的自動戰鬥關閉」的問題。
3. **動態多段結算處理 (Multi-Continue Winner)**：
   * 自動搜尋並快取 `templates/common/continue*.png` 等所有繼續按鈕。
   * 比對時採取「相似度 PK 機制」，僅會點選畫面中相似度最高的有效前台按鈕，完全無視背景殘留變暗按鈕的干擾，順暢通過多重結算頁面。
4. **自動定時領體力 (Stamina / Bread)**：
   * 支援啟動時與每隔 30 分鐘自動進行體力領取（透過 `door` ➔ `bread` ➔ `bread_collection` ➔ `confirm` ➔ `quit_bread` 系列按鈕）。
   * 具備體力已滿提示自動跳過容錯處理，絕不卡死。
5. **模組化狀態機設計**：
   * 採用**狀態模式 (State Pattern)** 重構，狀態處理邏輯完全與主調度器解耦，易於擴充新狀態。
6. **防作弊模擬點擊**：
   * 滑鼠移動模擬人類平滑曲線軌跡，並加入微幅的隨機像素偏移與點擊冷卻，保護遊戲帳號。

---

## 📂 專案目錄結構

```
BlackfireCrusade_tool/
│
├── requirements.txt        # 依賴套件清單 (OpenCV, PyAutoGUI, mss 等)
│
├── list_windows.py         # [工具] 列出所有活動中的 Windows 視窗與大小
├── crop_tool.py            # [工具] 互動式滑鼠拖曳模板裁剪工具
│
├── docs/
│   ├── dungeon_flow.md     # [文件] 領體力與地下城事件優先級決策樹流程圖
│   └── future_work.md      # [文件] 未來工作規劃與 iPad 控制方案
│
├── capture/
│   └── screen.py           # 視窗擷取模組
├── vision/
│   └── matcher.py          # 模板匹配定位模組
├── actions/
│   └── mouse.py            # 模擬人類滑鼠點擊模組
│
├── config.py               # 遊戲模式與圖片優先級配置檔
├── main.py                 # 主程式掛機入口 (支援 --mode 參數)
│
├── states/
│   ├── __init__.py         # 匯出 GameStateMachine
│   ├── state_machine.py    # 狀態機主調度器與全域掃描
│   └── handlers/           # [模組化處理器]
│       ├── base.py         # 處理器基類
│       ├── navigation.py   # 處理尋路與領體力
│       ├── lobby.py        # 處理普通關卡準備大廳
│       ├── battle.py       # 處理自動戰鬥監控
│       ├── result.py       # 處理關卡多段結算
│       └── explore.py      # 處理地下城隨機探險事件
│
└── templates/              # 分類存放裁剪的按鈕模板小圖
    ├── common/             # 通用圖示 (auto, continue1/2, bread 系列)
    ├── stages/             # 普通關卡專用 (start, retry, continue3)
    └── dungeons/           # 地下城專用 (door, dungeon, Slime_entry, 隨機事件系列)
```

---

## 🛠️ 環境配置與安裝

請確保您的電腦已安裝 **Python 3.7 或以上版本**，並在專案根目錄下使用終端機執行：

1. **建立虛擬環境**：
   ```powershell
   python -m venv .venv
   ```
2. **安裝依賴套件**：
   ```powershell
   .\.venv\Scripts\pip install -r requirements.txt
   ```

---

## 📖 詳細使用指南

請依照以下 3 個步驟進行設定與啟動：

### 步驟 1：🔍 確認您的遊戲視窗名稱
開啟遊戲後（不可最小化），執行：
```powershell
.\.venv\Scripts\python list_windows.py
```
確認您的遊戲視窗標題為 `Blackfire Crusade`（預設），若不同，請在步驟 3 中加入參數。

---

### 步驟 2：✂️ 裁剪您的遊戲專屬按鈕模板
執行以下命令啟動裁剪工具：
```powershell
.\.venv\Scripts\python crop_tool.py
```
1. 終端機將開始 **5 秒倒數**，請立即點擊切換到遊戲視窗，將畫面停留在含有目標按鈕的畫面上。
2. 5 秒後，程式會自動擷取遊戲視窗並彈出裁剪視窗。
3. **操作方式**：左鍵拖曳拉出一個矩形，選中按鈕後按下 `Enter` 或 `Space` 鍵確認選取。（按 `ESC` 鍵可取消並退出）
4. 在終端機中輸入對應的檔名保存，並將產生的圖片放入 `templates/` 下對應的子資料夾。

> 💡 **模板裁剪最佳實踐（避開背景變動）**：
> 裁剪時，請**儘可能縮小範圍，僅框選按鈕內固定的文字（例如只框「繼續」或「再戰」這兩個字）**，避免將按鈕周圍的發光特效、動態背景或陰影剪進去。這樣即使遊戲背景如何變化，程式都能 100% 辨識成功。

---

### 步驟 3：🚀 啟動自動掛機
執行以下指令開始掛機：

* **普通關卡模式**：
  ```powershell
  .\.venv\Scripts\python main.py --mode stage
  ```
* **史萊姆地下城模式**：
  ```powershell
  .\.venv\Scripts\python main.py --mode dungeon_slime
  ```

* **可用自訂參數**：
  * `--title "視窗標題"`：如果您的遊戲視窗名稱不叫 `Blackfire Crusade`。
  * `--interval 秒數`：調整畫面偵測頻率。預設為 `0.5` 秒。
  * *範例*：`.\.venv\Scripts\python main.py --mode dungeon_slime --interval 0.5`

* **終止程式**：在終端機隨時按下 `Ctrl + C`，程式會安全退出，並為您統計本次掛機一共完成的場次。

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

- **每兩小時自動領取鑽石** (待開發)
- **背包滿清理自適應保留與篩選過濾** (規劃中)
  - **自適應保留等級**：目前偵測到背包滿時一律點擊 `bagfull_quit.png` 並進行全部分解。未來需實作自適應保留特定等級的裝備。
  - **篩選高稀有度裝備**：大量分解時應保留藍色以上的裝備（紫色、黃色、橙色、紅色），僅分解藍色、綠色、土色的裝備。
    - **預期流程**：點擊「全選」後，需要將畫面上藍色以上（紫色、黃色、橙色、紅色）的裝備取消勾選，再進行分解。
    - **技術難點備忘**：由於不同裝備內容物不同，無法直接用固定的裝備模板進行模板比對。未來實作時，需改用**色彩範圍偵測**或**邊框顏色裁剪分析**（偵測物品欄格子的邊框 HSL/RGB 顏色範圍）來定位高稀有度裝備，並點擊其坐標以取消選取。
