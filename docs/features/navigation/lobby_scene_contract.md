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

任何未來的程式碼重構或新增功能，**必須永久滿足以下 4 大核心不變量**，違反任一項皆視為系統性退化 (Regression)：

### Invariant 1：成對差值主導保證 (Active-Dominance Invariant)
- **原則**：大廳按鈕具有選中態 (`Active / After`) 與未選中態 (`Inactive`)。選中態圖標常因光暈相似而在未選中畫面上產生高信心度假陽性（幽靈匹配）。
- **保證**：任何頁籤欲被判定為選中 (`Active`)，其 $c_{\text{active}}$ 必須**嚴格顯著高於**未選中態 $c_{\text{inactive}}$。若未選中態分數高於選中態，系統**保證堅決撤銷選中態**，絕不產生幽靈假陽性。

### Invariant 2：保守仲裁保證 (Conservative Disambiguation Invariant)
- **原則**：畫面可能受切換動畫、光影特效或外部干擾。
- **保證**：
  1. 當且僅當單一頁籤明確 Active，或最高信心度頁籤**顯著領先**次高者時，由優勢者勝出。
  2. 若複數頁籤同時宣稱 Active 且差距過小，系統遵循 Greenfield-lite 保守原則「**證據衝突時拒絕盲目猜測**」，**保證退回 `SceneId.LOBBY` (`LOBBY_OTHER`)**，等待下一幀畫面穩定。

### Invariant 3：大廳無大門導航保證 (No-Door in Lobby Invariant)
- **原則**：角色身處大廳內部時，客觀物理世界中絕無在大廳中尋找城門之可能。
- **保證**：
  1. 當確認身處大廳（`is_lobby=True` 或偵測到大廳特徵錨點）時，導航路徑過濾 (`filter_navigation_path`) **保證強制剃除 `common/door.png`**。
  2. 系統絕不在大廳內部將任何拱形裝飾或按鈕誤認為大門而觸發誤點擊。

### Invariant 4：純領域契約與單一真相保證 (Pure Domain & Single Truth Invariant)
- **原則**：決策層（Handlers / Preconditions / Intents）只消費不可變快照與領域型別，不應跨層持有視覺匹配器。
- **保證**：
  1. **`SceneId` 是全系統唯一 Canonical Truth**。
  2. 領域契約模組 [utils/scene_types.py](../../../utils/scene_types.py) **保證零 OpenCV、零 Matcher 依賴**，可被任何上層決策模組安全引用。

### Invariant 5：兩階段感知與預期頁籤最小化保證 (Two-Tier Perception & Expected Tab Invariant)
- **原則**：大廳穩態導航、卡片拖曳與頁籤滑動過程中，系統已由導航決策層明確獲知當前目標頁籤。
- **保證**：
  1. 當導航請求提供明確的 `expected_tab` 時，系統**保證僅比對該目標頁籤之一對 active/inactive 模板**（TemplateMatcher 呼叫次數 $\le 2$），嚴禁在穩態下重複掃描全量 10 模板造成畫面嚴重停頓。
  2. 若目標頁籤之成對檢驗未命中（兩者皆 miss），系統**保證自動升級至有界全局重定位 (`FULL_RELOCALIZE`)**，重新掃描 5 大頁籤並進行最大信心度仲裁，杜絕迷航。
  3. 頁籤感知與卡片 fallback 行為解耦：僅在全局重定位下允許降級至卡片推斷，在已知頁籤的快速感知下不執行多餘卡片推斷。

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
