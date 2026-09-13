# Bugfix Spec — Prevent structural close controls from being treated as dismissable overlays

## Goal

修復 `PRIMARY_NAVIGATION` 在 `STAGE_SELECT` 開啟關卡子抽屜後，因 `common/quit.png` 被誤判為 overlay close control 而產生的：

`open stage drawer → dismiss overlay → close drawer → reopen drawer → ...`

無限 navigation loop。

本次修改預設為 **behavior-preserving bugfix**：

* 修正已確認的錯誤 dismiss 行為。
* 不改變正常 stage navigation。
* 不改變既有 dungeon cooldown recovery，除非測試證明現有判斷同樣存在語意歧義。
* 不進行大型 Scene / Overlay framework 重構。

---

## Root cause

目前：

```text
common/quit.png
    ↓
ElementId.CLOSE_OVERLAY
    ↓
NavigationTable
    ↓
ActionId.DISMISS_OVERLAY
```

這個推論不成立。

`common/quit.png` 只證明「畫面存在一個 close control」，不能證明「目前存在應被自動 dismiss 的 blocking overlay」。

在 `STAGE_SELECT`：

```text
stage drawer open
+ common/quit.png
```

是正常 navigation UI，不是異常 overlay。

因此 Navigation Policy 不應因 `CLOSE_OVERLAY` 單一 element evidence 中斷 primary stage navigation。

---

## Required fix — Slice 1

### 1. Remove the invalid STAGE_SELECT dismiss edge

從 `V1_NAVIGATION_EDGES` 移除：

```python
NavigationEdge(
    IntentId.PRIMARY_NAVIGATION,
    SceneId.STAGE_SELECT,
    SceneId.STAGE_SELECT,
    ElementId.CLOSE_OVERLAY,
    ActionId.DISMISS_OVERLAY,
    PostconditionId.OVERLAY_CLOSED,
    ReasonCode.PRIMARY_CLOSE_OVERLAY,
)
```

修改後：

```text
PRIMARY_NAVIGATION
+ STAGE_SELECT
+ common/quit.png
```

不得產生：

```text
DISMISS_OVERLAY
```

當沒有其他 table edge 可執行時，policy 應維持目前 compatibility 行為：

```text
CONTINUE_PRIMARY
```

讓既有 `NavigationHandler` / sub-stage navigation 繼續處理 stage drawer。

---

## 2. Add regression tests

不要只修改 table edge count。

新增明確的 behavior regression test：

```text
given:
    intent = PRIMARY_NAVIGATION
    scene = STAGE_SELECT
    elements contains CLOSE_OVERLAY

when:
    NavigationIntentPolicy.resolve(...)

then:
    decision.action != DISMISS_OVERLAY
    decision.action == CONTINUE_PRIMARY
    decision.reason == PRIMARY_ROUTE_DELEGATED
```

最好另外加入：

```text
STAGE_SELECT
+ CLOSE_OVERLAY
+ other normal stage drawer evidence
```

仍不得 dismiss drawer。

目的：測試真正的 bug invariant，而不是測 implementation detail。

---

## 3. Update brittle table-shape test

目前：

```python
assert len(V1_NAVIGATION_EDGES) == 16
```

以及直接要求存在：

```text
PRIMARY_NAVIGATION
STAGE_SELECT → STAGE_SELECT
```

會把錯誤 architecture 鎖進測試。

修改為：

* 不再要求 STAGE_SELECT self-loop dismiss edge。
* edge count 如仍有價值可更新，但不要把 count 當主要 correctness assertion。
* 明確 assert：

```text
PRIMARY_NAVIGATION + STAGE_SELECT + CLOSE_OVERLAY
does not resolve to DISMISS_OVERLAY
```

---

## Required investigation — Slice 2

在保留：

```text
PRIMARY_NAVIGATION
DUNGEON_SELECT
CLOSE_OVERLAY
→ DISMISS_OVERLAY
```

