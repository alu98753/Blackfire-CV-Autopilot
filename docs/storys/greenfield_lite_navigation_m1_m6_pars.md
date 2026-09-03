# Greenfield-lite navigation M1–M6

## Purpose

修正 Diamond、Bread、Start 與未知懸賞任務各自改寫狀態造成的活鎖，並為 24/7 掛機建立低負載、有上限且可恢復的導航核心。

## Action

- 建立 immutable `SceneSnapshot`、唯一 `ActiveIntent`、純 `ActionDecision` 與固定 `NavigationTable`。
- 讓 `NAVIGATING`／`LOBBY` 共用 Diamond → Bread → Primary precedence，並保護已提交的 Start。
- 加入單一 `InFlightAction`、postcondition、TOML-only timeout／backoff／recovery limit。
- collection 失敗改為 defer 並保留 pending；success 或 cooldown evidence 才完成。
- 建立 scoped `DetectorRegistry` 與單幀 match cache，先套用明確的 Lobby control phase。
- 以 Capture／Input／Clock／Process ports 包住既有 adapter，所有最終重啟沿用 `GameRelaunchSubflow`。

## Result

固定導航 edge 只有一個決策 owner；Bread／Diamond 不會被 unknown Quest fallback 清除，collection 與 Start 的點擊在驗證前不會重複發出下一個業務動作。連續無進展、截圖失敗與戰鬥 hard timeout 都能走同一個 process recovery 邊界。

## So What

這個切片直接消除原事故中的 `NAVIGATING ↔ LOBBY` 無進展切換，並以有限 detector 工作集與 frame-local cache 降低重複 CV。設計保持在專案目前規模需要的程度，沒有引入 Event Bus、Reducer、Statechart framework、動態任務排序或戰鬥策略。

## Influence

完整 greenfield 文件保持不變。後續遷移以現有 contracts 為邊界，逐一將 Stage、Dungeon、Loading、Battle、Result 與 collection phase 改為只消費 snapshot；在完成 metrics 與移除 legacy direct matcher 前，不宣稱完整 v1 migration 全數完成。
