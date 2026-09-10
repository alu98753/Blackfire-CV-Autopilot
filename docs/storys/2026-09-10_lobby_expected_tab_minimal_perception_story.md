# 開發故事：大廳兩階段最小感知架構與預期頁籤極速導航實踐 ⚡

> 日期：2026-09-10  
> 分支：`feat/lobby-expected-tab-minimal-perception`  
> 規範來源：nav_slow_bug2 (已升格收斂至下方成果契約)  
> 成果契約：[Lobby Scene Contract](../features/navigation/lobby_scene_contract.md)  
> 關鍵模組：[utils/scene_snapshot.py](../../utils/scene_snapshot.py), [utils/scene_detector.py](../../utils/scene_detector.py), [states/navigation_routing.py](../../states/navigation_routing.py)  

---

## 1. Purpose (目的)

在日常掛機與懸賞任務運行過程中，大廳導航（尤其是地下城卡片左右拖曳滑動與穩態頁籤核驗時）出現嚴重的卡頓與反應遲緩：
1. **全量掃描開銷巨大**：以往大廳每一次幀循環或卡片拖曳釋放後，`SceneDetector` 皆無條件對 5 大頁籤共 10 張模板進行全量比對，單次感知耗時長達近 4 秒，導致操作節奏被嚴重拖慢。
2. **缺乏感知上下文下傳**：導航決策層（Navigation Routing / Navigation Progress）已經掌握了明確的目標頁籤（例如懸賞地下城目標為 `TabId.DUNGEON`、主線目標為 `TabId.STAGE`），但底層視覺感知模組卻對此一無所知，每次都盲目重做「我是誰我在哪」的重定位。
3. **感知先驗假設偏差**：舊有 Profile 依賴（如 `profile=STAGE_SELECT`）會在 `SceneDetector.detect` 開頭無條件盲目預設 `scene_info.is_lobby = True`，且導航 Profile 未註冊城鎮特徵，導致從城鎮出發時城鎮特徵被忽略、誤判為 `LOBBY_OTHER`。

---

## 2. Action (行動)

1. **定義兩階段感知契約 (Two-Tier Perception Request)**：
   - 於 [utils/scene_snapshot.py](../../utils/scene_snapshot.py) 新增 `LobbyTabScope` (`FULL_RELOCALIZE`, `EXPECTED_TAB`) 與 `SceneDetectionRequest` dataclass。
   - 於 [utils/scene_types.py](../../utils/scene_types.py) 建立 `LOBBY_TAB_BY_NAME` 字典映射，實現 $O(1)$ 快速查找頁籤定義。
2. **決策層注入與 Context 傳遞 (Routing & InFlight Integration)**：
   - 在 [states/navigation_progress.py](../../states/navigation_progress.py) 的 `InFlightAction` 與 `begin()` 補入 `expected_tab` 記錄。
   - 在 [states/navigation_routing.py](../../states/navigation_routing.py) 實作 `resolve_expected_tab_from_machine()` 與 `resolve_detection_request()`，依據配置與進行中意圖動態對應 `TabId`，並透過 `_begin_action` 持久化至追蹤進度。
   - 在 [states/handlers/navigation.py](../../states/handlers/navigation.py) 將解析出的 `SceneDetectionRequest` 傳入 `detect()`。
3. **極速 Fast-Path 與有界全局升級 (Minimal Perception Engine)**：
   - 在 [utils/scene_detector.py](../../utils/scene_detector.py) 實作 `_resolve_expected_lobby_tab()`：
     - **Fast Path**：僅比對目標頁籤之一對 active/inactive 模板（比對次數 $\le 2$），以門檻 0.70 與差值 0.02 快速判定。
     - **Bounded Upgrade**：若兩者皆 miss，紀錄升級日誌並自動升級為 `_resolve_full_relocalize()`，重新評估全局 5 大頁籤與最大信心度仲裁。
   - 移除舊式相容備援（`match_mutually_exclusive_tabs` 舊路徑），生產流程全面以標準 `matcher.match` 執行。
4. **客觀畫面證據修正 (Objective Perception Fix)**：
   - 徹底移除 `SceneDetector.detect` 開頭盲目預設 `scene_info.is_lobby = True` 的假設。
   - 在 [utils/detector_registry.py](../../utils/detector_registry.py) 的導航各 profile（STAGE_SELECT, DUNGEON_SELECT, DOMAIN_SELECT, LORD_SELECT, DEMON_LORD_SELECT）中補入 `DetectorGroup.TOWN`，確保在城鎮畫面執行導航時能正確識別 `SceneType.TOWN`。

---

## 3. Result (結果)

- **感知效率巨幅提升**：
  - 在目標明確的大廳平穩導航與滑動卡片期間，頁籤比對次數從 10 降至 2，模板掃描開銷下降 80%，每次滑動檢查耗時縮減至數十毫秒。
- **無縫向下相容與自我修復**：
  - 目標 miss 時 100% 安全觸發 `_resolve_full_relocalize`，不遺失任何場景狀態或產生死鎖。
- **聚焦單元測試 100% 全數通過**：
  - `tests.test_entity_lobby_panel`: 9 個測試全部通過（含 5 大頁籤 Fast Path 隔離驗證、Inactive 判定與 Miss 升級測試）。
  - `tests.test_behavior_navigation`: 28 個測試全部通過（含地下城快速導航路徑與目標 inactive 頁籤切換驗證）。
  - `tests.test_scene_detector`: 13 個測試全部通過（含期望頁籤隔離性與最大信心度仲裁測試）。
  - `tests.test_behavior_navigation_progress`: 12 個測試全部通過。
  - 4 套共 62 個領域單元測試全數綠燈。

---

## 4. So What (核心價值)

1. **落實「最小必要感知 (Minimal Necessary Perception)」**：
   - 拒絕每幀進行全局重定位，在維持最高防偽標準的前提下，依據決策上下文以最小代價獲取必要證據。
2. **落實「單向依賴與上層接線」**：
   - 底層 `SceneDetector` 純粹接收 `SceneDetectionRequest` 資料結構，不持有 `machine` 或上層 Handler 物件；上層 Routing 負責決策要看什麼，層次分明。
3. **消滅隱式假設，回歸物理證據**：
   - 徹底消滅「因為傳入 STAGE_SELECT 就認定是大廳」的幽靈預設立場，以畫面上真實錨點與模板命中為唯一事實。

---

## 5. Influence (後續影響)

- 大廳導航、懸賞任務地下城選關卡片拖曳與頁籤切換獲得極速流暢的反饋。
- 契約 [docs/features/navigation/lobby_scene_contract.md](../features/navigation/lobby_scene_contract.md) 升格記錄 Invariant 5，防範未來任何感知退化。
