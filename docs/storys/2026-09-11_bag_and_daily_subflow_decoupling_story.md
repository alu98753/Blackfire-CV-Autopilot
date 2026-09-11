1: # 研發故事：背包維護與每日子流程解耦及覆蓋層防護 (PARS) 🎒
2: 
3: - **日期**：2026-09-11 ~ 2026-09-12
4: - **分支**：`fix/bag-and-daily-subflow-decoupling`
5: - **上位架構**：[Greenfield-lite Architecture v1](../architecture/project_arch_greenfield_lite_v1.md)
6: - **權威契約**：[城鎮任務流水線佇列契約](../features/town_building/pipeline.md)、[每日懸賞任務架構報告](../features/daily_task/daily_task_architecture_report.md)
7: - **關聯 Issues**：[bag_bug.md](../todos/bag_bug.md)、[bag_jewelry_workshop_bug.md](../todos/bag_jewelry_workshop_bug.md)、[future_work.md](../todos/future_work.md)
8: 
9: ---
10: 
11: ## 1. Purpose (背景與目的)
12: 
13: 在先前的無人值守測試中，密集出現了三項破壞長掛機穩定性的嚴重異常：
14: 1. **背包滿後觸發珠寶店/血之祭壇時，背包未關閉即跳轉懸賞導致全域卡死**：
15:    珠寶店進店前打開背包，畫面暗化但邊緣仍匹配到城鎮大門 `common/door.png`，觸發 Scene Guard 防護攔截逃逸，留下未關閉的背包視窗；導航層前往懸賞任務時盲目點擊城門，被背包遮擋點擊無效，連續 15 次重試卡死。
16: 2. **懸賞告示牌尚未進入建築（還在背包/其他過渡畫面）就開始誤判任務**：
17:    告示牌處理器僅憑 `common/quit.png` 就認定進入告示牌，在殘留背包畫面上執行任務 OCR，因無任務而誤判定「今日所有任務均已接滿」，吞噬了整天的懸賞任務。
18: 3. **血之祭壇獻祭被每日紅點政策跳過**：
19:    戰後背包清理後借用 Daily 流水線，但血之祭壇在戰後滿包時並無紅點，被前置控制器誤當每日已完成跳過，且污染了每日完成狀態。
20: 4. **珠寶店內嵌整理時序穿透事故**：
21:    在初期版本中，將開包整理內嵌於珠寶店內部，因開包過渡期未就緒回傳 False 且缺乏 Early Return，導致時序穿透至進店點擊，進店失敗後在城門停留逾時觸發 Watchdog，造成 Sandbox 帳號連環重開。
22: 
23: 本任務目的為徹底將「背包維護流水線 (Maintenance)」與「每日福利流水線 (Daily)」解耦，將背包整理升格為一級獨立子流程 `BagTidyHandler`，並落實覆蓋層排他性門禁與建築進場專屬正交錨點。
24: 
25: ---
26: 
27: ## 2. Action (架構行動與實作細節)
28: 
29: 1. **配置與領域規格徹底雙軌解耦**：
30:    - 將每日速領（`blood_altar`，需紅點，簽核 daily）與維護獻祭（`blood_sacrifice`，不查紅點，不簽核 daily）徹底分離。
31:    - 統一背包維護順序為 `default_bag_maintenance_order = ["blood_sacrifice", "bag_tidy", "jewelry_workshop"]`。
32:    - 在 `states/town_subflow_registry.py` 登錄 `blood_sacrifice` 與 `bag_tidy` 規格。
33:    - 在 `states/handlers/bag_cleaning.py` 將城鎮調度統一導向 `trigger_bag_maintenance_chain()`。
34: 2. **獨立背包整理子流程 (`BagTidyHandler`) 與後置條件驗證**：
35:    - 建立 `states/handlers/bag_tidy.py`，徹底純化珠寶店職責，將整理邏輯自 `JewelryWorkshopHandler` 拔除。
36:    - 實作嚴格三項後置條件驗證：點擊關閉按鈕調用 `click_and_wait_until_gone("common/quit.png")` ➔ 重新截圖斷言 `quit` 為 None、`tidy` 為 None 且 `door` 成立（純淨城鎮無覆蓋層），全數滿足方可調用 `pop_and_next_town_subflow()`。
37: 3. **珠寶店 Scene Guard 修復與進店點擊遺失自癒**：
38:    - 於 `INIT` 階段加入覆蓋層清理：若偵測到殘留 `quit.png`，優先閉環清理。
39:    - 於 `ENTERED_BUILDING` 階段加入自癒：若超過 4 秒畫面依然停留在城門口且無店內特徵，判定進店點擊遺失（Missed Click），自癒退回 `INIT` 重新點擊進店，杜絕原地死鎖。
40: 4. **告示牌排他性專屬正交錨點防護與閉環自癒**：
41:    - 於 `states/handlers/bulletin_board.py` 實作 `_is_inside_bulletin_board()`：必須滿足 `quit.png` 可見 + 負向排除背包特徵 (`tidy.png`/`Disassembly.png`) + 正向三通道 OR 特徵（`task.png` / `task_after.png` / `reset.png` 命中任一）。
42:    - 若未滿足專屬特徵或存在背包遮罩，判定為外部干擾覆蓋層並點擊關閉自癒，絕不誤判任務接取狀態。
43: 5. **雙工作樹全套測試比對與修復**：
44:    - 於 `temp-main` (976 tests) 與 Feature HEAD (1002 tests) 執行全套基準測試比對。
45:    - 針對定位出的 9 項 `BRANCH_REGRESSIONS`（6 項珠寶店過期 mock、2 項維護鏈調度斷言、1 項獻祭命名對齊）與 4 項失真 Mock 邊界全數完成修復，達成 `BRANCH_REGRESSIONS: 0`。
46:    - 徹底清除 `town_building_detector.py` 中的測試專用特判代碼。
47: 
48: ---
49: 
50: ## 3. Result (驗證成果)
51: 
52: 1. **全套測試迴歸比對結果**：
53:    - `BRANCH_REGRESSIONS`: **0**
54:    - `UNCERTAIN`: **0**
55:    - `PRE_EXISTING_FAILURE`: 32（與 main 基準線完全一致的歷史固有錯誤）
56:    - `FIXED IN HEAD`: 5（本分支修復的既有錯誤）
57: 2. **聚焦單元測試覆蓋**：
58:    - `tests/test_behavior_bag_tidy_subflow.py` (6/6 OK)
59:    - `tests/test_behavior_bag_scenarios.py` (15/15 OK)
60:    - `tests/test_behavior_bag_cleaning.py` (6/6 OK)
61:    - `tests/test_behavior_jewelry_workshop_rotation.py` (10/10 OK)
62:    - `tests/test_bulletin_board_subflow.py` (7/7 OK)
63: 
64: ---
65: 
66: ## 4. So What (架構價值與影響)
67: 
68: 1. **職責單一與消除時序穿透**：背包純排序與珠寶店進店出售完全解耦為獨立子流程，消除了跨業務狀態交錯與時序穿透問題。
69: 2. **後置條件閉環保證**：任何視窗在交棒給下一個流程前，必須透過物理特徵驗證視窗已徹底關閉，保證後續流程永遠在純淨基準場景中啟動。
70: 3. **流水線雙軌解耦**：日常福利領取與戰後背包維護各司其職，互不干擾、互不污染。
71: 
72: ---
73: 
74: ## 5. Influence (後續維護指引)
75: 
76: - 新增城鎮內部流程時，必須依據 [城鎮任務流水線佇列契約](../features/town_building/pipeline.md) 實作獨立 Handler 與後置條件驗證，嚴禁在個別建築 Handler 內部偷跑其他業務流程。
77: - 建築進場判定必須採用專屬排他性錨點，嚴禁以通用按鈕（如 `common/quit.png`）作為特定場景的進場充分條件。
78: 
