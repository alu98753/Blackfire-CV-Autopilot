# 大廳頁籤場景感知與尋路防呆規格書 (Lobby Tab Scene Detection & Navigation Spec) 🧭

> 關聯檔案：
> - 感知核心：[utils/scene_detector.py](../../utils/scene_detector.py)
> - 檢測註冊：[utils/detector_registry.py](../../utils/detector_registry.py)
> - 圖像比對：[vision/matcher.py](../../vision/matcher.py)
> - 快照契約：[utils/scene_snapshot.py](../../utils/scene_snapshot.py)
> - 導航決策：[states/handlers/navigation.py](../../states/handlers/navigation.py)
> - 架構規範：[Greenfield-lite Architecture v1](../../docs/architecture/project_arch_greenfield_lite_v1.md)
> 建立日期：2026-09-10  
> 分支：`fix/lobby-tab-scene-detection`  
> 狀態：已定稿待審查 (Finalized Spec - Pending User Confirmation)

---

## 1. 背景與問題定義 (Problem Statement)

### 1.1 現象重現
在地下城通關回到活動大廳後，懸賞排程器自動派發下一個地下城任務（如黏糊糊的石窟）。然而系統在導航時無故點擊了底部的【禁域】按鈕；在切換至禁域畫面後，系統竟然堅定判定當前處於 `scene=dungeon_select`（地下城選關介面），並在完全不含地下城卡片的禁域畫面上連續向右滑動拉回 7 次，最後觸發 recovery 返回城鎮。

### 1.2 根本原因雙重剖析

#### 原因一：`SceneDetector` 頁籤感知失真 (`_after` 互斥缺陷與歷史遺留補丁)
1. **歷史成因考古 (Git Archaeology)**：
   - 經追查 Git 提交歷史：
     - **Commit `d620827a` (2026-09-04)**：當初為黃金古國（禁域）開發卡片對齊時，專案裡**只有 `Domains_entry.png`，尚未截取到 `Domains_entry_after.png`**。為了判定禁域是否被選中，作者撰寫了 `_has_red_selection_ring` 啟發式算法（計算 HSV 紅圈像素量）。因為該計算較耗 CPU 且為特定模式專用，作者為了避免其他模式（地下城、關卡）每幀盲算紅圈，**順手加了守護條件：`if config_type == "domain":`**。
     - **Commit `bfa9a84b` (2026-09-04)**：約 1 小時後截取到了 `Domains_entry_after.png` 模板，作者將紅圈算法替換為模板比對 `_selected_from_active_inactive_pair`，**但遺漏了拆除外層的 `if config_type == "domain":` 守護條件**！
2. **感知與配置耦合引發的災難**：
   - 當掛機地下城（`config_type == "dungeon"`）時，系統直接略過禁域檢測！
   - 一旦畫面因誤點切到禁域，系統對眼前的禁域視而不見，只能回頭拿「關卡」與「地下城」做兩者互斥比對。
3. **`dungeon_after.png` 產生假陽性高信心度 (幽靈匹配)**：
   - 實測在【禁域】被選中的畫面上：
     - `dungeons/dungeon.png` (未選中態): **0.9563**
     - `dungeons/dungeon_after.png` (選中態): **0.8974** ⚠️
     - `common/select_stage_after.png`: **0.8463**
     - `domains/Domains_entry_after.png`: **0.9487**
   - 因地下城選中與未選中圖標僅差外光暈，即便地下城**未被選中**，`dungeon_after.png` 依然高達 0.8974。
   - 因為 `0.8974 > 0.8463 + 0.02`，系統誤將禁域畫面裁定為 `dungeon_select_open = True`。
4. **未做成對差值 (Active vs Inactive) 驗證**：
   - 真正處於地下城頁籤時，`dungeon_after` 信心度必須高於 `dungeon`。當 `dungeon` (0.9563) > `dungeon_after` (0.8974) 時，代表地下城明確為未選中。
5. **註冊表漏洞 (Inactive 漏登)**：
   - 在 [utils/detector_registry.py](../../utils/detector_registry.py) 中，`DetectorGroup.TABS` 僅登錄了 `select_stage_after.png` 與 `dungeon_after.png`，卻漏登了 `select_stage.png` 與 `dungeon.png`，導致成對檢測在特定 Profile 下會被 `allows_template` 攔截。

