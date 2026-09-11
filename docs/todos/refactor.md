目前 feature 已完成，而且我已經在兩個 worktree 分別跑過完整 test suite：

* `main` worktree：作為 baseline
* 目前 feature branch `HEAD` worktree：作為本次變更結果

你可以直接查看並比較兩邊的完整測試結果。

本次任務的目標是：

> 在不改變已完成 feature observable behavior 的前提下，清理本 branch 引入或暴露出的 dead code、重複邏輯、temporary glue、legacy path 與不必要複雜度，讓後續維護與新增功能更容易。

---

## Phase 1 — Baseline Audit

先不要修改任何 production code。

比較 `main` 與 `HEAD` 的完整測試結果，將 failures 分類為：

* `PRE_EXISTING_FAILURE`

  * `main` 與 `HEAD` 都失敗
  * 屬於既有問題

* `BRANCH_REGRESSION`

  * `main` 通過
  * `HEAD` 失敗
  * 視為本 branch 新增 regression

* `EXPECTED_BEHAVIOR_CHANGE`

  * `main` 測試 expectation 已因本 feature 的合法需求改變而過期
  * 必須能由 spec / contract / acceptance criteria 證明

* `UNCERTAIN`

  * 無法確定是 production bug、test 問題或需求語意不清

如果存在 `BRANCH_REGRESSION` 或 `UNCERTAIN`：

* 先不要開始 refactor
* 先確認問題來源
* 不得直接修改 test expectation 讓它變綠

若測試本身過期，請先說明依據，再獨立修正測試。

---

## Phase 2 — Refactor Safety Check

檢查本 feature 的重要 observable behavior 是否已有足夠 regression coverage。

重點不是 coverage percentage，而是：

> 如果等等 refactor 改壞本 feature 的核心行為，目前測試是否能抓到？

如果缺少必要的 behavior / characterization tests：

* 先補測試
* 不要綁 private helper 或 implementation detail
* 測試與 production refactor 分開 commit

如果現有 safety net 已足夠，直接進入下一階段。

---

## Phase 3 — Maintenance Refactor Audit

請 review：

```text
git diff main...HEAD
```

以及本 branch 修改到的 production code、相關 specs、contracts、tests。

優先檢查：

* dead code
* unused imports
* unused helper / method
* obsolete flag
* legacy fallback
* compatibility path
* feature 完成後已不再需要的 temporary glue
* duplicated logic
* duplicated state ownership
* unnecessary branching
* special-case patch
* overly complex control flow
* responsibility leakage
* dependency direction violation
* 命名與 ownership 不清
* 可以安全簡化的 config / state / registry handling

修改前先輸出：

### Refactor Audit

* Safe dead code removal:
* Safe simplifications:
* Safe duplication removal:
* Ownership / boundary issues:
* Compatibility logic that must remain:
* Deferred architecture issues:
* Items explicitly out of scope:

---

## Phase 4 — Behavior-Preserving Refactor

只處理：

* 與本 branch 直接相關
* 可以由現有測試保護
* 不需要改變 observable behavior
* 不需要大型 architecture migration

的 refactor。

硬性限制：

1. 不得新增功能。
2. 不得改變已完成 feature 的 observable behavior。
3. 不得順便重寫無關模組。
4. 不得為了「漂亮」建立沒有明確維護價值的新 abstraction。
5. 不得修改正確的 behavior tests 來配合 refactor。
6. Refactor 後原本通過的測試失敗，優先視為 regression。
7. 刪除 dead code 前必須確認沒有：

   * runtime caller
   * callback / registry reference
   * dynamic dispatch
   * config-driven invocation
   * CLI / script entry
   * reflection-like usage
8. 需要 behavior change 才能處理的問題，移出本次。
9. 需要大型 migration / redesign 的問題，列為 deferred work。
10. 不擴大到 `main...HEAD` 之外的無關 cleanup。

---

## Git Strategy

如果需要補 safety tests：

```text
test: add regression coverage for <behavior>
```

如果需要修正已證明過期的 test：

```text
test: correct stale expectation for <behavior>
```

正式 refactor：

```text
refactor: simplify <scope> after feature implementation
```

不要把 test correction、behavior change、refactor 混在同一個 commit。

---

## Verification

Refactor 完成後：

1. 跑所有與修改直接相關的 focused tests。
2. 再跑 feature branch 的完整 test suite。
3. 將結果與 refactor 前的 HEAD baseline 比較。
4. 確認：

   * 原本通過的 tests 沒有新增 failure
   * known pre-existing failures 沒有因 refactor 增加
   * branch-specific behavior tests 維持通過
   * 沒有為了讓測試通過而修改正確 expectation

最後輸出：

### Final Refactor Report

* Removed dead code:
* Simplified logic:
* Reduced duplication:
* Ownership / boundary improvements:
* Tests added before refactor:
* Tests corrected before refactor:
* Pre-refactor HEAD baseline:
* Post-refactor full-suite result:
* Known pre-existing failures:
* New failures introduced: `NONE`
* Deferred architecture work:
* Behavior changed: `NO`

如果無法確認：

```text
New failures introduced: NONE
Behavior changed: NO
```

則不要把本次工作視為 refactor 完成。
