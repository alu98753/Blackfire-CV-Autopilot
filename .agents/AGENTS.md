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
2. **單一職責與架構警示 (Smell vs Goal)**：一檔一主要職責。檔案行數是架構警示（smell），不是重構目標。
   - **Production Code ~300 行架構審查觸發線（非硬上限）**：超過約 300 行時，主動審查：
     1. 是否存在兩個以上獨立 change reasons / responsibilities。
     2. 是否混合 domain policy、I/O、adapter、presentation、CLI 等不同層次。
     3. 是否出現不合理的跨層或反向依賴。
     4. 是否存在可形成清楚契約的獨立模組。
     * 若存在上述問題，應依責任與依賴邊界拆分。
     * 若職責仍單一、高內聚且依賴方向正確，可合理超過 300 行；不得為符合行數而機械拆檔。
   - **嚴禁 LOC-driven Refactoring / Code Golf**：
     - 不得為壓低行數而刪除有價值的 docstring、註解、型別資訊或空白行。
     - 不得將多個 statements 壓成單行。
     - 不得建立只有形式上分檔、卻沒有獨立責任或契約的 helper/module。
     - 不得以 `part1.py` / `part2.py` 等方式機械切割。
   - **Tools / CLI / Tests 不套用 300 行觸發線**：
     - 以 cohesion、可導航性與 change reason 判斷是否拆分。
     - 大型測試檔應依 behavior / subsystem 拆分，而非依行數拆分。
     - CLI 僅在 argument parsing、execution、presentation 或不同 workflow 已形成清楚獨立責任時拆分。
   - **方法規模 (~60 行) 與巢狀 (~3 層) 同樣視為具名步驟警示**：
     - 方法接近或超過約 60 行時，主動檢查是否包含多個具名步驟或責任。
     - 深層巢狀優先使用 guard clause、early return 或 extract method 改善。
     - 不得僅為符合數字限制而產生無語意的小函式。
   - **決策優先級**：
     `Responsibility → Dependency Direction → Cohesion → Testability → File/Method Size`
     （永遠不要反過來因為 LOC 超標才硬找地方拆）。
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
- **新開發分支啟動規範 (Branch Start Routing Rule)**：
  - 當使用者明確表示「開始新開發」、「開始新功能」、「開始修 bug」、「開新分支」或其他正式進入 implementation lifecycle 的指令時，統一調用 [`branch_start_workflow`](skills/branch_start_workflow/SKILL.md)。
  - 正式 Feature / Fix / Refactor 分支建立後，必須立即建立同名 remote tracking branch：`git push -u origin HEAD`，使開發期間即可透過遠端 `main...<branch>` 進行 review。
  - Branch 建立、同步與 safety guard 的詳細流程以 `branch_start_workflow` 為唯一權威；本文件不重複其執行細節。
- **Detached HEAD 唯讀停泊守則 (Read-Only Parking Invariant)**：
  - 分支收尾完成後，主開發目錄（`BlackfireCrusade_tool`）停泊於 `origin/main`（Detached HEAD）。
  - **此狀態為嚴格「唯讀停泊狀態 (Read-Only Parking State)」，絕非開發狀態**。
  - **AI 嚴禁在 Detached HEAD 狀態下直接修改代碼、更新設定或建立 Commit**！
  - 當使用者提出任何修改代碼、更新設定或修復 Bug 之實作需求時，AI 必須在動手前先檢查當前分支：
    - 若處於 Detached HEAD，**AI 必須主動阻斷**並引導建立新分支（調用 `branch_start_workflow` 執行 `git switch -c <branch> origin/main` 並建立 remote tracking），切換至具名分支後方可開始修改。


### 2. 極速掛機與延遲規範 ⚡
- `pyautogui.PAUSE = 0.002` (2ms)。
- `mouseDown`/`mouseUp` 間隔 `40ms` (`time.sleep(0.04)`)，釋放後至少等 `40ms`。
- 主迴圈 `--interval` 預設 `0.05` 秒 (50ms)；常規按鈕點擊後等待 `30ms`，跨場景/下樓等待 `40ms`。

