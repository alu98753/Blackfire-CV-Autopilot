# Demon Stamina Retreat Recovery Story

## Purpose

在深淵魔王按下 Start 後出現食物不足時，安全離場並進入定時領取，而不是反覆按
Start 或被 watchdog 判定卡死。

## Action

建立狀態機唯一持有的 `StaminaRetreatRecovery`。它將 `no_bread` 視為 Start 的
預期 outcome，依序關閉彈窗、每 tick 最多一次 Quit、最多三次、回城，最後切換到
`COLLECT_ONLY`；每一階段均等待下一張畫面驗證。

## Result

`no_bread.png` 使用 `cancel.png`，`no_bread2.png` 使用 `confirm.png`／`ok.png`
／`cancel.png`。Demon Lord 的 Start handler 不再自行 capture 輪詢，彈窗也不會被
一般 confirm guard 吞掉。

## So What

食物不足是可預期的資源限制，不再是未知畫面或卡死。真正沒有可驗證進展時才會
升級 recovery。

## Influence

- Demon Lord 工作被 defer，不會標記完成。
- 退避結束後由 Daily scheduler 重新挑選仍可挑戰的 Boss。
- 其他消耗食物流程可共用同一 recovery plan，避免再建立分散的彈窗處理分支。
