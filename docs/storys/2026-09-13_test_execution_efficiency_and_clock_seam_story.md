# 測試執行效率優化與時鐘接縫解耦開發故事 (PARS Story) 📜

---

## Purpose (背景與問題)

在先前的回歸測試中，專案完整單元測試套件（1087 tests）執行時間超過 **380 秒 (約 6.3 分鐘)**。長耗時主要源於測試執行期間對實體時間的無謂等待，包含：
1. `NavigationHandler` 中大量使用裸 `time.sleep()` 進行動畫沉澱、點擊間隔與防抖等待。
2. `ResultHandler` 在戰鬥結算與戰敗放棄流程中採用阻塞式 `time.sleep(1.5)` 及內部 `while` 迴圈輪詢。
3. 部分單元測試在測試案例中直接呼叫未解耦的真實等待邏輯。

本任務的目標是在**不降低測試覆蓋率、不修改可觀察業務行為、且生產端絕不引入 test-aware mock 嗅探邏輯**的前提下，透過引入時鐘依賴注入接縫（Clock Seam）與子流程 Tick 驅動化，顯著縮短全套測試執行時間。

---

## Action (實作行動與設計決策)

1. **擴充 `ClockPort` 契約與基類接縫**：
   - 於 [runtime/ports.py](../../runtime/ports.py) 的 `ClockPort` 協定中擴充 `sleep(self, seconds: float) -> None` 方法。
   - 於 [states/handlers/base.py](../../states/handlers/base.py) 提供 `_sleep()` 與 `_get_monotonic_time()` 輔助方法：生產環境走 `SystemClock`（真實等待維持不變），測試環境則可注入 [tests/support/fake_clock.py](../../tests/support/fake_clock.py) 的 `FakeClock`，使時間推進受控且無延遲。

2. **Phase A：`NavigationHandler` 時鐘接縫解耦**：
   - 盤點並將 [states/handlers/navigation.py](../../states/handlers/navigation.py) 中 26 處與時間間隔相關的裸 `time.sleep()` 遷移為 `self._sleep()`。
   - 維持既有導航後置條件驗證與超時重試機制不變。

3. **Phase B：`ResultHandler` Tick-Driven 子流程重構**：
   - 將 [states/handlers/result.py](../../states/handlers/result.py) 剛進入結算時的阻塞式 `time.sleep(1.5)` 遷移為非阻塞式計時狀態機步驟：`INIT_DELAY` ➔ `CONTINUE_LOOP` ➔ `FINAL_MATCH`。
   - 將戰敗連續達標後的放棄流程拆解為非阻塞 3-Tick 階段：
     - **Tick 1**：偵測並點擊放棄按鈕 (`defeat_giveup.png`) ➔ 轉入 `WAIT_GIVEUP_CONFIRM`。
     - **Tick 2**：偵測並點擊確認彈窗 (`common/confirm.png`) ➔ 轉入 `WAIT_GIVEUP_EXIT`。
     - **Tick 3**：驗證正向退出場景特徵（大廳/城鎮/領地）➔ 提交冷卻 side effects 並轉移回 `STATE_NAVIGATING`。
   - 調整業務邏輯順序：因戰敗定格畫面無需等待勝利金幣掉落動畫，將戰敗防護與擊殺事件廣播移至 `INIT_DELAY` 之前，避免戰敗場景產生不必要的沉澱等待。

4. **測試端契約適配與安全網補強**：
   - 編寫全新行為測試 [tests/test_behavior_result_tick_driven.py](../../tests/test_behavior_result_tick_driven.py)，全面驗證 `ResultHandler` 的子流程推進與超時保護。
   - 適配既有單元測試（`test_behavior_safety_and_battle_scenarios.py`、`test_behavior_collection_scenarios.py`、`test_behavior_dungeon_scenarios.py`），明確設置 Arrange 階段的子流程狀態，並驗證多 Tick 放棄流程。

---

## Result (實測數據與成果驗證)

由使用者執行全套測試套件（`discover tests`）驗證，成果如下：

| 評量指標 | 原始 Baseline | 初步 Seam (Nav) | 最終收斂 (Phase A+B) | 總體改善 |
| :--- | :--- | :--- | :--- | :--- |
| **全套測試耗時** | **380s+** (~6.3 分鐘) | **298.145s** (~5.0 分鐘) | **243.013s** (~4.0 分鐘) | **⬇️ 縮短約 137 秒 (-36%)** |
| **測試通過總數** | 1087 (1 Fail) | 1087 (OK) | **1092 (OK, 0 Fail, 14 Skipped)** | **✅ 100% 綠燈通過** |
| **新增行為測試** | - | - | +5 個完整行為測試 | 強化覆蓋 |
| **生產端 Test-Aware 痕跡** | - | - | **0 處** (嚴格遵循純依賴協定) | 符合架構規範 |

---

## So What (架構價值與效益)

1. **開發回饋迴圈大幅縮短**：全套測試從 6.3 分鐘降至 4.0 分鐘，單次完整迴歸驗證節省超過 2 分鐘，降低日後維護與重構的心理負擔與等待延遲。
2. **消弭隱性阻塞風險**：將 `ResultHandler` 內部阻塞輪詢徹底轉化為 Greenfield-lite 的「單次 Tick 感知 ➔ 單步動作 ➔ 返回狀態機」標準架構，避免因網路或遊戲卡頓導致主執行緒在結算中無法響應看門狗。

---

## Influence (後續規劃與注意事項)

1. **Profiling Hotspots 追蹤**：
   透過本次日誌間隙分析（`test_run.log`），提取出剩餘的實體時間等待 Hotspots（地下城寶箱逾時等待 ~12.6s、血祭壇 Phase 4 輪詢 ~16.0s、進程重啟 ~6.0s 等），已立項整理至 [test_profiling_hotspots_v3.md](../todos/test_profiling_hotspots_v3.md) 作為下一階段目標。
2. **地下城導航修復隔離**：
   開發期間發現之地下城路由不一致問題，已收斂為四階修復規格 [dungeon_bug.md](../todos/dungeon_bug.md)，嚴格未混入本次效能優化分支，後續將另立修復分支推進。
