# Lobby 導航感知最小化規格（nav_slow_bug2）

**狀態：Proposed**

**範圍：** 大廳五頁籤（關卡、地下城、界域、領主、深淵魔王）的導航、換頁與卡片清單左右拖曳。
**不改變：** 頁籤判定的正確性、安全優先序、既有 `SceneSnapshot` / `NavigationIntent` / `NavigationProgress` 的責任歸屬。

相關契約：

- `docs/architecture/precondition_contracts.md`
- `docs/features/navigation/reach_town_contract.md`
- `docs/features/navigation/lobby_scene_contract.md`
- `utils/scene_types.py` 的 `LOBBY_TAB_DEFINITIONS`

## 1. 問題定義與證據

`c1e7466` 建立了五組 active/inactive 的對稱頁籤模板；`2136ff9` 將其併入目前的導航場景消歧邏輯。這十張模板在「未知場景、需要重定位」時是必要的鐵證與衝突仲裁來源，但目前被用在所有導航 tick。

目前呼叫鏈為：

```text
NavigationHandler.handle()
  -> SceneDetector.detect(screen_img, machine=machine)  # 未傳 profile，預設 UNKNOWN
  -> _resolve_lobby_tabs()
  -> 對 5 個 tab 各比 active + inactive，共 10 次 match
  -> 若沒有 stage/dungeon 候選，再跑 legacy stage-vs-dungeon 比對
```

因此，已知正在地下城選關、剛完成卡片左右滑動時，下一個畫面仍會依序比對 stage、dungeon、domain、lord、demon_lord 的十張頁籤模板；紀錄中另可見 legacy fallback 再比一次 `select_stage_after` 與 `dungeon_after`。在提供的紀錄中，十張頁籤模板約由 `19:14:24.834` 跑到 `19:14:28.138`，再加 legacy fallback 至 `19:14:28.896`；這段純場景辨識已接近四秒，且每次拖曳後都會重複。

這不是卡片拖曳本身慢，而是拖曳後以全域、無上下文方式重新辨識頁籤。既有 `DetectionProfileId.STAGE_SELECT`、`DUNGEON_SELECT` 等 profile 目前只限制 detector group，沒有縮小 `_resolve_lobby_tabs()` 的五組迴圈；因此單純把 `UNKNOWN` 改為其他 profile 不足以修正問題。

## 2. 根因

1. `NavigationHandler.handle()` 沒有把已知的導航意圖、in-flight action 或前一個已驗證的 lobby scene，轉成可供感知層使用的「預期頁籤」。
2. `SceneDetector._resolve_lobby_tabs()` 對所有 profile 一律完整掃描 `LOBBY_TAB_DEFINITIONS`，把「重定位」成本放進「穩態維護」路徑。
3. `match_mutually_exclusive_tabs()` 的 legacy 相容 fallback 會在無 stage/dungeon 候選時額外進行 match；它是舊 mock/API 相容層，不應成為 production 熱路徑。
4. 卡片清單拖曳完成後，系統缺少「此 action 的 postcondition 只需驗證同一頁籤仍開啟」這個明確契約，因而退回全域場景消歧。

## 3. 目標與非目標

### 3.1 目標

1. 已知導航目標的穩態 tick，頁籤辨識只比對該目標的 **active/inactive 一對模板**；正常情況最多兩次頁籤 template match。
2. 卡片對齊、左右滑動及選卡的 postcondition 驗證，沿用同一目標頁籤，不得重新掃描其餘四個頁籤。
3. 畫面不符合預期、切頁 click 逾時、衝突、或 state/profile 不可信時，才進行一次完整十模板重定位；復原仍採 bounded retry/defer/relaunch，不無限掃描或無限點擊。
4. popup、Town、Dungeon explore/prepare 等優先安全場景仍先於導航判定；最佳化不得把錯頁面當成可安全操作的卡片清單。
5. `SceneInfo.active_tabs` 只有在 active 證據已確認時才填入；只看到 target 的 inactive 模板時，只能證明「在 lobby 且目標未開」，不能猜測目前是哪一個其餘頁籤。

