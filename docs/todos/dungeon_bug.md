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

# 診斷報告與技術規格說明書 (Root Cause & Specification)

依據 `user_data/native/logs/app.log` 2026-09-13 09:10 ~ 09:29 之實測日誌，對照 [NavigationHandler](../../states/handlers/navigation.py)、[SceneDetector](../../utils/scene_detector.py) 與 [navigation_routing](../../states/navigation_routing.py) 的執行邏輯，調查結果與規格收斂如下。

---

## 缺陷一：地下城冷卻中仍點擊 Entry，且彈窗無 Quit 機制卡死 (09:10 ~ 09:25)

### 1. 現場日誌還原 (Log Evidence)
於 09:20:00 地下城通關並設定冷卻後，系統切換至 Tier 4 地下城退守配置：
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

### 2. 程式碼邏輯與根因分析 (Root Cause)
1. **「判斷到木牌前就點」還是「確定冷卻仍點」？**
   - **結論：在判斷到木牌前就點擊，木牌檢測根本沒有被執行。**
2. **調用鏈追蹤**：
   - 專案中木牌檢測函式為 `detect_cooldown_sign_and_time`，封裝在 [NavigationHandler._check_dungeon_status](../../states/handlers/navigation.py#L573)。
   - 此檢查的唯一入口在 `if should_scan_dungeons:` 區塊（[navigation.py:L789](../../states/handlers/navigation.py#L789)）：
     ```python
     should_scan_dungeons = wants_dungeon_scan and dungeon_select_open
     ```
   - 當時 `scene.scene_type` 為 `SceneId.LOBBY`，`dungeon_select_open` 為 `False`，導致 `should_scan_dungeons` 為 `False`，完整跳過了地下城選關與木牌檢測流程。
   - 代碼隨後直接貫穿至最末端的通用循序導航（[navigation.py:L1254](../../states/handlers/navigation.py#L1254)）：
     ```python
     for btn in reversed(filtered_nav_path):
         pos, conf = match_current_frame(btn, threshold=thresh, ...)
         if pos:
             self.mouse.click(click_x, click_y)
             break
     ```
   - 在 `filtered_nav_path` 的逆序匹配中，模板 `dungeons/dark_prison.png`（或 `Ice_entry.png`）被直接以裸模板比對（閾值 0.60）命中，未做任何冷卻防護即觸發點擊。
3. **無退出機制（Quit）導致卡死**：
   - 點擊冷卻中的地下城入口後，遊戲彈出「冷卻中無法進入」之提示彈窗，右上角帶有退出按鈕 `common/quit.png`（相似度高達 0.9887）。
   - `NavigationHandler` 在大廳導航主迴圈中只處理了 `common/confirm.png` 與 `common/ok.png`（[navigation.py:L660](../../states/handlers/navigation.py#L660)），未將 `common/quit.png` 納入大廳通用遮擋彈窗清理清單。
   - 背景因彈窗變暗，但半透明遮罩下的入口按鈕仍能匹配出約 0.6091 相似度，導航持續重複點擊入口，直到 90 秒 Watchdog 逾時強殺遊戲。

---

## 缺陷二：地下城頁籤已是 dungeon_after 卻持續重複點擊 dungeon.png (09:25 ~ 09:28)

### 1. 現場日誌還原 (Log Evidence)
```text
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

### 2. 程式碼邏輯與「after > dungeon」合約查核
1. **「假設 after > dungeon 就可以確定進入地下城」是否存在？**
   - **程式碼中存在此邏輯**：定義於 [LOBBY_TAB_DEFINITIONS](../../utils/scene_types.py#L70)（`active_template="dungeons/dungeon_after.png"`, `inactive_template="dungeons/dungeon.png"`），由 [SceneDetector._evaluate_tab_active](../../utils/scene_detector.py#L569) 執行置信度差值比對（`diff = conf_act - conf_inact`，差值 $\ge 0.025$ 判定為 Active）。
2. **為何 09:28 完全沒有觸發比對？（根因）**
   - **根因 A：`resolve_expected_tab_from_machine` 意圖推導偏離**
     - 查核 [states/navigation_routing.py:L92-L98](../../states/navigation_routing.py#L92-L98)：
       ```python
       if config_type in {"mix", "daily"}:
           has_dg = machine.has_available_dungeon()
           return TabId.DUNGEON if has_dg else TabId.STAGE
       ```
     - 由於地下城已進入冷卻，`has_available_dungeon()` 為 `False`，意圖解析器將 `expected_tab` 推導為 **`TabId.STAGE`**。
   - **根因 B：`LobbyTabFastPath` 捷徑比對導致的感知識盲 (Perception Blindspot)**
     - 查核 [utils/scene_detector.py:L480-L540](../../utils/scene_detector.py#L480-L540)：
       當 `expected_tab` 為 `stage` 時，FastPath 為了節省運算，**僅比對 stage 的一對模板**（`select_stage_after.png` 與 `select_stage.png`），完全不比對 `dungeon` 頁籤模板。
     - 當畫面實際停留在地下城頁籤時，`stage` 模板比對結果為 Inactive（`conf_inact >= 0.70`），FastPath 判定為 `target_inactive`，**直接返回 `None` 而沒有 fallback 升級至全域掃描 `_resolve_full_relocalize`**。
   - **根因 C：過濾器未剔除按鈕，落入重複點擊循環**
     - 因感知識盲，`scene.active_tabs` 為空，`dungeon_select_open` 為 `False`。
     - [filter_navigation_path](../../states/handlers/navigation.py#L32) 無法將 `dungeons/dungeon.png` 自路徑中剃除。
     - 導航逆序掃描在畫面上找到未選中的暗態或鄰近特徵 `dungeons/dungeon.png`（相似度 0.9281），認定尚未切入頁籤，造成每秒重複發起點擊。

---

## 改善規格提案 (Technical Specification, 不動程式)

為徹底修復上述兩項問題，後續實作應遵循下列架構規格：

### Spec 1: LobbyTabFastPath 失效時強制 Full Relocalize
- **契約規範**：當 `LobbyTabFastPath` 針對 `expected_tab` 比對結果為非選中態（`target_inactive` 或兩者皆未達標）時，**不得直接返回 None/LOBBY**。
- **降級機制**：必須自動升級至 `_resolve_full_relocalize` 掃描其餘 4 大頁籤（含 `dungeon`、`lord`、`domain`、`demon_lord`），確認畫面目前到底停留在哪個頁籤上，確保 `scene.active_tabs` 真實反映現狀。

### Spec 2: 導航路徑中 Entry 級按鈕的前置冷卻防護 (Entry Click Gate)
- **契約規範**：在 [NavigationHandler](../../states/handlers/navigation.py) 的 `filtered_nav_path` 通用循序點擊迴圈中，凡點擊屬於各地下城 Entry 模板（如 `Ice_entry.png`, `dark_prison.png`）或透過命名解析出對應地下城索引時：
  1. **記憶體冷卻攔截**：若 `dungeon_cooldowns[target_idx] > now`，禁止點擊，直接發起退避或切換至替代路線。
  2. **木牌檢測門禁**：若未在冷卻名單但畫面上可見，必須先對卡片 ROI 執行 `detect_cooldown_sign_and_time`，確認無木牌方可發起點擊；若檢測到木牌，立即登記冷卻並退避。

### Spec 3: 大廳前置通用彈窗清理涵蓋 common/quit.png
- **契約規範**：在 [NavigationHandler.handle](../../states/handlers/navigation.py#L660) 頂部的前置彈窗清理清單中，將 `common/quit.png`（閾值 0.85）納入遮擋清理項目。當冷卻彈窗或意外說明彈窗彈出時，優先點擊關閉退出，避免畫面持續被模態遮罩覆蓋致使導航活鎖。


===

# 地下城尋路與頁籤消歧 Bug 調查報告與修復規格 (Technical Specification)

## 1. 調查結論概要 (Executive Summary)

經核對 `user_data/sandbox/logs/app.log` 於 2026-09-13 09:10 ~ 09:30 之詳細運行日誌與代碼執行鏈，兩個問題的根本原因與提問解答如下：

### Bug 1 解答：
- **是在判斷到木牌前就點，還是判斷到木牌確認冷卻後仍然點？**
  - **結論**：**在判斷木牌前就直接盲目點擊了**。冷卻木牌檢查函式 `detect_cooldown_sign_and_time` 在該當下**完全沒有被呼叫**。
  - **原因鏈**：
    1. 09:22:34 遇強敵 Calvia 撤退後，系統執行 Tier 4 退守 `apply_tier4_fallback_config()`。
    2. [`utils/tier4_config.py`](../../utils/tier4_config.py) 中因使用者設定未給定 `tier4_mode`，硬性將配置覆寫為 `fallback["type"] = "stage"`，但保留了原地下城導航路徑 `navigation_path = [..., "dungeons/Ice_entry.png"]`。
    3. `resolve_detection_request` 依據 `type == "stage"` 向 `SceneDetector` 請求了關卡頁籤的快速感知 (`expected_tab = TabId.STAGE`)。
    4. 大廳此時處於地下城頁籤，`select_stage_after` 未能勝出，快速感知回傳無活躍頁籤 (`active_tabs = []`)，地下城頁籤判定 `dungeon_select_open = False`。
    5. [`states/handlers/navigation.py`](../../states/handlers/navigation.py) 的地下城卡片掃描守衛條件 `should_scan_dungeons = wants_dungeon_scan and dungeon_select_open` 判定為 `False`，**導致專門檢查冷卻木牌的卡片掃描邏輯（第 808~1039 行）被完全旁路**。
    6. 代碼一路向下掉入末端的通用反向路徑點擊（第 1264 行），直接匹配到了畫面上的 `dungeons/Ice_entry.png` (相似度 0.9020)，在毫無木牌與冷卻檢查的情況下發起點擊。
    7. 點擊進入冷卻彈窗後，畫面變暗並出現右上角關閉按鈕 `common/quit.png` (0.9768)，但 `NavigationHandler` 的彈窗防護（第 660 行）只監控 `confirm.png` 與 `ok.png`，缺少 `quit.png` 處理，導致系統卡在彈窗內部。

### Bug 2 解答：
- **是否有寫 `after > dungeon` 邏輯？為什麼沒有生效？**
  - **結論**：**程式碼中確實有寫 `after > dungeon` 邏輯**，且地下城與普通關卡完全共用同一套差值判定核心。但在此場景下，**該邏輯根本沒有被執行到（未比對 `dungeon_after`）**。
  - **原因鏈**：
    1. 承 Bug 1，運行配置的 `type` 被竄改為 `"stage"`。
    2. 狀態機在向 `SceneDetector` 發起偵測時，最小感知請求限制為 `expected_tab = TabId.STAGE`。
    3. `SceneDetector._resolve_expected_lobby_tab()` 僅針對 `common/select_stage_after.png` 與 `common/select_stage.png` 進行比對。
    4. 現場畫面上 `select_stage.png` (未選中態) 匹配度達 0.9998 >= 0.70，觸發了 Fast-Path 規則「未選中態已確認（Inactive Confirmed）」，Fast-Path 判定目前不在普通關卡頁籤且無需升級重定位，直接回傳 `winner=None`。
    5. **因此 `SceneDetector` 完全沒有去讀取 `dungeons/dungeon_after.png` 與 `dungeons/dungeon.png`**，差值比較根本沒有發生。
    6. `scene.active_tabs` 呈現為空清單 `[]`，導航路徑中的 `dungeons/dungeon.png` 未被 `filter_navigation_path` 排除。
    7. 尋路系統在末端匹配 `dungeons/dungeon.png`，即使處於選中態，未選中模板依然具備 0.9236 的高相似度，系統誤認地下城頁籤尚未開啟，遂反覆點擊 (811, 934)。

---

## 2. 詳細日誌調查證據 (Log Evidence)

### 2.1 Bug 1 日誌現場 (09:22:34 ~ 09:22:59)

檔案來源：`user_data/sandbox/logs/app.log`

```text
2026-09-13 09:22:34,382 [INFO] 🔍 [領域強敵比對 第 1/3 次] 畫面相似度 (門檻 0.75) ➔ ice_boss_calvia_body: 0.7585
2026-09-13 09:22:34,383 [WARNING] 🚨 [領域強敵撤退] 偵測到領域強敵特徵 [dungeons/exception/ice_boss_calvia_body.png] (相似度: 0.7585 >= 0.75)，立即執行放棄戰鬥流程！
...
2026-09-13 09:22:37,945 [INFO] ⏳ 貪婪地下城：強敵撤退！設定 [冰雪洞窟] (#6) 進入 30 分鐘冷卻期。
2026-09-13 09:22:37,945 [INFO] 👉 [地下城強敵撤退] 遇強敵已主動放棄戰鬥，不計入單場戰敗次數，切換至 NAVIGATING 重新調度。
2026-09-13 09:22:37,945 [INFO] 🔄 狀態轉移: BATTLE -> NAVIGATING
2026-09-13 09:22:37,946 [INFO] 🔄 [GameStateMachine] 已切換至使用者設定的 Tier 4 退守配置: 地下城 - 冰雪洞窟 (關卡: default)
...
2026-09-13 09:22:48,913 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9220，相對亮度比: 0.93，座標: (664, 908)
2026-09-13 09:22:49,333 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.9998，相對亮度比: 1.00，座標: (657, 911)
2026-09-13 09:22:49,415 [INFO] [IntentRouting] intent=primary_navigation scene=lobby action=continue_primary reason=primary_route_delegated progress=idle
2026-09-13 09:22:49,834 [INFO] 成功匹配模板 'dungeons/Ice_entry.png'！相似度: 0.9020，相對亮度比: 1.02，座標: (1402, 430)
2026-09-13 09:22:49,835 [INFO] 🧭 尋路中：在畫面中找到 [dungeons/Ice_entry.png] (信心度: 0.9020)，點擊按鈕中心座標 (1402, 453)。
...
2026-09-13 09:22:51,807 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9730，相對亮度比: 0.70，座標: (81, 925)
2026-09-13 09:22:52,450 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.7785，相對亮度比: 1.22，座標: (1336, 163)
2026-09-13 09:22:56,765 [INFO] 成功匹配模板 'dungeons/Ruins_entry.png'！相似度: 0.9593，相對亮度比: 0.64，座標: (382, 428)
2026-09-13 09:22:59,307 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9768，相對亮度比: 1.00，座標: (1280, 215)
```

**關鍵事實**：
1. 09:22:37 記憶體中已清楚記錄冰雪洞窟冷卻 30 分鐘 (`dungeon_cooldowns[6] = now + 1800`)。
2. 09:22:49 比對到了 `dungeons/Ice_entry.png`，此時完全沒有輸出任何 `[CooldownDetector]` 的日誌（對比 09:18:08 與 09:20:41 時均有印出 `ℹ️ [CooldownDetector] 木牌模板最高匹配分數...`），直接在 09:22:49,835 點擊按鈕中心 (1402, 453)。
3. 點擊後畫面亮度比從 1.00 驟降至 0.64 ~ 0.70，且畫面出現 `common/quit.png` (相似度 0.9768，座標 1280, 215)。這是冷卻詳情遮罩彈窗。

---

### 2.2 Bug 2 日誌現場 (09:28:05 ~ 09:28:08)

檔案來源：`user_data/sandbox/logs/app.log`

```text
2026-09-13 09:28:05,201 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9999，相對亮度比: 1.00，座標: (81, 925)
2026-09-13 09:28:05,615 [INFO] 成功匹配模板 'common/bread.png'！相似度: 1.0000，相對亮度比: 1.00，座標: (1387, 67)
2026-09-13 09:28:06,746 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9220，相對亮度比: 0.93，座標: (664, 908)
2026-09-13 09:28:07,269 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.9998，相對亮度比: 1.00，座標: (657, 911)
2026-09-13 09:28:07,391 [INFO] [IntentRouting] intent=primary_navigation scene=lobby action=continue_primary reason=primary_route_delegated progress=idle
2026-09-13 09:28:08,086 [INFO] 成功匹配模板 'dungeons/dungeon.png'！相似度: 0.9236，相對亮度比: 1.06，座標: (811, 911)
2026-09-13 09:28:08,089 [INFO] 🧭 尋路中：在畫面中找到 [dungeons/dungeon.png] (信心度: 0.9236)，點擊按鈕中心座標 (811, 934)。
2026-09-13 09:28:08,261 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
```

**關鍵事實**：
1. 09:28:06~07 場景偵測時，比對了 `select_stage_after.png` (0.9220) 與 `select_stage.png` (0.9998)。
2. `dungeons/dungeon_after.png` 完全沒有出現在場景辨識日誌中。
3. `[IntentRouting]` 報告 `scene=lobby`，說明沒有任何頁籤被判定為 Active。
4. 09:28:08,086 尋路逆序掃描命中 `dungeons/dungeon.png` (0.9236)，發起點擊 (811, 934)。該現象在 09:26:54 ~ 09:28:08 間每隔約 5 秒重複一次。

---

## 3. 程式邏輯深度剖析 (Deep Logic Analysis)

### 3.1 為什麼 `after > dungeon` 邏輯存在卻失效？

在 [`utils/scene_types.py`](../../utils/scene_types.py) 中，大廳分頁規格定義如下：
```python
LobbyTabDefinition(
    name="dungeon",
    active_template="dungeons/dungeon_after.png",
    inactive_template="dungeons/dungeon.png",
    scene_type=SceneId.DUNGEON_SELECT,
)
```
在 [`utils/scene_detector.py`](../../utils/scene_detector.py) 的 `_evaluate_tab_active` 中：
```python
diff = conf_act - conf_inact
if diff >= LOBBY_TAB_CLEAR_MARGIN: # 0.025
    return True
if diff <= -LOBBY_TAB_CLEAR_MARGIN:
    return False
```
當 `dungeon_after` 與 `dungeon` 同時比對時，現場分數分別為 0.9768 與 0.9236，`diff = +0.0532 >= 0.025`，此邏輯能 100% 正確識別地下城頁籤已開啟。

**然而，在 9:25-28 的死循環中，這個方法根本沒被傳入 `dungeon` 模板**，原因在於：
1. 狀態機在 [`states/navigation_routing.py`](../../states/navigation_routing.py) 的 `resolve_detection_request`：
   ```python
   expected_tab = resolve_expected_tab_from_machine(machine)
   # 當 machine.config["type"] == "stage" 時，此處回傳 TabId.STAGE
   return SceneDetectionRequest(
       profile=profile,
       expected_tab=expected_tab,
       tab_scope=LobbyTabScope.EXPECTED_TAB,
       reason="navigation_steady",
   )
   ```
2. 在 `SceneDetector._resolve_expected_lobby_tab` 中：
   ```python
   # 2. Inactive confirmed or active not dominant
   if conf_inact >= LOBBY_TAB_THRESHOLD or pos_inact is not None or conf_act >= LOBBY_TAB_THRESHOLD:
       self._last_tab_was_full_relocalize = False
       return None, None, 0.0, False
   ```
   因為畫面在大廳，`select_stage.png`（未選中態）確實存在於畫面上且信心度高達 0.9998 >= 0.70，命中條件 2。
   函式直接回傳 `winner=None`，**沒有升級至全量重定位 (Full Relocalize)**。
3. 程式誤以為「既然目標頁籤 stage 是 inactive，就維持現狀」，完全不知道當前其實正停在 `dungeon` 頁籤上。

### 3.2 為什麼 `Ice_entry.png` 在冷卻時依然被點擊？

在 [`states/handlers/navigation.py`](../../states/handlers/navigation.py) 中：
1. 地下城選關卡片與木牌掃描（第 789 行）：
   ```python
   should_scan_dungeons = wants_dungeon_scan and dungeon_select_open
   ```
   因上述 Fast-Path 誤判，`scene.active_tabs` 為空，`dungeon_select_open` 為 `False`。
   `should_scan_dungeons` 變為 `False`！
2. 導致第 808~1039 行整段卡片掃描（包括記憶體冷卻檢查、滑動對齊、`detect_cooldown_sign_and_time` 木牌比對）**完全被跳過**。
3. 流程流向第 1264 行的通用導航路徑反向匹配：
   ```python
   filtered_nav_path = filter_navigation_path(nav_path, active_tabs, is_lobby=scene.is_lobby)
   for btn in reversed(filtered_nav_path):
       ...
       pos, conf = match_current_frame(btn, ...)
       if pos:
           self.mouse.click(click_x, click_y)
           break
   ```
   此處是盲目的模板反向掃描，完全沒有木牌檢驗邏輯。只要畫面上能看見 `Ice_entry.png`（無論是否有木牌、是否在記憶體冷卻中），就會直接點擊！

### 3.3 為什麼點進去後沒有退出機制 (點 quit)？

在 [`states/handlers/navigation.py`](../../states/handlers/navigation.py) 的 `handle` 開頭（第 660 行）：
```python
# 0. 全域最高優先防護：若畫面上出現歡迎/關閉彈窗 (common/confirm.png, common/ok.png)，優先點擊關閉以防止遮罩擋住導航與領取
for popup_btn in ["common/confirm.png", "common/ok.png"]:
    if os.path.exists(os.path.join("templates", popup_btn)):
        pos_popup, conf_popup = self.matcher.match(screen_img, popup_btn, threshold=0.90)
        if pos_popup:
            ...
```
- 防護名單中**只有 `confirm.png` 與 `ok.png`，沒有 `common/quit.png`**。
- `common/quit.png` 在 `NavigationHandler` 中僅出現在第 1239 行：
  ```python
  if "common/door.png" in nav_path and not stage_select_open and not dungeon_select_open and not in_detail_screen and not scene.is_lobby:
      pos_door, conf_door = self.matcher.match(...)
      if pos_door:
          pos_quit, _ = self.matcher.match(screen_img, "common/quit.png", threshold=0.75, quiet=True)
  ```
  該邏輯嚴格要求「人在城鎮、看到城門、且不在大廳」。當人已經在大廳或選關介面時，該分支完全不執行。
- 因此，當點擊冷卻中的地下城彈出帶有 `common/quit.png` 的冷卻提示覆蓋層時，系統完全無視該關閉按鈕，任由畫面被半透明黑色遮罩覆蓋，陷入死循環。

### 3.4 為什麼運行配置會突然被改成 `type = "stage"`？

在 [`utils/tier4_config.py`](../../utils/tier4_config.py) 中：
```python
def build_tier4_fallback_config(primary_config: dict, mode_configs: dict) -> dict:
    fallback = deepcopy(primary_config)
    tier4_mode = fallback.get("tier4_mode", TIER4_MODE_STAGE)
    if tier4_mode == TIER4_MODE_NONE:
        ...
        return fallback

    if tier4_mode != TIER4_MODE_DOMAIN:
        fallback["type"] = "stage"
        fallback["tier4_mode"] = TIER4_MODE_STAGE
        ...
        return fallback
```
使用者以 `--mode dungeon` 啟動時，`primary_config` 為純地下城模式，未設定 `tier4_mode`。
當戰鬥遇強敵撤退呼叫 `apply_tier4_fallback_config()` 時，因 `tier4_mode` 預設為 `TIER4_MODE_STAGE`，該函式無差別地將 `fallback["type"]` 強制改為 `"stage"`，形成了「`type` 是 stage，但 `navigation_path` 仍然是地下城路徑」的畸形配置。

---

## 4. 修復規格設計 (Fix Specification)

為徹底解決上述兩項 Bug，未來實作應遵循以下 4 點規格：

### Spec 1: 純地下城模式與 Tier 4 退守配置解耦 (Config SSOT)
- **影響模組**：[`utils/tier4_config.py`](../../utils/tier4_config.py) 與 [`states/state_machine.py`](../../states/state_machine.py)
- **規格要求**：
  1. `build_tier4_fallback_config` 必須尊重呼叫來源的原始意圖。當 `primary_config.get("type") == "dungeon"` 且非每日懸賞管線時，退守配置不得被篡改為 `stage`；應維持 `type = "dungeon"`，並由地下城自身的冷卻管理退避至 `COLLECT_ONLY` 或等待。
  2. 若為 `daily` 模式下退守，且使用者未啟用普通關卡，應遵循 `tier4_mode = "none"` 轉入 `collect_only`，嚴禁產生 `type="stage"` 但 `navigation_path` 為地下城模板的矛盾組合。

### Spec 2: SceneDetector 大廳快速感知升級重定位防線 (Fast-Path Upgrade)
- **影響模組**：[`utils/scene_detector.py`](../../utils/scene_detector.py)
- **規格要求**：
  1. 在 `_resolve_expected_lobby_tab` 中，當預期頁籤經比對為 Inactive（未選中），且畫面確認處於大廳結構（`scene_info.is_lobby == True`）時：
     - 若當前為導航調度或可能存在跨分頁操作，不能直接斷言無活躍頁籤並中止。
     - 應觸發 `FULL_RELOCALIZE`（或在候選分頁中進行快速掃描），確定當前真實選中的是哪一個分頁（例如判定出 `dungeon_after` 正在畫面上）。
  2. 確保 `scene_info.active_tabs` 能客觀反映畫面現況，而非受限於單一的 `expected_tab`。

### Spec 3: NavigationHandler 全域覆蓋層與彈窗防護補齊 `quit.png`
- **影響模組**：[`states/handlers/navigation.py`](../../states/handlers/navigation.py)
- **規格要求**：
  1. 在 `NavigationHandler.handle` 階段 0 的全域彈窗防護中，比對清單擴充支援 `common/quit.png`（或獨立之模態覆蓋層檢測）：
     - 若畫面上出現 `common/quit.png` 且伴隨背景變暗（或位於選關/大廳上層），優先點擊 `common/quit.png` 關閉彈窗以恢復底層視圖，禁止繼續執行尋路點擊。
  2. 點擊 `quit.png` 應包含後置驗證等待，確保彈窗徹底關閉後再進行下一幀辨識。

### Spec 4: 通用路徑逆序點擊門禁守衛 (Nav Path Fallback Guard)
- **影響模組**：[`states/handlers/navigation.py`](../../states/handlers/navigation.py)
- **規格要求**：
  1. 在 `for btn in reversed(filtered_nav_path):` 中，嚴禁直接點擊任何地下城 entry（如 `Ice_entry.png`, `dungeons/*_entry.png`）：
     - 凡屬於地下城 entry 之按鈕，必須強制進入冷卻驗證：
       - a. 若在記憶體冷卻中（`time.time() < dungeon_cooldowns[idx]`），禁止點擊！
       - b. 若在畫面可見範圍，必須先執行 `detect_cooldown_sign_and_time` 比對冷卻木牌。若有木牌，立即更新記憶體冷卻並跳過，嚴禁發射點擊！
  2. 當頁籤已為選中態（如 `dungeon_after` 存在），`filter_navigation_path` 必須百分之百保證剔除 `dungeons/dungeon.png`，杜絕任何重複點擊頁籤的行為。