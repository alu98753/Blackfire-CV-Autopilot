# 遊戲自動化 4 大架構支柱與狀態機領悟開發故事 (PARS Framework) 🧠🛡️

## Purpose (目的)
經過近期一系列的核心功能開發（地下城斷線重連、 Daily 跨日自動清零、背包已滿動態 SSOT 銷毀、 Watchdog 門檻優化與進程測試隔離），開發團隊對自動化腳本的底層設計產生了高維度的架構領悟：
遊戲自動化腳本的本質，並非單純累積瑣碎的流程腳本或調參，而是建立在 **4 大核心支柱** 之上的完備閉環：
1. **Entity (靜態實體)**
2. **State (狀態流轉)**
3. **Data (靈魂與記憶)**
4. **Exception (閉環自癒)**

本工程旨在將此 4 大架構哲學具體貫徹至系統設計中，並紀錄團隊對遊戲自動化架構的精髓領悟。

---

## Action (行動)

### 💡 1. 貫徹 4 大核心支柱 (Architecture Pillars)

* **🏢 Entity (靜態實體 - 畫面物件與特徵)**：
  - **概念**：遊戲內的靜態物件，例如角色、場景（城鎮、副本地圖）、建築門牌（血之祭壇、珠寶加工廠）以及各類按鈕與特徵圖案（如 `dungeons/leave.png`）。
  - **實作**：作為視覺辨識（Matcher / OCR）與特徵錨點的基礎。

* **🔄 State (狀態流轉 - 業務情境與轉移)**：
  - **概念**：玩家遊玩時的所有動態操作情境與轉換（賣東西、尋路導航、戰鬥、地下城探索）。
  - **實作**：由 [GameStateMachine](../../states/state_machine.py) 掌管控制流，負責處理情境之間的跳轉（如從 `NAVIGATING` 切換至 `DUNGEON_EXPLORING` 或 `BACKPACK_FULL_SORTING`）。

* **💾 Data (靈魂與記憶 - 動態數據與狀態更新)**：
  - **概念**：如果 Entity 是靜態實體，Data 就是賦予 Entity 生命與靈魂的動態資料。它記錄各個實體的詳細資訊，並隨 State 的轉移進行動態更新，讓 Entity「活起來」。
  - **實作**：
    - [daily_status.json](../../user_data/native/daily_status.json) 與 [daily_manager.py](../../utils/daily_manager.py)：持久化記憶完成狀態與跨日 08:05 Date Tag 清零。
    - [config.py](../../config.py) 中的 `goods_settings`：作為背包銷毀的單一權威來源 (SSOT)，隨使用者設定動態授權。

* **🛡️ Exception (閉環自癒 - 防卡死與意外救援)**：
  - **概念**：專門處理 State 在運轉過程中可能產生的意外卡死、廣告/懸賞彈窗遮擋或遊戲崩潰。
  - **實作**：由 [watchdog.py](../../states/exceptions/watchdog.py)（90s/30s 門檻）、[handler.py](../../states/exceptions/handler.py) (`UnexpectedPopupRecoveryHandler`) 與 [game_relaunch.py](../../states/exceptions/subflows/game_relaunch.py) 組成。當 State 卡死時，由 Exception 接管救援並復原回到原本的 State 與 Data，達成 100% 不中斷的防禦閉環。

---

## Result (結果)
- **架構升級**：系統自此具備清晰的分層哲學（Entity 定位 ➔ State 流轉 ➔ Data 更新 ➔ Exception 自癒）。
- **測試驗證**：全套件 **391 項單元測試 100% 綠燈通過 (OK)**，進程生命週期測試完備隔離 (`skipped=14`)。
- **長掛機安定性**：在無人值守 24/7 長掛機中，達成跨日自動重置、地下城斷線重連恢復、背包精準 2 格位移銷毀與導航 90 秒防誤判之安定運轉。

---

## So What (核心價值)
- **維度提升**：從「被動修 Bug」提升為「主動建構 4 大支柱閉環」。有了 Data 賦予生命與 Exception 提供保底，使整套系統具備極高抗壓性與靈活性。

---

## Influence (影響)
- 確立了「Entity 辨識 + State 控制 + Data 記憶 + Exception 自癒」為本專案後續所有功能模組開發的標準架構指引。
