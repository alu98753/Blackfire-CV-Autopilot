我審完了。整體上這份 `domain_entry_overlay_misclassification_analysis.md` **方向正確，但 implementation plan 還要收斂一下**。

先提醒一件事：你給的 `1ac3edab...` 在 GitHub 上顯示的是 **`docs: analyze domain entry overlay misclassification...`**，主要新增這份分析文件與 future work，不是 Stage 短期修正本身。如果你只是拿它當目前 baseline 沒問題；如果你認為它就是 Stage fix commit，SHA 可能貼錯了。

### 審核結論

分析文件抓到三個問題：

1. `LOBBY + CLOSE_OVERLAY → DISMISS_OVERLAY` 太寬。
2. domain 的 `start_btn` 沒有進 `ElementId.START`。
3. `DOMAIN_SELECT` 沒有 `START_PRIMARY` edge。

這三點我都同意，而且實際 code 有直接證據。

目前 table 仍存在：

```text
PRIMARY_NAVIGATION
+ LOBBY
+ CLOSE_OVERLAY
→ DISMISS_OVERLAY
```

所以只要 Domain preparation panel 被分類成 `LOBBY`，`common/quit.png` 就會直接贏得決策權。

同時 domain config 確實只有：

```toml
navigation_path = [
  "common/door.png",
  "domains/Domains_entry.png",
  "domains/golden_empire/entry.png",
  "domains/common/start_btn.png"
]
```

卻沒有 `lobby_start_btn`；反而 stage 明確有：

```toml
lobby_start_btn = "stages/start.png"
```

所以分析文件的 template-contract 判斷成立。

而 Navigation Table 現在確實只有 `LOBBY / STAGE_SELECT / DUNGEON_SELECT` 的 `START_PRIMARY`，沒有 `DOMAIN_SELECT`。

---

## 但我會修改分析文件中的修法優先級

我**不建議這次直接做完整 OverlayId medium-term refactor**。

原因是你現在已經連續在：

```text
STAGE
DOMAIN
```

踩到同一類 bug，但我們還沒有把 Dungeon cooldown 的真正 distinguishing evidence 找出來。

如果現在急著全面改：

```text
CLOSE_OVERLAY → OverlayId.xxx
```

很容易順手破壞之前已驗證能自癒的 cooldown 行為。

這一刀我建議仍然是：

> **Domain-specific behavior-preserving repair + 把 LOBBY close edge 的錯誤 applicability 收窄。**

而不是進行 Overlay subsystem 重構。

另外，我不同意只做：

```toml
lobby_start_btn = "domains/common/start_btn.png"
```

就算完成。

因為它只能讓：

```text
START
```

有機會跟：

```text
CLOSE_OVERLAY
```

競爭。

但真正的 invariant 應該是：

> **正常 domain preparation UI 即使存在 quit，也不得被當成 blocking overlay。**

否則只是靠 declaration order 或 detector timing 恰好讓 START 先贏，bug 還在。

我會讓 Codex 做下面這個 scope。

你正在修改：

`alu98753/Blackfire-CV-Autopilot`

目前 baseline 請先確認實際 branch / HEAD，不要只依賴本 prompt。

重要架構基準：

`docs/architecture/project_arch_greenfield_lite_v1.md`

相關問題分析：

`todos/domain_entry_overlay_misclassification_analysis.md`

先前 Stage 已發生過相同類型問題：

「正常次級 UI 含有 `common/quit.png`，但 `common/quit.png` 被轉成 `ElementId.CLOSE_OVERLAY`，Navigation Policy 因此錯誤派發 `DISMISS_OVERLAY`。」

這次 Domain 實機同樣重現。

---

# Goal

修復 Golden Empire / Domain navigation：

```text
Lobby
→ Domain tab
→ Golden Empire entry
→ preparation panel
→ START
→ Domain exploration
```

目前 preparation panel 開啟後包含 `common/quit.png`，系統錯誤執行：

```text
DISMISS_OVERLAY
```

把正常 preparation panel 關掉，形成：

```text
open → close → reopen → close
```

loop。

本次是 **behavior-preserving bugfix**。

只改正 Domain navigation 的誤關閉與缺失 routing contract。

不要順便進行完整 Overlay architecture rewrite。

---

# Before editing

請先重新檢查目前實際 implementation，至少閱讀：

* `todos/domain_entry_overlay_misclassification_analysis.md`
* `docs/architecture/project_arch_greenfield_lite_v1.md`
* `states/navigation_table.py`
* `states/navigation_intent.py`
* `states/navigation_routing.py`
* `states/handlers/navigation.py`
* `utils/scene_snapshot.py`
* Domain 相關 `scene_detector / scene_catalog / detector registry`
* `config/defaults.toml`
* Domain navigation / behavior tests

確認：

