# 開發故事：城鎮建築出口正規化與錯位讓渡協定 🏛️

> 日期：2026-09-14  
> 分支：`fix/town-building-egress-normalization`  
> 成果契約：[Town Subflow Pipeline](../features/town_building/pipeline.md) (Section 9 & Section 10)  
> 關鍵模組：[states/handler_mislocation_guard.py](../../states/handler_mislocation_guard.py), [states/reach_town_normalization.py](../../states/reach_town_normalization.py), [states/town_subflow_navigation.py](../../states/town_subflow_navigation.py), [states/town_subflow_perception.py](../../states/town_subflow_perception.py), [states/handlers/jewelry_workshop.py](../../states/handlers/jewelry_workshop.py), [states/handlers/chest.py](../../states/handlers/chest.py), [states/handlers/bulletin_board.py](../../states/handlers/bulletin_board.py), [states/handlers/bag_tidy.py](../../states/handlers/bag_tidy.py), [states/handlers/blood_altar.py](../../states/handlers/blood_altar.py), [states/handlers/hero_draw.py](../../states/handlers/hero_draw.py)

---

## 1. Purpose (問題脈絡)

城鎮子流程在長期無人值守掛機環境中，暴露了數項與場景邊界、動作生命週期及錯誤恢復相關的系統性脆弱點：

1. **建築退出同幀偽就緒**：
   - 珠寶工坊（`jewelry_workshop`）等建築在點擊退出按鈕後，未等待畫面渲染回到城鎮，即在同一個 frame tick 判定退出完成並讓渡狀態機。
   - 後續子流程立即啟動，將建築內部的殘留畫面誤判為城鎮，引發連續點偏與場景混亂。
2. **誤入建築時懲罰性消耗業務 Intent**：
   - 當機器人因畫面微幅位移或點偏誤入非目標建築時，各業務 Handler（如 `BagTidyHandler`、`BulletinBoardHandler`、`ChestHandler`）因無法識別自身專屬特徵，最終因操作超時觸發冷卻退避（`defer_subflow` 凍結 180 秒），甚至直接調用 `pop_and_next_town_subflow()` 將未執行的任務從佇列中移除。
   - 誤點偏屬於瞬時物理導航偏差，但懲罰卻落在業務 Intent 本身，導致日常懸賞任務接取或背包清理被非預期跳過。
3. **特徵語意混淆（通用特徵 vs 專屬特徵）**：
   - 既有邏輯常將通用建築退出按鈕特徵（`exitfromhouse_and_to_town.png`）誤當作特定建築的專屬內部證據，導致 Handler 無法正確辨識當前是否身處「非己建築」。
4. **登入世界就緒與城鎮就緒邊界混淆**：
   - 登入流程（`states/login_flow.py`）與地牢重啟流程曾隱含「重啟完成必須回到城鎮」的假設，造成在地牢戰鬥中重啟時被強制拉回城鎮，中斷進行中的地牢輪轉。
   - 城鎮就緒判定僅依賴 `door.png`（城門位置特徵），缺乏無遮擋互動錨點（`arena_of_glory.png`）的乾淨度驗證，常在彈窗或遮擋層尚未消退時即發射建築點擊。

---

## 2. Action (關鍵架構行動)

依循架構分層規範，以狀態驅動與感知決策分離為核心，實施全面正規化：

1. **城鎮位置特徵與互動就緒解耦 (Town Location vs Interaction Readiness)**：
   - 在 [states/town_subflow_perception.py](../../states/town_subflow_perception.py) 與 [states/town_subflow_navigation.py](../../states/town_subflow_navigation.py) 中，確立 `door.png` 僅代表「身處城鎮空間（Location）」，`arena_of_glory.png` 則作為「畫面乾淨無遮擋可互動（Interaction Readiness）」的排他錨點。
   - 提出三態就緒模型：
     - `READY`：同時具備 Location 與 Anchor，方允許觸發建築入口點擊。
     - `UNKNOWN`：僅具備 Location 但缺乏 Anchor（可能處於彈窗淡入或遮擋中），進入有界重測窗口。
     - `FAILURE`：超時未就緒時安全讓渡，且失敗不得懲罰性推遲或移除 Intent。
2. **建築退出生命週期有界驗證 (Bounded Egress Verification)**：
   - 廢除點擊退出按鈕即視為完成退出的假設。在各建築 Handler 中引入明確的退出確認階段（如 `VERIFY_EXIT`），必須持續觀察到城鎮特徵（`door.png`）且建築專屬特徵消失後，方完成退出生命週期並讓渡實體。
