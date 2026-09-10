# RFC: 將 Result (ResultHandler) 重構為 BattleResult (BattleResultHandler) 之語意對齊與職責收斂 📄

> **狀態**：RFC (Request for Comments) / 提案階段  
> **關聯文件**：  
> - [`docs/todos/result_todo.md`](result_todo.md) (Greenfield-lite M7 子切片：戰鬥結算與地下城通關閉環)  
> - [`docs/todos/future_work.md`](future_work.md) (未來規劃清單)  
> - [`states/handlers/result.py`](../../states/handlers/result.py)  
> - [`states/handlers/battle.py`](../../states/handlers/battle.py)  
> - [`states/state_machine.py`](../../states/state_machine.py)  

---

## 1. 背景與動機 (Context & Problem Statement)

在目前專案的狀態機中，狀態定義包含：
* `STATE_BATTLE` (`BattleHandler`): 戰鬥進行中，點選自動戰鬥並監控結算。
* `STATE_RESULT` (`ResultHandler`): 戰鬥結束結算，點擊繼續/再戰。

### 問題剖析：
1. **命名過於寬泛 (Semantic Ambiguity)**：
   - 系統中「`RESULT`」的名字過於籠統。然而在實際業務中，它**完全不處理**其他系統的結果（例如開寶箱 `STATE_CHEST`、抽英雄 `STATE_HERO_DRAW`、祭壇獻祭 `STATE_BLOOD_ALTAR` 等，均有自己的獨立狀態與 Handler）。
   - `ResultHandler` 的全部邏輯（`INIT_DELAY` 沉澱、`CONTINUE_LOOP` 點擊 Continue 消除掉落物/勝利彈窗、`FINAL_MATCH` 判定 `retry` 或 `exit_battle`）**100% 只針對「單場戰鬥（Battle）結束後的結算」**。
2. **`should_exit_battle` 職責過載**：
   - 目前在 `ResultHandler._handle_impl` 內部，`should_exit_battle` 混雜了至少 4 種不同維度的業務邏輯：
     - **安全點搶佔 (Safe-point Preemption)**：Tier 4 懸賞任務冷卻結束搶佔、深淵魔王次數可用搶佔、領主 Boss 冷卻結束搶佔。
     - **工作流完成 (Workflow Completion)**：日常懸賞任務批次達到（如第 4 場）、魔王/Boss 單次挑戰完畢離場。
     - **保護性復原/退避 (Recovery & Protective Retreat)**：體力耗盡（`stamina_retreat`）、背包滿需整理（`need_bag_cleaning`）。
     - **定時/閒置政策 (Scheduled / Idle Policy)**：08:05 跨日重置離場（`pending_daily_reset_exit`）、定時領鑽石/麵包。
3. **場景辨識與轉移邊界混淆**：
   - 在地下城探索中，戰鬥結算點擊 `continue.png` 後直接回到地下城地圖（`STATE_DUNGEON_EXPLORING`），甚至不一定進入 `STATE_RESULT`，導致 `BattleHandler` 與 `ResultHandler` 之間在地下城模式上有邊界不對稱的問題。

---

## 2. 提案目標 (Goals)

1. **語意精確化 (Precise Semantics)**：
   - 將 `STATE_RESULT` 明確重新命名為 **`STATE_BATTLE_RESULT`**。
   - 將 `ResultHandler` 明確重新命名為 **`BattleResultHandler`**（檔案路徑遷移或對齊為 `states/handlers/battle_result.py`）。
2. **狀態定義對稱性 (Structural Symmetry)**：
   - 主流程明確成對：`NAVIGATING` ➔ `LOBBY` ➔ `BATTLE` ➔ **`BATTLE_RESULT`** ➔ (`BATTLE` / `NAVIGATING` / 各 Subflow Entry)。
3. **決策分流解耦 (Deconstruct `should_exit_battle`)**：
   - 將現行巨大布林表達式拆解為語意清晰的決策策略：
     - `should_preempt_for_high_priority()`
     - `is_current_workflow_satisfied()`
     - `should_retreat_for_resource_protection()`
     - `should_exit_for_scheduled_tasks()`

---

## 3. 重構分階段執行規劃 (Phased Migration Plan)

### Phase 1: 概念與文檔對齊 (Docs Alignment)
- [x] 建立本 RFC 文檔，並於 `docs/todos/future_work.md` 建立待辦追蹤。
- [ ] 檢視並更新 `docs/architecture/project_arch_greenfield_lite_v1.md` 與 `docs/todos/result_todo.md` 中的場景定義（統一採用 `SceneId.BATTLE_RESULT` / `STATE_BATTLE_RESULT`）。

### Phase 2: 保持向下相容的別名引導 (Backward Compatible Aliasing)
- 在 `states/state_machine.py` 中引入：
  ```python
  STATE_BATTLE_RESULT = "BATTLE_RESULT"
  # 保留向下相容別名，避免既有外部測試或腳本瞬間損壞
  STATE_RESULT = STATE_BATTLE_RESULT
  ```
- 建立 `states/handlers/battle_result.py`（類別 `BattleResultHandler`），原 `ResultHandler` 作為子類別繼承或引用，並在日誌輸出中標註為 `BattleResultHandler`。

### Phase 3: `should_exit_battle` 策略模組化 (Policy Decomposition)
- 將原本集中在 `ResultHandler` 內的 20 行複合 `should_exit_battle` 條件，重構為明確的方法或獨立策略評估器：
  ```python
  def _evaluate_battle_exit_intent(self) -> BattleExitReason:
      if self._check_resource_retreat(): # 體力/背包滿
          return BattleExitReason.RESOURCE_RETREAT
      if self._check_high_priority_preemption(): # Tier 4 插隊
          return BattleExitReason.PRIORITY_PREEMPTION
      if self._check_workflow_completed(): # 懸賞 4 場打完 / Boss 結束
          return BattleExitReason.WORKFLOW_COMPLETED
      if self._check_scheduled_event(): # 08:05 重置 / 定時領取
          return BattleExitReason.SCHEDULED_EVENT
      return BattleExitReason.CONTINUE_FIGHTING
  ```

### Phase 4: 全局測試與引用替換 (Test & Reference Migration)
- 逐步更新 `tests/test_behavior_*.py` 中對 `STATE_RESULT` 的引用至 `STATE_BATTLE_RESULT`。
- 清理所有 Deprecated 別名。

---

## 4. 風險與評估 (Risks & Trade-offs)

1. **測試影響面較廣**：
   - 既有測試中有超過 20 個測試檔直接引用了 `STATE_RESULT` 或 `ResultHandler`。
   - **緩解措施**：採用 Phase 2 的別名機制（`STATE_RESULT = STATE_BATTLE_RESULT`），保證改動過程中所有既有單元測試 100% 綠燈，不造成破壞性中斷。
2. **運行時穩定性**：
   - 核心邏輯保持 `INIT_DELAY` ➔ `CONTINUE_LOOP` ➔ `FINAL_MATCH` 的 3 階段行為不變，僅提升架構可讀性與維護性。
