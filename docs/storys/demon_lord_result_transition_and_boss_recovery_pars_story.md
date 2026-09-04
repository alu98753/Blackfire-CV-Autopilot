# PARS Story: 深淵魔王結算跳轉、領域卡片對齊協定與防呆計數器單一真理源重構

## Purpose
在日常自動化掛機過程中，系統遭遇了數個關鍵導航與子流程卡頓問題：
1. **深淵魔王戰鬥結算與離場卡死**：戰鬥結束後的經驗與獎勵畫面未能及時跳轉至 `STATE_RESULT`，且在魔王次數耗盡離場時未正確核銷日常流水線，造成無窮迴圈重試。
2. **黃金帝國領域與首領討伐退場導航迷失**：黃金帝國場景未能精確識別，首領討伐退場後的大廳路由中斷。
3. **卡片對齊協議缺乏單一真理源與頁籤守門員**：過去卡片列表在未確認當前頁籤已正確選中時即盲目發動滑動拖曳，且導航重試上限在單幀頁籤漏判時會意外歸零，造成無限滑動。
4. **雙重計數狀態技術債**：地下城防呆拉回使用舊有的 `self.machine.fallback_swipe_count`，而通用卡片對齊使用 `card_alignment_attempts`，造成狀態不一致與維護困擾。

本重構旨在為戰鬥結算、領域探索、卡片對齊建立清晰且具備自癒防護的閉環契約，並徹底清理雙重狀態技術債。

## Action
1. **深淵魔王與首領討伐結算離場自癒**：
   - 於 [states/handlers/battle.py](../../states/handlers/battle.py) 與 [states/handlers/result.py](../../states/handlers/result.py) 完善戰鬥結算畫面辨識與狀態流轉契約。
   - 於 [states/handlers/demon_lords.py](../../states/handlers/demon_lords.py) 與 [states/handlers/lord_boss.py](../../states/handlers/lord_boss.py) 強化多魔王循序挑戰與退場後置條件核驗。
2. **領域探索與雙態頁籤互斥感知**：
   - 新增 [templates/domains/Domains_entry_after.png](../../templates/domains/Domains_entry_after.png) 範本，結合既有之 `Domains_entry.png` 納入雙態互斥頁籤機制。
   - 擴充 [utils/scene_detector.py](../../utils/scene_detector.py) 與 [utils/scene_catalog.py](../../utils/scene_catalog.py)，確保必須在雙態互斥比對確認頁籤選中後方認定進入特定選關畫面，徹底杜絕紅框雜訊誤判。
3. **跨幀保留卡片對齊重試計數與有界自癒**：
   - 在 [states/handlers/navigation.py](../../states/handlers/navigation.py) 中重構卡片對齊邏輯：若單幀短暫未確認頁籤，僅停止滑動但不清空嘗試計數器；僅在切換頁籤或對齊成功時才重置。
   - 當連續達到 7 次嘗試上限時，觸發有界自癒重啟或優雅退回城鎮，徹底根除無界滑動風險。
4. **徹底消除 `fallback_swipe_count` 技術債**：
   - 自 [states/state_machine.py](../../states/state_machine.py) 移除 `self.fallback_swipe_count`。
   - 將地下城防呆拉回計數全面收斂至 `NavigationHandler.card_alignment_attempts`，確立單一真理源 (Single Source of Truth)。
   - 同步重構所有相關單元測試與文檔矩陣。

## Result
1. 深淵魔王戰鬥獲勝與結算均能順暢轉移至 `STATE_RESULT` 並完成流水線核銷。
2. 領域探索與地下城選關介面在進入前均受互斥雙態頁籤嚴格把關，無誤判滑動。
3. 舊時代的 `fallback_swipe_count` 徹底除役，所有拉回與對齊次數統一由 `card_alignment_attempts` 掌控。
4. 相關領域測試全數通過：
   - `tests.test_behavior_golden_empire` 100% 通過
   - `tests.test_card_alignment` 100% 通過
   - `tests.test_demon_lords_subflow` 100% 通過
   - `tests.test_behavior_dungeon_cards` 9/9 通過
   - `tests.test_dungeon_swipe_unit` 5/5 通過
   - `tests.test_behavior_dungeon_scenarios` 7/7 通過
   - `tests.test_behavior_dungeon_state_machine` 19/19 通過
   - `tests.test_behavior_navigation_scenarios` 5/5 通過

## So What
落實 Greenfield-lite 架構的「感知與決策分離」與「有界契約防呆」。透過雙態頁籤守門員與通用卡片對齊器，專案在多解析度與長時間掛機下展現出極高的抗噪能力與穩定度，並藉由消除重複狀態落實了 DRY 與極簡原則。

## Influence
- 核心導航守門員維護於 [NavigationHandler](../../states/handlers/navigation.py)
- 通用對齊抽象維護於 [CardListNavigator](../../utils/card_navigator.py)
- 場景快照與互斥頁籤登錄於 [SceneDetector](../../utils/scene_detector.py) 與 [DetectorRegistry](../../utils/detector_registry.py)
- 測試規格集中於 `tests/test_card_alignment.py`、`tests/test_behavior_dungeon_cards.py` 與 `tests/test_behavior_golden_empire.py`