### 3. 分支收尾工作流與契約收斂規範 (Branch Closeout & Contract Archival) 📝
- **統一收尾工作流 (Branch Closeout)**：當使用者發出「`請分支收尾`」、「`分支收尾`」、「`準備 merge`」、「`請 merge`」等指令時，統一啟動由 [`branch_completion_workflow`](skills/branch_completion_workflow/SKILL.md) 總編排的 **11 階段硬性分段閘門工作流 (11-Phase Gated Workflow)**。
- 🛑 **最高硬性阻斷禁令 (Hard Blocking Invariant)**：
  - **「請 merge」代表「啟動分支收尾流程」，絕對禁止直接輸出 `git merge` 指令**！
  - 本流程為分段閘門工作流，**嚴禁一次跑到底**。每當遇到全套測試執行、文件清理範圍確認或決策分歧時，必須停下來等待使用者指示方可推進。
- **關鍵閘門守則**：
  1. **雙工作樹迴歸基準驗證 (Phase 1~2)**：AI 先於 `temp-main` 檢查 clean，執行 `git fetch origin` 並比對 `HEAD` 與 `origin/main`（若落後且 clean 則 `git pull --ff-only` 刷新），隨後以共用主專案 `.venv` 交付兩個 Terminal 的全套測試執行指令。使用者執行完畢後指示 AI 檢視終端輸出。比對確認 failures，嚴禁在存在 `BRANCH_REGRESSION` 或 `UNCERTAIN` 時進入重構或收尾。
  2. **保行為維護重構 (Phase 4~5)**：僅進行無行為改變的代碼清理（dead code, glue, duplication），獨立 commit。重構後必須再次對比測試無新增 failure。
  3. **程式碼潔淨度審計 (Phase 6)**：暫時 Spec / Issue 代號（如 todo 檔名、Task ID、分支名）嚴禁遺留在 production code 的 docstrings 或註解中進入 main。僅限引用長效 Canonical Contract。
  4. **文件收斂與契約歸檔 (Phase 7)**：調用 [`canonical_contract_archival`](skills/canonical_contract_archival/SKILL.md)。⚠️ **嚴禁 AI 自行決定清理範圍**，必須先列出候選清單向使用者確認。遵循「刪除是預設；封存是例外」果斷清理已提煉之過期 spec。
  5. **開發故事歸檔 (Phase 8)**：於 `docs/storys/` 建立 PARS 文檔。⚠️ **PARS 僅為歷史敘事日誌，絕非架構規範，絕不可作為架構證據**。
  6. **合併指令交付 (Phase 10)**：僅當所有前置閘門完成後，方可交付包含結構化日誌的 `--no-ff` 合併指令，AI 嚴禁自行執行 merge。



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
   > 3. **全套測試執行時機 (Full Test Suite by USER ONLY)**：
   >    - AI **嚴禁自行發起全套測試**。
   >    - 當 Feature/Fix 分支開發收尾、準備 Commit 或準備進入收尾流程前，AI 提示使用者手動執行全套測試時，**統一交付具備 UTF-8 重定向至記錄檔的標準指令**，以徹底防止 Windows 終端 Buffer 截斷與 PowerShell 亂碼：
   >      ```powershell
   >      cmd.exe /c "chcp 65001 >nul && cd /d E:\Side_Project\BlackfireCrusade_tool && .venv\Scripts\python.exe -X utf8 -m unittest discover tests > test_run.log 2>&1"
   >      ```
   >    - 使用者在終端執行完畢後告知 AI，由 AI 主動讀取 `test_run.log` 提取總耗時、通過狀態與失敗 Traceback 進行診斷與回報。

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

### 7. Markdown 文檔客觀寫作與超連結繪製規範 (write_docs) 📄✍️
- **全域文檔強制遵循 `write_docs` 技能**：本專案全域所有 Markdown 文章（包括但不限於 `docs/` 下的技術規格、架構契約、TODO/RFC、PARS 開發故事，以及 `meta_data/Game_docs/` 下的遊戲數據分析、攻略問答與機制指南），**一律強制遵循 `write_docs` (Evidence-Bound Natural Writing) 技能規範**：
  1. **確定性 ≤ 證據強度 (Certainty <= Evidence)**：斷言確定性嚴禁超過可用代碼、底層數據或實測紀錄之依據。嚴禁未經實測證實的誇飾（如「絕對」、「必須」、「完美解決」、「終局最佳」）；建議或策略陳述必須使用「建議……」、「通常……」、「可先……」等中立表達。
  2. **改寫嚴禁升級斷言與腦補空白 (No Evidence Inflation or Gap Filling)**：整理筆記、改寫規格或匯總 Q&A 時，嚴禁私自調高斷言語氣，或憑空捏造未驗證之數值、機率、排名與策略。
  3. **拒絕 AI 味修飾與情緒化黑話 (No AI Embellishment)**：禁止使用「過渡打工人」、「傾家蕩產」、「賭怪」、「停手！」、「神級」等情緒化浮誇詞彙；避免無效的前綴標籤（如「老手大白話：」、「核心原則：」）與過度裝飾的 Emoji。
  4. **優先連貫段落，禁止冗餘重述與假架構條列 (Continuous Prose & List Rule)**：優先以短段落自然敘述；嚴禁將內文重複抽成條列清單或無效懶人包（TL;DR）；只有在項目具備實質平行或步驟關係時才使用列表。
  5. **保留具體細節 (Preserve Concrete Details)**：保留實質數值、底層變數、換算公式、程式碼符號與確切路徑，禁止將具體資訊抽象化為無效空話。
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

