# PARS 開發故事：主入口模組化解耦與行為領域測試切片 🎯

- **建立時間**: 2026-08-29
- **影響模組**:
  - 主入口程式：[`main.py`](../../main.py)
  - 命令列互動與配置套件：[`cli/`](../../cli/) (`arguments.py`, `dungeon_setup.py`, `mode_setup.py`, `profile_updates.py`, `profiles.py`, `prompts.py`, `stage_setup.py`)
  - 執行期組裝與主迴圈套件：[`runtime/`](../../runtime/) (`bootstrap.py`, `loop.py`)
  - 行為測試領域切片套件：[`tests/`](../../tests/) (`test_behavior_main_entrypoint.py`, `test_behavior_bag_scenarios.py`, `test_behavior_town_scenarios.py`, `test_behavior_dungeon_scenarios.py`, `test_behavior_collection_scenarios.py`, `test_behavior_safety_and_battle_scenarios.py` 等)

---

## 1. Purpose (開發目的與問題背景)

依據 `AGENTS.md` 核心規範（單一職責：檔案 300 行、方法 60 行、巢狀 3 層、Google 軟體工程測試規範）：
1. **主入口臃腫超標**：
   舊有 `main.py` 累積達到 **783 行**，混雜了 CLI 引數解析、關卡與地下城終端互動選單、Profile TOML 回寫、模板預檢、狀態機依賴注入與主事件迴圈，嚴重違反單一職責原則。
2. **巨型測試包執行與維護成本高昂**：
   既有 `test_behavioral_scenarios.py` (2,831 行) 與 `test_state_machine_logic.py` (2,543 行) 形成了兩大巨石測試包，缺乏領域邊界，導致日常微調單一功能時難以快速執行局部測試。

---

## 2. Action (架構重構與具體行動)

### 2.1 主入口職責切分與模組化 (`cli/` 與 `runtime/`)
依據業務邊界將 `main.py` 完整解耦為獨立子模組：
- **`cli/arguments.py`**：純 CLI ArgumentParser 定義與解析。
- **`cli/profiles.py`**：Profile 與 daily_status 路徑的純判定。
- **`cli/prompts.py`**：終端互動選擇與 Fallback 退避機制。
- **`cli/profile_updates.py`**：CLI 選擇回寫 Profile TOML 的專屬 helper。
- **`cli/stage_setup.py`**：普通關卡大關/小關互動選擇與導航路徑組裝。
- **`cli/dungeon_setup.py`**：地下城、貪婪模式、戰鬥祝福與 CD 退避設定。
- **`cli/mode_setup.py`**：各主掛機模式（daily, mix, dungeon, stage, collect_only 等）與裝備品質設定。
- **`runtime/bootstrap.py`**：模板預檢（`check_mode_templates`）與狀態機完整依賴注入組裝（`init_state_machine_system`）。
- **`runtime/loop.py`**：主事件迴圈（`run_main_loop`）與熱鍵暫停調度。
- **`main.py`**：瘦身為 50 行的極簡啟動編排器（Orchestrator）。

### 2.2 行為領域測試切片 (Behavioral Domain Slicing)
將巨型測試拆分為職責單一的輕量化行為測試檔：
- 新增 `tests/test_behavior_main_entrypoint.py` 專注覆蓋主入口啟動契約、Profile 判定與互動 fallback。
- 按領域切分 `bag`、`dungeon`、`town`、`collection`、`safety`、`recovery` 等情境測試，使各領域單檔執行僅需 0.5~5 秒，達成 Google 級別的秒級反饋。

---

## 3. Result (成果驗證)

1. **代碼行數大幅縮減**：
   `main.py` 由 783 行精簡至 **50 行**（縮減超過 93%），完全符合 300 行以內之規範。
2. **零功能回歸 (Zero Regression)**：
   全套 593 個單元測試與各領域行為切片測試全數綠燈通過。
3. **日常開發反饋速度提升**：
   修改 CLI 或單一領域時，僅需秒級執行對應領域測試檔案即可確認完整契約。

---

## 4. So What (核心價值)

- 徹底消除了主入口的歷史架構債，實現「UI/CLI 介面層」、「執行期 Runtime 層」與「核心業務狀態機」的嚴格分層。
- 測試結構與代碼架構對齊，降低認知負擔並提升協同維護效率。

---

## 5. Influence & Maintenance Guidelines (後續維護指引)

- 新增或調整 CLI 參數請至 [`cli/arguments.py`](../../cli/arguments.py)。
- 新增掛機模式或調整互動選單請至 [`cli/mode_setup.py`](../../cli/mode_setup.py)。
- 調整主迴圈事件循環或暫停邏輯請至 [`runtime/loop.py`](../../runtime/loop.py)。
- 維護 [`main.py`](../../main.py) 時應保持其為純流水線呼叫，嚴禁在入口處直接撰寫業務分支邏輯。
