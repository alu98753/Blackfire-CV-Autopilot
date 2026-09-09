# 關卡懸賞 final 誤點 middle 修復故事（PARS Framework）

## Problem（問題）

Daily 動態調度「清除野豬」時，任務規則正確映射到第一大關的 `final`，但產生配置時從 `[primary_modes.stage]` 複製了 `tier4_sub_stage="six"`。導航判斷又優先讀取 Tier 4 欄位，因此把真正的 `final` 忽略，直接接受第一頁共用的 `boss_skull.png`，未先向下滑到第二頁。

## Action（行動）

1. `TaskNode.to_config_dict()` 在建立具體關卡懸賞 route 時移除 `tier4_stage_level` 與 `tier4_sub_stage`，讓 Tier 4 保持為 fallback 政策。
2. `NavigationHandler` 集中解析小關提示，固定讓當前 route 的 `sub_stage` 優先於 `tier4_sub_stage`，防守舊配置與外部組裝配置。
3. 新增真實 `QuestMapper` 與 Stage Profile 衝突情境的回歸測試，並驗證 final 在第一頁會拒絕骷髏頭、執行向下滑動。

## Result（結果）

- 「清除野豬」產出的配置只保留 `stage_level=1`、`sub_stage=final`，不再混入 Tier 4 的選關欄位。
- 第一頁的 middle 骷髏頭不會被點擊；導航會向下滑，第二頁的 final 骷髏頭仍可正常點擊。
- 新增的 2 項回歸測試，以及既有 middle/final 導航與 QuestMapper 相容性測試皆通過。

## So What（核心價值）

具體任務 route 與長駐 fallback 政策有了清楚邊界。未來玩家更換 Tier 4 大關或小關，不會改變 Daily 懸賞本身指定的關卡，也避免共用骷髏模板造成跨頁誤點。
