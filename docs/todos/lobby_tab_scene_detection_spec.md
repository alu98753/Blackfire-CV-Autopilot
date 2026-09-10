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

#### 原因三：架構反模式（測試反向污染實作與 Mock 洩漏）
1. **粗糙的全局 Mock 迫使生產代碼妥協**：
   - 既有單元測試（如 `test_behavior_navigation.py`）中大量存在全域粗糙 mock：`matcher.match_mutually_exclusive_tabs.return_value = (True, False, ...)`，對所有模板查詢無差別回傳 True。
   - 當擴充頁籤無條件比對時，導致多個擴充頁籤在測試中同時為 True。
   - 先前實作竟然在生產代碼 `utils/scene_detector.py` 中寫入針對單元測試假象的 `elif len(active_extended) > 1:` 與 `type(...).__name__ != "MagicMock"`，直接破壞了生產代碼的純粹性與客觀領域邏輯，嚴重違反架構規範（`project_arch_greenfield_lite_v1.md`）中的「測試不應影響實作」原則。
2. **缺乏對稱統一的抽象層**：
   - 大廳 5 大功能頁籤各自有 Active (選中) 與 Inactive (未選中) 狀態，共 10 張模板圖。
   - 過去代碼只對地下城做了防偽，關卡、地下城與擴充頁籤（禁域、領主、魔王）使用了兩套不同的比對路徑（一組走 `match_mutually_exclusive_tabs`，另一組走 `_selected_from_active_inactive_pair`），未能抽成對稱、統一的大廳頁籤解析器。

---

## 2. 兩階段交付計畫 (Two-Phase Plan)

依照使用者指示，本任務分兩次迭代推進：