### 3.2 非目標

- 不改動五頁籤的模板、threshold、active/inactive margin（目前為 active `>= 0.70` 且高於 inactive `0.02`）。
- 不移除 UNKNOWN/recovery 的十模板鐵證、最大信心度仲裁或衝突保守處理。
- 不在本案改寫地下城可見卡片、冷卻牌或目標卡的業務判斷；該等比對可另行做 ROI/template-cache 效能工作。本案保證它們不再被「五頁籤全掃」阻塞。
- 不讓 `NavigationHandler` 直接持有 OpenCV 判斷規則；頁籤證據仍由 `SceneDetector` 產生，路由仍由 intent/decision layer 決定。

## 4. 設計：兩層感知與明確 tab scope

新增感知請求模型（名稱可依實作調整，但語意不可改變）：

```python
class LobbyTabScope(Enum):
    FULL_RELOCALIZE = "full_relocalize"  # 五組、十模板、可仲裁
    EXPECTED_TAB = "expected_tab"        # 只驗證指定 TabId 的 active/inactive

@dataclass(frozen=True)
class SceneDetectionRequest:
    profile: DetectionProfileId
    expected_tab: TabId | None
    tab_scope: LobbyTabScope
    reason: str  # e.g. navigation_steady, switch_postcondition, recovery
```

`expected_tab` 必須由已存在的導航語意集中解析，而不是由 Handler 自行猜測：

| 執行語意 | expected tab 的來源 |
| --- | --- |
| `stage` | primary route 的 stage target |
| `dungeon` | primary route 的 dungeon target |
| `domain` / `lord` / `demon_lord` | 已提交 activity intent 的 destination |
| `mix` / `daily` | 當前已提交的 route decision；不可只讀 config type，避免與 Daily policy 搶決策權 |
| 無 committed route、UNKNOWN、recovery | `None`，使用 `FULL_RELOCALIZE` |

推薦將此解析放在 navigation routing/context 層，輸出給 `NavigationHandler`；它是「本次 action 要到哪一頁」的 single source of truth。`SceneDetector` 只接受 request 與回報證據，不決定下一個業務目標。

### 4.1 每個 tick 的順序

```text
capture one frame
  -> global critical safety evidence（task popup、已知 overlay、Town / dungeon transition guard）
  -> if safety scene wins: 交給既有 owner，不操作 tab/card
  -> expected_tab 有效且 profile/前一個 postcondition 可採信？
       -> EXPECTED_TAB：只比該 tab 的 active + inactive
       -> active 確認：可執行同頁卡片對齊 / 滑動 / 選卡
       -> inactive 確認：在 lobby 但目標未開，交由 navigation decision 執行一次切頁 action
       -> 兩者皆無：進入 bounded relocalize
  -> FULL_RELOCALIZE：十模板 + 原本 max-confidence 仲裁
  -> 仍未知：WAIT / bounded retry / defer / relaunch（依既有 NavigationProgress）
```

關鍵點是 `DetectionProfileId` 是「允許的感知範圍」而非事實本身。`EXPECTED_TAB` 不命中時，不得因 profile 是 `DUNGEON_SELECT` 就直接宣稱地下城頁開啟；它只能觸發一次完整重定位或等待下一張穩定畫面。

### 4.2 `EXPECTED_TAB` 的判定規則

對指定 `LobbyTabDefinition`：

1. 比對 active、inactive 各一次，以現有 threshold/margin 產生 `(active_confidence, inactive_confidence)`。
2. `active >= 0.70` 且 `active > inactive + 0.02`：
   - `is_lobby=True`
   - `scene_type=tab.scene_type`
   - `active_tabs=[tab.name]`
   - 允許同頁卡片操作。
3. inactive 命中，或 active/inactive 均為頁籤存在證據但不滿足 active-dominance：
   - `is_lobby=True`
   - `scene_type=LOBBY_OTHER`（或等價的「lobby, target inactive/ambiguous」結果）
   - `active_tabs=[]`
   - 僅允許路由層點擊該 target tab；不得掃描、拖曳、點擊該頁的卡片。
