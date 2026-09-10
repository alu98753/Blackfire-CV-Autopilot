# 大廳頁籤場景感知與尋路防呆規格書 (Lobby Tab Scene Detection & Navigation Spec) 🧭

> 關聯檔案：
> - 領域契約：[utils/scene_types.py](../../utils/scene_types.py) (Phase 3 抽離)
> - 感知核心：[utils/scene_detector.py](../../utils/scene_detector.py)
> - 快照契約：[utils/scene_snapshot.py](../../utils/scene_snapshot.py)
> - 檢測註冊：[utils/detector_registry.py](../../utils/detector_registry.py)
> - 導航決策：[states/handlers/navigation.py](../../states/handlers/navigation.py)
> - 架構規範：[Greenfield-lite Architecture v1](../architecture/project_arch_greenfield_lite_v1.md)
> - 前置條件：[Precondition Contracts](../architecture/precondition_contracts.md)
> - 回城契約：[REACH_TOWN Contract](../features/navigation/reach_town_contract.md)
> 建立日期：2026-09-10  
> 分支：`fix/lobby-tab-scene-detection`  
> 狀態：已完成交付 (Completed - Phases 1, 2, 3 All Delivered & Verified)

---

## 1. 核心問題與成因精要 (Problem & Root Causes Summary)

### 1.1 現象
地下城通關回到活動大廳後，系統誤將【禁域】畫面判定為 `SceneType.LOBBY_DUNGEON`，在完全不含地下城卡片的禁域畫面上連續拉回 7 次並觸發 recovery。

### 1.2 根本原因要點
1. **註冊表漏登**：[detector_registry.py](../../utils/detector_registry.py) 僅登錄 `_after.png`，漏登 Inactive 模板 `select_stage.png` 與 `dungeon.png`。
2. **缺乏成對差值檢驗**：地下城未選中態（`dungeon.png`）高達 0.956，但選中態（`dungeon_after.png`）仍有 0.897 幽靈假陽性；未比對差值導致誤判為地下城。
3. **歷史配置守護殘留**：`config_type == "domain"` 守護歷史遺留，造成掛地下城時略過禁域感知。
4. **測試反向污染實作**：粗糙全域 mock 導致生產代碼殘留 `elif len(active_extended) > 1:` 與 `MagicMock` 特化代碼。
5. **尋路閾值與大門誤點**：大廳倒序尋路誤點拱門相似物；門檻過低（0.60）。

---

## 2. 里程碑與交付進度 (Milestones & Status)

