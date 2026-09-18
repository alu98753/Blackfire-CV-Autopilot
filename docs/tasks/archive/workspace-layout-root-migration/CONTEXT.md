Now let me read the focused behavioral test and scan for stale layout references across the documented surface.
Now checking whether production code (outside tests) references the old layout name, and reading the two scope-listed skill docs.
Maximum steps for this agent have been reached. Tools are disabled; this is a text-only final report.

# Scout Context

## Relevant files and symbols

- **`scripts/task_start.ps1`** (read, 501 lines) ??Primary path-coupled defect. Lines 138??44 discover canonical main topology-first; lines 264??69 derive `$worktreesRoot` as `Join-Path (Split-Path $canonicalRoot -Parent) 'worktrees'` unless `TASK_START_WORKTREES_ROOT_OVERRIDE` is set. Under the new layout (`canonicalRoot = E:\Side_Project\Blackfire-CV-Autopilot`) the default silently becomes `E:\Side_Project\worktrees`, violating acceptance criterion 3. No hardcoded `BlackfireCrusade_tool` string exists in the script ??main discovery is already topology-driven (criterion 5 currently satisfied).
- **`scripts/task_cleanup.ps1`** (read, 178 lines) ??Task worktree found by leaf-name match over `worktree list --porcelain` (`Split-Path -Leaf` equals task id, line 124), not by a computed sibling root. It does **not** assume task paths share a project parent; location-agnostic, so it survives the migration unchanged (answers SPEC Uncertainty question 3: no indirect parent-directory assumption).
- **`tests/test_task_start_behavioral.py`** (read, 527 lines) ??15 focused fail-closed/happy-path cases. Fixture names main `base/"BlackfireCrusade_tool"` (line 92, cosmetic). **Every success/failure test injects `TASK_START_WORKTREES_ROOT_OVERRIDE`; no test asserts the default sibling-root derivation** (SPEC Uncertainty question 4 confirmed as a real gap).
- **`docs/architecture/ai_development_workflow.md`** (grep) ??Lines 43??3 still present the nested `BlackfireCrusade_tool\` + `worktrees\` layout as canonical current state with absolute old paths.
- **`.agents/skills/branch_start_workflow/SKILL.md`** and **`branch_completion_workflow/SKILL.md`** (grep) ??Both still encode the old ASCII layout (lines 33??4 / 84??5), old absolute main path, and `worktrees\<task-id>` example paths.
- **`tests/test_task_cleanup_behavioral.py`** (grep only) ??fixture also names main `BlackfireCrusade_tool` (line 58); content not read within budget.
- **`tests/test_behavior_pause_resume.py`** (grep) ??Window-title guard tests keyed on the literal `BlackfireCrusade_tool` string in window titles (lines 177??13). This is a **live repository-owned contract outside the declared Scope** that will break functionally once the directory is renamed; no production `.py` reference to the old name was found, only this test.

## Current control flow

`task_start.ps1`: validate args ??discover dependency-free common dir from `$scriptRoot` (or `TASK_START_COMMON_DIR_OVERRIDE`) ??derive `canonicalRoot` ??verify topology/branch/cleanliness of main ??fetch ??FF-only sync ??remote task branch/base/artifact validation ??**derive worktree root (defect point)** ??topology state machine (reuse/conflict/owned/created) ??post-attach artifact validation ??delegate venv bootstrap to `worktree_environment_bootstrap.ps1` ??emit one-line JSON result. `task_cleanup.ps1`: resolve main from topology ??safety helper detach ??`worktree remove` ??branch delete ??path-agnostic throughout.

## Existing safety mechanisms

- Fail-closed result codes for every failure class (`CANONICAL_MAIN_*`, `WORKTREE_PATH_CONFLICT`, `BRANCH_OWNED_ELSEWHERE`, `TASK_BRANCH_*`, `PYTHON_BOOTSTRAP_FAILED`, etc.).
- Clean-main requirement, fetch + `--ff-only`, branch-exclusivity and reuse rules preserved (criterion 6 dependencies).
- `TASK_START_WORKTREES_ROOT_OVERRIDE` override remains (criterion 4) ??no removal justified by evidence.
- Worktree-preservation on bootstrap failure is tested (`test_python_bootstrap_failure_preserves_worktree`).

## Existing tests

- `test_task_start_behavioral.py`: argument validation; canonical-main missing/dirty/wrong-branch/diverged; remote branch missing; stale base; missing/invalid task package; happy-path create; idempotent reuse; dirty-reuse fail-closed; branch-owned-elsewhere; unregistered-path conflict; wrong-branch registration; bootstrap failures preserve worktree.
- `test_task_cleanup_behavioral.py` (unread): analogous fail-closed cleanup coverage per task.json `focused_tests`.
- `test_worktree_environment_bootstrap.py` (unread): venv junction/readiness contract.
- Gap: **no test exercises default (override-free) worktree-root derivation**; the new layout is therefore only protectable via a new focused test.

## Regression and architecture risks

- **Default-derivation drift**: changing line 267 to sibling layout alters every create/reuse path; reuse of *existing* `E:\Side_Project\worktrees\*` tasks would silently break ??the migration must decide retain-vs-relocate for current linked worktrees (e.g., this very worktree is `...\worktrees\workspace-layout-root-migration`). Non-goal "moving active/dirty task worktrees" conflicts with wholesale cleanup of the old namespace.
- **Linked-worktree `.git` metadata**: primary-worktree move preserves `.git/` as a directory, but linked worktrees point at the common dir via `gitdir:` lines; if absolute, they break after main relocation. Could not verify `gitdir:` formats without inspecting filesystem (out of read budget; topology currently non-empty on this machine).
- **Out-of-scope live contract**: `test_behavior_pause_resume.py` window-title keywords name the old directory; renaming invalidates a runtime safety guard. SPEC scope permits only workflow tests/docs changes; this test sits outside, so SPEC scope or acceptance notes must address it explicitly.
- **Historical-vs-live prose**: dozens of stale references exist in `docs/todos/*`, archive task specs, stories, guides (mostly log transcripts = historical). Only `ai_development_workflow.md` and the two skills present the old layout as *canonical current state*.
- `task_cleanup.ps1` leaf-name matching is ambiguous only if two worktrees share a task leaf; pre-existing, not introduced by migration.

## Uncertainty

- Default-derivation behavior for legacy tasks already living under the old `worktrees\` root is unspecified by the SPEC (creation would now target the new sibling namespace ??divergent duplicate risk unless migration procedure covers it).
- Whether `test_behavior_pause_resume.py` keyword list is considered in-scope; SPEC does not list it.
- `test_task_cleanup_behavioral.py`, `test_worktree_environment_bootstrap.py`, and the skills' full bodies were not read within budget; findings limited to grep evidence.

## Minimal proposed change surface

1. `scripts/task_start.ps1:264-269` ??replace `'worktrees'` cluster with sibling-name derivation (e.g., `<parent of main>\Blackfire-CV-Autopilot-worktrees`), keeping the override branch.
2. `tests/test_task_start_behavioral.py` ??add one override-free default-derivation test (topology-driven) plus a legacy-namespace coexistence case; refresh fixture naming.
- Whether relocation needs Git metadata repair: current linked topology is **non-empty** (this worktree); `gitdir:` pointer type (absolute vs relative) in existing linked worktrees was not inspected.
3. `docs/architecture/ai_development_workflow.md` + both skills ??demote old layout to historical context, insert new canonical paths.
4. SPEC: explicitly rule on `test_behavior_pause_resume.py` keyword contract and legacy-worktree retention/relocation.

## Recommendation

**GO WITH SPEC CHANGES.** The single code defect is precisely localized (`task_start.ps1:267`) and cleanup is already layout-agnostic, but the SPEC must (a) answer the designed-in uncertainty about Git metadata repair for non-empty linked topology, and (b) rule on the pause/resume window-title contract currently outside declared scope ??otherwise a live safety guard goes stale under the renamed layout.