### 10. 日誌分級與終端潔淨規範 (Logging Hygiene & Level Guidelines) 📜
- **門檻過濾原則**：系統預設 `logging.INFO`，僅輸出 `INFO`、`WARNING`、`ERROR`。
- **高頻遙測入 `DEBUG`**：
  - 凡每幀執行、迴圈內部（頻率高於 1 秒一次）之數據（模板比對最高相似度、血條紅色像素數量、像素差異 diff、InFlightAction 等待後置條件確認、DetectorRegistry 指標、OCR 邊界計算），**一律使用 `logging.debug()`**。
  - 🚫 **嚴禁在 `INFO` 輸出每秒重複日誌造成終端洗屏**。
- **關鍵決策與狀態轉移入 `INFO`**：
  - 狀態機狀態跳轉（`STATE_NAVIGATING -> STATE_BATTLE`）、點擊後置條件驗證確認（Postcondition satisfied）、重大業務完成（日常子流程完成、任務獎勵領取、Intent 完成）、定時器事件（08:05 重置、定時領體力/鑽石）使用 `logging.info()`。
- **可自癒異常與警示入 `WARNING` (有界復原階梯 1~5)**：
  - 遮擋彈窗攔截點擊（Dismiss Overlay）、連續截圖失敗重試中、找不到視窗重試、背包已滿、門票耗盡、體力退避暫緩工作（Intent Defer）、戰鬥血條卡死觸發**原地重新開始**（<= 2 次）等自癒/保護性退避，使用 `logging.warning()`。
- **嚴重故障與不可逆中斷入 `ERROR` (有界復原階梯 6~7)**：
  - 戰鬥卡死原地重試超限升級殺進程重開（`ProcessPort.relaunch`）、連續截圖失敗超限重開、戰鬥超過 Hard Timeout、OCR 模型檔案損毀、未捕獲例外拋出，使用 `logging.error()`。

### 11. 提交前自審清單 (Pre-Commit Self-Review) ✅
> [!IMPORTANT]
> AI 在提交任何新增或修改的程式碼前，必須對照以下清單自審：

1. ☐ 檔案中是否有裸數字或裸字串？→ 提取為 `config.py` 常數
2. ☐ 是否有超過 3 行的重複邏輯？→ 抄取為共用方法
3. ☐ 職責與規模審查：Production 檔案是否超過 ~300 行且包含多重職責/不同層次？方法是否缺乏具名步驟？→ 依責任邊界拆分（嚴禁機械 Code Golf）
4. ☐ 是否有底層模組直接引用上層物件？→ 改為 callback 注入
5. ☐ 是否有重構後遺留的無人呼叫方法？→ 當次刪除
6. ☐ 座標計算是否統一使用 Client 座標系？→ 禁用 GetWindowRect
7. ☐ 日誌層級審查：高頻比對/像素差異/每幀運算是否使用 `logging.debug`？（嚴禁在 `INFO` 輸出高頻重複日誌）
8. ☐ Docstring 潔淨度審查：Production code / docstrings / 註解中是否殘留暫時性 spec/issue 名稱（如 `nav_slow_bug2`、task ID、分支名）？→ 重寫為穩定行為語意描述或引用 Canonical Contract。
9. ☐ 文檔客觀性審查（write_docs）：全專案文檔（`docs/`、`meta_data/Game_docs/`）是否符合「確定性 ≤ 證據強度」？是否剔除「絕對/必須/唯一/打工人」等誇飾、無效重複條列與未證實猜測？
