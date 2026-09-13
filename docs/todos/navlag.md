# 尋路延遲排查與分析：從關卡選單至大廳開始點擊 (navlag.md)

## 1. 核心結論與時間分佈概述

從使用者提供的日誌觀察，流程從 **14:09:41 點擊關卡小關入口 (first_stage)** 到 **14:09:58 真正發射大廳開始按鈕 (stages/start.png) 點擊**，耗時達 **約 17.4 秒**（若從 14:09:27 點擊冰洞算起更長達 31 秒）。

經過全鏈路比對與程式碼追蹤，這段延遲主要是由以下四大原因疊加所造成：
1. **子關卡點擊後的跳轉動畫期，誤觸發 `LobbyTabUpgrade` 升級為 `FullRelocalize`**：在轉場黑屏/半透明階段，`select_stage_after.png` 尚未就緒或被遮蔽，導致 FastPath 判定 inactive，退避進入全量 5 大頁籤掃描，單次耗時高達 4.67 秒。
2. **重度重試與遮擋/暗區模板匹配循環**：`stages/level6_ice_cave.png` 於抽屜彈出或畫面轉場時反覆進行暗區過濾判定（每次耗時約 0.5~1.0 秒）。
3. **場景辨識未能在主迴圈前段優先短路 `stages/start.png`**：在 `SceneDetector.detect()` 中，必須先依序走完 `task_complete`、`dungeon_scene`、`result_scene`、`battle_scene`、`door`、`diamond`、`goback_town`、`bread`、`quit`，才抵達 `stages/start.png`；且在抵達之前若被認定為在大廳，還會被頁籤重定位邏輯拖累。
4. **狀態機切換與雙重確認循環**：`NAVIGATING -> LOBBY` 狀態轉移發生在 14:09:54，但在切換到 LOBBY 後，LobbyHandler 重新進行了 auto/features/popup 掃描以及完整的 SceneDetector 流程，直到 14:09:58 才真正發出第一次 mouse.click。

---

## 2. 關鍵日誌節點時間軸 (Timeline & Root Cause Tracing)

| 時間戳記 | 耗時 | 關鍵事件 | 瓶頸模組 / 原因分析 |
| :--- | :--- | :--- | :--- |
| **14:09:41,289** | 基準點 (0s) | 🧭 尋路中找到 `stages/first_stage.png` 並點擊 | 成功點擊子關卡 (first_stage)，遊戲 UI 開始播放淡入/切換至關卡大廳動畫。 |
| **14:09:43,283 ~ 14:09:43,921** | +2.6s | 成功匹配 `goback_town.png`、`bread.png`、`quit.png` | 畫面處於切換過渡期，大廳基礎元素剛浮現，但關卡選單尚未完全切入大廳態。 |
| **14:09:45,325 ~ 14:09:49,992** | **+6.7s** | ⚠️ `[LobbyTabUpgrade]` 升級 `FULL_RELOCALIZE` (耗時 4.67s) | **【致命瓶頸 1】** 預期頁籤 `stage` 匹配度不足 (`act=0.6803 < 0.70`)，觸發全量頁籤掃描，依序比對 dungeon、demon_lords 等頁籤，白白浪費 4.67 秒。 |
| **14:09:51,013 ~ 14:09:52,109** | +2.1s | 匹配到 `level4_desert_ruins` 與暗區過濾 `level6_ice_cave` | **【致命瓶頸 2】** 因上一動全量掃描耗時過長，畫面已轉變，NavigationHandler 仍嘗試比對路徑中的 level 小島與暗區過濾。 |
| **14:09:53,811 ~ 14:09:54,845** | +2.7s | 偵測到 `stages/start.png` (相似度 1.0000) | 關卡大廳開始按鈕終於被辨識出來，判定 `scene=lobby, action=start_primary`。 |
| **14:09:54,934** | +0.1s | 🔄 狀態轉移: `NAVIGATING -> LOBBY` | 觸發狀態機跳轉，此時**尚未發射點擊**，只是交出控制權給 LobbyHandler。 |
| **14:09:57,385 ~ 14:09:58,359** | **+3.4s** | LobbyHandler 重新感知：再次檢測 goback, bread, quit, start | **【致命瓶頸 3】** LobbyHandler 接手後重新進行了一整輪全域特徵掃描、SceneDetector 偵測與決策執行。 |
| **14:09:58,701** | +0.4s | 🎯 `Lobby start button [stages/start.png] detected; clicking.` | **真正觸發第一次滑鼠點擊** (距離 14:09:41 點擊 entry 已過 17.4 秒)。 |

---

## 3. 詳細技術瓶頸剖析 (Reviewer 技術架構分析)