1. Domain preparation panel 實際被辨識成哪個 `SceneId`。
2. `domains/common/start_btn.png` 是否存在於 `scene_info.matched_elements`。
3. 為什麼它目前沒有成為 `ElementId.START`。
4. `LOBBY + CLOSE_OVERLAY → DISMISS_OVERLAY` 是否正是此次錯誤 action 的來源。
5. Domain legacy navigation 在 policy 回傳 `CONTINUE_PRIMARY` 後原本如何推進。

不要只根據 todo 文件假設。

---

# Root semantic invariant

不要再使用：

```text
common/quit.png exists
    ⇒ blocking overlay exists
```

這個 inference。

`common/quit.png` 只是：

```text
WHERE = close control location
```

不是：

```text
WHAT = this UI should be automatically dismissed
```

正常 Domain preparation panel 即使有：

```text
ElementId.CLOSE_OVERLAY
```

也不得因此被關閉。

---

# Required change — Slice A

## Fix Domain START template contract

讓 Domain mode 使用正確的：

```text
domains/common/start_btn.png
```

作為 `ElementId.START` evidence。

優先使用目前既有 configuration contract。

如果目前 architecture 的設計就是：

```python
machine.config["lobby_start_btn"]
```

則在：

```toml
[primary_modes.golden_empire]
```

加入：

```toml
lobby_start_btn = "domains/common/start_btn.png"
```

不要為此新增 mode-specific if/elif chain。

只有當檢查 repo 後證明 `lobby_start_btn` 已不再是 canonical contract，才採用更符合目前 implementation 的方式。

保持 Stage / Dungeon 既有 template behavior 不變。

---

# Required change — Slice B

## Make DOMAIN_SELECT a first-class START source if perception already exposes DOMAIN_SELECT

如果目前 SceneDetector / SceneSnapshot 已會把 Domain selection / preparation UI 穩定表示為：

```text
SceneId.DOMAIN_SELECT
```

則 Navigation Table 應支援：

```text
PRIMARY_NAVIGATION
DOMAIN_SELECT
START
→ START_PRIMARY
→ LOADING_OR_BATTLE
```

形式應沿用現有：

```text
STAGE_SELECT
DUNGEON_SELECT
```

的 declarative NavigationEdge，不要在 Handler 寫特殊 case。

但是：

如果實際 Domain preparation panel 被設計上穩定分類為 `LOBBY`，不要為了這次 bug 強行建立另一個 Scene。

先尊重目前 SceneCatalog / detector contract。

---

# Required change — Slice C

## Prevent normal Domain preparation UI from being dismissed

這是本 bugfix 最重要的 acceptance invariant。

正常：

```text
Domain preparation panel
+ START
+ common/quit.png
```

不得 resolve 成：

```text
DISMISS_OVERLAY
```

應該 resolve 成：

```text
START_PRIMARY
```

或在 START 尚未形成可靠 evidence 時：

```text
CONTINUE_PRIMARY
```

交還既有 Domain navigation。

不得關閉 preparation panel。

---

## How to fix LOBBY dismiss edge

請先確認 `PRIMARY_NAVIGATION + LOBBY + CLOSE_OVERLAY → DISMISS_OVERLAY`
原本到底保護什麼 verified behavior。

不要無條件直接刪除，除非能證明它沒有合法 use case。

若它仍然有已驗證的 recovery purpose：

* 收窄 applicability；
* 不得讓 Domain preparation UI 命中；
* 不得單靠 declaration ordering 掩蓋 semantic ambiguity。

例如以下修法不夠：

```text
put START edge before CLOSE_OVERLAY edge
```

因為只要 START 某一 frame detector miss，下一條 CLOSE_OVERLAY 還是會關掉正常 panel。

因此 regression invariant 必須涵蓋：

```text
Domain preparation UI
+ CLOSE_OVERLAY
+ temporary START miss
```

不得立即被當作 blocking overlay 關閉。

如果目前沒有可靠 semantic evidence 能保留 `LOBBY` generic dismiss，
請評估移除 `PRIMARY_NAVIGATION + LOBBY + CLOSE_OVERLAY` edge，
但在移除前先找出並測試它原先服務的 behavior。

不要猜。

---

# Do NOT perform the medium-term Overlay refactor in this change

目前已知 architecture debt：

```text
ElementId.CLOSE_OVERLAY
```

與：

```text
OverlayId
```

語意尚未真正解耦。

未來理想模型是：

```text
overlay-specific evidence
→ OverlayId.X
→ policy decides DISMISS_OVERLAY
→ CLOSE_OVERLAY only supplies click coordinates
```

但本次不要：

* 建立 generic Overlay framework
* 大改 `NavigationEdge` schema
* 新增 Overlay DSL
* 大量新增 SceneId
* 重寫 SceneDetector
* 一次遷移所有 Dungeon / Lord / Stage overlays

如果修復 Domain 必須依賴完整 Overlay redesign，先停止並在結果中說明原因，不要擴大 scope。

