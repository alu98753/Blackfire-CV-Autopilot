# 地下城導航路由與大廳感知升級開發故事 (PARS Story) 📜

---

## Purpose (背景與問題)

在 2026-09-13 的日常掛機運行中，地下城與關卡導航出現兩項連鎖異常：
1. **冷卻地下城重複盲點與卡死**：當地下城進入冷卻時，系統仍重複點擊冷卻中的地下城入口，且遭遇冷卻提示彈窗（右上角帶有 `common/quit.png`）時無對應關閉邏輯，導致畫面變暗並陷入活鎖，最終觸發 90 秒導航逾時。
2. **大廳地下城頁籤重複點擊迷航**：畫面已明確處於活動大廳的地下城頁籤（`dungeons/dungeon_after.png` 明顯可見），但系統卻丟失當前頁籤證據（判定 `active_tabs = []`），反覆點擊未選中態的 `dungeons/dungeon.png`。

經交叉比對運行日誌與源碼，發現其背後存在深層的架構偏離：
- **上游路由不一致**：Daily Tier 4 退守普通關卡時，僅修改 `type = "stage"`，卻未置換 `navigation_path`，殘留地下城路徑。
- **FastPath 感知識盲**：預期頁籤未選中時直接返回 `None`，將「目標不是 active」誤等同於「全畫面無 active」，丟失畫面實際處於 `dungeon_after` 的事實。
- **通用尋路越權分派**：通用逆序導航迴圈直接分派領域入口，缺乏前置冷卻門禁。
- **覆蓋層缺少上下文自癒**：導航頂部僅防護 `confirm/ok`，未將遮擋性 `quit` 彈窗納入導航意圖表治理。

---

## Action (實作行動與設計決策)

本次修復嚴格拒絕在業務邏輯隨手增修局部 `if` 補釘，而是依據 **Config ➔ Perception ➔ Dispatch ➔ Recovery** 四層邊界進行架構對齊：

1. **Spec 0：路由配置不變量保證 (Route Config Coherence Invariant)**：
   - 於 [utils/tier4_config.py](../../utils/tier4_config.py) 中，落實純地下城模式（`type == "dungeon"`）作為獨立玩法，退守時保持自身配置，不套用 Daily Tier 4 轉關。
   - Daily/Mix 模式退守普通關卡時，強制以 canonical stage 路由（優先取 `stage_navigation_path`，次取 `stage_cfg`）覆蓋 `navigation_path`，保證 `fallback["type"] == "stage"` 時絕不含任何地下城入口。
   - 移除無端發明的 `TIER4_MODE_DUNGEON`，防止產品領域模型不當擴張。

2. **Spec 1：感知升級與職責歸位 (Perception Escalation & Single Ownership)**：
   - 於 [utils/scene_detector.py](../../utils/scene_detector.py) 的 `_resolve_expected_lobby_tab()` 中，當預期頁籤經比對為 inactive 時，升級調用 `_resolve_full_relocalize` 全量掃描，客觀確認畫面實際勝出的 active 頁籤（如 `dungeon_after`），保證 `scene.active_tabs` 包含 `{DUNGEON}`。
   - 徹底移除 [states/handlers/navigation.py](../../states/handlers/navigation.py) 中手動比對 `dungeons/dungeon_after.png` 補 `active_tabs` 的 workaround，NavigationHandler 僅單向消費 `scene.active_tabs`。

3. **Spec 2：通用尋路僅消費冷卻門禁 (Generic Navigation Cooldown Gating)**：
   - 嚴守架構邊界：卡片 ROI 裁剪、木牌 OCR、時間解析與冷卻寫入全權歸 Canonical Scanner（`_check_dungeon_status`）所有。
   - 通用逆序尋路迴圈移除所有第二套 OCR 掃描邏輯，僅保留 defense-in-depth 的記憶體冷卻門禁（`if time.time() < cooldown_until: continue`）。

4. **Spec 3：導航覆蓋層意圖路由閉環 (Contextual Overlay Dismissal)**：
   - 於 [states/navigation_table.py](../../states/navigation_table.py) 中，在 `PRIMARY_NAVIGATION` 下為 `LOBBY`、`STAGE_SELECT`、`DUNGEON_SELECT` 場景宣告 `CLOSE_OVERLAY ➔ DISMISS_OVERLAY` 邊。
   - 遇到冷卻提示彈窗時，由意圖路由安全關閉覆蓋層，避免畫面變暗引發活鎖。

---

## Result (實測數據與成果驗證)

由使用者執行完整全套測試套件（`discover tests`），測試結果如下：

| 評量指標 | 修復前現況 | 修復後成果 |
| :--- | :--- | :--- |
| **全套測試通過率** | 1087 tests (2 Failures) | **1096 tests 全數通過 (0 Failure, 14 Skipped)** |
| **全套測試耗時** | 約 241.5 秒 | **241.561 秒** (~4.0 分鐘) |
| **聚焦單元測試** | - | **83 tests 100% 綠燈** (包含 Tier4、感知、導航、實體面板) |
| **架構不變量** | 存在 3 處邊界偏離 | **全部修正：零第二套 Scanner、零手動感知補洞、零殘留地下城路徑** |

---

## So What (架構價值與效益)

1. **落實 Greenfield-lite 感知/決策單向流**：徹底消滅在 NavigationHandler 中私自補感知、私自做 OCR 掃描的 God-handler 傾向，讓 `SceneDetector` 成為場景感知的唯一真理來源。
2. **根除跨模式狀態污染**：保證可執行配置的不變量，避免 Daily 退守與純地下城模式之間因配置污染導致的跳頁盲點與反覆切換。

---

## Influence (後續規劃與注意事項)

1. **導航覆蓋層關閉執行器阻塞式等待技術債**：
   目前 `NavigationDecisionExecutor` 在處理 `DISMISS_OVERLAY` 時調用了 `self.handler.click_and_wait_until_gone(...)`，內部包含阻塞式等待。已將此項目標記於 [docs/todos/future_work.md](../todos/future_work.md)，後續將排程遷移至每幀響應式後置條件驗證。