### (1) 過度感知與未防震的 `FullRelocalize` 震盪
- **檔案**：`utils/scene_detector.py` L538-L545、L598-L644
- **現象**：
  在點擊 `first_stage.png` 之後，UI 正在進入準備戰鬥的大廳。此時底部的 `common/select_stage_after.png` 可能因為轉場動畫、彈窗遮罩或變暗，導致信心度只有 `0.6803`（未達 `LOBBY_TAB_THRESHOLD = 0.70`）。
- **問題**：
  系統立刻判定 `Expected tab 'stage' not active` 並升級為 `FullRelocalize`。在 `_resolve_full_relocalize` 中，對 5 大頁籤共 10 張模板全部進行比對與光環計算，外加互斥比對，單次辨識拉長到 **4.672 秒**。在此期間完全阻斷任何其他操作。

### (2) 導航路徑中殘留按鈕在轉場期的無效掃描
- **檔案**：`states/handlers/navigation.py` L1266-L1332
- **現象**：
  即使已經點了 `first_stage.png`，在下一幀中系統依然在 `nav_path` 中由後往前比對 `level6_ice_cave.png`、`level4_desert_ruins.png` 等，甚至對暗區按鈕進行 NMS 與亮度過濾比對，消耗 CPU 與截圖週期。

### (3) 狀態跳轉與動作發射未合一（狀態跳轉空轉週期）
- **檔案**：`states/navigation_routing.py` L266-L271 與 `states/handlers/lobby.py` L66-L80
- **現象**：
  在 `14:09:54,845`，NavigationHandler 已經偵測到 `stages/start.png` 信心度 1.0000。
  此時 `NavigationDecisionExecutor` 執行的動作是：
  ```python
  if decision.action == ActionId.START_PRIMARY:
      self.machine.transition_to(self.machine.STATE_LOBBY)
      return True
  ```
  這導致它**只切換了狀態**，沒有當場點擊開始！
  等到下一次主迴圈循環，由 `LobbyHandler` 接收時：
  1. `LobbyHandler` 先掃描 `common/auto.png`、`battle_features`（非戰鬥略過）
  2. 再掃描 `confirm.png`、`ok.png`（無彈窗略過）
  3. 調用 `self.scene_detector.detect()` 又跑了一次完整的場景與大廳偵測
  4. 經由 routing context 解析出 `START_PRIMARY`
  5. 最終在 `14:09:58,701` 才真的呼叫 `self.mouse.click()`。
  光是這段「辨識到可以點 ➔ 狀態切換 ➔ 下一輪重新辨識 ➔ 點擊」就浪費了 **3.8 秒**。

---

## 4. 具體改善建議 (Actionable Proposals)

1. **轉場期 FastPath Inactive 降頻或抑制作業 (Debounce / Suppress FullRelocalize)**：
   - 當剛執行過關卡/子關卡點擊（如 2 秒內），畫面已知處於跳轉過渡狀態。若 `expected_tab` 未命中，應先以 `wait` 或維持原 profile，而不應立刻盲目發起耗時 4.6 秒的 `FullRelocalize`。
2. **大廳開始按鈕偵測提速與點擊發射直接合一 (Direct Action Execution)**：
   - 當 NavigationHandler 在尋路尾段已經直接辨識到 `stages/start.png`（或配置的 `lobby_start_btn`）且信心度達到 0.95+ 時，應可直接發射點擊並同時轉移至 `LOBBY` / `LOADING`，省去切換狀態後由 LobbyHandler 重新全套感知的大量延遲。
3. **路徑清理 (Committed Path Pruning)**：
   - 一旦已點擊目標子關卡（`first_stage.png` / `boss_skull.png`），將該關卡標記為已提交（In-flight committed），過渡期間不再回頭比對小島入口（如 `level6_ice_cave.png`），避免背景暗區比對等無效運算。

---

## 5. 原始日誌留存 (Original Log Reference)

