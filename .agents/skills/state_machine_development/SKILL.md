---
name: state_machine_development
description: 指引 AI 協同開發人員維護與擴充本專案的模組化 GameStateMachine 狀態機與狀態處理器 (State Handlers)。當需要新增狀態、重構 Handler 或維護導航跳轉時觸發。
---

# GameStateMachine 開發指南 🤖

本專案使用狀態模式 (State Pattern) 實現遊戲自動化決策。主狀態機 `GameStateMachine` 負責狀態變數維護與跳轉調度，具體的操作邏輯拆分至 `states/handlers/` 中。

---

## 1. 核心開發準則與導覽 (Quick Navigation)

進行狀態機與 Handler 開發時，**必須優先遵循專案核心架構與各專題規範**：

- 🏛️ **8 大 Clean Architecture 與 CLI 規範** ➔ [references/core_design_patterns.md](references/core_design_patterns.md)
  - 互斥頁籤比對 (`match_mutually_exclusive_tabs`)
  - 生命週期 Context 自動 Hook (`TOWN_SUBFLOW_CONFIG_MAP`)
  - 導航路徑防重入過濾器 (`filter_navigation_path`)
  - 體力退避狀態顯式路由 (`stamina_retreat_start_time`)
  - 鎖定測試保護網 (`test_stamina_retreat_routing.py`)
  - Handler 極速 Phase 流轉 (`Fast Phase-driven Flow`)
  - 中央配置規範化 (`normalize_config`)
  - Windows CLI 啟動器與 `.bat` CRLF 編碼規範 (`run.bat`)
- 🎒 **裝備自適應分選技術規格** ➔ [references/backpack_sorting_spec.md](references/backpack_sorting_spec.md)
- ⚔️ **地下城探索優先級與冷卻** ➔ [references/explore_priorities.md](references/explore_priorities.md)
- 📖 **領取體力/鑽石城鎮邊界規範** ➔ [docs/knowledge.md](../../../docs/knowledge.md)

---

## 2. 新增遊戲狀態與 Handler 3 步驟 Standard

當需要引進新狀態（例如 `STATE_BULLETIN_BOARD`）：

1. **常數定義與對照表註冊**：
   - 在 `states/state_machine.py` 新增狀態常數（如 `STATE_BULLETIN_BOARD = "BULLETIN_BOARD"`）。
   - 若屬於城鎮獨立子流程，必須在 `GameStateMachine.TOWN_SUBFLOW_CONFIG_MAP` 補上一行註冊對應 Key。
2. **實作 Handler 類別**：
   - 在 `states/handlers/bulletin_board.py` 中繼承 `BaseStateHandler` 並實作 `handle(self, screen_img, rect)`。
3. **完成實體註冊**：
   - 在 `states/handlers/__init__.py` 匯出該類別，並在 `state_machine.py` 的 `self.handlers` 字典完成註冊。

---

## 3. 開發實作防錯 Checklist ✅

- [ ] **思考 Clean 原則並跟使用者說明**：主動說明所引用的架構設計原則與理由。
- [ ] **無硬編碼比對**：互斥頁籤必須調用 `self.match_mutually_exclusive_tabs(...)`。
- [ ] **無手動 Config 複製**：子流程切換統一呼叫 `self.transition_to(...)`，由 Hook 自動同步 Context。
- [ ] **退避顯式分流**：Handler 跳轉退出時，必須判斷 `stamina_retreat_start_time is not None` 導航至 `COLLECT_ONLY` 或 `NAVIGATING`。
- [ ] **測試 100% 綠燈**：完成變更後，必須執行 `tests/test_stamina_retreat_routing.py` 等全套測試。
