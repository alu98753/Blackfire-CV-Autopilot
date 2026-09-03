# Daily Tier 4 玩家長駐路由開發故事（PARS Framework）

## Purpose

Daily 原本把地下城選擇與普通關卡退守混在同一段 CLI，無法表達「地下城、Lord 是定時插隊活動；stage、domain 才是可持續執行的長駐打法」，也無法讓每位玩家獨立選擇 Tier 4 項目。

## Action

1. 將 daily 排程政策與 Tier 4 執行路由分離：`primary_config` 保留活動開關，`build_tier4_fallback_config()` 在安全點解析實際路由。
2. 新增兩層 CLI：先選 `stage` / `domain`，再選關卡大關與小關，或領地（目前黃金古國）。
3. 透過既有 Profile 設定層把選擇增量寫入 `user_data/<profile>/config.toml`。
4. 將 `enable_dungeon`、`enable_lord_boss` 設為 daily 明確預設值，保留 TOML 與 CLI 關閉能力。
5. 讓 domain 長駐也能在城鎮工作、懸賞、Lord 或地下城就緒時離場並重新排程。
6. 補上 Tier 4 選單、配置組裝、Profile 政策保留及 domain 插隊的聚焦行為測試。

## Result

- `--mode daily` 啟動時會顯示清楚的 Tier 4 主選單與子選單。
- `native`、`sandbox` 與自訂 Profile 可保存不同的 Tier 4 玩法。
- stage 與黃金古國均可作為長駐路由，週期活動仍保持較高優先級。
- Supervisor `--resume` 不讀取 stdin，直接重建已保存的玩家路由。

## So What

Tier 4 從固定的 Mix 補丁提升為可擴充的路由選擇模型。新增領地時只需加入模式配置與選項，不必把領地細節塞進 Daily 排程器。

## Influence

未來可在 `TIER4_DOMAIN_OPTIONS` 擴增其他領地，或新增其他可持續模式；Profile TOML 仍是單一真值來源，狀態機只在導航安全點切換完整配置。
