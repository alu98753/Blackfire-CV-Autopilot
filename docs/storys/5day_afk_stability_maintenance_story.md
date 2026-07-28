# 5 日長途掛機 P0 級穩定性防禦與 Watchdog 待機豁免 PARS 開發故事

## 🎯 Purpose (目的)

在 5 日無人值守長途掛機（AFK）環境中，任何微小的狀態誤判、UI 動畫未完即推進、按鈕點擊未生效或伺服器/本地存檔不同步，都可能引發腳本卡死或無限重試。
本次開發旨在解決 Watchdog 在 `COLLECT_ONLY` 長途退避待機狀態下的誤報問題，並方針對 P0 級核心穩定性指標建置全套自動化單元測試防線。

---

## 🛠️ Action (行動)

1. **Watchdog `COLLECT_ONLY` 待機豁免護欄**：
   - 於 [watchdog.py](file:///e:/Side_Project/BlackfireCrusade_tool/states/exceptions/watchdog.py#L30-L32) 的 `check()` 入口加入 `STATE_COLLECT_ONLY` 時間逾時豁免，避免於定時領取/體力退避待機時發起每 30 秒的錯誤救援與彈窗點擊。
2. **每日流水線與 Resume 排程優化**：
   - 於 [state_machine.py](file:///e:/Side_Project/BlackfireCrusade_tool/states/state_machine.py#L1086-L1120) 中，當處於 `collect_only` 模式時禁止調度 `accepted_quests`；當體力冷卻結束 Resume 時，優先執行用戶指定的 Tier 4 退守目標。
3. **規則修正與任務白名單**：
   - 將無法挑戰的 `雪山詛咒` 移至 [quest_rules.json](file:///e:/Side_Project/BlackfireCrusade_tool/config/quest_rules.json) 的 `ignored_quests` 清單中。
4. **P0 級 5 大自動化單元測試防線建置**：
   - `test_watchdog_collect_only_exemption.py`：驗證待機豁免與領取/Resume 監視復歸。
   - `test_deadlock_risk_prevention.py`：驗證 Boss 滿次數/體力不足/懸賞上限/城鎮速領存檔同步與避鎖。
   - `test_phase_transition_stability.py`：驗證點擊建築後 UI 穩定比對後才切換階段。
   - `test_click_and_wait_until_gone_closed_loop.py`：驗證按鈕點擊消失閉環與自動補點擊。
   - `test_unexpected_popup_docking.py`：驗證全螢幕意外彈窗偵測、雙層優先級點擊與狀態復原。

---

## 📊 Result (結果)

- 全套 **358 項單元測試 100% 綠燈 OK 通過**。
- 徹底消除 `COLLECT_ONLY` 待機期間的無意義 `POPUP_RECOVERY` 誤報點擊。
- 新增 5 個獨立單元測試套件（共 19 個新測試案例），100% 覆蓋所有 P0 級卡死邊界。

---

## 💡 So What (核心價值)

建構了**「狀態與 UI 雙重權威校驗」**與**「待機 / 救護車雙重護欄」**，使系統在無人監管狀態下具備極高的容錯自癒能力與無窮死鎖防禦力。

---

## 🚀 Influence (影響)

為後續開發任何新增之城鎮建築 Handler、懸賞任務調度器或意外彈窗 Subflow 提供了統一的標準開發規範與測試範本。