4. 兩張皆無，或結果不可用：回報 `expected-tab-miss`；不得把它當成「其他 tab 一定開啟」。

若需要在換頁 click 後驗證 postcondition，第一次應先用上述兩張模板；只有 click 的 action timeout、連續觀測 miss、或安全場景證據與預期矛盾時，才升級 `FULL_RELOCALIZE`。

### 4.3 `FULL_RELOCALIZE` 的保留規則

完整十模板掃描只允許用於：

- 初始啟動、`STATE_UNKNOWN`、relaunch 後尚無可採信 snapshot；
- 未存在 committed navigation target；
- expected-tab miss 達到本 action 的重定位門檻；
- action timeout、互斥模板衝突、或 safety/transition guard 指出 profile 已失效；
- 明確的 recovery/relocalize action。

此模式維持 `lobby_scene_contract.md` 的鐵證、active-dominance 與 max-confidence conflict 規則。多候選差距不足 `0.05` 時仍回傳保守的 `LOBBY_OTHER` / 無 active tab，不能以導航目標強行覆寫觀測結果。

production path 應移除 `match_mutually_exclusive_tabs()` 的 legacy fallback。必要的測試相容性應修改 mock/fixture，使其支援標準 `matcher.match()` 回傳值；不得以額外 production CV 呼叫維持舊 mock 行為。

## 5. 導航與卡片操作契約

| 動作階段 | 必要頁籤證據 | 禁止行為 | 失敗處理 |
| --- | --- | --- | --- |
| 尚未在目標頁 | 目標 inactive/ambiguous，且 lobby 證據成立 | 掃描或拖曳目標頁卡片 | 發出一次切頁 action，等待其 postcondition |
| 切頁 postcondition | 只比目標 pair | 預設跑五 tab 全掃 | bounded wait 後一次重定位 |
| 卡片首次對齊 | 目標 active | 因為卡片不在左側就改判別的 tab | 僅執行 `CardListNavigator` 的對齊重試 |
| 卡片左右拖曳 | 目標 active，且 drag in-flight | 每一拖曳後重新全域 tab 仲裁 | 用同一 target pair 驗證；miss 才升級重定位 |
| 選卡 / 卡片未找到 | 目標 active | 以其他 tab 的 active 模板猜測位置 | 保持該 tab 的 card recovery；耗盡後走既有 progress recovery |
| 重定位 | 無可信 target 或預期失效 | 直接操作卡片 | 十模板仲裁後重建 route context |

卡片拖曳 action 的 postcondition 是「目標頁仍為 active」，不是「所有五個頁籤再被證明一次」。`NavigationProgress.InFlightAction` 應記錄該 action 的 `expected_tab`，直到 postcondition 成功、defer、cancel 或 recovery 清除，避免下一 tick 遺失上下文。

## 6. 實作邊界

預計修改點：

1. `utils/scene_detector.py`
   - 讓 `detect()` 接受明確 `SceneDetectionRequest`（或等價參數）。
   - 將 `_resolve_lobby_tabs()` 分為 target-pair 與 full-relocalize 兩個明確路徑；不可在 expected path 迴圈五個 `LOBBY_TAB_DEFINITIONS`。
   - 保留 `_frame_match_cache`，所有同 frame、同 threshold 的 target template 查詢必須重用結果。
   - 移除 legacy matcher fallback 的 production 呼叫。
2. `states/navigation_routing.py`（或既有 context resolver）
   - 從 committed intent / route decision / in-flight action 解析 `expected_tab`，並產生 detection request。
3. `states/handlers/navigation.py`
   - 改為使用 request 呼叫 scene detector；不再裸呼叫預設 `UNKNOWN`。
   - 對拖曳、對齊與換頁採同一個 `expected_tab`；只有規格列出的事件才能要求 full relocalize。
