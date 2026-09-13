# PARS 開發故事：次級選關與備戰視窗防誤關修復 (Sub-panel Dismissal Protection) 🛡️

## 1. P - Purpose (問題與背景)
在掛機自動化運行期間，觀察到兩起次級視窗被誤關閉的異常行為：
1. **Stage 模式**：點開小關卡選擇抽屜時，因右上角包含關閉按鈕，被意圖表規則 `STAGE_SELECT + CLOSE_OVERLAY → DISMISS_OVERLAY` 誤判為阻塞性覆蓋層而立即點擊關閉。
2. **Domain 模式**：點擊領地入口彈出出戰準備面板時，因右上角同樣帶有 `common/quit.png`，且配置缺少 `lobby_start_btn` 導致開始按鈕未被映射為 `ElementId.START`，系統在 `SceneId.LOBBY` 下將其誤判為 Blocking Overlay 並派發 `DISMISS_OVERLAY`，陷入「點開 ➔ 關閉 ➔ 再點開」的循環。

---

## 2. A - Action (關鍵行動與設計決策)
遵循 Greenfield-lite 架構原則與極簡修復方針，實施以下分層調整：
1. **配置契約對齊 (Slice A)**：在 [config/defaults.toml](../../config/defaults.toml) 的 `[primary_modes.golden_empire]` 補齊 `lobby_start_btn = "domains/common/start_btn.png"`，使領地備戰面板的開始按鈕正確轉譯為 `ElementId.START`。
2. **聲明式路由補充 (Slice B)**：在 [states/navigation_table.py](../../states/navigation_table.py) 宣告 `PRIMARY_NAVIGATION + DOMAIN_SELECT + START → START_PRIMARY` 邊，使領地出戰具備一等公民的路由能力。
3. **過濾過寬之 Dismissal 邊 (Slice C)**：
   - 移除 `V1_NAVIGATION_EDGES` 中錯誤的 `STAGE_SELECT + CLOSE_OVERLAY` 邊。
   - 在 [states/navigation_intent.py](../../states/navigation_intent.py) 建立相容斷言 `_should_delegate_primary_overlay`，限制僅在具備合法自帶關閉鈕的 `domain` 備戰場景下抑制通用大廳關閉邊，並安全回退至 `CONTINUE_PRIMARY`，同時保留 `stage` 與 `dungeon` 模式在真實大廳彈窗下的 `DISMISS_OVERLAY` 自癒能力。
4. **回歸防護網固化**：在 [tests/test_behavior_navigation_table.py](../../tests/test_behavior_navigation_table.py) 建立 6 個新增測試案例，涵蓋感知契約對齊、路由轉發、START 與 QUIT 競態優先級、CV 漏偵測 START 之防護韌性，以及既有大廳彈窗自癒能力。

---

## 3. R - Result (驗證結果與數據)
1. **單元聚焦測試**：
   - `tests.test_behavior_navigation_table`：13/13 測試全數通過。
   - `tests.test_behavior_navigation_intent`、`tests.test_behavior_navigation_progress`、`tests.test_behavior_navigation_scenarios`、`tests.test_behavior_golden_empire`：48/48 測試全數通過。
2. **全套基準線測試 (Phase 1/2)**：
   - Feature 分支 HEAD：**1119 tests 全數通過 (OK, skipped=14)**，耗時 247.026s。
   - 與 main baseline 比對：`BRANCH_REGRESSION = 0`。

---

## 4. S - So What (業務價值與深遠意義)
- **解鎖無人值守多模式掛機**：徹底修復普通關卡選關抽屜與領地古國備戰面板的「循環開關」死循環，確保掛機流程能順利進入關卡與領地戰鬥。
- **維持架構純潔性**：避免為解決局部覆蓋層誤判而引發 FSM State Explosion（未額外引入細碎 SceneId），嚴格遵循 Scene、Overlay 與 Element 的正交分離原則。

---

## 5. I - Influence (架構影響與後續注意事項)
- **長效契約升格**：已在 [Lobby Scene Contract Invariant 7](../features/navigation/lobby_scene_contract.md#invariant-7次級出戰與選關視窗防誤關保證-sub-panel-dismissal-protection-invariant) 固化次級面板防誤關保證。
- **Overlay 技術債備忘**：目前系統以 `common/quit.png` 直接代表 `ElementId.CLOSE_OVERLAY`，在語意上仍混淆了「控制位置 (WHERE)」與「關閉意圖 (WHAT)」。長期應推動基於 `OverlayId` 的獨立感知架構，由 Policy 根據具體覆蓋層識別結果決策是否 dismiss。
