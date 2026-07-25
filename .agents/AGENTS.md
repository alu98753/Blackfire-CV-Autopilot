# Project Global Guidelines & Rules (AGENTS.md) 🤖

本文件包含所有 AI 協同開發人員在維護本專案時必須嚴格遵守的全域行為規範。

---

## 1. Git 分支與 Commit 規範 🔀
1. **Commit 訊息格式**：採用 Angular Standard Commit 規範（`feat:`, `fix:`, `refactor:`, `docs:`, `test:`）。
2. **分支合併限制 (Strict Rule)**：
   - ⚠️ **AI 協同開發人員絕對禁止自行執行分支合併**（例如將 feature 分支 merge 到 `main` 分支）。
   - 只有在使用者明確指示「可以進行 merge」時，AI 方可執行合併操作。

---

## 2. 極速掛機效能與物理延遲規範 ⚡
1. **PyAutoGUI 全域延遲**：必須維持 `pyautogui.PAUSE = 0.002` (2ms) 的極低全域預設阻塞。
2. **滑鼠點擊物理時長**：`mouseDown` 與 `mouseUp` 之間必須保留 `40ms` 間隔 (`time.sleep(0.04)`)，且點擊釋放後至少等待 `40ms`，確保遊戲客戶端能穩定輪詢捕捉事件。
3. **主迴圈偵測間隔**：`--interval` 預設為 `0.05` 秒 (50ms)。
4. **狀態處理器點擊後等待**：常規按鈕點擊後睡眠統一壓縮至 `30ms`；跨場景/下樓睡眠壓縮至 `40ms`。

---

## 3. 開發故事與成果記錄規範 (PARS Framework) 📝
當需要描寫與記錄專案中的開發故事與成果時，必須遵循 **PARS 架構** 在 `docs/storys/` 目錄下建立文件：
1. **Purpose (目的)**: 描述需求或痛點。
2. **Action (行動)**: 具體改進措施與細節。
3. **Result (結果)**: 成效與測試驗證結果。
4. **So What (核心價值)**: 提煉出最核心的工程價值。
5. **Influence (影響)**: 對後續架構與其他模組的借鑑。

---

## 4. 通用卡片/彈窗局部比對與 Scale 視務規範 (Scoped Crop & Scale Guidelines) 🎯
1. **禁止全螢幕盲目比對 (Scoped Crop Only)**：
   - 涉及卡片狀態（如冷卻木牌 `cooldown_left.png` / `cooldown_right.png`）或大彈窗內部按鈕（如 `free_treasure.png` 內的 `free.png`）比對時，**絕對禁止直接對全螢幕 `screen_img` 進行全局掃描**。
   - 必須先透過範本匹配取得主體（卡片或彈窗）中心座標與邊界，切割局部區域 `crop = screen_img[y1:y2, x1:x2]` 後，僅在 `crop` 內部進行木牌比對、按鈕定位或 OCR 解析。
2. **解析度 Scale 自適應 (Template Scale Adaptation)**：
   - 在計算卡片/彈窗裁切邊界時，必須考量不同遊戲視窗尺寸與解析度縮放。
   - 透過 `scale_x = w / base_w` 縮放範本寬高 `t_w, t_h`，避免因螢幕縮放導致裁切座標偏離或木牌/按鈕漏檢。
3. **無木牌預先防呆機制 (Pre-Click Sign Verification)**：
   - 比對出 `cooldown_left.png` 或 `cooldown_right.png` ➔ 代表冷卻中，啟動 OCR 解析剩餘時間。
   - **無木牌** ➔ 代表可挑戰，方可發射點擊。

---

## 5. 懸賞任務對應規則維護與擴充規範 (Quest Rules Maintenance) 📋
1. **任務規則唯一定義檔與參考報告**：
   - 所有的懸賞任務對應規則（將任務標題/關鍵字映射至關卡或地下城）與三大任務全名清單（`DETERMINISTIC_QUESTS`, `BANNER_VERIFY_QUESTS`, `IGNORED_QUESTS`）皆集中定義在 [utils/quest_mapper.py](file:///e:/Side_Project/BlackfireCrusade_tool/utils/quest_mapper.py#L84) 的 `QuestMapper` 類別中。
   - 完整對照與多階梯排序報告請參閱 [quest_mapping_rules_report.md](file:///e:/Side_Project/BlackfireCrusade_tool/docs/storys/daily_task/quest_mapping_rules_report.md)。
   - **多階梯優先級排序 (`sort_quests`)**：`確定性` (0) > `僅彈窗核銷` (1)；`地下城` (0) > `關卡` (1)；`dungeon_index/stage_level` 大者優先！
   - **顯式忽略任務**：定義於 `IGNORED_QUESTS`（`獵金之蟲`, `完成任何地下城`, `敵人剿滅` ➔ 不執行、不上報 unknown_quests）。
2. **未定義任務新增加載流程 (Adding New Quests)**：
   - 當懸賞告示牌出現未對應的全新任務時，系統會自動記錄於 [user_data/daily_status.json](file:///e:/Side_Project/BlackfireCrusade_tool/user_data/daily_status.json) 的 `subflows.bulletin_board.unknown_quests` 列表中 (每日不清空)。
   - 當使用者指示「加入新任務」時，AI 與開發者必須直接開啟 [utils/quest_mapper.py](file:///e:/Side_Project/BlackfireCrusade_tool/utils/quest_mapper.py#L84) 補充對應正則關鍵字規則與分類全名清單。

---

## 6. 測試執行精準度與效能規範 (Test Execution Efficiency) 🧪
1. **修改核心業務邏輯 (Core Logic Edit)**：
   - 當修改 `states/`, `utils/`, `config.py` 或 `main.py` 等核心業務邏輯程式碼時，**必須執行全套單元測試** (`.venv\Scripts\python -m unittest discover tests`)，確保無 Regression。
2. **僅新增或微調單一測試檔 (Test-Only Edit)**：
   - 當未修改核心業務邏輯，**僅新增、補充或微調單一測試檔案/測試方法**時，**只須精準執行該單一測試檔或測試方法**，絕不盲目跑全套測試。
   - 範例指令：
     - 精確執行單一測試檔案：`.venv\Scripts\python -m unittest tests.test_state_machine_logic`
     - 精確執行單一測試方法：`.venv\Scripts\python -m unittest tests.test_state_machine_logic.TestStateMachineLogic.test_multiple_task_complete_popups_sequential_handling`




