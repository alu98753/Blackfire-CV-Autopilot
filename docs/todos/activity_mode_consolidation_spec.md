## 目標

收斂目前散落的 `mix / dungeon / stage / collect_only / golden_empire / subflow ...` 啟動模式。

未來對外只保留兩種 orchestration mode：

### 1. `daily`

固定的 24/7 ActivityPlan。

啟動時讀取使用者持久化設定，按照系統既有 Scheduler、Priority、cooldown、defer、preemption 規則持續執行。

### 2. `custom`

讓使用者 enable / disable 個別 Activity，並設定必要 target。

`custom` 不建立另一套 scheduler；必須與 `daily` 共用相同的 Activity selection、priority、intent lifecycle 與 prerequisite 機制。

`daily` 本質上應只是官方預設的一份 ActivityPlan，`custom` 則是使用者自行組合的 ActivityPlan。

## 單一功能執行

不要把第三類稱為一般 runtime `mode` 或把所有功能都叫 `subflow`。

建立「直接執行單一 Activity」的開發入口，例如：

`--activity dungeon`
`--activity stage`
`--activity golden_empire`
`--activity chest`
`--activity bag_clean`

其用途是開發、debug、驗證單一 Activity，繞過全域 Scheduler。

目前 `--subflow` 可視為此能力的早期版本；未來逐步泛化，而不是把 dungeon、stage 等概念硬塞入 Town Subflow。

## 核心語意

統一名詞：

`Mode` = 使用者如何建立執行計畫
`ActivityPlan` = 哪些 Activities 啟用以及相關設定
`Activity` = scheduler 可以選擇的一個工作
`Intent` = runtime 目前承諾完成的工作
`Handler/FSM` = Activity 被 dispatch 後的局部執行

目標依賴方向：

User configuration
→ ActivityPlan
→ Scheduler / Intent selection
→ prerequisite satisfaction
→ Activity Handler / FSM

底層 Navigation / Handler 不得根據 `mode` 名稱自行選擇其他 Activity。

## 特別注意

目前 `daily` 仍使用 `type="mix"` 作為 runtime compatibility mechanism，此為過渡實作，不應成為未來架構。

也不要再新增新的 `if config["type"] == ...` 來解決跨 Activity priority 問題。

此 Future Work 應另開 architecture/spec branch 實作，不與目前 Daily Quest priority bugfix 混在一起。
