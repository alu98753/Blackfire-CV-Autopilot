我發現 經過現在的改動,dungeon 在看到entry 如(E:\Side_Project\BlackfireCrusade_tool\templates\dungeons\Ice_entry.png) 在冷卻時 仍會 點擊进入 (E:\Side_Project\BlackfireCrusade_tool\templates\dungeons\Ice_entry.png)
並且沒有退出機制(點quit),而導致他intent已經跑到別的目標而卡死, 我不確定他是在判斷到木牌前就點 還是判斷到了木牌 確定再冷卻  仍然點, 請檢查code邏輯, 並查詢 913 9:10-9:25 的log確認原因, 並把spec 寫在這個.md。不動程式

===

同時第二個bug出現在 9/13 中 9:25-28

我已經確定他畫面已經進入lobby中的地下城且已經 dungeon_after, 但她仍然重複點擊, 我記得我有寫假設after > dungeon就可以確定進入地下城 還是沒有寫這個邏輯? 我確定stage是有這個邏輯的, 請檢查code邏輯, 並查詢 913 9:25-28 的log確認原因, 並把spec 寫在這個.md。不動程式

0.9998，相對亮度比: 1.00，座標: (657, 911)
2026-09-13 09:28:07,391 [INFO] [IntentRouting] intent=primary_navigation scene=lobby action=continue_primary reason=primary_route_delegated progress=idle
2026-09-13 09:28:08,086 [INFO] 成功匹配模板 'dungeons/dungeon.png'！相似度: 0.9236，相對亮度比: 1.06，座標: (811, 911)
2026-09-13 09:28:08,089 [INFO] 🧭 尋路中：在畫面中找到 [dungeons/dungeon.png] (信心度: 0.9236)，點擊按鈕中心座標 (811, 934)。
2026-09-13 09:28:08,261 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png

---

# 權威診斷報告與技術規格說明書 (Canonical Root Cause & Specification)

經全面交叉比對 `user_data/native/logs/app.log` 與 `user_data/sandbox/logs/app.log` 於 2026-09-13 09:10 ~ 09:30 之運行日誌，對照 [NavigationHandler](../../states/handlers/navigation.py)、[SceneDetector](../../utils/scene_detector.py)、[navigation_routing](../../states/navigation_routing.py) 與 [tier4_config.py](../../utils/tier4_config.py)，將兩次異常之根本原因收斂為單一權威因果鏈，並訂定四階防護架構規格。

---

## 一、單一權威因果鏈 (Canonical Causal Chain)

```text
[Root Cause A: 上游配置不一致]
Tier 4 退守時強制將 type 改為 "stage"，但未替換 navigation_path (仍為 [..., Ice_entry.png])
       │
       ▼
[Root Cause B: FastPath 感知識盲]
expected_tab 被推導為 STAGE ➔ FastPath 僅比對 stage 模板 ➔ stage 為 inactive 時直接返回 None
丟失畫面實際上已處於 dungeon_after (地下城頁籤) 的正向證據，誤判 active_tabs = ∅
       │
       ▼
[Safety Gap C: 循序導航未設領域門禁]
dungeon_select_open 誤判為 False ➔ 跳過專屬卡片/木牌檢測 ➔ 跌入通用 navigation_path 逆序點擊
generic loop 無權限直接點擊具有 domain-specific precondition 的 entry 模板
       │
       ▼
[Recovery Gap D: 阻擋彈窗缺少上下文自癒]
點擊冷卻中地下城彈出提示彈窗 (帶有 common/quit.png)
NavigationHandler 頂部僅防護 confirm/ok 彈窗，缺少 quit 之上下文自癒，畫面變暗活鎖直至 Watchdog 逾時
```

---

## 二、四大異常環節詳細分析 (Root Cause & Gap Analysis)