#### 原因二：尋路導航未在大廳排除城鎮大門 (`common/door.png`)
1. **大門模板與禁域圖標外型高度相似**：
   - [common/door.png](../../templates/common/door.png) 是城鎮中央的拱門形「傳送門」建築。
   - 大廳底部的【禁域】按鈕 ([Domains_entry.png](../../templates/domains/Domains_entry.png)) 同樣是拱門形建築。
2. **大廳尋路未過濾大門**：
   - 懸賞配置路徑包含 `["common/door.png", "dungeons/dungeon.png", "dungeons/Slime_entry.png"]`。
   - 在大廳時若卡片暫時不在螢幕上，[navigation.py](../../states/handlers/navigation.py) 倒序尋路掃描，由於 [filter_navigation_path](../../states/handlers/navigation.py) 未在大廳排除 `door.png`，加上通用入場閾值（`ENTRY_THRESHOLD = 0.60`）過於寬鬆，禁域按鈕跑出 0.6723 相似度，被誤當作大門點擊。

---

## 2. 兩階段交付計畫 (Two-Phase Plan)

依照使用者指示，本任務分兩次迭代推進：

```text
┌─────────────────────────────────────────────────────────────┐
│ 第 1 次（當前實作）：解決 _after 誤判與 SceneDetector 頁籤重構   │
│ - DetectorRegistry.classify() 補齊 Inactive 頁籤模板         │
│ - 重構 SceneDetector 頁籤感知機制 (徹底刪除 config_type 補丁) │
│ - 納入大廳 5 大頁籤成對判定 (Active vs Inactive)               │
│ - 全局競爭選出唯一定位頁籤，解決幽靈匹配                     │
│ - 補強單元測試覆蓋                                          │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 第 2 次（後續步驟）：修正尋路導航會抓的 scene 與防呆防誤點        │
│ - filter_navigation_path 於 is_lobby 時強制剃除 door.png    │
│ - 提高 door.png 獨立比對門檻至 0.88 以上                      │
│ - 完善已在目標頁籤但未見卡片時的滑動防護，禁止點擊大門        │
│ - 驗證完整地下城尋路與懸賞切換流程                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 第 1 次交付技術規格：大廳 5 大頁籤感知重構

### 3.1 支援頁籤與模板清單

大廳底部 5 大按鈕對照表：

| 索引 | 頁籤語意 | 未選中模板 (Inactive) | 選中模板 (Active / After) | 對應 SceneType | 對應 SceneId |
| :---: | :---: | :--- | :--- | :--- | :--- |
| 1 | **普通關卡** | `common/select_stage.png` | `common/select_stage_after.png` | `SceneType.LOBBY_STAGE` | `SceneId.STAGE_SELECT` |
| 2 | **地下城** | `dungeons/dungeon.png` | `dungeons/dungeon_after.png` | `SceneType.LOBBY_DUNGEON` | `SceneId.DUNGEON_SELECT` |
| 3 | **禁域 (領地)**| `domains/Domains_entry.png` | `domains/Domains_entry_after.png` | `SceneType.DOMAIN_SELECT` | `SceneId.DOMAIN_SELECT` |
| 4 | **首領 (領主)**| `load/Lord_entry.png` | `load/Lord_entry_after.png` | `SceneType.LORD_SELECT` | `SceneId.LORD_SELECT` |
| 5 | **魔王 (魔神)**| `demon_lords/demon_lords_entry.png`| `demon_lords/demon_lords_entry_after.png`| `SceneType.DEMON_LORD_SELECT` | `SceneId.DEMON_LORD_SELECT` |

### 3.2 註冊表補強 ([utils/detector_registry.py](../../utils/detector_registry.py))

在 `classify()` 中，將 5 大頁籤的 **所有 10 張模板** 以及 `locked_entry.png` 完整登錄至 `DetectorGroup.TABS`：
```python
if template_name in {
    "common/select_stage.png",
    "common/select_stage_after.png",
    "dungeons/dungeon.png",
    "dungeons/dungeon_after.png",
    "domains/Domains_entry.png",
    "domains/Domains_entry_after.png",
    "load/Lord_entry.png",
    "load/Lord_entry_after.png",
    "demon_lords/demon_lords_entry.png",
    "demon_lords/demon_lords_entry_after.png",
    "common/locked_entry.png",
}:
    return DetectorGroup.TABS