3. **通用建築內部特徵明確化與 MislocationGuard 讓渡協定**：
   - 正式將 `exitfromhouse_and_to_town.png` 定義為「全域通用建築內部特徵」，嚴禁任何 Handler 將其作為自身專屬證據。
   - 建立 [states/handler_mislocation_guard.py](../../states/handler_mislocation_guard.py)：當偵測到通用內部特徵、且確認缺乏自身專屬特徵時，透過有界連續幀（預設連續 2 幀）防抖確認，判定為「誤入外宿建築（Mislocation）」。
   - **讓渡契約核心**：判定誤入後，Handler 必須釋放實體所有權給城鎮正規化控制器（`REACH_TOWN`），**嚴格禁止調用 `defer_subflow`、`pop_and_next_town_subflow` 或完成 Intent**。當前 Intent 必須保持原樣未消費狀態，待回到城鎮後重新分發。
   - 依序將讓渡協定整合至 `ChestHandler`（新增 `VERIFY_ENTRY` 階段）、`HeroDrawHandler`、`BloodAltarHandler`、`BagTidyHandler`、`BulletinBoardHandler`、`JewelryWorkshopHandler`。
4. **登入世界就緒邊界收斂 (World-Ready Boundary)**：
   - 規範登入與重啟（`states/login_flow.py`、`supervisor`）之職責僅限於抵達已知合法世界場景（`WORLD_READY`）。若重啟後處於 `IN_DUNGEON`，地牢狀態機保留所有權繼續執行；僅有真正需要城鎮的下游消費者才發起 `REACH_TOWN` 正規化。
5. **長效契約提煉與過期規格清理**：
   - 於 [docs/features/town_building/pipeline.md](../features/town_building/pipeline.md) 正式增補 Section 9（城鎮位置與退出正規化契約）與 Section 10（誤入建築防護與讓渡協定），收斂為長效架構規範。
   - 遵循「刪除是預設；封存是例外」準則，安全刪除過期實作計畫（`Town Building Egress Normalization Fix Spec.md` 與 `Verify Town Building Egress Normalization Fix Spec.md`），維持專案單一真相源。

---

## 3. Result (驗證結果)

1. **行為與領域測試覆蓋**：
   - [tests/test_behavior_handler_mislocation_relinquish.py](../../tests/test_behavior_handler_mislocation_relinquish.py)：24 項測試全數通過（涵蓋全部 6 個 Handler 在誤入建築時的兩幀防抖確認、保留 Intent、安全讓渡至 `REACH_TOWN` 之端到端行為）。
   - [tests/test_behavior_reach_town_normalization.py](../../tests/test_behavior_reach_town_normalization.py)：13 項測試全數通過（涵蓋城鎮三態就緒判定、錨點排他驗證、連續失敗閉鎖）。
   - [tests/test_behavior_login_and_town_boundary_regression.py](../../tests/test_behavior_login_and_town_boundary_regression.py)：13 項測試全數通過（驗證地牢重啟保持與下游按需回城契約）。
   - [tests/test_behavior_jewelry_workshop_rotation.py](../../tests/test_behavior_jewelry_workshop_rotation.py)：更新退出驗證邏輯，多幀退出確認測試全數通過。
2. **全套測試迴歸驗證**：
   - 本地全套測試（包含所有業務模組與狀態機）共 1165 項測試全數通過：
     ```text
     Ran 1165 tests in 234.431s
     OK (skipped=14)
     ```
   - 迴歸測試結果確認：Genuine Regression 數量為 0。
3. **程式碼與文檔潔淨度**：
   - 完成 production code 潔淨度審計，無殘留臨時 WIP/Spec 標籤。
   - 兩份過期實作計畫安全清除，長效規則完整沉澱至 canonical contract。

---

## 4. So What (架構價值)

1. **根治瞬時導航微偏導致的業務意圖丟失**：
   - 將「導航失敗」與「業務執行失敗」徹底分離。點偏入錯建築不再導致懸賞或背包整理被吞掉，系統具備自動退出回城並重試的原生自我修復能力。
2. **消滅同幀退出假象，確立視覺感知時序對齊**：
   - 強制執行退出確認窗口，確保下一個動作發起時遊戲畫面已確實處於目標場景，消除因時序不同步引發的連鎖誤判。
3. **確立世界就緒與場景就緒的分層邊界**：
   - 釐清全域登入生命週期（`WORLD_READY`）與局部業務就緒（`TOWN_READY`）的權責劃分，保護跨子系統（如地牢重啟）的獨立性與上下文延續性。
