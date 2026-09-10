# RFC: 全專案命名統一與徹底廢除 `SceneType` 別名 (Unify to SceneId & Deprecate SceneType) 📌

> 狀態：待排期提案 (Pending RFC)  
> 關聯契約：[Lobby Scene Contract](../features/navigation/lobby_scene_contract.md)  
> 領域模型：[utils/scene_types.py](../../utils/scene_types.py)  
> 建立日期：2026-09-10  

---

## 1. 背景與動機

在歷史演進中：
- 舊架構使用 `SceneType.LOBBY_STAGE` 與 `SceneType.LOBBY_DUNGEON`，而新擴充的頁籤使用了 `DOMAIN_SELECT`、`LORD_SELECT`、`DEMON_LORD_SELECT`。
- 在 Greenfield-lite 架構中，標準化為 `SceneId.STAGE_SELECT`、`SceneId.DUNGEON_SELECT` 等正規名稱。
- 在 `fix/lobby-tab-scene-detection` 分支中，我們已在 [utils/scene_types.py](../../utils/scene_types.py) 將 `SceneId` 立為全系統唯一的領域契約實體，並透過 `SceneType = SceneId` 宣告與屬性別名（`LOBBY_STAGE = STAGE_SELECT`, `LOBBY_DUNGEON = DUNGEON_SELECT`）在底層實現了 1:1 零阻抗映射。

然而，專案中既有的數十個 Handlers、FSM 與測試檔案中仍散落著舊名稱 `SceneType.LOBBY_STAGE` 與 `SceneType.LOBBY_DUNGEON` 的字面引用。本 RFC 旨在未來進行全域純語法重命名，達成乾淨單一的命名空間。

---

## 2. 待辦工作清單 (TODO Roadmap)

### TODO 1: 全專案業務程式碼遷移至正規 `SceneId`
- 開立獨立重構分支 `refactor/unify-scene-type-enums` (或 `refactor/unify-to-scene-id`)。
- 將 `SceneType.LOBBY_STAGE` 統一更名為 `SceneId.STAGE_SELECT`。
- 將 `SceneType.LOBBY_DUNGEON` 統一更名為 `SceneId.DUNGEON_SELECT`。
- 將所有 Handlers（`navigation.py`, `town.py`, `battle.py` 等）中的 `SceneType.XXX` 批次替換為正規的 `SceneId.XXX`。
- 將 `SceneInfo.scene_type` 屬性更新（或提供 property 橋接）為 `SceneInfo.scene_id`。

### TODO 2: 單元測試全數對齊 `SceneId`
- 將全套測試案例中的 `SceneType.LOBBY_STAGE` / `SceneType.LOBBY_DUNGEON` 替換為 `SceneId.STAGE_SELECT` / `SceneId.DUNGEON_SELECT`。
- 將斷言中的 `SceneType` 統一替換為 `SceneId`。

### TODO 3: 徹底廢除並移除 `SceneType = SceneId` 別名 (Deprecate & Remove Alias)
- 在完成所有模組遷移後，正式自 `scene_snapshot.py` 中移除歷史遺留的 `_SCENE_TYPE_MAP` 字典。
- 自 `utils/scene_types.py` 與 `utils/scene_detector.py` 中徹底刪除 `SceneType` 別名以及舊相容屬性（`LOBBY_STAGE`, `LOBBY_DUNGEON`），實現完全乾淨、唯一的 `SceneId` 命名空間。
