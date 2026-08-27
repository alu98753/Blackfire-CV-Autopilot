# Config Hot Reload Phase 1

## Purpose

讓執行中的自動化腳本能安全讀取更新後的 JSON 設定，而不因使用者儲存到一半的檔案而中斷。

## Action

新增 `JsonConfigManager` 作為 JSON 設定的唯一熱重載基礎，使用 `mtime_ns` 與檔案大小偵測更新，並只在完整 JSON 成功讀取後發布新快照。`quest_rules.json` 與 `exception_features.json` 已改由它載入。

## Result

有效的新設定會在下一次既有讀取點套用；若 JSON 暫時無效，程式繼續使用最後一份有效設定。呼叫端取得深複製快照，無法誤改已發布的設定。

## So What

這消除了兩份 JSON 設定各自實作 mtime cache 的差異，也避免快速連續儲存時只比較秒級 mtime 而漏掉更新。

## Influence

下一階段可讓 TOML 的主模式設定也接入同一個 manager，並在狀態機的安全轉移點套用新的模式快照。