### 1. Root Cause A：可執行配置不變量破壞 (Invalid Tier 4 Route Config)
- **代碼位置**：[utils/tier4_config.py:L26-L50](../../utils/tier4_config.py#L26-L50)
- **問題機制**：
  在 `build_tier4_fallback_config` 中，代碼先執行 `fallback = deepcopy(primary_config)`。當使用者設定或預設之 `tier4_mode != TIER4_MODE_DOMAIN` 時，代碼直接執行：
  ```python
  fallback["type"] = "stage"
  fallback["tier4_mode"] = TIER4_MODE_STAGE
  ```
  但**完全沒有將 `fallback["navigation_path"]` 置換為普通關卡的導航路徑**！
  若進入退守前的 `primary_config` 是地下城配置，退守後的 config 便破壞了不變量：
  ```text
  type = "stage"
  navigation_path = ["common/door.png", "dungeons/dungeon.png", "dungeons/Ice_entry.png"]
  ```
  這是在各層引發連鎖崩潰的最上游源頭。

### 2. Root Cause B：目標未選中誤判為全頁籤無效 (Target-Inactive Perception Blindspot)
- **代碼位置**：[utils/scene_detector.py:L480-L540](../../utils/scene_detector.py#L480-L540) 與 [states/navigation_routing.py:L92-L98](../../states/navigation_routing.py#L92-L98)
- **問題機制**：
  1. 因 `type == "stage"`（或因地下城冷卻中 `has_available_dungeon() == False`），`resolve_expected_tab_from_machine` 推導出 `expected_tab = TabId.STAGE`。
  2. `SceneDetector._detect_lobby_fast_path` 依據 `expected_tab` 僅比對 `select_stage_after.png` 與 `select_stage.png`，完全不比對其餘 4 個頁籤。
  3. 當畫面實際上已進入地下城頁籤時，`stage` 比對結果為 Inactive（`conf_inact >= 0.70`），FastPath 判定為 `target_inactive`，**直接返回 `None` 而未升級至全域掃描 `_resolve_full_relocalize`**。
  4. 破壞了核心感知不變量：`expected tab inactive ≠ no active tab`。FastPath 將「目標不是 active」誤等同於「畫面沒有任何 active tab」，使 `scene.active_tabs` 為空，丟失了畫面已在 `dungeon_after` 的事實。

### 3. Safety Gap C：通用導航越權分派領域入口 (Dungeon Entry Dispatched Without Ownership)
- **代碼位置**：[states/handlers/navigation.py:L789 & L1254-L1320](../../states/handlers/navigation.py#L789)
- **問題機制**：
  1. 因 `dungeon_select_open` 誤判為 `False`，專屬的地下城選關與木牌檢測流程（[navigation.py:L789](../../states/handlers/navigation.py#L789)）被完全跳過（在判斷木牌前就繞過了檢查）。
  2. 導航落入末端 `filtered_nav_path` 通用循序點擊迴圈。
  3. 通用迴圈缺乏對 domain entry 的前置檢查門禁，將 `Ice_entry.png` 或 `dark_prison.png` 當作普通按鈕直接點擊（[navigation.py:L1316](../../states/handlers/navigation.py#L1316)）。
  4. 違反了職責邊界：通用導航僅負責線性 UI 跳轉，無權分派具有領域前置依賴（冷卻、解鎖、可打性）的關卡入口。

### 4. Recovery Gap D：阻擋彈窗缺少上下文處置路徑 (Blocked-Entry Modal Recovery Gap)
- **代碼位置**：[states/handlers/navigation.py:L660](../../states/handlers/navigation.py#L660)
- **問題機制**：
  點擊冷卻中的地下城後，遊戲跳出提示彈窗，畫面中央變暗並在右上角呈現 `common/quit.png`（相似度 0.9887）。`NavigationHandler` 頂部的前置清理只處理 `confirm.png` 與 `ok.png`，無法關閉該提示彈窗，導致導航持續在遮罩下重複點擊同一目標，最終觸發 Watchdog 逾時。

---

## 三、四階架構改善規格提案 (Specs 0 ~ 3, 不動程式)

為從根本消除上述缺陷且杜絕補洞過頭與邏輯漂移，後續實作應遵循以下 4 條規格：

### Spec 0 — Route Config Coherence Invariant (最優先上游修復)
- **不變量契約**：
  可執行的路由配置中，`type`、`navigation_path` 與 `expected_tab` 必須維持強一致性：
  ```text
  type == "stage"   ➔ navigation_path 必須是 stage 專屬路徑 ➔ expected_tab == STAGE
  type == "dungeon" ➔ navigation_path 必須是 dungeon 專屬路徑 ➔ expected_tab == DUNGEON
  type == "domain"  ➔ navigation_path 必須是 domain 專屬路徑 ➔ expected_tab == DOMAIN
  ```
  **嚴禁出現 `type == "stage"` 卻攜帶地下城入口模板的混合狀態。**
- **實作落地**：
  在 [utils/tier4_config.py](../../utils/tier4_config.py) 的 `build_tier4_fallback_config` 中：
  當退守為 `TIER4_MODE_STAGE` 時，必須完整由 `mode_configs["stage"]` 覆寫 `navigation_path`、`stage_entry`、`stage_target` 與 `stage_templates`，徹底清除原本殘留的地下城 Entry 模板。

### Spec 1 — Perception Escalation on Target Inactive (感知升級)
- **不變量契約**：
  FastPath 僅能用於快速肯定目標（`target active`）；若 FastPath 判定目標為未選中（`target inactive`），且下游導航決策需要當前真實活躍頁籤（`active_tabs`），**禁止將 unknown 當成 inactive-all，必須主動升級至 `_resolve_full_relocalize` 全域掃描**。
- **實作落地**：
  在 [utils/scene_detector.py](../../utils/scene_detector.py) 的 `_detect_lobby_fast_path` 中：
  當目標頁籤經比對為 inactive 時，不再直接返回 `None`，而是升級調用 `_resolve_full_relocalize`，確定當前畫面上到底哪個頁籤處於 `_after` 激活態（如 `dungeon_after`），保證 `scene.active_tabs` 正確產出。

### Spec 2 — Dungeon Entry Dispatch Gate (領域分派門禁)
- **不變量契約**：
  Generic navigation fallback 不得直接 dispatch 具有領域前置條件（domain-specific precondition）的入口。**嚴禁在通用導航迴圈中複製貼上第二套 OCR 冷卻檢測**（防止邏輯漂移）。
- **實作落地**：
  在 [NavigationHandler](../../states/handlers/navigation.py) 的通用循序路徑中，若下一點擊目標屬於地下城 Entry 模板（`DungeonCatalog.resolve_index_from_nav_path` 命中）：
  **必須滿足三日前置條件方可分派點擊**：
  1. `current active tab == DUNGEON`（已身處地下城大廳頁籤）
  2. 記憶體冷卻未阻擋（`now >= dungeon_cooldowns[idx]`）
  3. 該關卡可打性已由 Canonical Dungeon Scanner（`_check_dungeon_status`）檢驗通過。
  若任一項未知或不滿足，**通用迴圈嚴禁發起點擊**，必須交回地下城專屬選關路徑（或原地等待/路由重設）。

### Spec 3 — Contextual Modal Recovery (上下文約束彈窗復原)
- **不變量契約**：
  **嚴禁將 `common/quit.png` 定義為全域無條件點擊**（防止搶走戰鬥結算、領地探索或其它合法業務流程的 quit 意圖）。
- **實作落地**：
  在 [NavigationHandler](../../states/handlers/navigation.py) 中，`common/quit.png` 的清理必須具備嚴格的上下文門禁（Contextual Gate）：
  ```python
  if (
      scene.scene_type in (SceneId.LOBBY, SceneId.DUNGEON_SELECT, SceneId.STAGE_SELECT)
      and has_modal_overlay_evidence(screen_img) # 畫面中心變暗或有阻塞模態框
      and pos_quit is not None
  ):
      dismiss_blocked_modal(pos_quit)
  ```
  僅在明確的大廳/選關阻塞遮罩情境下，才允許將 `common/quit` 作為彈窗復原路徑消費。


---

## 四、實測日誌現場證據附錄 (Appendix: Log Traces)

### 1. 缺陷一：幽暗監獄與冰雪洞窟冷卻點擊與彈窗現場
#### 現場 A (09:20:00 ~ 09:20:14, native/logs/app.log):
```text
2026-09-13 09:20:00,015 [INFO] ⏳ 貪婪地下城：設定 [幽暗監獄] (#5) 進入 25 分鐘冷卻期。
2026-09-13 09:20:00,016 [INFO] 🔄 [GameStateMachine] 已切換至使用者設定的 Tier 4 退守配置: 地下城 - 幽暗監獄 (關卡: default)
2026-09-13 09:20:03,432 [INFO] [IntentRouting] intent=primary_navigation scene=lobby action=continue_primary reason=primary_route_delegated progress=idle
2026-09-13 09:20:04,011 [INFO] 成功匹配模板 'dungeons/dark_prison.png'！相似度: 0.6841，相對亮度比: 1.15，座標: (1327, 344)
2026-09-13 09:20:04,013 [INFO] 🧭 尋路中：在畫面中找到 [dungeons/dark_prison.png] (信心度: 0.6841)，點擊按鈕中心座標 (1328, 1447)。
2026-09-13 09:20:07,587 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.8960，相對亮度比: 1.12，座標: (1049, 141)
2026-09-13 09:20:11,918 [INFO] 成功匹配模板 'dungeons/dark_prison.png'！相似度: 0.6091，相對亮度比: 1.05，座標: (1327, 344)
2026-09-13 09:20:11,919 [INFO] 🧭 尋路中：在畫面中找到 [dungeons/dark_prison.png] (信心度: 0.6091)，點擊按鈕中心座標 (1328, 1447)。
2026-09-13 09:20:14,216 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9887，相對亮度比: 1.01，座標: (1024, 164)
```

#### 現場 B (09:22:37 ~ 09:22:59, sandbox/logs/app.log):
```text
2026-09-13 09:22:37,945 [INFO] ⏳ 貪婪地下城：強敵撤退！設定 [冰雪洞窟] (#6) 進入 30 分鐘冷卻期。
2026-09-13 09:22:37,946 [INFO] 🔄 [GameStateMachine] 已切換至使用者設定的 Tier 4 退守配置: 地下城 - 冰雪洞窟 (關卡: default)
2026-09-13 09:22:48,913 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9220，相對亮度比: 0.93，座標: (664, 908)
2026-09-13 09:22:49,333 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.9998，相對亮度比: 1.00，座標: (657, 911)
2026-09-13 09:22:49,415 [INFO] [IntentRouting] intent=primary_navigation scene=lobby action=continue_primary reason=primary_route_delegated progress=idle
2026-09-13 09:22:49,834 [INFO] 成功匹配模板 'dungeons/Ice_entry.png'！相似度: 0.9020，相對亮度比: 1.02，座標: (1402, 430)
2026-09-13 09:22:49,835 [INFO] 🧭 尋路中：在畫面中找到 [dungeons/Ice_entry.png] (信心度: 0.9020)，點擊按鈕中心座標 (1402, 453)。
2026-09-13 09:22:51,807 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9730，相對亮度比: 0.70，座標: (81, 925)
2026-09-13 09:22:52,450 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.7785，相對亮度比: 1.22，座標: (1336, 163)
2026-09-13 09:22:59,307 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9768，相對亮度比: 1.00，座標: (1280, 215)
```

### 2. 缺陷二：地下城頁籤已選中卻每秒重複點擊地下城圖標 (09:28:05 ~ 09:28:41)
```text
2026-09-13 09:28:06,746 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9220，相對亮度比: 0.93，座標: (664, 908)
2026-09-13 09:28:07,269 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.9998，相對亮度比: 1.00，座標: (657, 911)
2026-09-13 09:28:07,391 [INFO] [IntentRouting] intent=primary_navigation scene=lobby action=continue_primary reason=primary_route_delegated progress=idle
2026-09-13 09:28:08,086 [INFO] 成功匹配模板 'dungeons/dungeon.png'！相似度: 0.9236，相對亮度比: 1.06，座標: (811, 911)
2026-09-13 09:28:08,089 [INFO] 🧭 尋路中：在畫面中找到 [dungeons/dungeon.png] (信心度: 0.9236)，點擊按鈕中心座標 (811, 934)。
...
2026-09-13 09:28:10,092 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9811，相對亮度比: 0.99，座標: (531, 712)
2026-09-13 09:28:10,584 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.8558，相對亮度比: 1.06，座標: (526, 715)
2026-09-13 09:28:10,667 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=action_timeout_retry progress=timed_out in_flight=enter_lobby expected=lobby age=8.1s deadline=54029.593 attempt=4
2026-09-13 09:28:11,469 [INFO] 成功匹配模板 'dungeons/dungeon.png'！相似度: 0.9805，相對亮度比: 1.00，座標: (648, 715)
2026-09-13 09:28:11,472 [INFO] 🧭 尋路中：在畫面中找到 [dungeons/dungeon.png] (信心度: 0.9805)，點擊按鈕中心座標 (649, 1818)。
...
2026-09-13 09:28:15,087 [INFO] [IntentRouting] intent=primary_navigation scene=lobby action=continue_primary reason=primary_route_delegated progress=idle
2026-09-13 09:28:15,815 [INFO] 成功匹配模板 'dungeons/dungeon.png'！相似度: 0.9281，相對亮度比: 1.05，座標: (648, 715)
2026-09-13 09:28:15,818 [INFO] 🧭 尋路中：在畫面中找到 [dungeons/dungeon.png] (信心度: 0.9281)，點擊按鈕中心座標 (649, 1818)。
```