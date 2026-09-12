# 開發故事：待辦清單全域超連結補全、24/7 風險排序與核心架構契約收斂 (PARS) 📜

> 類別：開發歷程複盤（Narrative Log）
>
> ⚠️ **重要聲明**：本文件僅為歷史敘事日誌，記錄當時問題脈絡、執行的修復行動與除錯統計，供團隊複盤回溯。**PARS 故事不是架構規範，絕不可作為未來開發或架構設計的依據或證據**。架構規範請以 [Supervisor Lifecycle Contract](../architecture/supervisor_lifecycle_contract.md) 與 [Battle Stall Recovery Contract](../architecture/battle_stall_recovery_contract.md) 為準。

---

## 1. Problem (問題脈絡)

在系統逐步由舊型 FSM 邁向 Greenfield-lite 分層架構的過程中，長期維護的中央待辦清單與架構文件出現了數個維護痛點：
1. **待辦清單過度膨脹且缺乏結構化約束**：[`future_work.md`](../todos/future_work.md) 中累積了 70+ 個程式檔案、模板、規格與待辦項目的引用，但早期條目多使用純文字表示，缺少精確的相對 Markdown 超連結，降低操作員檢閱與追溯效率。
2. **24/7 無人值守風險排序倒置**：未實作項目未按嚴重性分級，導致可能引發排程活鎖、持久化事實污染或進程死鎖的嚴重隱患與一般的 UI/多語言優化混雜。
3. **架構契約與臨時規格邊界模糊**：
   - 多進程 Supervisor 的 S1~S7 重啟生命週期矩陣此前僅存於 PARS 故事中，缺乏正式架構契約約束。
   - 戰鬥血條卡死重試自癒機制已在 production code 穩定運行，但仍殘留過期規格草案 [`battle_stall_recovery_spec.md`](../todos/battle_stall_recovery_spec.md)。
4. **章節層級未標準化**：部分待辦事項未使用標準 `###` 領域前綴，造成層級與導航不一致。

---

## 2. Action (架構設計與實作行動)

### 2.1 全域相對路徑超連結補齊
- 遍歷並重構 [`future_work.md`](../todos/future_work.md) 中的所有檔案路徑、模板圖片、規格文件與單元測試引用，全面轉換為合規的標準相對 Markdown 連結（如 `[states/state_machine.py](../../states/state_machine.py)`），嚴格杜絕 `file:///` 絕對路徑。

### 2.2 24/7 掛機故障階梯排序與紅點標註
- 依據「死鎖/活鎖/崩潰迴圈 > 假陽性完成/持久化污染 > Tier 洩漏 > Action 未驗證推進 > 資源耗盡 > 功能缺失 > 效能/架構 > UI/多語言」階梯原則，將各 `###` 領域中最可能危害 24/7 長期掛機的項目重排至該章節第一位，並以 `🔴` 標記。

### 2.3 提煉兩大長效 Canonical Contracts 並清理過期檔案
- **Supervisor 生命週期契約**：建立 [`docs/architecture/supervisor_lifecycle_contract.md`](../architecture/supervisor_lifecycle_contract.md)，明定 S1~S7 狀態矩陣、單次消費旗標 `--restart-game`、PID 守護與安全重啟流程。
- **戰鬥卡死自癒契約**：建立 [`docs/architecture/battle_stall_recovery_contract.md`](../architecture/battle_stall_recovery_contract.md)，定義 30 秒血條變化量 $\Delta < 300$ 判定標準、上限 2 次原地重新開始與超限升級殺進程不變量。
- **清理過期規格**：依據「刪除是預設；封存是例外」原則，安全移除已落盤實作之 [`docs/todos/battle_stall_recovery_spec.md`](../todos/battle_stall_recovery_spec.md)。

### 2.4 章節層級正規化
- 將已完成之「長期掛機定期安全重啟服務」移入已完成區域。
- 將「終端 Config 設定」併入 `### DEV`；「記憶體洩漏分析」併入 `### Exception`。
- 新設 `### 多實例與沙盒環境`、`### 全域架構審查與技術債治理`、`### 產品化與變現方式` 三大正規分類，且 `- [ ]` 內容保持 100% 不變。

---

## 3. Result (成果驗證)

1. **純文件變更核驗**：
   - 異動檔案全數位於 `docs/` 目錄（`future_work.md`、`supervisor_lifecycle_contract.md`、`battle_stall_recovery_contract.md`、`battle_stall_recovery_spec.md`），無修改任何 Python 代碼或 runtime 資產，符合 `AGENTS.md` 規則 0 之純文件變更免測試條款。
2. **契約收斂完成**：
   - 核心不變量正式升格為長效約束文件。
   - 待辦清單具備清晰的 24/7 風險視野與完整可點擊超連結。