4. `states/navigation_progress.py`（若現有 in-flight metadata 不足）
   - 擴充 action metadata 的 `expected_tab` 與 relocalize 次數/原因，並在終止 action 時清除。
5. `tests/`
   - 測試應對 `matcher.match` 的呼叫集合與次數做精確斷言，不只驗證最終 scene。

## 7. 驗收條件

### 功能正確性

- 五個目標頁籤各自有「active 命中 → 可操作卡片」與「inactive 命中 → 只切目標 tab」測試。
- 目標 pair 皆未命中時，不可操作卡片；必須觸發 bounded full relocalize。
- full relocalize 保留：任一 active/inactive 模板可證明 lobby、active dominance、兩個候選差距 `< 0.05` 時保守不選 tab。
- Town、task popup、Dungeon explore/prepare 的安全優先序在 expected-tab mode 下與現況相同；它們出現時不得拖曳或點選卡片。
- `mix` / `daily` 的 expected tab 來自 route decision，地下城可用性改變時不會沿用過期 target。
- 切頁或拖曳失敗後，重定位與 retry 次數受現有 `NavigationProgress` 上限約束；不得無限使用 full scan。

### 效能與可觀測性

- 在已知 `expected_tab` 的一次穩態導航 tick，頁籤模板 matcher 呼叫數 **<= 2**，且呼叫集合只能是該 tab 的 active/inactive 模板。
- 卡片左右拖曳後的 postcondition tick，不得呼叫其餘四個 tab 的任何模板，也不得呼叫 legacy `match_mutually_exclusive_tabs()`。
- `FULL_RELOCALIZE` 的十模板掃描必須有結構化 log：`reason`、`expected_tab`、`action_id`、`attempt`、耗時與候選結果。
- 每次 expected-tab fast path 亦記錄 `tab`、active/inactive confidence、耗時與是否 upgrade；日誌可證明正常滑動不再觸發 full scan。
- 以提供的地下城滑動案例驗證：不再出現每次滑動後依序輸出 stage/domain/lord/demon_lord 全部 tab 模板成功比對的序列。

## 8. 建議測試清單

- `tests/test_entity_lobby_panel.py`
  - 參數化測試五個 `EXPECTED_TAB`，斷言僅匹配目標 pair。
  - expected miss 後升級 full relocalize；衝突仍保守處理。
- `tests/test_behavior_navigation.py`
  - 地下城卡片向左/右拖曳後，以 `DUNGEON_SELECT + expected_tab=dungeon` 驗證只有 `dungeon_after.png` / `dungeon.png`。
  - target inactive 時先切頁、尚未 active 前不呼叫卡片 navigator。
- `tests/test_behavior_navigation_progress.py`
  - in-flight drag/switch action 保存與清除 `expected_tab`；timeout 後只可 bounded relocalize。
- `tests/test_scene_detector.py`
  - full mode 維持十模板仲裁；expected mode 不洩漏至其他四頁籤。

執行測試時遵循 `project-test-rules`：僅執行上述直接相關的聚焦測試，不執行全套測試。

## 9. 風險與回退

主要風險是將過期 profile 當成事實，導致在錯頁操作卡片。緩解方式不是降低門檻，而是：安全場景優先、target pair 必須真的 active、inactive/miss 一律禁止卡片操作、失效時升級 full relocalize。

若 fast path 在真機上出現未涵蓋的轉場，可暫時以設定旗標停用 `EXPECTED_TAB`，統一退回 `FULL_RELOCALIZE`，但不得恢復 legacy fallback。回退只影響效能，不得改變既有場景判定契約。

## 10. 完成定義

此 TODO 在下列條件全部滿足後才可封存：五頁籤 fast path 與 recovery path 的聚焦測試全綠、真機地下城至少一次「對齊 → 左右拖曳 → 選卡」紀錄證明沒有非目標 tab match、full relocalize 的 telemetry 可追蹤且 bounded、`lobby_scene_contract.md` 若有行為改動已同步為 canonical contract。