```log
2026-09-13 14:09:23,141 [INFO] 🔄 [GameStateMachine 動態調度] ⚔️ 執行關卡懸賞任務 [擊敗冰元素] (進度: 17/20) ➔ 即時自動切換至目標配置: 懸賞任務 - 冰凍峽谷 (first) (任務: 擊敗冰元素)
2026-09-13 14:09:24,814 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9999，相對亮度比: 1.00，座標: (81, 925)
2026-09-13 14:09:25,186 [INFO] 成功匹配模板 'common/bread.png'！相似度: 1.0000，相對亮度比: 1.00，座標: (1387, 67)
2026-09-13 14:09:26,329 [INFO] 成功匹配模板 'common/select_stage_after.png'！相似度: 0.9999，相對亮度比: 1.00，座標: (664, 908)
2026-09-13 14:09:26,824 [INFO] 成功匹配模板 'common/select_stage.png'！相似度: 0.9310，相對亮度比: 1.07，座標: (657, 911)
2026-09-13 14:09:26,908 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-13 14:09:27,463 [INFO] 成功匹配模板 'stages/level6_ice_cave.png'！相似度: 0.9880，相對亮度比: 0.99，座標: (1559, 475)
2026-09-13 14:09:27,958 [INFO] 成功匹配模板 'stages/level6_ice_cave.png'！相似度: 0.9880，相對亮度比: 0.99，座標: (1559, 475)
2026-09-13 14:09:27,958 [INFO] 🧭 尋路中：在畫面中找到關卡小島按鈕 [stages/level6_ice_cave.png] (信心度: 0.9880)，套用向上偏移 149 像素點擊島嶼本體。
2026-09-13 14:09:28,112 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-13 14:09:28,120 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-13 14:09:29,861 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9730，相對亮度比: 0.70，座標: (81, 925)
2026-09-13 14:09:30,225 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9887，相對亮度比: 0.39，座標: (1387, 67)
2026-09-13 14:09:30,486 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9304，相對亮度比: 1.07，座標: (1300, 125)
2026-09-13 14:09:31,184 [INFO] [LobbyTabUpgrade] Expected tab 'stage' not active (act=0.3669, inact=0.4199, elapsed=0.360s); upgrading to FULL_RELOCALIZE
2026-09-13 14:09:32,819 [INFO] [FullRelocalize] reason=expected_tab_inactive expected_tab=stage candidates=[] winner=None is_conflict=False elapsed=1.640s
2026-09-13 14:09:33,848 [INFO] 成功匹配模板 'stages/level4_desert_ruins.png'！相似度: 0.9715，相對亮度比: 0.60，座標: (523, 661)
2026-09-13 14:09:33,930 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-13 14:09:34,486 [INFO] 成功匹配模板 'stages/level6_ice_cave.png'！相似度: 0.9685，相對亮度比: 0.64，座標: (1559, 475)
2026-09-13 14:09:34,959 [WARNING] ⚠️ 模板 'stages/level6_ice_cave.png' 匹配到 1 個候選點，但所有點的亮度比例均低於門檻 0.70，判定為背景暗區按鈕，予以過濾！
2026-09-13 14:09:34,960 [INFO] ⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...
2026-09-13 14:09:36,572 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9730，相對亮度比: 0.70，座標: (81, 925)
2026-09-13 14:09:36,963 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9887，相對亮度比: 0.39，座標: (1387, 67)
2026-09-13 14:09:37,280 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9994，相對亮度比: 1.00，座標: (1280, 148)
2026-09-13 14:09:38,003 [INFO] [LobbyTabUpgrade] Expected tab 'stage' not active (act=0.3669, inact=0.4199, elapsed=0.360s); upgrading to FULL_RELOCALIZE
2026-09-13 14:09:39,541 [INFO] [FullRelocalize] reason=expected_tab_inactive expected_tab=stage candidates=[] winner=None is_conflict=False elapsed=1.531s
2026-09-13 14:09:40,525 [INFO] 成功匹配模板 'stages/level4_desert_ruins.png'！相似度: 0.9715，相對亮度比: 0.60，座標: (523, 661)
2026-09-13 14:09:40,608 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-13 14:09:40,928 [INFO] 成功匹配模板 'stages/stage_label.png'！相似度: 1.0000，相對亮度比: 1.00，座標: (762, 471)
2026-09-13 14:09:41,286 [INFO] 成功匹配模板 'stages/first_stage.png'！相似度: 0.9714，相對亮度比: 1.00，座標: (756, 344)
2026-09-13 14:09:41,289 [INFO] 🧭 尋路中：在畫面中找到 [stages/first_stage.png] (信心度: 0.9714)，點擊按鈕中心座標 (756, 367)。
2026-09-13 14:09:41,417 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-13 14:09:41,426 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-13 14:09:43,283 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9730，相對亮度比: 0.70，座標: (81, 925)
2026-09-13 14:09:43,653 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9887，相對亮度比: 0.39，座標: (1387, 67)
2026-09-13 14:09:43,921 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9914，相對亮度比: 0.49，座標: (1280, 148)
2026-09-13 14:09:45,325 [INFO] [LobbyTabUpgrade] Expected tab 'stage' not active (act=0.6803, inact=0.5549, elapsed=1.062s); upgrading to FULL_RELOCALIZE
2026-09-13 14:09:46,720 [INFO] 成功匹配模板 'dungeons/dungeon.png'！相似度: 0.7067，相對亮度比: 0.75，座標: (811, 911)
2026-09-13 14:09:47,628 [INFO] 成功匹配模板 'dungeons/dungeon.png'！相似度: 0.7067，相對亮度比: 0.75，座標: (811, 911)
2026-09-13 14:09:49,541 [INFO] 成功匹配模板 'demon_lords/demon_lords_entry_after.png'！相似度: 0.7100，相對亮度比: 0.59，座標: (1257, 914)
2026-09-13 14:09:49,989 [INFO] 成功匹配模板 'demon_lords/demon_lords_entry.png'！相似度: 0.7485，相對亮度比: 0.60，座標: (1256, 913)
2026-09-13 14:09:49,992 [INFO] [FullRelocalize] reason=expected_tab_inactive expected_tab=stage candidates=[] winner=None is_conflict=False elapsed=4.672s
2026-09-13 14:09:51,013 [INFO] 成功匹配模板 'stages/level4_desert_ruins.png'！相似度: 0.9715，相對亮度比: 0.60，座標: (523, 661)
2026-09-13 14:09:51,095 [INFO] [IntentRouting] intent=primary_navigation scene=stage_select action=continue_primary reason=primary_route_delegated progress=idle
2026-09-13 14:09:51,619 [INFO] 成功匹配模板 'stages/level6_ice_cave.png'！相似度: 0.9686，相對亮度比: 0.64，座標: (1559, 475)
2026-09-13 14:09:52,108 [WARNING] ⚠️ 模板 'stages/level6_ice_cave.png' 匹配到 1 個候選點，但所有點的亮度比例均低於門檻 0.70，判定為背景暗區按鈕，予以過濾！
2026-09-13 14:09:52,109 [INFO] ⌛ 尋路按鈕已不在畫面上，正在等待畫面載入或大廳開始按鈕出現...
2026-09-13 14:09:53,811 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9730，相對亮度比: 0.70，座標: (81, 925)
2026-09-13 14:09:54,239 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9887，相對亮度比: 0.39，座標: (1387, 67)
2026-09-13 14:09:54,515 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9914，相對亮度比: 0.49，座標: (1280, 148)
2026-09-13 14:09:54,845 [INFO] 成功匹配模板 'stages/start.png'！相似度: 1.0000，相對亮度比: 1.00，座標: (1097, 684)
2026-09-13 14:09:54,933 [INFO] [IntentRouting] intent=primary_navigation scene=lobby action=start_primary reason=primary_start_ready progress=idle
2026-09-13 14:09:54,934 [INFO] 🔄 狀態轉移: NAVIGATING -> LOBBY
2026-09-13 14:09:57,385 [INFO] 成功匹配模板 'goback_town.png'！相似度: 0.9730，相對亮度比: 0.70，座標: (81, 925)
2026-09-13 14:09:57,769 [INFO] 成功匹配模板 'common/bread.png'！相似度: 0.9887，相對亮度比: 0.39，座標: (1387, 67)
2026-09-13 14:09:58,028 [INFO] 成功匹配模板 'common/quit.png'！相似度: 0.9914，相對亮度比: 0.49，座標: (1280, 148)
2026-09-13 14:09:58,359 [INFO] 成功匹配模板 'stages/start.png'！相似度: 1.0000，相對亮度比: 1.00，座標: (1097, 684)
2026-09-13 14:09:58,362 [INFO] [IntentRouting] intent=primary_navigation scene=lobby action=start_primary reason=primary_start_ready progress=idle
2026-09-13 14:09:58,698 [INFO] 成功匹配模板 'stages/start.png'！相似度: 1.0000，相對亮度比: 1.00，座標: (1097, 684)
2026-09-13 14:09:58,701 [INFO] Lobby start button [stages/start.png] detected (confidence 1.0000); clicking.
2026-09-13 14:09:58,827 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-13 14:09:58,834 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-13 14:10:00,981 [INFO] 成功匹配模板 'stages/start.png'！相似度: 1.0000，相對亮度比: 1.00，座標: (1097, 684)
2026-09-13 14:10:00,986 [INFO] Lobby start button is still visible after 2.3s; retrying click.
2026-09-13 14:10:01,215 [INFO] [DebugArtifacts] Debug image written to: E:\Side_Project\BlackfireCrusade_tool\scratch\debug\debug_click.png
2026-09-13 14:10:01,223 [INFO] 🎯 [DebugVisualizer] 已成功將診斷標記 (ROI/BBox/OCR/Click) 寫入 debug_click.png
2026-09-13 14:10:02,647 [INFO] Battle feature [common/auto.png] detected (confidence 0.9997); entering BATTLE.
2026-09-13 14:10:02,648 [INFO] 🔄 狀態轉移: LOBBY -> BATTLE
```