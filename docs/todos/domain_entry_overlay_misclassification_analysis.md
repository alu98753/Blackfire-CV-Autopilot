# 領地與大廳覆蓋層誤判關閉問題分析 (domain_entry_overlay_misclassification_analysis.md)

## 1. 問題概述與現象描述

在日常掛機與領地探索（如黃金古國 `golden_empire`）的導航過程中，觀察到類似普通關卡（Stage）子抽屜的誤關閉行為：
系統順利點擊領地分頁入口（`domains/Domains_entry.png`）或領地卡片（`domains/golden_empire/entry.png`）後，畫面彈出出戰準備視窗；此時本應點擊啟動按鈕（如 `domains/common/start_btn.png`）進入探索，系統卻優先辨識並點擊了視窗右上角的退出按鈕（`common/quit.png`），將準備視窗關閉，導致探索進場失敗並陷入「點開 ➔ 關閉 ➔ 再點開」的重複循環。

此現象在機制上與已修復的 Stage Select 誤關閉屬於同一架構根因，但牽涉到領地特有的模板契約與意圖表宣告邊界。

---

## 2. 根本原因剖析 (Root Cause Analysis)

經比對 [NavigationHandler](../../states/handlers/navigation.py)、[NavigationRouting](../../states/navigation_routing.py)、[NavigationTable](../../states/navigation_table.py) 與 [defaults.toml](../../config/defaults.toml)，確認該問題是由以下三重缺陷疊加所致：

### 缺陷 A：大廳覆蓋層邊過度泛化 (`LOBBY + CLOSE_OVERLAY ➔ DISMISS_OVERLAY`)

在 [states/navigation_table.py](../../states/navigation_table.py#L162-L169) 中，`PRIMARY_NAVIGATION` 在 `SceneId.LOBBY` 場景保留了以下邊：

```python
NavigationEdge(
    IntentId.PRIMARY_NAVIGATION,
    SceneId.LOBBY,
    SceneId.LOBBY,
    ElementId.CLOSE_OVERLAY,  # common/quit.png
    ActionId.DISMISS_OVERLAY,
    PostconditionId.OVERLAY_CLOSED,
    ReasonCode.PRIMARY_CLOSE_OVERLAY,
)
```

遊戲 UI 中，不論是普通關卡抽屜、地下城卡片、領地出戰視窗或首領討伐卡片，只要是在大廳介面上浮現的次級面板，其右上角大多原生帶有 `common/quit.png`。
若場景感知輸出為 `SceneId.LOBBY`（或 `SceneType.LOBBY_OTHER`），只要畫面上露出 `common/quit.png`，意圖表即認定為「畫面存在遮擋覆蓋層」，直接派發 `ActionId.DISMISS_OVERLAY` 發起點擊。

### 缺陷 B：開始按鈕模板契約脫節 (`lobby_start_btn` 預設值與領地不一致)

在 [states/navigation_routing.py](../../states/navigation_routing.py#L145) 的上下文構建中：

```python
start_template = (machine.config or {}).get("lobby_start_btn", "stages/start.png")
```

而在 [config/defaults.toml](../../config/defaults.toml#L123-L130) 的 `[primary_modes.domain]` 配置中：
- 導航路徑為：`["common/door.png", "domains/Domains_entry.png", "domains/golden_empire/entry.png", "domains/common/start_btn.png"]`
- 領地開始探索按鈕為：`domains/common/start_btn.png`
- **配置中未定義 `lobby_start_btn`**，故系統回退使用預設值 `"stages/start.png"`。

這導致在 [utils/scene_snapshot.py](../../utils/scene_snapshot.py#L144-L145) 的元素映射中：
- 只有 `"stages/start.png"` 會被轉譯為 `ElementId.START`。
- 領地畫面的 `"domains/common/start_btn.png"` **無法被映射為 `ElementId.START`**。
- 結果：在領地出戰面板中，`scene.has(ElementId.START)` 永遠為 `False`，而 `scene.has(ElementId.CLOSE_OVERLAY)` 卻為 `True`。

### 缺陷 C：意圖表缺少領域選取邊 (`DOMAIN_SELECT` / `LORD_SELECT`)

在 [states/navigation_table.py](../../states/navigation_table.py#L143-L160) 的 `START_PRIMARY` 宣告中：
- 僅宣告了 `LOBBY`、`STAGE_SELECT`、`DUNGEON_SELECT` 轉移至 `LOADING`。
- 完全未宣告 `SceneId.DOMAIN_SELECT` 或 `SceneId.LORD_SELECT` 的 `START` 邊。
若 `SceneDetector` 將頁籤正確識別為 `DOMAIN_SELECT`，系統亦無任何原生 Edge 可供推進，只能落入 `PRIMARY_ROUTE_DELEGATED` 的通用尋路逆序比對。

---

## 3. 架構意涵與對齊方向 (Greenfield-lite Principles)

此問題進一步印證了先前的架構診斷：

1. **存在性判定 (WHAT) 與點擊座標 (WHERE) 倒置**：
   - 目前以 `common/quit.png` 直接等同於 `ElementId.CLOSE_OVERLAY`，是「看見關閉按鈕」即反推「有需要關閉的彈窗」。
   - 正確模型應為：由畫面整體特徵確認存在阻擋性 Overlay（例如 `OverlayId.DUNGEON_COOLDOWN`、`OverlayId.TASK_COMPLETE`），決策執行 `DISMISS_OVERLAY` 時，才將 `common/quit.png` 當作發射點擊的座標位置。
2. **遵守 Greenfield-lite 原則，嚴禁 FSM State 爆炸**：
   - 不得為了解決此問題而新增 `DOMAIN_DRAWER`、`LORD_DRAWER` 等過度細碎的 SceneId。
   - 保持主場景與 Overlay 的正交分離，是維持狀態機精簡與穩定的關鍵。

---

## 4. 具體修復方案規劃 (Actionable Roadmap)

### 短期修正 (Short-term Bugfix)
1. **配置契約對齊**：
   於 `config/defaults.toml` 的領地配置與狀態機設定中，補齊 `lobby_start_btn = "domains/common/start_btn.png"`，或在 `resolve_navigation_context` 中依據當前 active mode / `navigation_path` 解析開始按鈕模板。
2. **審查 `LOBBY` 的 `DISMISS_OVERLAY` 邊**：
   檢視 `SceneId.LOBBY` 是否有保留 `CLOSE_OVERLAY ➔ DISMISS_OVERLAY` 的必要性。若保留，必須收緊觸發條件（例如排除出戰準備視窗）。

### 中期解耦 (Medium-term Architectural Hardening)
1. **落實 `OverlayId` 感知**：
   在 `SceneDetector` 中針對遮擋性彈窗（如冷卻提示彈窗）建立客觀特徵比對，寫入 `SceneSnapshot.overlays`。
2. **意圖表僅對明確 Overlay 派發關閉**：
   將 Navigation Table 中的邊由「依賴 `ElementId.CLOSE_OVERLAY`」遷移為「依賴 `OverlayId.xxx` 存在」，徹底根除所有大廳次級視窗被誤關閉的系統性隱患。
