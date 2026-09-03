# Battle Session Recovery Story

## Purpose

讓正常進行中的 Boss 戰不會因前一場戰鬥留下的逾時計時器而被錯誤重開。

## Action

將戰鬥逾時計時收斂為 `GameStateMachine` 唯一持有的 `BattleSession`；所有
進入與離開 `STATE_BATTLE` 的路徑都由狀態轉移邊界建立或終止 session，並以
`ClockPort` monotonic 時間計算經過時間。

## Result

全域重新定位、Lord Boss、深淵魔王、Stage、Domain 和重啟後的戰鬥觀測，都不
能再攜帶舊 session 的時間。只有目前 session 真的超過 TOML 的 hard cap 才會
呼叫 ProcessPort 進行重啟。

## So What

日誌中「剛辨識到 auto.png 卻已戰鬥數萬秒」的矛盾被消除，正常 Boss 戰能繼續
執行，同時保留真正卡死時的有界重啟能力。

## Influence

- Handler 不再是戰鬥 timeout 資料的多個 writer。
- 重啟和全域掃描共享同一個明確的 recovery 邊界。
- 後續若遷移為完整 `SceneSnapshot` 流程，BattleSession 可以直接由
  `SceneId.BATTLE` 的 observation 建立，不需改變 timeout policy。
