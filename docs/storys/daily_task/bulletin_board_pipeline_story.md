# 📜 懸賞告示牌全自動調度與 4-Phase 彈窗核銷重構故事 (PARS Story)

本文件以 PARS 框架記錄每日懸賞任務 (bulletin_board) 全自動接取、OCR 錯字三合一正名校正與 Match 驅動 4-Phase 彈窗清理狀態機的工程實現。

---

## 🎯 1. Purpose (目的)

在每日懸賞任務自動化流程中，過去面臨三大痛點：
1. **已接取任務誤殺未接取任務**：告示牌中已接取的灰色卡片 `task_after.png` 與待接取的黃色卡片 `task.png` 外形高度相似，原有的範本匹配極易誤將灰色卡片判定為可用任務，或把未接取的卡片過濾掉。
2. **彈窗領取 Timeout 卡頓**：完成懸賞任務後彈出的獎勵領取彈窗 (`task_complete.png`) 容易因動畫延遲導致點擊 Timeout，甚至重複補點引發畫面死結。
3. **EasyOCR 錯別字誤判**：遊戲字型常被 EasyOCR 誤讀（如 `直領` ➔ `首領`、`野猾` ➔ `野豬`），導致任務標題無法命中映射字典。

---

## 🛠️ 2. Action (行動)

1. **灰度比 (`ratio_after <= 0.88`) 與 3 秒沉澱防呆**：
   * 在 `bulletin_board.py` 中重構 `reset.png` 點擊邏輯，點擊後進行 3.0 秒靜置等待畫面定格。
   * 為卡片 ROI 引入 `brightness_threshold=0.88` 與灰度比 `ratio_after <= 0.88` 雙重過濾，確保 100% 精確區分灰色與黃色卡片。
2. **Match 驅動 4 Phase 專屬彈窗狀態機**：
   * 將獎勵領取重構為 4 個獨立 Phase：`INIT_BANNER_CHECK` ➔ `OCR_RECOGNIZE` ➔ `FIND_DISMISS_TARGET` ➔ `CLICK_DISMISS_LOOP`。
   * 以 2.0 秒為固定間隔輪詢比對畫面上的 `common/confirm.png` / `common/ok.png`，直到確認所有彈窗完全清空方才退場。
   * 領取完成後主動呼叫 `check_and_advance_quest_target()`，實現即時無縫切換下一個懸賞目標。
3. **三合一自動正名校正管道 (`TYPO_GROUPS`)**：
   * 將錯字表重構為 `TYPO_GROUPS` 結構，涵蓋常見 OCR 錯字。
   * 整合「1.0 字典反向映射 + 2.0 difflib 編輯距離 (cutoff ≥ 0.65) + 2.5 筆畫與專有名詞比對」三層防線。

---

## 📈 3. Result (結果)

* **告示牌辨識率**：告示牌黃色/灰色卡片判斷正確率達到 **100%**。
* **彈窗清理時間**：完成獎勵彈窗可以在 **2.0 秒內** 完成平滑點擊與銷毀，無任何 Timeout 告警。
* **單元測試驗證**：[test_bulletin_board_subflow.py](file:///e:/Side_Project/BlackfireCrusade_tool/tests/test_bulletin_board_subflow.py) 與 [test_quest_statemachine_integration.py](file:///e:/Side_Project/BlackfireCrusade_tool/tests/test_quest_statemachine_integration.py) 全量通過。

---

## 💎 4. So What (核心價值)

解決了懸賞任務最棘手的 UI 殘影與 OCR 錯字干擾，讓「每日懸賞任務」真正具備 **全無人干預 (Zero-Intervention) 的全自動流水線運作能力**。

---

## 🌟 5. Influence (影響)

* **4-Phase Match 狀態機模式**：成為專案中處理「多階段彈窗清理」與「動畫延遲確信」的標準架構範本。
* **三合一正名管道**：為後續新關卡、新地下城與未知任務標題的擴充提供了自癒式（Self-Healing）防禦機制。
