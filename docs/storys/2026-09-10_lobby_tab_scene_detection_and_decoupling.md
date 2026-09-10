# 開發故事：大廳頁籤感知防偽、尋路大門防呆與契約解耦實踐 🏛️

> 日期：2026-09-10  
> 分支：`fix/lobby-tab-scene-detection`  
> 成果契約：[Lobby Scene Contract](../features/navigation/lobby_scene_contract.md)  
> 領域模型：[utils/scene_types.py](../../utils/scene_types.py)  

---

## 1. Purpose (目的)

地下城通關回到活動大廳後，懸賞排程器派發下一個地下城任務，導航系統卻在切換至【禁域】後誤將禁域堅定判定為 `SceneType.LOBBY_DUNGEON`，連續滑動拉回 7 次後崩潰回城。  
深入排查發現三個系統性問題：
1. **幽靈假陽性**：地下城選中圖標 (`dungeon_after.png`) 在未選中畫面上高達 0.897 相似度，未做成對未選中態比對导致誤判。
2. **尋路誤點大門**：大廳內部倒序尋路門檻過低（0.60），將拱門相似裝飾誤認為城鎮大門。
3. **架構反模式**：生產代碼中殘留迎合測試的 `elif len(active_extended) > 1:` 與 `MagicMock` 判斷；`SceneType`、`SceneInfo` 與 `SceneDetector` 高度耦合，缺乏獨立純粹的領域模型。

---

## 2. Action (行動)

1. **大廳 10 模板對稱成對差值與最大信心度仲裁 (Phase 1)**：
   - 在 `detector_registry.py` 中登錄全部 10 張頁籤模板。
   - 實作對稱成對差值檢驗（Active 必須高於 Inactive 且差距達 0.02），杜絕幽靈假陽性。
   - 實作最大信心度仲裁（Max-Confidence Disambiguation），顯著優勢者勝出；差距 $< 0.05$ 則保守退回 `LOBBY_OTHER`，拒絕盲猜。
   - 徹底拔除生產代碼中所有迎合測試的 mock 判斷代碼，並全面清理單元測試 mock。
2. **大廳尋路剃除大門與獨立高門檻 (Phase 2)**：
   - 增強 `filter_navigation_path`，在 `is_lobby=True` 時強制自路徑中移除 `common/door.png`。
   - 將 `door.png` 獨立比對門檻提升至 0.88 以上。
3. **Scene 領域契約與 Detector 感知引擎解耦 (Phase 3)**：
   - 抽離純資料契約模組 [utils/scene_types.py](../../utils/scene_types.py)，保證零 CV 依賴。
   - 確立 `SceneId` 為唯一 Single Source of Truth，`SceneType = SceneId` 實現零破壞無縫相容。
   - 徹底拋棄 `priority` 偽控制流數值，改用聲明式 `SceneAnchorSpec`。
   - `SceneInfo` 內建 `.to_snapshot()` 橋接 Greenfield-lite 不可變快照。
4. **契約收斂與規格歸檔**：
   - 提煉核心不變量至 [Lobby Scene Contract](../features/navigation/lobby_scene_contract.md)。
   - 將全域重命名待辦事項獨立為 [unify_scene_id_rfc.md](../todos/unify_scene_id_rfc.md)。
   - 刪除過期開發 Spec，杜絕 Doc Drift。

---

## 3. Result (結果)

- **缺陷徹底修復**：禁域畫面上即使地下城達 0.897 也不再誤判，大廳中不再誤點大門。
- **架構純粹乾淨**：領域層無任何 OpenCV / Matcher 依賴，`detect()` 內部消滅命令式 hardcode if-else。
- **測試 100% 通過**：
  - `tests.test_scene_types`: 5 通過
  - `tests.test_entity_lobby_panel`: 6 通過
  - `tests.test_scene_detector`: 12 通過
  - `tests.test_behavior_navigation`: 25 通過
  - `tests.test_behavior_detector_registry`: 4 通過
  - 5 套共 52 個聚焦單元測試全數綠燈。

---

## 4. So What (核心價值)

1. **從「打補丁」走向「對稱結構」**：將過去東加一個 if、西加一個 config 檢查的零散邏輯，收斂為 10 模板對稱檢驗與最大信心度仲裁，代碼具備自我防護力。
2. **落實「測試不應影響實作」**：徹底拔除針對測試 mock 的 hack，以真實遊戲特徵為唯一契約。
3. **雙軌契約防線 (Living Executable Contract)**：以 Markdown 記錄高層不變量，以 52 個單元測試作為活防護網，兼顧架構清晰與 Code as SSOT。

---

## 5. Influence (影響與後續)

1. **為後續頁籤擴充建立標準範式**：未來若新增第 6、第 7 個大廳功能，只需在 `LOBBY_TAB_DEFINITIONS` 宣告一組 Active/Inactive 模板即可自動享有成對差值與仲裁能力。
2. **為 Greenfield-lite 全場景遷移鋪平道路**：`scene_types.py` 的解耦與 `to_snapshot()` 讓所有 Handlers 與前置條件檢查可以直接消費不可變快照。
3. **驗證了 `canonical_contract_archival` 工作流**：建立了「刪除是預設；封存是例外」的文件收斂標準，為專案後續分支收尾樹立典範。
