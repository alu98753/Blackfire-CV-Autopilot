# 懸賞告示牌開窗自適應尺度判定與感知分離開發故事 (PARS Story)

## P - Purpose (目的與背景問題)

在自動化掛機日常流程中，懸賞告示牌 (bulletin_board) 出現進店開窗逾時與誤退回問題：
1. **轉場黑屏誤入沉澱計時**：在城鎮點擊告示牌建築後，轉場與畫面載入期間畫面上未出現 quit.png。舊實作在未看見 quit.png 時即開始消耗 2.5 秒開窗沉澱等待窗口，導致動畫尚未渲染完成便過早判定逾時。
2. **單一解析度模板尺度侷限**：開窗驗證依賴之 3 張核心特徵模板（reset.png、task.png、task_after.png）在不同解析度或 UI 縮放下缺少候選尺度自適應匹配，比對信心度易受縮放影響。
3. **感知與決策耦合**：BulletinBoardHandler 內部包含底層 ROI 切割、模板比對、灰度計算與狀態機決策，檔案規模膨脹且不符合 Greenfield Lite v1 之感知與決策分離原則。

---

## A - Approach (方案與實作)

依據既有架構規範與單一來源設計原則，落實下列調整：

1. **獨立純感知檢測器 ([bulletin_board_detector.py](../../utils/bulletin_board_detector.py))**：
   - 封裝 Scoped ROI 局部模板比對與 is_inside_bulletin_board 門禁檢測，只負責觀察畫面特徵並輸出快照結果，不觸發任何滑鼠點擊或狀態跳轉。
   - 採用 matcher.compute_candidate_scales(w) 動態計算候選尺度，並實現三通道 Early Return：reset.png、task.png、task_after.png 任一通道命中即刻返回 True，減少多模板比對耗時。
   - 封裝 has_bag_features：以背包專屬按鈕（sort.png、recycle.png）進行排他過濾，防止非告示牌覆蓋層被誤判為告示牌。

2. **時序沉澱計時與階梯 1 自癒防線 ([bulletin_board.py](../../states/handlers/bulletin_board.py))**：
   - 在 WAIT_BOARD_OPEN 階段，只有當畫面**確認偵測到 quit.png** 時才啟動 2.5 秒的沉澱等待，避免將遊戲轉場黑屏計入等待時間。
   - 保留 BOARD_OPEN_HARD_TIMEOUT = 5.0 秒防線：若點擊建築後超過 5.0 秒依然未見任何彈窗或 quit.png，退回 INIT 發起重新進店點擊，提供低成本的輕量自癒能力。

3. **核心接取流程完整保留 (Zero Regression)**：
   - PROCESS_ACCEPT_QUESTS 階段之任務掃描、灰度比比對、OCR 標題對齊與全部重要排查日誌 100% 原封不動保留，避免重構引入接取邏輯回歸。

---

## R - Results (成果與驗證)

1. **雙工作樹全套測試迴歸驗證 (Dual-Worktree Baseline Verification)**：
   - 執行 1,000 項單元測試逐項比對：
     - BRANCH_REGRESSION: 0（零迴歸）。
     - FIXED_IN_HEAD: 5（修復了告示牌退出與紅點等測試案例）。
     - PRE_EXISTING_FAILURE: 33（既有基準線錯誤，與本分支無關）。
2. **聚焦業務測試**：
   - tests.test_behavior_bulletin_board_settle: 6/6 通過。
   - tests.test_bulletin_board_subflow: 7/7 通過。
   - tests.test_quest_ocr_extractor: 3/3 通過。

---

## S - Summary (總結與後續)

- 本次修正解決了懸賞告示牌在轉場動畫時被提前逾時打斷的問題，透過專屬檢測器抽離與自適應候選尺度，使開窗驗證更具強韌性。
- 接續可依排程推進深淵魔王與領主討伐相關維護。
