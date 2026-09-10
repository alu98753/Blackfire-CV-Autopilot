# 每日懸賞任務優先於常規地下城調度修復故事（PARS Framework）

## Purpose & Problem（背景與問題）

使用者在 `--mode daily` 下接完 8 項每日懸賞任務後，期望系統優先執行懸賞任務（做任務升級與領取每日獎勵），然而系統卻在大廳直接切換至 Tier 4 常規貪婪地下城（如冰雪洞窟、獸人地堡）。

經過端到端追蹤與架構審視，定位出兩大根本原因：
1. **城鎮前置條件退避未釋放 (Precondition Livelock)**：領體力逾時退避（連續 3 幀未見按鈕）時，未能清除 `need_bread_collection = False`，且 `TownSubflowPreconditionController._collection_pending()` 每一幀均回傳 `True`，阻塞城鎮大門導航；導致待辦城鎮子流程卡在隊首，高層 `evaluate_next_activity()` 提早返回，懸賞任務 (Tier 3) 無法被派發。
2. **底層導航越權搶跑 (Navigation Layering Violation)**：在城鎮子流程前置條件期間，配置保留 daily 基準配置（底層 `type: "mix"`）；[NavigationHandler](../../states/handlers/navigation.py) 看到 `type == "mix"` 且地下城有空位，擅自於活動大廳點擊 `dungeons/dungeon.png` 切換頁籤，越權發起 Tier 4 常規地下城。

## Action（行動）

依據 [project_arch_greenfield_lite_v1.md](../architecture/project_arch_greenfield_lite_v1.md) 與 [precondition_contracts.md](../architecture/precondition_contracts.md)，分三階段徹底收斂架構邊界：

1. **Phase 1: 退避狀態清理與 Precondition Defer 感知**
   - 在 [bread_collection.py](../../states/handlers/bread_collection.py) 與 [diamond_collection.py](../../states/handlers/diamond_collection.py) 逾時退避時，同步重設 `need_bread_collection = False` 與 `need_diamond_collection = False`。
   - 在 [town_subflow_navigation.py](../../states/town_subflow_navigation.py) 的 `_collection_pending()` 增加 `not progress.is_deferred(...)` 防禦，處於 DEFER 退避期間不再阻斷城鎮前置條件。

2. **Phase 2: 剝離 NavigationHandler 越權 Selection**
   - 在 [NavigationHandler](../../states/handlers/navigation.py) 混合模式頁籤切換前，引入 `allow_mix_tab_switching = (not is_managed_daily) or is_tier4_fallback` 守衛。在 Daily 大流水線受管模式下，非 Tier 4 退守狀態嚴禁擅自切換大廳頁籤，嚴格服從當前 `navigation_path`。

3. **Phase 3: 狀態機 Tier 1 ~ Tier 4 優先級契約收斂**
   - 在 [state_machine.py](../../states/state_machine.py) 的 `evaluate_next_activity()` 中：
     - 若 `has_pending_town_subflow()` 為真，立即維持 Tier 1 活躍，不洩漏至後續層級。
     - 若 `quest_scheduler` 存在且有未冷卻任務，唯一合法動作為派發 Tier 3 懸賞任務。
     - 僅在懸賞任務全冷卻時，才顯式套用 `apply_tier4_fallback_config()`，打上 `is_tier4_fallback = True` 並武裝 `arm_daily_quest_preemption()`。

## Result（結果）

- 所有修改聚焦於架構分層與責任邊界，未增加任何臨時補釘。
- 執行業務領域聚焦測試全部通過：
  - `tests.test_town_subflow_precondition_navigation`: 30/30 OK
  - `tests.test_behavior_navigation`: 26/26 OK
  - `tests.test_behavior_daily_tier4`: 26/26 OK
  - `tests.test_behavior_daily_preemption`: 10/10 OK
  - `tests.test_behavior_town_subflows`: 5/5 OK
  - 總計 97 個單元測試 100% 綠燈通過。

## So What（核心價值）

- **階層職責分明**：Selection（任務選擇）100% 由狀態機核心調度器收斂，底層導航僅專注於執行路徑點擊，解決了底層 Handler 越權搶跑的架構隱患。
- **排程優先級確定**：確立了 `Tier 1 (城鎮速領) > Tier 2 (首領討伐) > Tier 3 (每日懸賞) > Tier 4 (常規退守)` 的絕對階梯，保障玩家接完懸賞任務必定優先完成任務。

## Influence（影響範圍）

- `states/handlers/bread_collection.py`
- `states/handlers/diamond_collection.py`
- `states/town_subflow_navigation.py`
- `states/handlers/navigation.py`
- `states/state_machine.py`
- `tests/test_town_subflow_precondition_navigation.py`
- `tests/test_behavior_navigation.py`
- `tests/test_behavior_daily_tier4.py`