```

### 3.3 判定演算法與代碼重構重點 ([utils/scene_detector.py](../../utils/scene_detector.py))

#### 1. 刪除歷史補丁程式碼 (Dead/Coupled Code Elimination)
- **徹底刪除** [scene_detector.py:L227-L262](../../utils/scene_detector.py#L227-L262) 依賴任務配置的孤立判定：
  ```python
  # 🚫 全部刪除以下代碼：
  if config_type == "domain": ...
  if config_type == "lord_boss": ...
  if config_type == "demon_lords": ...
  ```
- **清理廢棄 Helper**：移除已無存在價值的 `_selected_from_active_inactive_pair` 與 `_runtime_config_value`，不再從 `machine.config` 動態覆寫頁籤模板路徑，統一定義於靜態表格。

#### 2. 成對差值與全局競爭抉擇 (Competitive Tab Disambiguation)
在 `SceneDetector` 中引入專用頁籤解析方法 `_resolve_active_lobby_tab(screen_img, profile)`：
- **成對對比**：
  對 5 大頁籤分別比對 `(template_after, template_normal)`：
  $$c_{after, i} = \text{match}(template\_after_i)$$
  $$c_{normal, i} = \text{match}(template\_normal_i)$$
  $$\Delta_i = c_{after, i} - c_{normal, i}$$
- **候選合格條件 (Candidate Qualification)**：
  - $c_{after, i} \ge \text{TAB\_CONFIDENCE\_THRESHOLD}$ (預設 `0.70`)
  - $\Delta_i \ge \text{TAB\_DELTA\_MARGIN}$ (預設 `-0.03`，即 Active 必須顯著優於或逼近 Inactive；當 Inactive 明顯高於 Active 時，例如 $0.956 > 0.897 + 0.03$，明確排除非選中態)
- **評分與決策 (Scoring & Decision)**：
  - 計算綜合指標：$Score_i = c_{after, i} + \Delta_i$
  - 選取最高分且合格者作為唯一勝出頁籤。
  - 若所有頁籤皆未符合條件（如切換動畫、黑屏）：
    - 若 `is_lobby` 為 True，設為 `SceneType.LOBBY_OTHER`，`active_tabs` 為空。
    - 若 `is_lobby` 為 False，維持 `SceneType.UNKNOWN`。

### 3.4 第 1 次驗證與測試計畫 (Verification Plan 1)

- **目標測試檔**：`tests/test_entity_lobby_panel.py` 與 `tests/test_behavior_detector_registry.py`
- **測試案例清單**：
  1. `test_tab_disambiguation_domain_selected_over_dungeon_ghost_match`：
     當前畫面為「禁域」時（`Domains_entry_after` 高），即使 `dungeon_after` 達 0.89，仍必須正確判定為 `SceneType.DOMAIN_SELECT`，`active_tabs == ["domain"]`，絕不可判定為 `dungeon`。
  2. `test_tab_disambiguation_dungeon_selected`：地下城選中時正確識別為 `SceneType.LOBBY_DUNGEON`。
  3. `test_tab_disambiguation_stage_selected`：關卡選中時正確識別為 `SceneType.LOBBY_STAGE`。
  4. `test_tab_disambiguation_lord_selected`：領主選中時正確識別為 `SceneType.LORD_SELECT`。
  5. `test_tab_disambiguation_demon_lord_selected`：魔王選中時正確識別為 `SceneType.DEMON_LORD_SELECT`。
  6. `test_detector_registry_includes_inactive_tabs`：驗證 `select_stage.png` 與 `dungeon.png` 確實被分類至 `DetectorGroup.TABS`。
- **執行指令**：
  ```powershell
  .venv\Scripts\python -m unittest tests.test_entity_lobby_panel
  .venv\Scripts\python -m unittest tests.test_behavior_detector_registry
  ```

---

## 4. 第 2 次交付技術規格：尋路導航 Scene 修正與防誤點

### 4.1 大廳導航強制剔除大門 ([states/handlers/navigation.py](../../states/handlers/navigation.py))

1. **`filter_navigation_path(nav_path, active_tabs, is_lobby=False)` 增強**：
   - 既有函式僅能根據 `active_tabs` 跳過 `select_stage.png` 或 `dungeon.png`。
   - **新增規則**：若傳入 `is_lobby=True`（或畫面上偵測到大廳錨點 `goback_town.png` / `common/bread.png`）：
     - **強制從 `nav_path` 中移除 `common/door.png`**。
     - 理由：角色身處大廳內部，絕無在大廳中尋找城門的可能，從根源杜絕在大廳將其他拱形圖標誤認為大門。

2. **提高 `common/door.png` 獨立檢測門檻**：
   - 目前在 [navigation.py:L1208](../../states/handlers/navigation.py#L1208) 的倒序尋路中，`door` 落入通用 `ENTRY_THRESHOLD = 0.60`。
   - **修改為獨立高閾值**：`common/door.png` 比對閾值提升至 **0.88 以上**（與城鎮大門直點邏輯 line 1175 之 0.90 對齊），禁止以 0.60 模糊比對。

3. **已在目標頁籤時的卡片滑動防呆**：
   - 當 `dungeon_select_open` 為 True 且當前為地下城模式，若當前畫面未見目標卡片：
     - 導航應直接維持在卡片對齊／滑動流程（`CardListNavigator.swipe_towards_target`）。
     - 禁止 fallback 回倒序尋路掃描，防止在清單邊緣進行未定義點擊。

### 4.2 第 2 次驗證與測試計畫 (Verification Plan 2)

- **目標測試檔**：`tests/test_behavior_navigation.py`
- **測試案例清單**：
  1. `test_filter_navigation_path_strips_door_when_in_lobby`：
     輸入包含 `["common/door.png", "dungeons/dungeon.png", "dungeons/Slime_entry.png"]`，在 `is_lobby=True` 時，過濾後結果絕不可包含 `common/door.png`。
  2. `test_navigation_does_not_click_door_on_lobby_screen`：
     模擬在大廳畫面（`goback_town` 可見），即使畫面上出現與拱門相似的圖形且信心度為 0.70，系統絕不點擊該座標。
- **執行指令**：
  ```powershell
  .venv\Scripts\python -m unittest tests.test_behavior_navigation
  ```

---

## 5. 未來獨立工作註記 (Future Work RFC)

### RFC: 全專案 `SceneType` 命名正規化與統一 (Unify SceneType Enums)

* **背景與動機**：
  目前舊架構使用 `SceneType.LOBBY_STAGE` 與 `SceneType.LOBBY_DUNGEON`，而新擴充的頁籤使用了 `DOMAIN_SELECT`、`LORD_SELECT`、`DEMON_LORD_SELECT`；在 Greenfield-lite 架構中則標準化為 `SceneId.STAGE_SELECT`、`SceneId.DUNGEON_SELECT` 等。目前透過 `scene_snapshot.py` 的 `_SCENE_TYPE_MAP` 字典進行等價橋接轉換。
* **為何不納入本次修正**：
  該重構屬於「全域純語法重命名（Rename Refactoring）」，影響數十個 Handlers 與單元測試檔案。為了遵循 **變更收斂（Scope-Isolated）** 與 **單一職責** 原則，本次 `fix/lobby-tab-scene-detection` 分支應專注於行為 Bug 修復，避免 PR 膨脹與迴歸風險。
* **獨立規劃目標**：
  1. 建立獨立分支 `refactor/unify-scene-type-enums`。
  2. 將 `SceneType.LOBBY_STAGE` 統一更名為 `SceneType.STAGE_SELECT`。
  3. 將 `SceneType.LOBBY_DUNGEON` 統一更名為 `SceneType.DUNGEON_SELECT`。
  4. 消除 `_SCENE_TYPE_MAP` 的別名轉換，實現 `SceneType` 與 `SceneId` 的 1:1 零阻抗映射。
