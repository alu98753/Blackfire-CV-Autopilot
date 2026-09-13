# Lobby Scene Detection & Navigation Contract 🧭

> 狀態：正式開發準則（Normative Contract）  
> 上位架構：[Greenfield-lite Architecture v1](../../architecture/project_arch_greenfield_lite_v1.md)  
> 前置條件：[Precondition Contracts](../../architecture/precondition_contracts.md)  
> 關聯契約：[REACH_TOWN Contract](reach_town_contract.md)  
> 領域實體：[utils/scene_types.py](../../../utils/scene_types.py)  
> 感知實作：[utils/scene_detector.py](../../../utils/scene_detector.py)  
> 導航決策：[states/handlers/navigation.py](../../../states/handlers/navigation.py)  
> 活契約驗證檔 (Executable Contracts)：
> - [tests/test_entity_lobby_panel.py](../../../tests/test_entity_lobby_panel.py) (頁籤防偽與衝突仲裁)
> - [tests/test_behavior_navigation.py](../../../tests/test_behavior_navigation.py) (大廳剔除城門防誤點)
> - [tests/test_scene_types.py](../../../tests/test_scene_types.py) (領域模型純潔性與零 CV 依賴)
>
> 術語與判讀：[Canonical Invariant Registry](../../architecture/canonical_invariant_registry.md)

---

## 1. 文件責任與範圍 (Scope & Responsibility)

本文件定義系統身處「活動大廳 (Lobby)」環境時，**場景識別、頁籤狀態裁決、以及大門導航防護之不可動搖的長期行為不變量 (Invariants)**。

本契約約束：
- `SceneDetector` 對大廳環境與 5 大功能頁籤的識別行為。
- `SceneInfo` / `SceneSnapshot` 對大廳場景的客觀表述。
- `NavigationHandler` 在大廳環境下的路徑過濾防誤點行為。

本契約不包含：
- 特定地下城或活動內部的探索／戰鬥邏輯。
- 暫時性的微調閾值（閾值由代碼與設定檔維護，本契約只保證差值行為）。

---

## 2. 核心架構不變量 (Canonical Invariants)

任何未來的程式碼重構或新增功能，**必須滿足以下 6 項核心不變量**。本節的精確模板路徑、信心門檻、ROI、呼叫次數與狀態名稱均屬可替換的實作或策略；只要本節規則與聚焦驗證仍成立，這些細節可以調整。

### Invariant 1：成對差值主導與二維色相光環消歧保證 (Active-Dominance & Chromatic Disambiguation Invariant)
- **Scope**：大廳頁籤選中態的感知。
- **Rule**：系統 MUST 以能區分選中與未選中態的成對證據裁決；當主要證據不足以區分時，MUST 使用獨立的視覺證據，而非把相似的中央圖樣當成選中態。
- **Observable consequence**：相似頁籤不會因單一模糊匹配而被誤判為已選中。
- **Allowed variation**：差值、色相特徵、ROI 與門檻可變更。
- **Verification**：`tests/test_entity_lobby_panel.py`。

### Invariant 2：保守仲裁保證 (Conservative Disambiguation Invariant)
- **Scope**：多個大廳頁籤候選互相衝突時的場景裁決。
- **Rule**：只有充分且可區分的證據才可裁決特定頁籤；證據衝突或不足時，系統 MUST 保留保守的大廳結果並等待新的觀測。
- **Observable consequence**：不穩定畫面不會被強制導向任一頁籤。
- **Allowed variation**：信心計算、仲裁演算法、保守場景型別與觀測節奏可變更。
- **Verification**：`tests/test_entity_lobby_panel.py`。

### Invariant 3：大廳無大門導航保證 (No-Door in Lobby Invariant)
- **Scope**：已確認大廳中的導航行為。
- **Rule**：系統 MUST NOT 在大廳中發出僅適用於城鎮入口的導航操作。
- **Observable consequence**：大廳裝飾或頁面元素不會觸發返回城鎮的誤點擊。
- **Allowed variation**：大廳識別器、路徑過濾器、入口特徵與導航資料結構可變更。
- **Verification**：`tests/test_behavior_navigation.py`。

### Invariant 4：純領域契約與單一真相保證 (Pure Domain & Single Truth Invariant)
- **Scope**：大廳場景的領域表述與決策輸入。
- **Rule**：決策層 MUST 消費穩定的場景領域表述，且該表述 MUST NOT 依賴特定視覺實作。
- **Observable consequence**：視覺引擎可以替換，而依賴場景結果的決策契約維持不變。
- **Allowed variation**：場景列舉、快照型別、模組位置與感知實作可變更。
- **Verification**：`tests/test_scene_types.py`。

