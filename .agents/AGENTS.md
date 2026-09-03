# Project Global Guidelines & Rules (AGENTS.md) 🤖

本文件包含所有 AI 協同開發人員在維護本專案時必須嚴格遵守的全域行為規範。

---

## Mandatory AI Test Execution Policy

- AI agents must never run the complete test suite, including
  `python -m unittest discover tests`.
- During implementation, AI agents may run only the smallest directly relevant
  test method, test class, or test file for the changed behavior.
- After all requested work and focused tests are complete, the AI agent must ask
  the user to run the complete test suite and report any remaining failures.
- These rules supersede every older instruction in this repository that asks an
  AI agent to run a full-suite, pre-merge, branch-completion, or coverage-union
  verification.

## 核心原則：AI Agent 5 大極簡原則 💡

1. **「感知」與「決策」分離 + 分層禁止反向依賴**：`Detector` 只負責觀察畫面並輸出狀態 (`SceneInfo`)，絕不觸發點擊；`Handler` 只根據狀態做決策，絕不現場比對畫面。
   - **分層依賴方向**：`main` → `state_machine` → `handlers` → `actions/mouse`。依賴只能由上往下流。底層模組（如 `actions/mouse.py`）**嚴禁持有上層物件的直接引用**。若需跨層通知，必須使用 **callback 注入**，由上層在初始化時接線。
2. **單一職責：檔案 300 行、方法 60 行、巢狀 3 層**：一檔一職。
   - 任何檔案超過 **300 行**或出現非本檔職責之 `if` 分支時，必須主動提請重構抽離。
   - 單一方法超過 **60 行**時，必須拆分為具名子步驟。
   - `if` / `try` / `for` 的巢狀層數不得超過 **3 層**，超過時必須使用 Early Return 或 Extract Method。
3. **狀態驅動，拒絕補釘**：面對新需求/彈窗，優先建立獨立 State 或子狀態機，絕不在主流程中增修 `if is_special_case` 補釘。
4. **全局審視優先於局部編寫**：寫代碼前必須先審視既有架構，嚴禁無視模組邊界隨手插入跨層邏輯。
5. **零容忍三害：Magic Number、Dead Code、DRY 違規**：
   - **Magic Number/String 禁令**：任何在業務邏輯中出現的裸數字（如 `1920.0`）或裸字串（如 `"Blackfire Crusade"`），必須提取為 `config.py` 常數或類別常數，並附帶語意命名。
   - **Dead Code 零容忍**：重構後遺留的無呼叫者方法、僅测試呼叫但生產環境無人用的方法、以及 try-except 中 except 與 try 執行完全相同邏輯的冗餘防穮代碼，必須在當次 PR 中主動清除。
   - **DRY 三行即抄**：當相同或近似邏輯在兩處以上出現且超過 3 行時，必須抄取為共用私有方法或工具函式。複製貼上再微調是被禁止的。

---

## 研發與維護實務規範 🛠️

### 1. Git 分支與 Commit 規範 🔀
> [!CRITICAL]
> **禁止自行合併**：AI 絕對禁止自行執行分支合併 (`git merge`)，必須等待使用者明確指示。

