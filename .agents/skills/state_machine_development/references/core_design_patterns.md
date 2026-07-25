# 專案核心通用工具與 Clean Architecture 規範 🏛️🛡️

本文件記錄專案中已沉澱的 5 大核心設計模式與重構工具。開發新的 State Handler 時請優先複用：

---

## A. 互斥 UI 頁籤相對優勢比對 (Mutually Exclusive Tabs Matcher)
* **API**：`matcher.match_mutually_exclusive_tabs(screen_img, template_a, template_b, margin=0.02, threshold=0.70)`
* **門面代理**：`BaseStateHandler.match_mutually_exclusive_tabs(...)`
* **規範**：
  - ⚠️ **嚴禁**對互斥頁籤（如大廳選關 `select_stage_after.png` 與地下城列表 `dungeon_after.png`）採用簡單的單張圖片 threshold 比對。
  - ✅ **必須**呼叫 `match_mutually_exclusive_tabs` 進行雙向相對優勢閥值計算 ($c_a \ge 0.70 \land c_a > c_b + 0.02$)，完全防範背景畫面雜訊導致的假陽性誤判。

---

## B. 生命週期 Context 自動同步與聲明式對照表 (Lifecycle Context Hook & Registry)
* **核心機制**：`GameStateMachine.transition_to()` 在切換狀態的同一毫秒內，會自動觸發 `_on_state_transition_sync_context()`。
* **聲明式對照表** (`GameStateMachine.TOWN_SUBFLOW_CONFIG_MAP`)：
  ```python
  TOWN_SUBFLOW_CONFIG_MAP = {
      STATE_BLOOD_ALTAR: "blood_altar",
      STATE_JEWELRY_WORKSHOP: "jewelry_workshop",
      STATE_BULLETIN_BOARD: "bulletin_board", # 👈 新增城鎮子流程只需在此補一行！
  }
  ```
* **規範**：
  - ⚠️ **嚴禁**在 Handler 或外部寫手動複製 `self.config = GAME_CONFIGS["xxx"].copy()` 的冗餘程式碼。
  - ✅ 新增子流程只需在 `TOWN_SUBFLOW_CONFIG_MAP` 註冊對應 Key，呼叫 `transition_to(STATE_NAME)` 時 Hook 將全自動完成配置替換與髒資料清空。

---

## C. 導航路徑防重入過濾器 (Data-Driven Navigation Filter)
* **API**：`filter_navigation_path(nav_path, active_tabs)`
* **規範**：
  - ⚠️ **嚴禁**在尋路逆序迴圈中寫死 `if btn == "common/select_stage.png" and stage_select_open:` 這類硬編碼字串判斷。
  - ✅ **必須**呼叫 `filter_navigation_path` 進行資料驅動過濾，當目標層級頁籤已處於開啟狀態時，自動過濾父階入口按鈕，防止無謂重入與頁面閃退。

---

## D. 體力退避狀態顯式路由規範 (Explicit Stamina Retreat Routing)
* **核心變數**：`self.machine.stamina_retreat_start_time` (退避開始時間標記)
* **規範**：
  - ⚠️ `transition_to` 保持為純粹的狀態切換器，**禁止**在 `transition_to` 內部暗中修改目標狀態。
  - ✅ 所有 Handler 完工或跳轉退出時，**必須**顯式根據退避時間標記做分流：
    ```python
    next_state = (
        self.machine.STATE_COLLECT_ONLY 
        if self.machine.stamina_retreat_start_time is not None 
        else self.machine.STATE_NAVIGATING
    )
    self.machine.transition_to(next_state)
    ```

---

## E. 鎖定測試保護網 (Lock-in Test Harness)
* **執行測試套件**：`tests/test_stamina_retreat_routing.py`
* **規範**：
  - 每當修改 Handler 的退出或狀態轉移邏輯時，**必須**同步在 `test_stamina_retreat_routing.py` 或對應單元測試中補充專屬的雙向行為測試（退避期間 ➔ `COLLECT_ONLY`；正常期間 ➔ `NAVIGATING`）。
  - 在發起 Git Commit 前，**必須**確保全套 118 個門禁測試 100% 綠燈 PASS。
