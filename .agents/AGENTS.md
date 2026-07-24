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
