# 開發故事：重開登入全域感知解耦與地下城交棒前置路由修復 🛡️

> 日期：2026-09-11  
> 分支：`fix/login-flow-dungeon-handover`  
> 成果契約：[Precondition Contracts](../architecture/precondition_contracts.md), [Project Architecture Greenfield Lite](../architecture/project_arch_greenfield_lite_v1.md)  
> 關鍵模組：[utils/scene_detector.py](../../utils/scene_detector.py), [utils/scene_catalog.py](../../utils/scene_catalog.py), [states/login_flow.py](../../states/login_flow.py), [states/handlers/explore.py](../../states/handlers/explore.py), [states/state_machine.py](../../states/state_machine.py)  

---

## 1. Purpose (目的)

當遊戲在地下城深層、戰鬥進行中或結算畫面遇卡死/崩潰觸發重開（`GameRelaunchSubflow`）後，系統在重新登入並交棒給主狀態機的過程中出現三大架構性失控：
1. **登入流程感知狹隘與私有白名單維護雙軌制**：
   - `LoginFlow` 的 `_wait_for_game_ready` 私自維護了 11 個白名單模板（如 `auto.png`、`continue.png` 等）作為 fallback，而未直接信任全域感知層。
   - `SceneDetector.detect` 原先將地下城檢測限定於 `is_dungeon_mode`（配置為 dungeon 或 mix），重開後若模式未顯式指定或地下城已通關，全域感知無法客觀辨識當前畫面為地下城通關 (`dungeons_complete.png`) 或戰鬥結算 (`SceneId.RESULT`)。
2. **地下城通關後離場路由遺失 (Intent Latching 失效)**：
   - 登入完成後若停留在地下城通關畫面（`dungeons_complete.png`），`ExploreHandler` 嘗試呼叫 `state_machine.navigate_after_dungeon()`，但因為 `state_machine.config` 尚未載入目標路由，導致尋路失敗並無限重試卡死。
3. **登入主畫面誤判遮擋**：
   - 若重啟後遊戲尚未完全載入而停留在登入主畫面（`login.png`），缺乏全域守護導致被誤認為未知遮擋物或直接落入預設處理。

---

## 2. Action (行動)

1. **升格 `SceneDetector` 為全域客觀感知層 (Mode-Agnostic Perception)**：
   - 於 [utils/scene_detector.py](../../utils/scene_detector.py) 的 `SCENE_ANCHOR_SPECS` 正式登錄 `SceneId.DUNGEON_EXPLORING`（以 `dungeons_complete.png` 為核心特徵）、`SceneId.BATTLE`（`auto.png`、`battle_features`）與 `SceneId.RESULT`（`defeat.png`、`continue.png` 等）。
   - 重構 `detect()` 流程，將客觀場景比對（地下城、戰鬥、結算）提升至不受 `is_dungeon_mode` 限制的客觀前置檢測，一律如實回傳 `SceneInfo`。
2. **徹底移除 `LoginFlow` 私有 Fallback 白名單 (DRY 原則與單一感知來源)**：
   - 於 [states/login_flow.py](../../states/login_flow.py) 廢除 `_wait_for_game_ready` 中的私有 11 項 fallback 白名單，統一呼叫全域 `SceneDetector.detect()` 與 `SceneCatalog.is_known_world_scene(scene)`。
   - 只要畫面抵達任何合法世界場景（城鎮、大廳、地下城、戰鬥、結算），立即判定登入就緒並交棒。
3. **補齊地下城離場前置路由 (Precondition Route Injection & Intent Latching)**：
   - 於 [states/exceptions/subflows/game_relaunch.py](../../states/exceptions/subflows/game_relaunch.py) 注入 `build_dungeon_exit_prerequisite_route()`，確保重啟恢復地下城時預載 `goback_town.png` 與 `leave.png` 必備離場尋路資產。
   - 於 [states/handlers/explore.py](../../states/handlers/explore.py) 與 [states/state_machine.py](../../states/state_machine.py) 當前無導航路徑時自動保底生成地下城離場路由，達成 Intent Latching。
4. **全域登入主畫面守護 (Login Guard)**：
   - 於 [states/state_machine.py](../../states/state_machine.py) 的 `locate_current_scene()` 與 [states/handlers/explore.py](../../states/handlers/explore.py) 最前端加入 `login.png` 優先核驗；若檢測到登入主畫面，立即觸發 `LoginFlow`，絕不誤將登入按鈕當作遮擋彈窗。
5. **精準單元測試防護網補強**：
   - 補強 [tests/test_scene_detector.py](../../tests/test_scene_detector.py) 驗證 mode-agnostic 的地下城、結算與戰鬥場景辨識。
   - 補強 [tests/test_scene_catalog.py](../../tests/test_scene_catalog.py) 確保已知世界場景判定精確。
   - 補強 [tests/test_dungeon_relaunch_recovery.py](../../tests/test_dungeon_relaunch_recovery.py) 驗證登入後地下城交棒與離場路由注入。
   - 補強 [tests/test_login_flow_popup.py](../../tests/test_login_flow_popup.py) 驗證全域感知下彈窗排除與登入就緒。

---

## 3. Result (結果)

- **實測 100% 閉環驗證**：
  - 使用者在包含 `dungeons_complete.png` 的真實場景進行重啟實測，日誌確認 `SceneDetector` 第一時間成功識別 `SceneType.IN_DUNGEON`，`LoginFlow` 乾淨判定登入完成並交棒，`ExploreHandler` 順利獲取離場路由並點擊 `leave.png` 順暢離開地下城返回大廳。
- **架構潔淨度大幅提升**：
  - 徹底消除了雙軌制維護的私有 fallback 白名單，全系統統一透過 `SceneDetector` 與 `SceneCatalog` 進行感知。
  - 登入畫面具有最高優先權保護，不再被誤觸誤認。
- **單元測試 100% 綠燈**：
  - [tests/test_scene_detector.py](../../tests/test_scene_detector.py) PASS
  - [tests/test_scene_catalog.py](../../tests/test_scene_catalog.py) PASS
  - [tests/test_dungeon_relaunch_recovery.py](../../tests/test_dungeon_relaunch_recovery.py) PASS
  - [tests/test_login_flow_popup.py](../../tests/test_login_flow_popup.py) PASS

---

## 4. So What (架構意義)

1. **貫徹「感知」與「決策」分離**：
   - 感知層（`SceneDetector`）只負責客觀輸出當前畫面的事實，決策層（`LoginFlow` / `ExploreHandler`）基於客觀場景做狀態轉移與動作發射。
2. **單一真實來源 (Single Source of Truth)**：
   - 杜絕在業務流程中散落私有場景檢測邏輯，所有世界場景的語意與模板特徵集中於 `SceneDetector` 與 `SceneCatalog`。
3. **長效契約保證**：
   - 確立了「登入就緒條件 = 進入任何合法非載入世界場景」之不變量契約，未來新增任何副本或場景皆可直接繼承，無須修改登入流程。

---

## 5. Influence (影響與後續)

- 後續所有涉及重新啟動、崩潰自癒、斷線重連之子流程，皆可直接複用此一套穩健的感知交棒機制。
- 體力退避、懸賞調度與活動排程在面對意外重啟時具備更高的容錯與自主復原能力。