### Invariant 5：兩階段感知與預期頁籤最小化保證 (Two-Tier Perception & Expected Tab Invariant)
- **Scope**：已知目標頁籤的穩態導航與定位失敗處理。
- **Rule**：已知目標時，系統 MUST 先採用目標範圍內的感知；該感知未提供足夠證據時，MUST 進入有界的全局重定位。卡片推斷不得改寫快速路徑的判定。
- **Observable consequence**：已知頁籤不會無限制地全量掃描；目標證據消失時可重新定位而非持續迷航。
- **Allowed variation**：掃描範圍、模板數量、重定位名稱與嘗試預算可變更。
- **Verification**：`tests/test_entity_lobby_panel.py` 與 `tests/test_behavior_navigation.py`。

### Invariant 6：導航地下城客觀特徵自癒彈回保證 (Dungeon Re-entrant Guard Invariant)
- **Scope**：導航流程重新觀測到地下城時的控制權交接。
- **Rule**：導航層 MUST NOT 在客觀地下城場景中執行大廳頁籤或路徑操作，並 MUST 將控制權交回地下城的合法擁有人。
- **Observable consequence**：地下城轉場或回退不會觸發大廳定位與點擊。
- **Allowed variation**：場景列舉、交接時機與處理器名稱可變更。
- **Verification**：`tests/test_dungeon_relaunch_recovery.py` 與 `tests/test_behavior_navigation.py`。

### Invariant 7：次級出戰與選關視窗防誤關保證 (Sub-panel Dismissal Protection Invariant)
- **Scope**：大廳次級出戰與選關視窗（如 Stage 關卡抽屜、Domain 出戰準備面板）之關閉控制項處理。
- **Rule**：主線導航在合法次級備戰或選關流程中，MUST NOT 僅因觀測到局部關閉控制項（`common/quit.png` / `ElementId.CLOSE_OVERLAY`）而派發 `DISMISS_OVERLAY`；在缺乏獨立阻擋性覆蓋層（`OverlayId`）證據時，系統 MUST 優先推進出戰或委派續行。
- **Observable consequence**：正常開啟之出戰抽屜與領地準備視窗不會因右上角關閉鈕被誤殺關閉。
- **Allowed variation**：判斷 predicate 名稱、受保護之 primary 模式集合與底層 SceneId 列舉可合理調整。
- **Verification**：`tests/test_behavior_navigation_table.py`。


---

## 3. 領域對稱規格：大廳 5 大頁籤對照表

大廳 5 大功能頁籤具備客觀對稱性，任一模板出現均為身處大廳 (`is_lobby=True`) 之客觀充分證據：

| 頁籤語意 | 未選中模板 (Inactive) | 選中模板 (Active / After) | Canonical SceneId | 歷史相容 SceneType |
| :--- | :--- | :--- | :--- | :--- |
| **普通關卡** | `common/select_stage.png` | `common/select_stage_after.png` | `SceneId.STAGE_SELECT` | `SceneType.LOBBY_STAGE` |
| **地下城** | `dungeons/dungeon.png` | `dungeons/dungeon_after.png` | `SceneId.DUNGEON_SELECT` | `SceneType.LOBBY_DUNGEON` |
| **禁域 (領地)** | `domains/Domains_entry.png` | `domains/Domains_entry_after.png` | `SceneId.DOMAIN_SELECT` | `SceneType.DOMAIN_SELECT` |
| **首領 (領主)** | `load/Lord_entry.png` | `load/Lord_entry_after.png` | `SceneId.LORD_SELECT` | `SceneType.LORD_SELECT` |
| **魔王 (魔神)** | `demon_lords/demon_lords_entry.png`| `demon_lords/demon_lords_entry_after.png`| `SceneId.DEMON_LORD_SELECT`| `SceneType.DEMON_LORD_SELECT`|

---

## 4. 責任邊界與禁止事項 (Boundaries & Anti-Patterns)

1. **🚫 嚴禁測試特化代碼滲入實作 (Zero Test Leakage)**：
   - 嚴禁在生產代碼中撰寫 `if isinstance(..., MagicMock)` 或 `if len(active) > 1: # 單元測試假象` 等特例。
   - 測試必須以真實遊戲世界的成對特徵進行 mock，維護真實契約。
2. **🚫 嚴禁使用 Priority 數值模擬控制流**：
   - 場景特徵具物理正交性，嚴禁在場景識別中引入 `priority: int` 數字互相踩踏。
   - 一律使用「特徵錨點 (`required_any`) + 排他守護 (`excluded_any`) + 信心度仲裁」進行聲明式識別。
3. **🚫 嚴禁在 Handler 中私自重新比對頁籤**：
   - Handler 必須直接消費 `scene_info.scene_type` / `snapshot.scene`，禁止在決策邏輯中私下呼叫 CV matcher 重複掃描。

---

## 5. 變更與廢止規範 (Supersession Rule)

若未來遊戲 UI 改版導致頁籤增減或視覺特徵重大變更：
1. 本契約的修改必須與 Production Code、聚焦測試在同一個 PR 中同步提交。
2. 任何變更必須附帶對應的單元測試，嚴禁在缺乏測試保護下單方面修改本契約。