```text
┌─────────────────────────────────────────────────────────────┐
│ 第 1 次：大廳 5 大頁籤感知重構與測試邊界淨化                 │
│ - DetectorRegistry.classify() 補齊 10 張頁籤模板            │
│ - 建立大廳 10 模板結構化定義與對稱成對判定 (Active vs Inact)  │
│ - 10 模板兼任大廳環境鐵證，讓 SceneDetector 具備完整大廳感知 │
│ - 實作真實領域的「最大信心度仲裁 (Max-Confidence)」，消除衝突 │
│ - 徹底清除生產代碼中的 MagicMock 判斷與測試假象特化代碼       │
│ - 清理既有測試中粗糙的全域 Mock，符合真實合約               │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 第 2 次：修正尋路導航會抓的 scene 與防呆防誤點              │
│ - filter_navigation_path 於 is_lobby 時強制剃除 door.png    │
│ - 提高 door.png 獨立比對門檻至 0.88 以上                      │
│ - 完善已在目標頁籤但未見卡片時的滑動防護，禁止點擊大門        │
│ - 驗證完整地下城尋路與懸賞切換流程                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 第 1 次交付技術規格：大廳 10 模板對稱感知與仲裁重構

### 3.1 支援頁籤與 10 模板對照表

大廳底部 5 大按鈕（10 張模板）對照表：

| 索引 | 頁籤語意 | 未選中模板 (Inactive) | 選中模板 (Active / After) | 對應 SceneType | 對應 SceneId |
| :---: | :---: | :--- | :--- | :--- | :--- |
| 1 | **普通關卡** | `common/select_stage.png` | `common/select_stage_after.png` | `SceneType.LOBBY_STAGE` | `SceneId.STAGE_SELECT` |
| 2 | **地下城** | `dungeons/dungeon.png` | `dungeons/dungeon_after.png` | `SceneType.LOBBY_DUNGEON` | `SceneId.DUNGEON_SELECT` |
| 3 | **禁域 (領地)**| `domains/Domains_entry.png` | `domains/Domains_entry_after.png` | `SceneType.DOMAIN_SELECT` | `SceneId.DOMAIN_SELECT` |
| 4 | **首領 (領主)**| `load/Lord_entry.png` | `load/Lord_entry_after.png` | `SceneType.LORD_SELECT` | `SceneId.LORD_SELECT` |
| 5 | **魔王 (魔神)**| `demon_lords/demon_lords_entry.png`| `demon_lords/demon_lords_entry_after.png`| `SceneType.DEMON_LORD_SELECT` | `SceneId.DEMON_LORD_SELECT` |

> [!IMPORTANT]
> **大廳存在的客觀鐵證**：
> 除了既有的 `goback_town.png` 與 `common/bread.png` 外，畫面上若能比對到這 **10 張頁籤模板中的任何一張**（信心度 $\ge 0.70$），均可作為畫面身處「活動大廳 (is_lobby = True)」的客觀充分證據！

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

#### 1. 嚴禁測試反向污染實作 (Zero Test Leakage)
- **徹底移除**：
  - 移除所有 `elif len(active_extended) > 1: ...單元測試假象...` 等迎合測試的 hack。
  - 移除所有 `type(...).__name__ != "MagicMock"` 的型別判斷，改用純粹的標準型別檢驗與領域邏輯。
- **解耦跨頁籤互斥與單一按鈕成對檢驗**：
  - 不再對單一頁籤按鈕呼叫 `matcher.match_mutually_exclusive_tabs`，統一使用 `self._safe_match` 分別取得 Active 與 Inactive 信心度。

#### 2. 對稱成對檢驗 (Symmetric Pairwise Verification)
對 5 大頁籤統一執行對稱的成對檢驗：
- 對每一對 $(T_{active}, T_{inactive})$：
  $$c_{active} = \text{safe\_match}(T_{active})$$
  $$c_{inactive} = \text{safe\_match}(T_{inactive})$$
- **判定為 Active 候選之嚴格條件**：
  1. $c_{active} \ge 0.70$
  2. $c_{active} > c_{inactive} + 0.02$（**5 個頁籤一律同理**：若未選中態分數高於選中態，如地下城 $0.956 > 0.897$，堅決撤銷選中態，根除幽靈匹配）。

#### 3. 真實領域之最大信心度仲裁 (Max-Confidence Disambiguation)
收集所有滿足上述條件的 Active 頁籤：
- **Case 0（無頁籤 Active）**：
  若畫面具有大廳錨點（10 模板任一或 goback/bread），確認處於大廳但非 5 大選關頁籤（如彈窗、過渡畫面），裁定為 `SceneType.LOBBY_OTHER`，`active_tabs = []`。
- **Case 1（恰有 1 個頁籤 Active）**：
  明確無歧義，該頁籤勝出，輸出對應 `SceneType` 與 `active_tabs = [tab_name]`。
- **Case 2（多個頁籤同時宣稱 Active）**：
  真實遊戲畫面受光影或動畫干擾時：
  - 取最高信心度 $C_{\text{top}}$ 與次高信心度 $C_{\text{second}}$。
  - 若 $C_{\text{top}} - C_{\text{second}} \ge 0.05$：最高信心度者具顯著優勢，由其勝出！
  - 若差距 $< 0.05$：兩者旗鼓相當，遵循 Greenfield-lite 核心原則「**證據衝突時保持保守、不猜測**」，標記 `tab_conflict = True`，退回 `SceneType.LOBBY_OTHER`，不盲目猜測任何一個頁籤，等待下一幀畫面穩定！

### 3.4 測試端清理與修復規範
- 檢視 `tests/` 下所有 mock `match_mutually_exclusive_tabs` 或 `match` 的測試：
  - 嚴禁使用無差別全局 `return_value = (True, False, ...)`。
  - 測試必須依據傳入的 `template` 名稱模擬真實畫面特徵（例如測試關卡畫面時，僅對關卡模板給予高信心度，其餘給予未選中或低信心度），確保測試恪守真實契約。

### 3.5 第 1 次驗證與測試計畫 (Verification Plan 1)

- **目標測試檔**：`tests/test_entity_lobby_panel.py`, `tests/test_behavior_detector_registry.py`, `tests/test_scene_detector.py`
- **測試案例清單**：
  1. `test_tab_disambiguation_domain_selected_over_dungeon_ghost_match`：
     當前畫面為「禁域」時（`Domains_entry_after` 高），即使 `dungeon_after` 達 0.89，仍必須正確判定為 `SceneType.DOMAIN_SELECT`，`active_tabs == ["domain"]`，絕不可判定為 `dungeon`。
  2. `test_tab_disambiguation_dungeon_selected`：地下城選中時正確識別為 `SceneType.LOBBY_DUNGEON`。
  3. `test_tab_disambiguation_stage_selected`：關卡選中時正確識別為 `SceneType.LOBBY_STAGE`。
  4. `test_tab_disambiguation_lord_selected`：領主選中時正確識別為 `SceneType.LORD_SELECT`。
  5. `test_tab_disambiguation_demon_lord_selected`：魔王選中時正確識別為 `SceneType.DEMON_LORD_SELECT`。
  6. `test_tab_disambiguation_conflict_remains_lobby_other`：多個頁籤同時滿足且差距過小時，視為衝突落入 `SceneType.LOBBY_OTHER`。
  7. `test_detector_registry_includes_inactive_tabs`：驗證 `select_stage.png` 與 `dungeon.png` 確實被分類至 `DetectorGroup.TABS`。
- **執行指令**：
  ```powershell
  .venv\Scripts\python -m unittest tests.test_entity_lobby_panel tests.test_behavior_detector_registry tests.test_scene_detector
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
