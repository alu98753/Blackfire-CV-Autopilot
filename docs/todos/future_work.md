# 待辦事項與未來優化規劃 (Future Work & Project TODOs) 📋

本文件彙整《黑火遠征》專案的所有**待辦事項 (Active TODOs)**、**暫時擱置需求 (Shelved)** 與**已解決/已驗證項目 (Completed & Verified)**，作為長期維護與疊代之單一清單。

---

## 已經完成 正在觀察

- [x] **任務依關卡上限過濾 (Quest Level Filter)**：依據不同模式透過 TOML 設定追蹤最高關卡上限（`max_stage` / `max_dungeon`），在告示牌接完任務後自動過濾無法通關的任務。（已由 [`utils/quest_mapper.py:filter_unreachable_quests`](../../utils/quest_mapper.py#L243) 與 [`utils/quest_scheduler.py`](../../utils/quest_scheduler.py) 實現）
- [x] 關卡等沒看到要向左滑動到底，直到看到第一關。
- [x] 現在商人適用次數，應該改成金錢擁有數。（已完成）
- [x] 驚嘆號排除橘色的任務點，只接受紅色的每日領取點。（已完成）
- [x] 關卡小關卡 (1, 5/mid, 6, 10/final) 通用化與零截圖擴充：以通用 [`boss_skull.png`](../../templates/stages/boss_skull.png) 與頂部 ([`first_stage.png`](../../templates/stages/first_stage.png)) / 底部 ([`six_stage.png`](../../templates/stages/six_stage.png)) 視覺閉環，實現全章節（含 Stage 7+）全量子關卡免截圖支援。（已完成）
- [x] 朱王與朱厚判定任務完成的 OCR 邊界擴大與 debug 截圖。（已加入除錯視覺化）
- [x] 地下城通關狀態早產與大廳導航迷航已閉環修復。（已升格至 [Precondition Contracts 7.1](../architecture/precondition_contracts.md#71-活動與地下城通關離場後置條件閉環契約-activity--dungeon-exit-postcondition-contract) 與 [Lobby Scene Contract Invariant 6](../features/navigation/lobby_scene_contract.md#invariant-6導航地下城客觀特徵自癒彈回保證-dungeon-re-entrant-guard-invariant)）
- [x] 重開登入全域感知解耦與地下城交棒前置離場路由已閉環修復。（已升格至 [Precondition Contracts 7.2](../architecture/precondition_contracts.md#72-重開登入全域感知解耦與前置離場路由契約-game-relaunch-world-perception--prerequisite-route-injection-contract) 與 PARS 故事 [2026-09-11_login_flow_dungeon_handover_and_global_perception_story.md](../storys/2026-09-11_login_flow_dungeon_handover_and_global_perception_story.md)）

### Daily

- [x] **每日任務閉環 (Daily Master Pipeline)**：`chest`、`hero_draw`、`blood_altar`、`bulletin_board` 穩定執行。
- [x] **Discord 自動化運作與健康度通報**：朝向「早上不打開遠端、不看遊戲，也能確信腳本正常運作；只有需要人工介入時才通報」之架構契約。（已收斂至 [Notification Contract](../features/notification/notification_contract.md)）
- [x] **Daily 模式退避進入 `COLLECT_ONLY` 後，地下城冷卻結束無法定時回歸**：待機喚醒機制與型態判斷缺陷修復，冷卻就緒後自動喚醒復歸。（由 commit 8d4ce03、0626e03 與 fix/stamina-retreat-dungeon-resume 驗證完成）
- [x] **`COLLECT_ONLY` 期間定時領完體力竟擅自跑去打 Tier 4 關卡**：退避待機期間領完體力安全返回城鎮等待，不破壞待機節奏。（由 fix/stamina-retreat-dungeon-resume 閉環修復）
- [x] **背包滿後觸發珠寶店/血之祭壇時，背包未關閉即跳轉懸賞導致全域卡死**：背包整理升格為一級獨立子流程 `BagTidyHandler` 並以消失閉環確認關閉。（詳細見 [城鎮任務流水線佇列契約](../features/town_building/pipeline.md)）
- [x] **懸賞告示牌尚未進入建築（還在背包/其他過渡畫面）就開始誤判任務**：告示牌處理器增加 `_is_inside_bulletin_board` 排他性專屬正交錨點門禁，見干擾覆蓋層點擊關閉自癒。（詳細見 [每日懸賞任務報告](../features/daily_task/daily_task_architecture_report.md#3-告示牌進場排他性正交錨點契約-building-entry-unique-anchor-invariant)）
- [x] **血之祭壇 (Blood Altar) 判定被紅點掠過問題**：徹底拆分為日常任務速領 (`blood_altar`，需紅點) 與戰後背包滿時的獻祭 (`blood_sacrifice`，不查紅點)。（詳細見 [城鎮任務流水線佇列契約](../features/town_building/pipeline.md)）
- 核心契約：[城鎮任務流水線佇列契約](../features/town_building/pipeline.md) (已完成雙軌解耦、獨立 bag_tidy 與後置條件驗證契約)
- 長期架構 RFC：[模式與活動大一統規格書](activity_mode_consolidation_spec.md) (統一名詞為 ActivityPlan/Activity/Intent，徹底消除 Mode 與 Subflow 歷史割裂)

### Navigation

- [x] 選關與地下城向右翻頁/滑動過慢且比對過多無關圖片。（已在 commit 6cea216 完成優化）

---

## 📌 一、 進行中與待開發項目 (Active TODOs)

> 💡 **24/7 排序指標**：各章節第一項標註 `🔴` 者，代表最可能導致無人值守時陷入死鎖、活鎖、假陽性完成或無效空轉之最高風險項目，優先推進。

### Daily
- [ ] **公告牌 livelock 修正** [bulletboard_bug.md](bulletboard_bug.md)
- [ ] 🔴 **定時領體力打不開視窗觸發 DEFER 時，被誤當成 Blocking 導致主排程活鎖**：
  - **24/7 風險 (活鎖)**：定時領取體力在特定畫面打不開視窗時觸發 DEFER，若狀態機將 DEFER 誤判為阻塞性條件，會導致主排程停止派發後續所有 Activity，全系統陷入活鎖停擺。
  - **規劃方向**：明確切分 DEFER 與 BLOCKING 語意；DEFER 僅延後當前 Intent，主排程必須能自由降級並推進其他非依賴任務。
- [ ] 🔴 **Boss 誤判已完成與次數判定修復 ([`fix_boss_bug.md`](fix_boss_bug.md))**：
  - **24/7 風險 (持久化狀態污染)**：目前「Start 點了沒有進入戰鬥」會被推論為次數已滿，直接呼叫 `mark_boss_completed()`。這種假陽性推論會持久化寫入 [`user_data/native/daily_status.json`](../../user_data/native/daily_status.json)，導致當日後續完全不再嘗試打 Boss，嚴重破壞日常責任移交。
  - **規劃方向**：廢除 Start 逾時反推次數的猜測邏輯，改以畫面中 5 個黑/白點作為 Boss 次數耗盡的客觀真理依據。
- [ ] 🔴 **COLLECT_ONLY 期間洩漏進入 Tier 4 / 黃金古國問題排查**：
  - **24/7 風險 (Tier 階梯契約違規)**：操作員回報在 daily 模式進入 `COLLECT_ONLY` 後，系統竟偶發跑到黃金古國（Tier 4 設定）。此現象直接違反「高 Tier 未完成禁止洩漏 Tier 4」與「待機期間嚴禁執行非待機任務」之階梯契約。
  - **規劃方向**：於 `DailyMasterPipeline` 與狀態機調度層增加強型態門禁，當處於 `COLLECT_ONLY` 待機狀態時，絕對禁止任何 Tier 4 意圖派發。
- [ ] 🔴 **跨流程 Action 與後置條件驗證閉環推進 (消除卡頓無效推進風險)**：
  - **24/7 風險 (進度漂移與狀態迷航)**：在逐步消除 `while` 死等改為 tick 驅動時，若遊戲或系統卡頓，缺少後置條件驗證的點擊會導致流程在 action 尚未生效時無效推進。新 Navigation 已採用 `InFlightAction` 與後置條件確認，但部分 Legacy Handler 仍仰賴固定延遲，需全面建立通用契約。
  - **規劃方向**：建立通用「Action 發起 ➔ 次幀特徵驗證 ➔ 成功推進 / 逾時重試」推進契約，全面取代裸點擊與脆弱 sleep。
- [ ] **領主 Boss(Lord) 與深淵魔王(Demon Lord) 穩定運行與材料防護**：
  - 保證 Lord、Demon Lord 執行不被其他 Activity 搶佔，能穩定打完。
  - Demon 石頭耗盡時的策略（黃色耗盡是否改用紫色）；評估加入商店定時購買材料與競技場門票之機制。
- [ ] **釐清 Daily Complete 與 Defer 的判斷依據**：
  - 統整並固化 Daily 各子流程「何時標記 Complete、何時進入 Defer」的客觀規則。
- [ ] **王核自動挑戰與分解 (feat-auto-king-core)**：
  - 每日任務全部完成後的空檔，自動檢視背包王核並前往討伐；背包滿時自動分解傳奇以下裝備，並前往珠寶店出售。
- [ ] **修復領鑽石延遲 (fix diamond collect lag)**：
  - 分析領取鑽石子流程中的視覺比對與點擊延遲。
- [ ] **驗證橘紅雙點共存功能在 Daily 正常**：
  - 確保告示牌或城鎮中橘色任務驚嘆號與紅色每日領取點共存時，優先級與過濾邏輯正確。
- [ ] **通知訊息多語言擴充 (Notification i18n Expansion)**：
  - 目前已支援繁體中文 (`zh-TW`) 與英文 (`en`)；未來規劃支援簡體中文 (`zh-CN`)、日文 (`ja`)、韓文 (`ko`)。

### 商店

- [ ] 🔴 **珠寶店商人金幣耗盡防護與通知**：
  - **24/7 風險 (經濟迴圈中斷)**：長時間掛機時商人金幣可能被賣光（低於預設門檻 1000）。若無防護，會反覆進入商店嘗試出售失敗並空轉。
  - **規劃方向**：偵測商人剩餘金額，低於閾值時標註 `shop_money_notenough` 暫時封閉進入，並發送通知提醒操作員；後續規劃向商人購買關鍵材料/道具以補給商人金幣。

### 資源與模板路徑重構 (Template Assets Reorganization)

- [ ] 🔴 **安全移動關卡頁籤模板至 `templates/stages/` 並更新引用路徑**：
  - 將 [`common/select_stage.png`](../../templates/common/select_stage.png) 與 [`common/select_stage_after.png`](../../templates/common/select_stage_after.png) 移動至 `templates/stages/`（與 `dungeons/`、`domains/`、`demon_lords/` 保持一致）。
  - 同步更新 [`utils/scene_types.py`](../../utils/scene_types.py) (`LOBBY_TAB_DEFINITIONS`)、相關 Handler 與所有測試案例。

### Navigation

- [ ] 🔴 **導航 90 秒逾時觸發 Watchdog 強制殺進程重開，且重啟後反覆卡死陷入死循環 ([`watchdog.md`](watchdog.md))**：
  - **24/7 風險 (無限崩潰迴圈)**：導航因特徵未命中逾時達到 90 秒觸發 Watchdog，若重啟後依然無法辨識（如解析度/偏移/彈窗未關），會陷入「導航逾時 ➔ 重啟 ➔ 再次逾時」的死循環，最終觸發 Supervisor crash-loop 告警。
  - **規劃方向**：完善導航各子場景的客觀特徵比對與主動自癒退回，防止看門狗假陽性升級。
- [ ] **推進 Scoped Perception (`DetectorRegistry`) 全面遷移，根除 `SceneDetector` 中所有殘留的 `config_type` 硬特判 ([`scoped_perception_migration.md`](scoped_perception_migration.md))**：
  - 卡片與玩法感知徹底移出全域感知，消除 [`utils/scene_detector.py`](../../utils/scene_detector.py) 中的 `allow_card_fallback`。
  - **當前進度與階段成果**：
    - ✅ **已完成 (fix/login-flow-dungeon-handover)**：徹底刪除原步驟 1 主動路徑 `is_dungeon_mode = config_type in ["dungeon", "mix"]` 硬特判與步驟 3.5 過渡期後備防禦；將地下城、戰鬥與結算客觀特徵登錄至 `SCENE_ANCHOR_SPECS`。
    - ⏳ **待完成殘留**：[`utils/scene_detector.py:326-328, 393-420`](../../utils/scene_detector.py#L393-L420) 仍有 `config_type` 與步驟 5 的「大廳卡片模板備援掃描 (`allow_card_fallback`)」，需待獨立議題將卡片與玩法感知徹底移出全域感知並封裝入 `ScopedDetector`。
- [ ] **模式 `mix` 解耦**：
  - 將歷史遺留的混合模式 `mix` 解耦為純場景與排程驅動，消除 `daily` 構建於 `mix` 之上的歷史包袱。
- [ ] **導航與狀態機模組化縮編 (~300 行原則)**：
  - 目前 [`states/handlers/navigation.py`](../../states/handlers/navigation.py) (1,334 行) 與 [`states/state_machine.py`](../../states/state_machine.py) (2,449 行) 規模龐大，需依 BDI 與業務職責進一步拆分。
- [ ] 不知道為何小號會卡在 breadcollection 導致30s watchdog(./todos/bread_collect_watchdogbug.md)

### .agent

- [ ] 🔴 **審核 `state_machine_development` skill 規範對齊**：
  - 檢視該技能是否與 [Greenfield-lite Architecture v1](../architecture/project_arch_greenfield_lite_v1.md) 的感知/決策分離、分層依賴與不變量一致，消除過時指示。

### Battle & Result

- [ ] 🔴 **戰鬥結算與通關閉環重構 ([`result_todo.md`](result_todo.md) / [RFC: 重構 Result 為 BattleResult](rfc_rename_result_to_battle_result.md))**：
  - **24/7 風險 (結算卡死與誤退場)**：`STATE_RESULT` 語意模糊且 `should_exit_battle` 複合條件過於複雜，容易在地下城通關、懸賞完成與常規戰鬥之間產生結算時機誤判。
  - **規劃方向**：將 `STATE_RESULT` 正名為專屬戰鬥結算的 `STATE_BATTLE_RESULT`，按「安全點搶佔、任務完成、資源退避、定時政策」分流維護退出條件。
- [ ] **強敵比對退出戰鬥位置與命名重構**：
  - 將目前偏向 domains 的強敵比對邏輯通用化，提升為全戰鬥通用能力。
- [ ] **戰鬥系統固定點擊探索**：
  - 利用已有的角色技能與站位數據，探索固定座標點擊出招，不需額外 CV 即能提升戰鬥效率。

### Exception
- [ ] 假設需要使用者介入 那應該暫停掛機 而非繼續 避免像是(game server 維護  我卻不斷嘗試登入 導致可能被鎖帳號的問題)

- [ ] 🔴 **長途運行 OpenCV 影像矩陣與 EasyOCR 快取生命週期監控**：
  - **24/7 風險 (記憶體耗盡崩潰)**：掛機數日後記憶體持續攀升，最終觸發 OOM 或系統卡頓。
  - **規劃方向**：使用 `tracemalloc` 排查 OpenCV `cv2.Mat`、EasyOCR 辨識快取與 Win32 HWND / DC 控制代碼之生命週期，確保無暫存物件殘留。
- [ ] **整合自癒升級階梯與看門狗滑動窗口**：
  - 持續完善階梯 1~7 自癒機制（彈窗清理 ➔ 重設戰鬥 ➔ 返回城鎮 ➔ 重開遊戲 ➔ 殺進程 ➔ 警報發送），確保各層級自癒均能如實回報進展並寫入 [`runtime/incident_journal.py`](../../runtime/incident_journal.py)。

### Town

- [ ] **背包維護加入可合成有價值材料之預先製作**：
  - **24/7 風險 (資源浪費)**：在觸發珠寶店賣東西前，若背包中有可合成的高階有價值材料，未先合成即直接被賣掉或分解，降低掛機效益。
  - **規劃方向**：在 `subflow_configs.bag_maintenance` 流程中，於整理與出售前加入合成子步驟。

### DEV

- [ ] 🔴 **測試執行效率優化與消除阻塞式 `while` 迴圈 ([`test_redundent.md`](test_redundent.md))**：
  - **24/7 與工程品質風險**：部分舊測試執行過慢（全套需 380s+），且部分輔助函式殘留 `while` 死等邏輯，不符合 BDI 單次 tick 與事件驅動架構。
  - **規劃方向**：重構慢速測試，將假等待改為 mock time / clock 注入，加速反饋閉環。
- [ ] 優化終端 `config.toml` 與執行參數呈現排版，提升操作員檢視直觀度。

### 多實例與沙盒環境 (Multi-Instance & Sandboxie)

- [ ] 🔴 **排查沙盒環境跨程序 IPC 與渲染幀率延遲**：
  - 分析 Win32 API 跨沙盒發送訊息 (`PostMessage` / `SendMessage`) 之焦點延遲。
  - 評估 `ScreenCapturer`（`mss` / `BitBlt`）在沙盒隔離視窗下的截圖幀率與開銷。
  - 測試多實例 CPU 競爭與進程優先級（Priority Boost）對沙盒實例的提速效果。

### 全域架構審查與技術債治理 (Technical Debt & Rule Auditing)

- [ ] 🔴 **核心巨型模組依責任邊界拆分**：
  - 依據 [`AGENTS.md`](../../.agents/AGENTS.md) 的「生產代碼 ~300 行審查觸發線、方法 ~60 行、巢狀 ~3 層、感知與決策分離」原則，排查出以下亟待重構的核心檔案：

| 檔案路徑 | 當前行數 (實測) | 規範限制 | 違反原則與架構隱患 |
| :--- | :---: | :---: | :--- |
| [`states/state_machine.py`](../../states/state_machine.py) | **2,449 行** | ~300 行觸發線 | **嚴重超標**。狀態機身兼狀態流轉、全域例外協調、各 Tier 子流程調度與看門狗接線，職責過度混雜。 |
| [`states/handlers/navigation.py`](../../states/handlers/navigation.py) | **1,334 行** | ~300 行觸發線 | **嚴重超標**。內部包含大量關卡滾動、島嶼點擊、頁籤切換等複雜巢狀分枝，需推進至 Scoped Navigation。 |
| [`utils/daily_manager.py`](../../utils/daily_manager.py) | **982 行** | ~300 行觸發線 | **超標**。同時管理 Date Tag 重置、Boss CD、懸賞持久化事實與未知任務正名，應依領域拆分。 |

### 產品化與變現方式 (Productization & Monetization)

- [ ] 評估未來是否封裝為獨立 `.exe`、GUI 介面或 Web 儀表板，降低無 Python 環境用戶的使用門檻。
- [ ] 現階段專注於 24/7 掛機穩定性與核心邏輯完善；後續評估 PyInstaller / Nuitka 打包或 Electron / Tauri 介面封裝。

---

## ⏸️ 二、 暫時擱置與備用項目 (Shelved / Postponed)

> 💡 **說明**：以下項目經架構評估或已被現有更完善之機制覆蓋，暫時予以擱置，保留記錄以備未來參考。

### 1. 🔒 戰鬥結算稀有戰利品自動背包鎖定
- **原始構想**：在戰鬥結束結算畫面（`continue` 處）同時偵測到「獲得戰利品」時，前往背包進行特定裝備的鎖定防護。
- **擱置原因**：此功能目前已由**「背包 18 格 HSV 色彩分類與貴重品階反選保留機制」**完整覆蓋（藍/紫/橘/紅自動保留，灰/綠自動分解/銷毀），無需再額外進入背包點擊鎖定。

### 2. 📱 iPad 遠端操控 PC 腳本
- **原始構想**：使用 Windows PC 遠端控制 iPad 上的遊戲進行自動化。
- **擱置原因**：專案專注於 Steam PC 視窗端高解析度、高幀率與後台非搶占式掛機，目前無行動裝置跨端需求。

### 3. 🔄 城鎮點錯重來與容錯退回機制
- **原始構想**：手動或意外點錯建築時的全局重來。
- **擱置原因**：各城鎮 Handler 與子流程目前均已建立獨立的退場按鈕與 [`exitfromhouse_and_to_town.png`](../../templates/town_building/exitfromhouse_and_to_town.png) 安全退回城鎮路徑。

### 4. 🛡️ 地下城誤入非目標地圖防呆容錯
- **原始構想**：手動按錯或誤入非目標地下城地圖時，偵測並點擊退出按鈕安全返回大廳重開。
- **擱置原因**：目前的 `mix` 混合模式、自適應卡片定位與貪婪選關已能全自動接管選關流程，無人工誤點問題。

---

## ✅ 三、 已解決與完成項目 (Completed & Verified)

### 1. 🛡️ 看門狗與例外自癒子系統 (Exception Watchdog & Game Relaunch)
*(詳細架構分析與除錯筆記請參閱 [exception_subsystem_architecture.md](../architecture/exception_subsystem_architecture.md))*
- [已完成並驗證] **5 次重試失敗直接重開自癒**：在 [`UnexpectedPopupRecoveryHandler`](../../states/exceptions/handler.py) 中，當 5 次嘗試仍無法消除畫面障礙時，直接喚起 `GameRelaunchSubflow` 殺進程並重啟遊戲。
- [已完成並驗證] **狀態轉移防抖與時間戳保護**：在 [`GameStateMachine.transition_to`](../../states/state_machine.py) 增加 `if self.current_state != new_state` 狀態防抖，防止相同狀態重複刷新 `last_state_change` 導致 Watchdog 失效。
- [已完成並驗證] **長任務真實進度回報 (`notify_ui_progress`)**：背包清理、長途出售與翻頁時定時回報有效 UI 進度，徹底消除假陽性卡死。
- [已完成並驗證] **COLLECT_ONLY 待機動態 CD 逾時與視窗崩潰檢查**：支援動態 CD 逾時保護與 HWND 遺失自動重啟。
- [已完成並驗證] **導航狀態 Watchdog 90 秒寬鬆門檻**：將 `STATE_NAVIGATING` 放寬至 90 秒，排除選關卡卡片與翻頁導航誤判。
- [已完成並驗證] **全螢幕意外彈窗對接 (Watchdog & Popup Recovery)**：支援輪盤 (`WheelOfFortuneSubflow`)、掃蕩盒 (`RaidBoxSubflow`) 與全域關閉 (`GenericAntiStuckSubflow`) 雙層救援。

### 2. 🎮 多實例與長掛機支援 (Multi-Instance & Long-Running AFK)
- [已完成並驗證] **Sandboxie-Plus Steam 雙開掛機與多實例目標選擇**：支援自動掃描本機/沙盒視窗（`[#] Blackfire Crusade [#]`）、互動選單以及 `--target` 快速參數。(參見指南 [sandboxie_dual_instance_guide.md](../guides/sandboxie_dual_instance_guide.md) 與 PARS 故事 [sandboxie_dual_instance_pars_story.md](../storys/sandboxie_dual_instance_pars_story.md))。
- [已完成並驗證] **5 天長掛機 3 大架構支柱**：
  1. **狀態持久化 ([`DailyManager`](../../utils/daily_manager.py))**：所有完成子流程與 08:05 重置週期自動記錄於 [`daily_status.json`](../../user_data/native/daily_status.json)，斷線重啟無縫接續進度。
  2. **全局看門狗與自癒修復 ([`Watchdog`](../../states/exceptions/watchdog.py) & [`UnexpectedPopupRecoveryHandler`](../../states/exceptions/handler.py))**：逾時自動清除遮擋或重啟。
  3. **點擊消失驗證閉環 (`click_and_wait_until_gone`)**：關鍵按鈕點擊後持續輪詢確認消失，防止狀態過早推進。
- [已完成並驗證] **長時間運轉資源與記憶體無洩漏** (1,000 次循環僅微增 1.09MB)。
- [已完成並驗證] **CPU 低功耗睡眠控管** (參見指南 [cpu_optimization.md](../guides/cpu_optimization.md))。
- [已完成並驗證] **Mode-Agnostic 地下城斷線與遊戲重開自癒** (全模式辨識 [`dungeons/leave.png`](../../templates/dungeons/leave.png) 起點恢復探索)。

### 3. 🎯 視覺比對與座標適配 (Vision & Adaptive Coordinates)
- [已完成並驗證] **關卡選關優先按相似度而非亮度比例過濾**：解決選第 4 關誤點第 2 關周邊背景的 Bug。
- [已完成並驗證] **全域「任務完成」彈窗動態 Scale 適配**：領取按鈕依視窗高度比例動態縮放，解決非 1080p 解析度下點擊無效問題。
- [已完成並驗證] **領鑽石退出按鈕 Hover 焦點與消失確認**：後台點擊增加 `WM_MOUSEMOVE` 穩定焦點，持續比對 [`quit.png`](../../templates/common/quit.png) 消失後才轉移狀態。
- [已完成並驗證] **按鈕點擊消失驗證閉環 (`click_and_wait_until_gone`)**：防止過早推進狀態。
- [已完成並驗證] **地下城寶箱確認防黏住重試與消失閉環**：[`Get_tresure_comfirm.png`](../../templates/dungeons/Get_tresure_comfirm.png) 改為每 0.25 秒重新辨識，持續存在逾 0.75 秒自動重點，確認消失後方轉向退出按鈕，並受 10 秒子流程總上限保護。

### 4. ⚔️ 掛機模式與流水線調度 (Pipelines & Modes)
- [已完成並驗證] **地下城全冷卻瀑布流混合模式 (`mix`)**：副本全在冷卻中時自動切換至 Stage 刷關，CD 結束即時切回地下城。
- [已完成並驗證] **體力耗盡全域自動退避 (`collect_only`)**：彈出 [`no_bread.png`](../../templates/no_bread/no_bread.png) 時自動關閉彈窗，退回城鎮切換至待機模式 4.0 小時，結束後自動恢復原模式。
- [已完成並驗證] **單一權威來源 (SSOT) 與 Fail-Fast 配置**：所有模式配置由 [`config.py`](../../config.py) 驅動，參數缺失時立即拋出防禦性例外中斷。
- [已完成並驗證] **每日任務 08:05 四階梯流水線 (`DailyMasterPipeline`)**：
  - Tier 1: 城鎮速領 (寶箱 `chest` ➔ 抽卡 `hero_draw` ➔ 祭壇 `blood_altar` ➔ 珠寶 `jewelry_workshop`)。
  - Tier 2: 領主 Boss 討伐 (`lord_boss` 蜘蛛/惡靈計時器搶佔)。
  - Tier 3: 懸賞告示牌與動態任務 (`bulletin_board`)。
  - Tier 4: 動態退守刷關。
- [已完成並驗證] **背包已滿 18 格標題中心錨定與 2 格 (279px) 精準像素 Drag 位移銷毀**。
- [已完成並驗證] **地下城索引全面統一為 1-based (消除 0-indexed 歷史包袱)**：
  - 徹底將地下城編號由 `0..5` 統一為 `1..6`，全面對齊關卡 `1..6`。
  - 消除所有 `+ 1` / `- 1` 混亂轉換與認知衝突；更新 [`defaults.toml`](../../defaults.toml) (`max_dungeon = 6`、`greedy_allowed_indices = [1..6]`、`cooldown_map` 鍵值 `1..6`)。
  - 同步重構 [`config/quest_rules.json`](../../config/quest_rules.json)、[`utils/quest_mapper.py`](../../utils/quest_mapper.py)、[`utils/quest_scheduler.py`](../../utils/quest_scheduler.py)、[`cli/dungeon_setup.py`](../../cli/dungeon_setup.py)、[`states/state_machine.py`](../../states/state_machine.py)、[`states/handlers/navigation.py`](../../states/handlers/navigation.py)。
  - 11 個單元測試套件已 100% 綠燈通過驗證。
- [已完成並驗證] **地下城重啟下樓自癒與通關離場路由 (`fix_dungeon_go_town`)**：
  - 徹底修復地下城通關後迷航與下樓自癒路由，已升格為長效契約 [`dungeon_relaunch_recovery_contract.md`](../features/navigation/dungeon_relaunch_recovery_contract.md)。
- [已完成並驗證] **懸賞任務依最高關卡上限動態過濾 (Quest Level Filter)**：
  - 由 [`utils/quest_mapper.py:filter_unreachable_quests`](../../utils/quest_mapper.py#L243) 與 [`defaults.toml`](../../defaults.toml) 的 `max_stage` / `max_dungeon` 實現，接取懸賞後自動排除超過戰力上限之地圖。

### 5. 🛡️ 戰鬥血條靜止卡死自癒 (Battle Stall Recovery)
- [已完成並驗證] **設定 ➔ 重新開始戰鬥原地自癒機制**：
  - 依據架構契約 [`battle_stall_recovery_contract.md`](../architecture/battle_stall_recovery_contract.md)，由 [`BattleSession`](../../states/battle_session.py) 追蹤敵我血條特徵向量變化。
  - 若連續 30 秒血條完全無進展判定為戰鬥死鎖，由 [`BattleHandler`](../../states/handlers/battle.py) 觸發「設定 ➔ 重新開始戰鬥」子流程原地自癒，無需重啟遊戲。
  - 包含上限 2 次原地重試保護；超過 2 次自動升級殺進程重開，並寫入 incident journal。

### 6. 🔄 長期掛機定期安全重啟與進程管理 (Supervisor S1~S7 Restart Matrix)
- [已完成並驗證] **Supervisor 生命週期自癒與 S1~S7 遊戲重啟矩陣**：
  - S1 (每日 08:00 定時維護) 與 S2 (心跳逾時 >180s)：強制終止子進程後注入單次消費之 `--restart-game` 旗標，清除舊遊戲進程並透過 Steam 直連重開登入。
  - S3 (遊戲未回應視窗偵測)：調用 `IsHungAppWindow(hwnd)` 自動升級強制重開。
  - S4 (執行期卡死)：Watchdog 觸發重構後的 `GameRelaunchSubflow`。
  - S5 (Python 例外崩潰) 與 S6 (Ctrl+C)：快速秒級 Attach，無損接續進度。
  - S7 (手動退出 `Ctrl+Shift+Q`)：優雅退出 Supervisor 且不重啟遊戲。
  - 詳見架構規範 [`supervisor_lifecycle_contract.md`](../architecture/supervisor_lifecycle_contract.md)、PARS 故事 [`supervisor_lifecycle_game_restart_matrix_story.md`](../storys/supervisor_lifecycle_game_restart_matrix_story.md) 與單元測試 [`tests/test_behavior_supervisor_lifecycle.py`](../../tests/test_behavior_supervisor_lifecycle.py)。

### 7. 📜 執行期事件日誌持久化 (Runtime Incident Journaling)
- [已完成並驗證] **Profile 隔離的結構化異常事件持久化**：
  - 於 [`runtime/incident_journal.py`](../../runtime/incident_journal.py) 實作 CRASH、HEARTBEAT_TIMEOUT、SCHEDULED_MAINTENANCE、IN_GAME_RECOVERY 四大類別事件記錄。
  - 自動脫敏敏感資訊（token、password 等），保證寫入 `user_data/<profile>/runtime/incidents/<date>.jsonl` 與 `latest_child_termination.json`。
  - 詳見架構規格 [`runtime_incident_recording_spec.md`](../architecture/runtime_incident_recording_spec.md) 與單元測試 [`tests/test_incident_journal.py`](../../tests/test_incident_journal.py)。
