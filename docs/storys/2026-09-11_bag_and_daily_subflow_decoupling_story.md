# 研發故事：背包維護與每日子流程解耦及覆蓋層防護 (PARS) 🎒

- **日期**：2026-09-11
- **分支**：`fix/bag-and-daily-subflow-decoupling`
- **上位架構**：[Greenfield-lite Architecture v1](../architecture/project_arch_greenfield_lite_v1.md)
- **規格書**：[bag_and_daily_subflow_decoupling_spec.md](../todos/bag_and_daily_subflow_decoupling_spec.md)
- **關聯 Issues**：[bag_bug.md](../todos/bag_bug.md)、[bag_jewelry_workshop_bug.md](../todos/bag_jewelry_workshop_bug.md)、[future_work.md](../todos/future_work.md)

---

## 1. Purpose (背景與目的)

在先前的無人值守測試中，密集出現了兩項破壞掛機穩定性的嚴重異常：
1. **背包滿後觸發珠寶店/血之祭壇時，背包未關閉即跳轉懸賞導致全域卡死**：
   珠寶店進店前打開背包，畫面暗化但邊緣仍匹配到城鎮大門 `common/door.png`，觸發 Scene Guard 防護攔截逃逸，留下未關閉的背包視窗；導航層前往懸賞任務時盲目點擊城門，被背包遮擋點擊無效，連續 15 次重試卡死。
2. **懸賞告示牌尚未進入建築（還在背包/其他過渡畫面）就開始誤判任務**：
   告示牌處理器僅憑 `common/quit.png` 就認定進入告示牌，在殘留背包畫面上執行任務 OCR，因無任務而誤判定「今日所有任務均已接滿」，吞噬了整天的懸賞任務。
3. **血之祭壇獻祭被每日紅點政策跳過**：
   戰後背包清理後借用 Daily 流水線，但血之祭壇在戰後滿包時並無紅點，被前置控制器誤當每日已完成跳過，且污染了每日完成狀態。

本任務目的為徹底將「背包維護流水線 (Maintenance)」與「每日福利流水線 (Daily)」解耦，落實覆蓋層排他性門禁與建築進場專屬正交錨點。

---

## 2. Action (架構行動與實作細節)

1. **配置與領域規格徹底解耦並統一設定命名**：
   - 移除了歷史遺留且命名重複的 `default_town_subflow_order`，統一為 `default_bag_maintenance_order = ["blood_sacrifice", "jewelry_workshop"]` 與 `[subflow_configs.blood_sacrifice]`。
   - 在 `states/town_subflow_registry.py` 登錄 `blood_sacrifice` 規格（`requires_red_dot=False`）。
   - 在 `states/state_machine.py` 新增專屬調度方法 `trigger_bag_maintenance_chain()`，`trigger_town_subflow_chain` 轉為相容轉發；並保護 `complete_current_town_subflow()` 在執行 `blood_sacrifice` 時不污染 `DailyManager` 的 daily completed 紀錄。
   - 在 `states/handlers/bag_cleaning.py` 將城鎮調度統一導向 `trigger_bag_maintenance_chain()`。
2. **珠寶店前置整理有界化與 Scene Guard 修復**：
   - 珠寶店進店前的城鎮背包預先整理維持獨立有界邏輯，以 `click_and_wait_until_gone("common/quit.png")` 嚴格驗證背包視窗徹底消失，才允許進入商店尋找與進店階段。
   - 修復 Scene Guard：僅在 `SELL_MENU_OPEN` 階段且確認商人看板丟失時才評估 `common/door.png`，在過渡期 `ENTERED_BUILDING` 與 `INIT` 階段嚴禁觸發假陽性逃逸。
3. **告示牌排他性專屬正交錨點防護與閉環自癒**：
   - 於 `states/handlers/bulletin_board.py` 升級 `_is_inside_bulletin_board()`，將特徵門檻提高至 `0.80`（`quit_btn`, `tidy.png`, `Disassembly.png`, `reset.png`, `task.png`, `task_after.png`），杜絕背景雜訊誤判。
   - 刪除 `WAIT_BOARD_OPEN` 中 `or (pos_quit and not has_bag_overlay)` 漏洞，只有滿足 `is_board` 才能進入重置與領取。
   - 若在 `WAIT_BOARD_OPEN` 或 `INIT` 階段偵測到非告示牌之干擾覆蓋層（如殘留背包或彈窗），調用 `click_and_wait_until_gone(quit_btn, ...)` 閉環確認關閉消失後退回 `INIT`，下一影格在乾淨城鎮畫面重新點擊告示牌建築進入，實現可靠自癒。
4. **導航層城門模態覆蓋層門禁**：
   - 於 `states/handlers/navigation.py` 點擊 `common/door.png` 前加入覆蓋層檢查：若畫面殘留未關閉的背包或彈窗，優先點擊關閉按鈕，絕不盲目點擊被遮擋的城門。

---

## 3. Result (驗證成果)

- 新增聚焦行為單元測試 `tests/test_behavior_bag_and_daily_decoupling.py`（5 個測試全部 100% 綠燈通過）：
  1. `test_trigger_bag_maintenance_chain_queues_independent_subflows`: 通過
  2. `test_blood_sacrifice_spec_and_completion_does_not_pollute_daily`: 通過
  3. `test_bulletin_board_with_backpack_overlay_does_not_swallow_quests`: 通過
  4. `test_navigation_overlay_gate_blocks_blind_door_click`: 通過
  5. `test_jewelry_workshop_scene_guard_does_not_abort_before_shop_entry`: 通過
- 既有相關業務領域測試均通過：
  - `tests/test_behavior_bag_cleaning.py` (6/6 OK)
  - `tests/test_jewelry_workshop_pre_tidy.py` (3/3 OK)
  - `tests/test_behavior_jewelry_stuck.py` (2/2 OK)
  - `tests/test_behavior_town_subflows.py` (5/5 OK)
  - `tests/test_bulletin_board_subflow.py` (7/7 OK)
  - `tests/test_entity_bulletin_board_panel.py` (2/2 OK)

---

## 4. So What (架構價值與影響)

1. **同源根治**：不再需要對個別 Handler 進行 ad-hoc 打補釘，而是依據 Greenfield-lite 的「Scene vs Overlay 排他性」不變量，全鏈路確保模態視窗的生命週期閉環。
2. **流水線純潔化**：徹底切分了「日常免費福利領取」與「戰後資源消耗維護」兩條生命週期與觸發條件完全不同的流水線，互不污染。

---

## 5. Influence (後續維護指引)

- 未來新增城鎮內部模態視窗或子流程時，必須恪守「進入前正交專屬錨點檢驗」與「退出時 `click_and_wait_until_gone` 配對消失閉環」，不得以單一 `quit.png` 作為進場憑證。
