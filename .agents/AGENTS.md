# Project Global Guidelines & Rules (AGENTS.md) 🤖

本文件包含所有 AI 協同開發人員在維護本專案時必須嚴格遵守的全域行為規範。

---

## 核心原則：AI Agent 4 大極簡原則 💡

1. **「感知」與「決策」分離**：`Detector` 只負責觀察畫面並輸出狀態 (`SceneInfo`)，絕不觸發點擊；`Handler` 只根據狀態做決策，絕不現場比對畫面。
2. **單一職責與 300 行警戒線**：一檔一職。任何檔案超過 300 行或出現非本檔職責之 `if` 分支時，必須主動提請重構抽離。
3. **狀態驅動，拒絕補釘**：面對新需求/彈窗，優先建立獨立 State 或子狀態機，絕不在主流程中增修 `if is_special_case` 補釘。
4. **全局審視優先於局部編寫**：寫代碼前必須先審視既有架構，嚴禁無視模組邊界隨手插入跨層邏輯。

---

## 研發與維護實務規範 🛠️

### 1. Git 分支與 Commit 規範 🔀
> [!CRITICAL]
> **禁止自行合併**：AI 絕對禁止自行執行分支合併 (`git merge`)，必須等待使用者明確指示。

- **Commit 格式**：Angular Standard (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`).
- **強制 `--no-ff`**：合併至 `main` 必須使用 `git merge --no-ff` 並附帶包含異動統計、模組細節與測試結果的結構化 Merge Log。
- **跨平台 Shell 貼上語法規範**：
  - 為防止 Terminal 貼上多行指令時因換行符號（`\n`）導致指令截斷或報錯，提供 Merge 指令時必須**感應用戶 OS/Shell**。
  - **Windows (PowerShell / CMD)**：必須使用**多個 `-m` 參數**串聯多段訊息 (例如 `git merge --no-ff <branch> -m "標題" -m "變更摘要..." -m "測試結果..."`)，避免任何跨列換行。
  - **Linux / macOS (Bash / Zsh)**：可使用多個 `-m` 參數或標準多行引號。

### 2. 極速掛機與延遲規範 ⚡
- `pyautogui.PAUSE = 0.002` (2ms)。
- `mouseDown`/`mouseUp` 間隔 `40ms` (`time.sleep(0.04)`)，釋放後至少等 `40ms`。
- 主迴圈 `--interval` 預設 `0.05` 秒 (50ms)；常規按鈕點擊後等待 `30ms`，跨場景/下樓等待 `40ms`。

### 3. 開發故事規範 (PARS Framework) 📝
- 功能/修復收尾時於 `docs/storys/` 建立 PARS 文檔 (`Purpose`, `Action`, `Result`, `So What`, `Influence`)。

### 4. 局部比對與 Scale 視務規範 🎯
- **Scoped Crop Only**：卡片/彈窗內部比對禁止全螢幕掃描，必須先切割 `crop` 區域再比對。
- **Scale 自適應**：以 `scale_x = w / base_w` 縮放範本；卡片發射前需先核驗無冷卻木牌。

### 5. 懸賞任務對應規範 📋
- 集中於 [utils/quest_mapper.py](file:///e:/Side_Project/BlackfireCrusade_tool/utils/quest_mapper.py#L84) 的 `QuestMapper`；報告維護於 [quest_mapping_rules_report.md](file:///e:/Side_Project/BlackfireCrusade_tool/docs/storys/daily_task/quest_mapping_rules_report.md)。
- 優先級：`確定性` > `僅彈窗`；`地下城` > `關卡`；`關卡層數`大者優先。未知任務自動下記 `user_data/daily_status.json`。

### 6. 測試架構設計與執行規範 (Google Software Engineering Standard) 🧪

1. **測試行為而非實作 (Test Public Behaviors, Not Private Implementation)**：
   - **Google 軟體工程最佳實務**：測試案例必須專注於驗證系統的**外部可觀察行為**與狀態轉移契約（Given 特性畫面/狀態 ➔ When 觸發處理 ➔ Then 斷言發射點擊或轉移狀態）。
   - **拒絕與實作細節耦合**：嚴禁測試內部私有 Helper 或依賴中間變數。當進行內部架構重構（如抽離 `SceneDetector`）時，行為測試應在不改動測試程式碼的前提下維持 100% 綠燈，真正作為防護網。

2. **按業務領域輕量化拆分測試檔 (Behavioral Domain Slicing)**：
   - **拒絕單一巨型測試包**：測試檔應按獨立業務行為領域（Behavior Domains）拆分，單一測試檔維持輕量且職責單一：
     - `tests/test_behavior_navigation.py` (導航與頁籤切換行為)
     - `tests/test_behavior_stamina_retreat.py` (體力退避與狀態切換行為)
     - `tests/test_behavior_daily_pipeline.py` (懸賞任務動態調度行為)
     - `tests/test_behavior_town_subflows.py` (城鎮子流程行為)
     - `tests/test_behavior_bag_cleaning.py` (背包滿與整理銷毀行為)
   - 每一包專注特定行為閉環，組合後可 100% 涵蓋系統所有現有功能。

3. **測試執行與修復疊代流程 (Test Execution Efficiency)**：
   > [!IMPORTANT]
   > **測試執行三大精確規則**：
   > 1. **僅修改測試檔案 (Test-Only Modification)**：**嚴禁執行全套測試！只精確執行該修改的測試檔案或方法** (例如: `.venv\Scripts\python -m unittest tests.test_xxx`)。
   > 2. **測試失敗修復 (Failed Tests Handling)**：修復測試時，**僅精確執行有錯的測試檔案或測試方法** (`.venv\Scripts\python -m unittest tests.test_xxx.TestClass.test_method`) 進行除錯，通過後才執行全套驗證。
   > 3. **有修改核心程式碼 (Code Modification)**：修改 `states/`, `utils/`, `config.py` 或 `main.py` 時，**必須執行全套單元測試** (`.venv\Scripts\python -m unittest discover tests`)，確保全域無 Regression。

4. **增量覆蓋率驗證流程 (Incremental Union Coverage Workflow)**：
   - 當僅更新、編寫或補強單一行為測試檔，而沒有修改邏輯實作時，**禁止盲目每次重新執行 4 分鐘全套測試**。
   - **精要兩步流程**：
     1. **增量累加**：使用 `-a` (`--append`) 僅執行新編寫之測試檔，將覆蓋數據與原數據庫求**聯集 (Union)**：
        ```bash
        .venv\Scripts\python -m coverage run -a -m unittest tests.test_behavior_xxx
        ```
     2. **報表**：
        ```bash
        .venv\Scripts\python -m coverage report --include="states/handlers/navigation.py,utils/scene_detector.py" -m
        ```
   - **最終全域驗證**：完成所有增量開發準備 Commit 前，才執行全套測試 (`.venv\Scripts\python -m unittest discover tests`) 作為收尾。

### 7. Markdown 文檔與超連結繪製規範 📄
- **嚴禁使用絕對路徑 `file:///`**：在撰寫 `docs/` 下的 Markdown 技術文檔時，**絕對禁止使用 `file:///...` 絕對路徑**（避免 VS Code Markdown Preview 預覽器無法解析而自動斷行，呈現未解析的長文字網址）。
- **強制使用標準相對路徑 (Relative Markdown Links)**：
  - 引用專案範本或模組時，必須依據當前 Markdown 檔案位置使用標準相對路徑。
  - 例如在 `docs/` 檔案中引用範本圖片與程式碼時，統一採用：
    - `[common/door.png](../templates/common/door.png)`
    - `[NavigationHandler](../states/handlers/navigation.py)`
  - 確保在 GitHub 與 VS Code Preview 預覽時均能呈現乾淨、單行且可點擊的藍色超連結。

