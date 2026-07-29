# PARS 開發故事：懸賞離場判定、Tier 4 導航死鎖修復、背包八大動作模組化與 Pre-Tidy 狀態機重構

## 1. Purpose (目的與痛點)
- **痛點 1 (懸賞第 10 次無限續戰)**：在每日懸賞任務執行至第 10/10 場戰鬥結束時，因 `is_in_tier4` 判定混淆了當前懸賞配置與 Tier 4 退守模式，導致結算處理器誤以為進入退守無限續戰，觸發 `retry.png` 而未點擊 `exit_battle.png` 離場。
- **痛點 2 (Tier 4 導航死鎖)**：懸賞全數完成切換至 Tier 4 退守模式後，`NavigationHandler._switch_to_stage_or_back` 因無條件 Early Return 攔截，導致「點擊 `select_stage.png` 頁籤」被跳過，系統停留在舊懸賞地點並重複執行舊指令。
- **痛點 3 (背包清理單體混亂)**：`BagCleaningHandler` 原本為巨型單體（Monolith）邏輯，無法將「開背包、整批分解、選擇品質、整理、退出」等 8 大子動作靈活被其他城鎮建築（如珠寶加工廠進場前 Pre-Tidy）單獨調用。
- **痛點 4 (Pre-Tidy 背包開啟遮擋死鎖)**：珠寶加工廠進場前開啟背包後，背包彈窗直接遮擋了身後的城鎮大門與建築，導致 `if pos_building and pos_door:` 判定失效，使點擊「整理」與「退出」無法被執行。

---

## 2. Action (行動與修復細節)
- **行動 1 (精確化 `is_in_tier4` 判定)**：
  修改 `ResultHandler` 的離場條件，將 `is_in_tier4` 嚴格綁定至當前 `config` 的 `is_tier4_fallback == True` 標記：
  ```python
  is_in_tier4 = is_daily and self.machine.config.get("is_tier4_fallback", False)
  ```
  確保 10/10 懸賞完成當下 `should_exit_battle` 返回 `True` 並點擊離場。

- **行動 2 (解除 Navigation Early Return 死鎖)**：
  在 `NavigationHandler._switch_to_stage_or_back` 中，僅在「仍有懸賞任務排程中 (`quest_scheduler is not None`)」且「非 Tier 4 退守模式 (`is_tier4_fallback == False`)」時才 Early Return：
  ```python
  if self.machine.is_daily_pipeline_active() and getattr(self.machine, "quest_scheduler", None) is not None and not self.machine.config.get("is_tier4_fallback", False):
      self.machine.evaluate_and_schedule_daily_pipeline()
      return
  ```
  確保 Tier 4 退守模式下精確點擊 `common/select_stage.png` 並切換導航關卡。

- **行動 3 (背包 8 大核心 Function 模組化與 SSOT 抽取)**：
  將 `BagCleaningHandler` 重構為 8 個具備統一簽署 `func(self, screen_img, rect) -> bool` 的高強度獨立 Function：
  `open_backpack`, `enter_mass_disassembly`, `select_all_items`, `deselect_valuable_items`, `execute_disassembly`, `confirm_popups`, `tidy_backpack`, `quit_backpack`。
  並建立獨立測試單元 `test_bag_cleaning_modular_functions.py` (7 tests PASS)。

- **行動 4 (Unnesting 珠寶加工廠 Pre-Tidy 狀態機)**：
  將 `is_backpack_opened` 的處理獨立提升至最高層級，解除其對 `pos_building` 與 `pos_door` 的層級依賴。背包開啟時不受遮擋影響獨立完成「整理 ➔ 退出」，背包關閉露出身後建築後再點擊進入。

- **行動 5 (使用者介入時間補償架構)**：
  在 `MouseController` 手動滑數介入時記錄 `last_user_input_time`，從 Watchdog 與流轉計時器中扣除使用者操作時間，避免超時誤判。

---

## 3. Result (成果與驗證)
- **單元測試全綠**：全套件 **406 項單元測試 100% 綠燈通過 (OK)**，覆蓋率包含懸賞 10/10 結算、Tier 4 導航、背包八大模組、Pre-Tidy 狀態機與使用者介入時間補償。
- **程式碼穩定度**：所有重構均相容於現有每日大流水線 (Daily Master Pipeline) 與 Watchdog 復原機制。

---

## 4. So What (核心工程價值)
- **架構四支柱徹底實踐 (Entity, State, Data, Exception)**：
  - **Entity**: 將 `BagCleaningHandler` 的大動作抽象成原子化 Entities，利於跨 Handler（如 `JewelryWorkshopHandler`）高複用。
  - **State**: 解除狀態機層級嵌套 (Unnesting)，消除 UI 彈窗遮擋導致的虛假死鎖。
  - **Data**: 嚴格維護 Single Source of Truth (SSOT)，以 `is_tier4_fallback` 標旗作為離場與退守導航的唯一權威數據。
  - **Exception**: Watchdog 考量 User Intervention 時間補償，打造閉環自癒與抗人為干擾能力。

---

## 5. Influence (影響與後續借鑑)
- **後續模組開發範本**：未來的城鎮建築子流程（如 `HeroDraw`, `BloodAltar`）若需預先整理背包，可直接鏈接 `bag_handler` 的原子 Function，零邊際維護成本。
- **分支營運無痛合併**：確保 `feature/dungeon-relaunch-recovery` 分支完全符合 `--no-ff` 合併規範，保持 Commit 歷史清潔透明。