- **Commit 格式**：Angular Standard (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`).
- **精確 Commit 檔案範疇禁令 (Scope-Isolated Commit Only)**：
  - 🚫 **嚴禁全域打包**：絕對禁止使用 `git add .`、`git add -A` 或 `git commit -a` 進行盲目打包。
  - ✅ **白名單精確 Stage**：每次 Commit 僅能明確指定本次任務或修復所涉及的具體檔案路徑（例如 `git add path/to/target.py`）。
  - **嚴禁污染工作區**：非本次任務修改的檔案、使用者未完成的工作區代碼、未列入任務的臨時檔案，一律嚴禁加入暫存區或 Commit。
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
- 集中於 [utils/quest_mapper.py](../utils/quest_mapper.py#L84) 的 `QuestMapper`；報告維護於 [quest_mapping_rules_report.md](../docs/features/daily_task/quest_mapping_rules_report.md)。
- 優先級：`確定性` > `僅彈窗`；`地下城` > `關卡`；`關卡層數`大者優先。未知任務自動下記 `user_data/daily_status.json`。

### 6. 測試架構設計與執行規範 (Google Software Engineering Standard) 🧪

0. **純文件變更免測試 (Docs-Only Test Exemption)**：
   - 當本次異動**只有 Markdown／文件規格**（例如 `docs/**/*.md`、`.agents/AGENTS.md`），且完全沒有修改 Python 程式、TOML／JSON 設定、templates、測試 fixture、腳本或其他 runtime 資產時，**不需要執行單元測試或全套測試**。
   - 交付前仍必須用 `git status --short`／`git diff --name-only` 核對變更範圍，並在回報中明確註明：`未執行測試（純文件變更）`。
   - 只要異動包含任何可能改變 runtime／build／test 行為的非文件檔案，就不適用此例外，必須依下列精準測試與收尾規則執行。

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
   > 1. **日常開發與核心修改 (Daily Development & Behavioral Slicing)**：日常開發、修改核心代碼（`states/`, `utils/`, `config.py`, `main.py`）或微調邏輯時，**僅限精準執行該業務領域最小相關的單元測試檔案** (例如: `.venv\Scripts\python -m unittest tests.test_behavior_xxx`)（耗時 0.5~5 秒），以取得即時反饋並快速迭代。
   > 2. **測試失敗修復 (Failed Tests Handling)**：修復測試時，**僅精確執行有錯的測試檔案或測試方法** (`.venv\Scripts\python -m unittest tests.test_xxx.TestClass.test_method`) 進行除錯，通過後再推進。
   > 3. **全套測試執行時機 (Full Test Suite by USER ONLY)**：AI **嚴禁自行發起全套測試**。當 Feature/Fix 分支開發收尾、準備 Commit 或準備合併回 `main` 前，AI 必須在對話中**提醒使用者手動執行全套測試** (`.venv\Scripts\python -m unittest discover tests`)，並請使用者回報剩餘失敗。

4. **增量覆蓋率驗證流程 (Incremental Union Coverage Workflow)**：
   - 當僅更新、編寫或補強單一行為測試檔，而沒有修改邏輯實作時，**禁止執行全套測試**。
   - **精要兩步流程**：
     1. **增量累加**：使用 `-a` (`--append`) 僅執行新編寫之測試檔，將覆蓋數據與原數據庫求**聯集 (Union)**：
        ```bash
        .venv\Scripts\python -m coverage run -a -m unittest tests.test_behavior_xxx
        ```
     2. **報表**：
        ```bash
        .venv\Scripts\python -m coverage report --include="states/handlers/navigation.py,utils/scene_detector.py" -m
        ```
   - **全域收尾提醒**：完成所有增量開發後，由 AI 提示使用者手動執行全套測試驗證。

### 7. Markdown 文檔與超連結繪製規範 📄
- **嚴禁使用絕對路徑 `file:///`**：在撰寫 `docs/` 下的 Markdown 技術文檔時，**絕對禁止使用 `file:///...` 絕對路徑**（避免 VS Code Markdown Preview 預覽器無法解析而自動斷行，呈現未解析的長文字網址）。
- **強制使用標準相對路徑 (Relative Markdown Links)**：
  - 引用專案範本或模組時，必須依據當前 Markdown 檔案位置使用標準相對路徑。
  - 例如在 `docs/` 檔案中引用範本圖片與程式碼時，統一採用：
    - `[common/door.png](../templates/common/door.png)`
    - `[NavigationHandler](../states/handlers/navigation.py)`
  - 確保在 GitHub 與 VS Code Preview 預覽時均能呈現乾淨、單行且可點擊的藍色超連結。

### 8. MetaData 腳本與資料庫維護規範 🗃️
- **`meta_data/scripts/` 分類與 Git Track 原則**：
  1. **核心工具與生成器 (強制 Track)**：具備長期復用價值、機率算法計算（如 `calc_treasure_probs.py`）、文檔自動化生成（如 `update_all_hero_docs.py`）與關卡/任務鏈解析（如 `map_all_quests.py`）之腳本，必須規範命名並納入 Git 追蹤。
  2. **拋棄式探索腳本 (禁止 Track / 主動清理)**：回答臨時疑問或除錯產生的一次性查詢腳本（如 `inspect_*.py`, `query_*.py`, `temp_*.py`），應優先置於 `.gitignore` 的 `scratch/` 目錄，或在任務結束前**主動清理刪除**，嚴禁遺留雜亂檔案於 `meta_data/scripts/`。
- **自主閉環與做完即回報原則 (End-to-End Delivery & Report)**：
  - AI 協同開發時，面對分析與文檔維護需求，必須主動完成「資料解析 ➔ 文檔精確更新 ➔ 工具腳本分類保留/臨時檔清理 ➔ 狀態核驗」，做到完整無缺漏後才回報給使用者。

### 9. 座標體系一致性與共用工具規範 📐
- **全鏈路統一 Client 座標系**：所有模組的座標傳遞與計算，統一使用 `GetClientRect` + `ClientToScreen` 的 Client 座標體系。**嚴禁混用 `GetWindowRect`**（包含外框，會導致 8px 偏移偽）。
- **共用工具不重複實作**：
  - 視窗控制代碼 (hwnd) 查詢統一使用 [`utils/window.py`](../utils/window.py) 的 `WindowHandle` 類別，禁止各模組自行實作。
  - 跨模組共用的常數（視窗標題、基準解析度、安全區座標）統一定義於 [`config.py`](../config.py)。

### 10. 提交前自審清單 (Pre-Commit Self-Review) ✅
> [!IMPORTANT]
> AI 在提交任何新增或修改的程式碼前，必須對照以下清單自審：

1. ☐ 檔案中是否有裸數字或裸字串？→ 提取為 `config.py` 常數
2. ☐ 是否有超過 3 行的重複邏輯？→ 抄取為共用方法
3. ☐ 方法行數是否超過 60 行？巢狀是否超過 3 層？→ 拆分
4. ☐ 是否有底層模組直接引用上層物件？→ 改為 callback 注入
5. ☐ 是否有重構後遺留的無人呼叫方法？→ 當次刪除
6. ☐ 座標計算是否統一使用 Client 座標系？→ 禁用 GetWindowRect