```text
┌─────────────────────────────────────────────────────────────┐
│ [已完成] Phase 1：大廳 10 模板對稱感知與最大信心度仲裁      │
│ - 註冊表補齊 10 張模板；移除生產代碼所有 MagicMock 判斷     │
│ - 實作對稱成對差值檢驗與最大信心度仲裁；清理單元測試 mock   │
│ (Commit: c1e7466 | 47 個聚焦單元測試全數綠燈通過)            │
├─────────────────────────────────────────────────────────────┤
│ [已完成] Phase 2：導航大廳防呆與大門守護                    │
│ - 大廳狀態強制自 nav_path 剔除 door.png                     │
│ - door.png 獨立比對門檻提升至 0.88 以上                      │
│ (Commit: c1e7466 | 47 個聚焦單元測試全數綠燈通過)            │
├─────────────────────────────────────────────────────────────┤
│ [已完成] Phase 3：Scene 領域契約與 Detector 感知引擎解耦     │
│ - 抽離純資料契約 utils/scene_types.py (零 CV/Matcher 依賴)   │
│ - 統一契約：SceneId 為唯一 Truth，SceneType = SceneId 別名   │
│ - 徹底拋棄 priority，採用宣告式 SceneAnchorSpec 與特徵驅動  │
│ - SceneDetector 演進為無 hardcode if-else 之規則評估引擎    │
│ - 對齊 Greenfield-lite SceneSnapshot 與 to_snapshot() 橋接   │
│ (聚焦單元測試 5 套共 52 個測試全數綠燈通過)                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 已完成交付精要 (Completed Deliverables Summary)

> **Commit 記錄**：`c1e7466` (`fix(scene_detector): implement symmetric lobby tab disambiguation and clean test mocks`)

### 3.1 大廳 10 模板對照表與客觀鐵證
大廳 5 大功能按鈕共 10 張模板，任一模板出現（信心度 $\ge 0.70$）即為身處大廳（`is_lobby=True`）之客觀充分證據：

| 頁籤語意 | 未選中 (Inactive) | 選中 (Active) | 映射 SceneType | 映射 SceneId |
| :--- | :--- | :--- | :--- | :--- |
| **普通關卡** | `common/select_stage.png` | `common/select_stage_after.png` | `SceneType.LOBBY_STAGE` | `SceneId.STAGE_SELECT` |
| **地下城** | `dungeons/dungeon.png` | `dungeons/dungeon_after.png` | `SceneType.LOBBY_DUNGEON` | `SceneId.DUNGEON_SELECT` |
| **禁域 (領地)** | `domains/Domains_entry.png` | `domains/Domains_entry_after.png` | `SceneType.DOMAIN_SELECT` | `SceneId.DOMAIN_SELECT` |
| **首領 (領主)** | `load/Lord_entry.png` | `load/Lord_entry_after.png` | `SceneType.LORD_SELECT` | `SceneId.LORD_SELECT` |
| **魔王 (魔神)** | `demon_lords/demon_lords_entry.png`| `demon_lords/demon_lords_entry_after.png`| `SceneType.DEMON_LORD_SELECT`| `SceneId.DEMON_LORD_SELECT`|

### 3.2 判定與防呆演算法
1. **成對差值驗證**：要求 $c_{active} \ge 0.70$ 且 $c_{active} > c_{inactive} + 0.02$，徹底根除幽靈假陽性。
2. **最大信心度仲裁**：單一 Active 直接勝出；複數 Active 時，領先差距 $\ge 0.05$ 勝出，差距 $< 0.05$ 視為衝突退回 `LOBBY_OTHER`。
3. **導航大門守護**：`is_lobby=True` 時 `filter_navigation_path` 強制剃除 `door.png`，且比對門檻提升至 0.88。
4. **測試邊界淨化**：徹底拔除 `elif len(active_extended) > 1:` 與 `MagicMock` 判斷，修復測試粗糙 mock。

---

## 4. Phase 3 技術規格：Scene 領域契約與感知引擎解耦重構

### 4.1 架構設計背景與原則對齊
依據專案核心架構規範：
1. **[Greenfield-lite Architecture v1](../architecture/project_arch_greenfield_lite_v1.md)**：
   - **依賴單向流動**：`main` → `agent_loop` → `handlers` / `preconditions` → `perception` (ports)。
   - **SceneSnapshot 不可變性**：決策層（Handler / Intent）只消費 Frozen 快照與場景識別結果，不得反向依賴 CV 比對器。
2. **[Precondition Contracts](../architecture/precondition_contracts.md)** 與 **[REACH_TOWN Contract](../features/navigation/reach_town_contract.md)**：
   - 場景是前置條件（Execution Precondition）的驗證標的（如 `SceneId.TOWN`、`SceneId.DUNGEON_SELECT`）。
   - 上層契約模組只需要 Scene 的「定義與型別」，不應被迫引用包含 OpenCV、Template Matcher 的肥大偵測模組。
3. **痛點現況**：目前 `SceneType`、`SceneInfo` 與 `SceneDetector` 混於同一個檔案 [utils/scene_detector.py](../../utils/scene_detector.py)，且 `detect()` 方法內部充斥著命令式 hardcoded `if-elif-else` 分支。

### 4.2 核心契約統一：以 `SceneId` 為唯一 Truth (Single Source of Truth)

#### 1. 為什麼要統一？現有兩者是什麼？
- **現況分析**：
  - `SceneType`（定義於 `utils/scene_detector.py`）是舊狀態機時代遺留的 `auto()` 整數枚舉，包含 `LOBBY_STAGE`, `LOBBY_DUNGEON` 等舊稱號。
  - `SceneId`（定義於 `utils/scene_snapshot.py`）是 Greenfield-lite 正規契約的 `(str, Enum)` 字串列舉，包含標準化命名 `STAGE_SELECT`, `DUNGEON_SELECT`。
  - 兩者目前仰賴 `_SCENE_TYPE_MAP` 字典進行執行期字串轉接，造成跨層阻抗與概念重複。
- **統一策略（零破壞無縫對齊）**：
  - 在抽離的 [utils/scene_types.py](../../utils/scene_types.py) 中，將 **`SceneId(str, Enum)`** 定義為系統唯一的場景契約實體。
  - 為了讓現有數十個既有 Handlers 與測試零破壞，宣告 **`SceneType = SceneId`**，並掛載相容性別名：
    ```python
    class SceneId(str, Enum):
        UNKNOWN = "unknown"
        TOWN = "town"
        STAGE_SELECT = "stage_select"
        DUNGEON_SELECT = "dungeon_select"
        DOMAIN_SELECT = "domain_select"
        LORD_SELECT = "lord_select"
        DEMON_LORD_SELECT = "demon_lord_select"
        LOBBY = "lobby"
        BATTLE = "battle"
        RESULT = "result"
        ...
        # 歷史相容性屬性別名 (值完全相同)
        LOBBY_STAGE = STAGE_SELECT
        LOBBY_DUNGEON = DUNGEON_SELECT
        LOBBY_OTHER = LOBBY

    # 全域等價別名：使舊代碼引用 SceneType 時直接獲得正規 SceneId
    SceneType = SceneId
    ```
  - **直接效益**：
    - `SceneType.LOBBY_DUNGEON == SceneId.DUNGEON_SELECT` 恆成立。
    - 徹底消除 `_SCENE_TYPE_MAP` 轉接字典。
    - 新舊模組直接共享同一套不可變領域契約。

### 4.3 聲明式場景規格目錄 (Declarative Scene Catalog) 與拋棄 Priority

#### 1. 為什麼徹底捨棄 `priority`？
在早期規劃中曾考慮加入 `priority: int` 數字以模擬 `if-else` 的順序，但經深思後決定**完全拔除 `priority`**，原因如下：
1. **消除控制流隱性耦合（Anti-Pattern）**：
   `priority` 只是把 hardcoded `if-else` 的先後順序換成 hardcoded 數字。未來維護人員新增場景時必須猜測權重數值，極易導致場景相互遮蔽（Shadowing）。
2. **符合遊戲畫面的物理正交性**：
   真實遊戲同一幀在物理上是互斥的（在城鎮就絕不在戰鬥、在地下城就絕不在大廳）。若畫面同時出現多種特徵，屬於閥值需要校準或特徵需要互斥排除，而非「比誰 priority 大」。
3. **Phase 1 的成功驗證（Evidence-based 仲裁）**：
   Phase 1 在大廳 5 大頁籤的重構中，完全沒有使用 priority，純粹仰賴**成對差值（Active vs Inactive Pairwise Verification）**與**最大信心度仲裁（Max-Confidence Disambiguation）**，已證明客觀特徵證據比偽優先序更穩健可靠。

#### 2. 聲明式規格定義 (`SceneAnchorSpec`)

```python
@dataclass(frozen=True)
class SceneAnchorSpec:
    """單一場景錨點規則宣告 (完全無 priority，純特徵驅動)"""
    scene_id: SceneId
    required_any: tuple[str, ...]          # 任一模板出現即可成立候選
    required_all: tuple[str, ...] = ()     # 必須全部出現
    excluded_any: tuple[str, ...] = ()     # 任一模板出現即排除 (衝突守護)
    min_confidence: float = 0.70           # 最低門檻