---

# Tests

至少新增以下 behavior-level regression tests。

## Test 1 — Domain start contract

Given:

```text
mode = golden_empire / domain
scene contains domains/common/start_btn.png
```

Then snapshot 必須包含：

```text
ElementId.START
```

---

## Test 2 — Domain start routing

若 canonical scene 為 `DOMAIN_SELECT`：

```text
PRIMARY_NAVIGATION
+ DOMAIN_SELECT
+ START
```

Then：

```text
START_PRIMARY
LOADING_OR_BATTLE
```

若 canonical scene 實際為 `LOBBY`，依實際 contract 寫等價測試。

---

## Test 3 — Domain panel must not be dismissed

Given 正常 Domain preparation panel evidence：

```text
PRIMARY_NAVIGATION
+ canonical domain preparation scene
+ CLOSE_OVERLAY
+ START
```

Then：

```text
decision.action == START_PRIMARY
```

並且：

```text
decision.action != DISMISS_OVERLAY
```

---

## Test 4 — temporary START miss

Given：

```text
normal Domain preparation context
+ CLOSE_OVERLAY
+ START temporarily absent
```

不得因為 `common/quit.png` 單獨存在就關閉 preparation panel。

驗證結果應符合目前 architecture 的 safe fallback：

```text
CONTINUE_PRIMARY
```

或其他既有非 destructive behavior。

---

## Test 5 — Preserve verified overlay recovery

找出此次修改可能影響的既有真正 overlay recovery case。

證明：

```text
real blocking overlay
```

仍可以被 dismiss。

不要用：

```text
LOBBY + CLOSE_OVERLAY
```

本身作為「real blocking overlay」的完整測試 fixture；

fixture 必須包含能區分真正 overlay 與正常 preparation panel 的 evidence，
或者明確記錄目前 legacy limitation。

---

# Existing invariants that must not change

保持：

1. Stage navigation 實機已驗證 behavior。
2. Dungeon navigation / cooldown recovery 已驗證 behavior。
3. Daily tier scheduling precedence。
4. ActiveIntent selection。
5. Single `InFlightAction` contract。
6. 一個 tick 一份 SceneSnapshot。
7. Policy 不做 IO。
8. Detector 不執行 click。
9. NavigationHandler 不新增 task-selection responsibility。
10. Domain explore 戰鬥後既有流程。
11. Existing config compatibility。

---

# Architectural constraints

遵守 Greenfield-lite：

```text
Scene
Overlay
Element
```

是不同語意。

不要因為這個 bug 新增：

```text
DOMAIN_PREPARE_WITH_CLOSE
DOMAIN_PREPARE_NO_CLOSE
DOMAIN_DRAWER
...
```

之類的 scene explosion。

如果現有 `DOMAIN_SELECT` 足以描述主畫面狀態，就沿用它。

---

# Non-goals

本次不要：

* 完整 OverlayId migration
* 重構 navigation.py 大檔
* 清理 unrelated dead code
* 修改 Daily scheduler
* 修改 battle logic
* 修改 domain gameplay strategy
* 新增 generic planner
* 重寫 Navigation Table
* 修改已驗證 Stage fix

---

# Validation

完成後執行：

1. targeted navigation policy tests
2. scene snapshot / perception tests
3. Domain navigation tests
4. full existing automated test suite

並檢查 git diff，確認沒有 unrelated changes。

---

# Final report

完成後不要只說 tests pass。

請回報：

1. Root cause 最終確認結果。
2. Domain preparation panel 實際 SceneId。
3. 修改哪些檔案。
4. 是否新增 `lobby_start_btn`。
5. 是否新增 `DOMAIN_SELECT → START_PRIMARY` edge，以及原因。
6. 如何防止 `common/quit.png` 再誤殺正常 Domain panel。
7. `LOBBY + CLOSE_OVERLAY` edge 最終保留、收窄或移除，以及證據。
8. 新增哪些 regression tests。
9. 哪些 behavior invariants 明確保持不變。
10. 尚未處理的 Overlay semantic debt。

不要提交 medium-term architecture refactor。

我會特別強調 **Test 4**。這是這次和「單純把 start template 修好」最大的差別。

因為假設你只補：

```toml
lobby_start_btn = "domains/common/start_btn.png"
```

正常情況可能變成：

```text
START exists
→ START wins
```

看起來修好了。

但 CV 本來就可能某一幀漏掉 START：

```text
START miss
CLOSE_OVERLAY still detected
→ DISMISS_OVERLAY
```

然後你一樣偶發關掉視窗。

所以這次真正應該鎖住的 invariant 是：

> **正常 Domain preparation context 中，`quit.png` 單獨出現也沒有足夠權限觸發 destructive dismiss。**

這樣才算把第二次出現的同類 bug 修對，而不是再打一個 template patch。
