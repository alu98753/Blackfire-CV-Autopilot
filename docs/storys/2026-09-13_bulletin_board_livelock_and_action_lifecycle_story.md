# 開發故事：懸賞告示牌開窗死鎖根治與動作生命週期契約 📋

> 日期：2026-09-13  
> 分支：`fix/bulletin-board-livelock`  
> 成果契約：[Precondition Contracts](../architecture/precondition_contracts.md), [Town Subflow Pipeline](../features/town_building/pipeline.md)  
> 關鍵模組：[states/handlers/bulletin_board.py](../../states/handlers/bulletin_board.py), [utils/bulletin_board_detector.py](../../utils/bulletin_board_detector.py), [tests/test_behavior_bulletin_board_settle.py](../../tests/test_behavior_bulletin_board_settle.py)  

---

## 1. Purpose (問題脈絡)

城鎮任務流水線在執行懸賞告示牌 (`bulletin_board`) 子流程時，出現兩處影響長時間掛機穩定度的關鍵問題：
1. **開窗未就緒誤殺與無界死鎖 (Livelock)**：
   - 點擊告示牌進入開窗過渡期時，因動畫尚未完成、僅比對到關閉按鈕 (`quit.png`) 而缺乏正向特徵，舊邏輯將其視為「干擾覆蓋層」立即點擊關閉。
   - 關閉後又判定未完成任務而重新點擊進店，造成「點進 ➔ 立即關閉 ➔ 再點進」的無限迴圈死鎖。
2. **重置按鈕無條件連點 (Consecutive Action Spam)**：
   - 進入告示牌介面後，點擊重置按鈕 (`reset.png`)，在遊戲 UI 渲染刷新期間（1~2 秒），下一個 frame tick 因按鈕尚未消失而立即發射第二次重複點擊。
   - 若重試達到上限，舊邏輯強行推進至任務接取流程，將操作失敗（`RESET_ACTION_FAILED`）偽裝成業務成功，導致後續接取未刷新的舊任務。
3. **排他特徵混淆**：
   - 舊邏輯使用 `common/tidy.png` 作為背包負向排他特徵，但在告示牌等介面同樣存在相似的整理圖示，造成誤判。

---

## 2. Action (關鍵架構行動)

依循 [Precondition Contracts](../architecture/precondition_contracts.md) 與 Greenfield-lite 架構準則，執行以下改動：

1. **落實開窗四互斥語意分類與感知決策分離**：
   - 在 [utils/bulletin_board_detector.py](../../utils/bulletin_board_detector.py) 中定義互斥語意：`BOARD_CONFIRMED`、`KNOWN_INTERFERENCE`、`UNKNOWN_OVERLAY`、`NO_OVERLAY`。
   - 決策模型嚴格僅依據局部 Scoped ROI 特徵比對；全螢幕與全尺度比對限制於診斷階段，並以開關 `run_full_diagnostics` 達成決策與診斷的計算成本分離。
2. **開窗有界沉澱窗口與冷卻退避階梯 (Anti-Livelock)**：
   - 點擊建築後引入 `BOARD_OPEN_SETTLE_TIMEOUT` 沉澱窗口，窗口內即使僅見 `quit.png` 亦不誤殺彈窗。
   - 連續未達成開窗時設有 `MAX_OPEN_ATTEMPTS` 上限，超限後調用 `defer_subflow` 進入冷卻退避並讓渡城鎮佇列，徹底根絕無界重試。
3. **背包排他特徵正交化**：
   - 廢除 `common/tidy.png` 作為背包排他證據，改以背包專屬的 `common/Disassembly.png` 為排他錨點。
4. **重置按鈕 Bounded Click-Observe-Retry 契約**：
   - 重置按鈕遵循「點擊 ➔ 沉澱等待 ➔ 有界重試 ➔ 失敗升級退避」生命週期：
     - 點擊後於 `RESET_CLICK_RETRY_INTERVAL` 窗口內嚴禁連點。
     - 窗口結束若按鈕仍在，允許有界重試（最多 `MAX_RESET_CLICK_ATTEMPTS` 次）。
     - 重試預算耗盡時嚴禁偽裝成功，必須調用 `_defer_and_yield` 進入冷卻退避。
5. **架構不變量升格至 Canonical Contract**：
   - 於 [docs/features/town_building/pipeline.md](../features/town_building/pipeline.md) 正式增補「懸賞告示牌子流程契約」，固化感知分類、Scoped 決策、動作生命週期與失敗升級四大架構不變量。

---

## 3. Result (驗證結果)

- **實機運行時序驗證**：
  - 實機日誌確認開窗進入告示牌後，重置點擊由原先的秒級連點收斂為標準沉澱等待與推進：
    ```text
    58.763 click reset attempt 1/3
    59.xxx settle，處於沉澱等待窗口，不重複點擊
    60.xxx settle，處於沉澱等待窗口，不重複點擊
    61.xxx reset 成功消失（UI 刷新完成）➔ 自然推進至 PROCESS_ACCEPT_QUESTS
    ```
- **單元與子流程測試覆蓋**：
  - [tests/test_behavior_bulletin_board_settle.py](../../tests/test_behavior_bulletin_board_settle.py)：20 項測試全數通過（涵蓋開窗沉澱、四分類語意、診斷成本分離、重置有界重試、重試超限退避）。
  - [tests/test_bulletin_board_subflow.py](../../tests/test_bulletin_board_subflow.py)：7 項子流程整合測試全數通過。
  - [tests/test_behavior_bag_and_daily_decoupling.py](../../tests/test_behavior_bag_and_daily_decoupling.py)：5 項解耦測試全數通過。
- **全套測試迴歸驗證**：
  - 1110 項全套測試驗證完成，本分支引入之 regression 為 0 項。

---

## 4. So What (架構價值)

1. **消滅城鎮佇列中的假性死鎖與連點**：
   - 將開窗動畫過渡期與按鈕渲染延遲納入標準沉澱窗口管轄，杜絕了高頻重複發射動作與誤殺彈窗。
2. **落實「動作失敗不得偽裝成功」之品質底線**：
   - 確立了重試超限即為操作失敗（Failure），必須由冷卻退避（Defer）或讓渡（Yield）承接，防止帶病推進後續業務。
3. **契約歸檔與文件收斂**：
   - 提煉高階不變量進入長效契約，安全清理臨時 spec，維持專案文件的單一真相與高內聚。