```

**場景規格目錄範例**：
- **`TOWN`**：`required_any=("common/door.png", "common/diamond.png")`
- **`BATTLE`**：`required_any=("battle/blood_empty.png", "battle/battle_head.png")`
- **`BATTLE_RESULT`**：`required_any=("battle/result_win.png", "battle/result_fail.png")`
- **`LOBBY`**：由 10 模板與 `goback_town.png`、`bread.png` 搭配排除 `common/door.png`，並由最大信心度仲裁決定具體子頁籤。
- **`UNKNOWN`**：無任何特徵符合時之安全退避。

### 4.4 模組職責劃分與向後相容

```text
┌─────────────────────────────────────────────────────────────┐
│ 領域契約層 (Domain Contracts) - 無 CV / 零依賴              │
│ 檔案：utils/scene_types.py                                  │
│ - SceneId(str, Enum): 唯一正規領域場景契約                  │
│ - SceneType = SceneId: 向後相容別名                         │
│ - SceneInfo: 單幀場景感知結果 (內建 to_snapshot() 方法)     │
│ - LobbyTabDefinition: 頁籤成對宣告                          │
│ - SceneAnchorSpec: 宣告式場景特徵錨點規格                   │
└──────────────────────────────┬──────────────────────────────┘
                               │ 依賴引入 (不反向依賴)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 感知實作層 (Perception Engine) - 規則驅動                   │