之前，先確認遊戲實際 UI semantics。

回答：

1. `DUNGEON_SELECT` 正常 dungeon detail / drawer 是否也存在 `common/quit.png`？
2. cooldown popup 的 `common/quit.png` 是否有其他穩定 evidence：

   * popup anchor
   * cooldown text/icon
   * ROI
   * 独立 template
   * existing SceneInfo evidence
3. 是否可能同時存在：

   ```text
   normal dungeon drawer + common/quit.png
   ```

   如果可以，目前 DUNGEON_SELECT edge 與這次 Stage bug 屬於同一類 latent bug。

如果無法證明：

```text
DUNGEON_SELECT + CLOSE_OVERLAY
=> blocking cooldown popup
```

則不得把這條 implication 當 invariant。

---

## Preferred semantic direction

不要以 template filename 定義 UI semantics。

錯誤模型：

```text
common/quit.png
→ CLOSE_OVERLAY
→ DISMISS_OVERLAY
```

應逐步朝：

```text
visual close control
+
overlay-specific evidence
→ known overlay
→ dismiss overlay
```

例如利用現有 `SceneSnapshot.overlays`：

```python
OverlayId.DUNGEON_COOLDOWN
```

讓 policy 判斷：

```text
scene == DUNGEON_SELECT
AND DUNGEON_COOLDOWN in snapshot.overlays
→ DISMISS_OVERLAY
```

close button 僅作為 action target：

```text
overlay semantics determines WHAT to do
element determines WHERE to click
```

但本次不要為此建立新的通用 Overlay framework、workflow DSL 或 planner。

如果目前沒有足夠 perception evidence，可先只完成 Slice 1，另開 follow-up。

---

## Architectural invariants

修改後必須維持：

1. `NavigationHandler` 不新增 task-selection responsibility。
2. Policy 不直接做 CV matching 或 IO。
3. Detector / Snapshot 提供 evidence；Policy 消費 evidence。
4. Template filename 本身不得被視為完整 domain semantics。
5. 一個 tick 仍只產生一個決策。
6. Existing stage navigation path 與 sub-stage scrolling behavior 不得被改寫。
7. Existing validated dungeon cooldown behavior 不得在未建立替代 evidence 前被偷偷移除。
8. 不新增第二套 navigation state source。
9. 不因 bugfix 將 stage drawer 建成新的大型 FSM scene，除非有獨立架構需求。

---

## Acceptance criteria

### Stage regression

實際流程：

```text
STAGE_SELECT
→ click level6 island
→ stage drawer opens
→ common/quit.png visible
```

必須：

```text
NOT dismiss quit
→ continue existing sub-stage navigation
→ select target sub-stage
→ eventually START / LOADING / BATTLE
```

不得再次出現：

```text
PRIMARY_CLOSE_OVERLAY
→ close drawer
→ reopen island
→ PRIMARY_CLOSE_OVERLAY
```

### Tests

至少包含：

```text
PRIMARY + STAGE_SELECT + CLOSE_OVERLAY
    → CONTINUE_PRIMARY

PRIMARY + STAGE_SELECT + START
    → START_PRIMARY
```

並確保現有 navigation / intent / progress tests 全部通過。

若保留 Dungeon dismiss behavior，必須存在 regression test 證明其真正對應 cooldown popup，而不是僅測：

```text
DUNGEON_SELECT + CLOSE_OVERLAY
```

這個過度寬鬆的條件。

---

## Non-goals

本次不要：

* 重寫 NavigationHandler。
* 新增完整 popup FSM。
* 建立 generic overlay engine。
* 修改 stage scrolling algorithm。
* 修改 task scheduler / Daily tier priority。
* 順便清理 unrelated legacy navigation。
* 因為 edge 數量改變而重構整張 Navigation Table。

先做最小可 rollback bugfix，再根據 Dungeon investigation 決定是否進行 semantic hardening。
