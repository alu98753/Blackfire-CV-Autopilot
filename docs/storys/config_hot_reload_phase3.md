# Phase 3：執行中設定熱更新

## Purpose

讓自動化腳本以 `config/defaults.toml` 作為共用預設，並讓每位使用者可用未追蹤的 `config/local.toml` 覆蓋個人設定；不必重啟正在執行的腳本。

## Action

- 讀取時遞迴合併 `defaults.toml` 與可選的 `local.toml`；純量與陣列以 local 值覆蓋。
- 只在 TOML 成功完整解析後發布新快照。編輯器正在存檔、內容不完整或語法錯誤時，沿用上一份有效設定。
- 主迴圈每輪呼叫 `GameStateMachine.refresh_config_at_safe_point()`，在下一個 `step()` 前套用更新。
- CLI 與啟動互動選擇（例如祝福、地下城、關卡）會被記錄為執行期覆蓋，設定檔更新時仍會保留。

## Result

可建立下列個人覆蓋檔：

```toml
# config/local.toml（已在 .gitignore）
[primary_modes.dungeon]
bless_mode = "exp"

[primary_modes.dungeon.cooldown_map]
1 = 60.0
```

儲存後，腳本會在目前 Handler 完成、進入下一輪主迴圈時採用新設定。`config/local.toml` 被刪除時，會自動回到 `defaults.toml`。

## So What

更新不會插進一串點擊、OCR 或子流程的中間，避免同一個操作半途換模板或策略。錯誤設定不會讓執行中的腳本失去既有可用配置。

## Influence

- 所有既有 `from config import GAME_CONFIGS` 的呼叫仍可使用，因為匯出 mapping 會原地更新。
- 主模式會即時收到新設定；暫時切入的城鎮子流程仍會在下一次狀態切換時從最新設定建立。
- 結構性修改（新增模式 key、改變啟動參數）仍建議重啟，避免改變已建立的 CLI/Handler 拓撲。