│ 檔案：utils/scene_detector.py                               │
│ - SCENE_CATALOG: 聲明式場景規則目錄                         │
│ - SceneDetector: 規則評估引擎 (Rule Evaluation Engine)      │
│ - 徹底消除 hardcode if-else，純粹依 Catalog 特徵比對        │
│ - Re-export SceneId / SceneType / SceneInfo 保持 100% 相容  │
└─────────────────────────────────────────────────────────────┘
```

### 4.5 Phase 3 驗證與測試計畫 (Verification Plan 3)
- **目標測試檔**：
  1. `tests/test_scene_types.py` (新增：驗證純資料合約、預設值、`to_snapshot()` 橋接、`SceneType is SceneId` 等價性)。
  2. `tests/test_scene_detector.py` (既有回歸測試)。
  3. `tests/test_entity_lobby_panel.py` (既有大廳 10 模板仲裁測試)。
  4. `tests/test_behavior_navigation.py` (既有導航與大門剔除測試)。
- **斷言標準**：
  - 47 個既有測試 100% 維持綠燈。
  - 新增測試驗證 `utils/scene_types.py` 能在無 OpenCV / Matcher 環境下獨立被 import 與實例化。
- **執行指令**：
  ```powershell
  .venv\Scripts\python -m unittest tests.test_scene_types tests.test_scene_detector tests.test_entity_lobby_panel tests.test_behavior_navigation
  ```

---

## 5. 未來獨立工作註記 (Future Work RFC)

### RFC: 全專案命名統一與徹底廢除 `SceneType` 別名 (Unify to SceneId & Deprecate SceneType)

* **背景與動機**：
  目前舊架構使用 `SceneType.LOBBY_STAGE` 與 `SceneType.LOBBY_DUNGEON`，而新擴充的頁籤使用了 `DOMAIN_SELECT`、`LORD_SELECT`、`DEMON_LORD_SELECT`；在 Greenfield-lite 架構中則標準化為 `SceneId.STAGE_SELECT`、`SceneId.DUNGEON_SELECT` 等。目前透過 `scene_snapshot.py` 的 `_SCENE_TYPE_MAP` 字典進行等價橋接轉換。
  雖然 Phase 3 已在 `utils/scene_types.py` 中將 `SceneId` 立為全系統唯一的領域契約實體，並透過 `SceneType = SceneId` 宣告與屬性別名（`LOBBY_STAGE = STAGE_SELECT`, `LOBBY_DUNGEON = DUNGEON_SELECT`）在底層實現了值與型別的 1:1 零阻抗映射，但專案中既有的數十個 Handlers、FSM 與測試檔案中仍散落著舊名稱 `SceneType.LOBBY_STAGE` 與 `SceneType.LOBBY_DUNGEON` 的字面引用。

* **為何不納入本次修正**：
  該重構屬於「全域純語法重命名（Rename Refactoring）」，涉及全專案跨模組數十個 Handlers 與測試檔案的大規模字面修改。為了遵循 **變更收斂（Scope-Isolated）** 與 **單一職責** 原則，本次 `fix/lobby-tab-scene-detection` 分支應專注於行為 Bug 修復、大門守護防呆與底層資料契約解耦，避免 PR 膨脹與全域迴歸風險。

* **未來獨立重構規劃目標 (Future Work Roadmap & TODOs)**：
  無論後續是以「單一全面重構分支」或是「兩階段推進」，皆須完成以下目標：
  1. **TODO 1: 全專案業務程式碼遷移至正規 `SceneId` (或重命名舊名稱)**：
     - 開立獨立重構分支 `refactor/unify-scene-type-enums` (或 `refactor/unify-to-scene-id`)。
     - 將 `SceneType.LOBBY_STAGE` 統一更名為 `SceneId.STAGE_SELECT`。
     - 將 `SceneType.LOBBY_DUNGEON` 統一更名為 `SceneId.DUNGEON_SELECT`。
     - 將所有 Handlers（`navigation.py`, `town.py`, `battle.py` 等）中的 `SceneType.XXX` 批次替換為正規的 `SceneId.XXX`。
     - 將 `SceneInfo.scene_type` 屬性更新（或提供 property 橋接）為 `SceneInfo.scene_id`。
  2. **TODO 2: 單元測試全數對齊 `SceneId`**：
     - 將全套測試案例中的 `SceneType.LOBBY_STAGE` / `SceneType.LOBBY_DUNGEON` 替換為 `SceneId.STAGE_SELECT` / `SceneId.DUNGEON_SELECT`。
  3. **TODO 3: 徹底廢除並移除 `SceneType = SceneId` 別名 (Deprecate & Remove Alias)**：
     - 在完成所有模組遷移後，正式自 `scene_snapshot.py` 中移除歷史遺留的 `_SCENE_TYPE_MAP` 字典。
     - 自 `utils/scene_types.py` 與 `utils/scene_detector.py` 中徹底刪除 `SceneType` 別名以及舊相容屬性（`LOBBY_STAGE`, `LOBBY_DUNGEON`），實現完全乾淨、唯一的 `SceneId` 命名空間。


