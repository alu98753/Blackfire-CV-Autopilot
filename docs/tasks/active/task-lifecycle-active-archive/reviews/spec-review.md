# Spec Review

Gate-accepted verdict: BLOCK
Blocking findings: 1

# Spec Review

## Clause coverage

- **Path SSOT / resolver outcomes (Arch-Dec 1-5, AC 1-3):** `scripts/task_package_resolver.ps1` owns canonical path semantics (`Get-TaskPackageRelativePath`, `Get-TaskPackageGitPath`, `Resolve-TaskPackage`) and covers ACTIVE/ARCHIVED/MISSING/MALFORMED/AMBIGUOUS_ARCHIVE, with task-id validation on every path. Verified in the working tree.
- **Start/Scout/Gate consume resolver (Arch-Dec 6-7, AC 4):** `task_start.ps1` uses `Get-TaskPackageGitPath`, `ai_scout.ps1`/`ai_gate.ps1` use `Resolve-TaskPackage -RequireActive`; no script still reconstructs `docs\tasks\$Task`. Archive-only requests fail explicitly (TASK_MISSING / TASK_PACKAGE_MISSING), no fallback (Arch-Dec 8, AC 5).
- **Bootstrap migration / no flat-layout compatibility (Bootstrap 1-5, AC 11-12):** active package `docs/tasks/active/task-lifecycle-active-archive/` exists with SPEC.md + task.json (`models.review` explicit string present); no temporary flat-layout bridge remains in any script.
- **Docs/contracts convergence (AC 13, scope):** `docs/tasks/README.md`, `BACKLOG.md`, `ai_development_workflow.md`, agent rules/skills, `docs/todos/README.md`, and probe/harness updated to active-path semantics; gate reviewer-model contract tightened (explicit provider/model string, no default fallback) with a matching focused test.
- **Required tests (spec "Required deterministic tests"):** new `tests/test_task_package_resolver.py` and `tests/test_task_archive.py` cover resolver classifications, archive success/fail-closed, UTC year boundary, collision tokens; `test_task_start_behavioral.py` and harness migrated to active layout.
- **Archive command (spec "Archive command"):** exists; resolves exactly one active package, verifies integration via ancestry + unique first-parent merge boundary, derives UTC year from `%cI`, moves via `git mv` in a detached temp worktree, checks destination/branch collisions, forbids `-force`/destructive ops, never touches the task worktree/.venv/local branches, and reports `ARCHIVE_CLOSEOUT_READY` (deliberately distinct from ARCHIVED).

## Blocking findings

### ARCH-1
Severity: BLOCKING
Contract / invariant: SPEC "Archive command": "fail closed on ... unproven integration" and "report exactly what repository state changed ... unless the archive move is durably represented in repository history"; Invariant "preserve canonical-main cleanliness"
Location: scripts/task_archive.ps1 (durability-establishing git steps; no $LASTEXITCODE guards)
Claim: The archive script can emit `{"ok":true,"outcome":"ARCHIVE_CLOSEOUT_READY",...,"durability":"pushed closeout branch"}` even when the closeout move was never committed or never pushed, because the exit codes of `git mv`, `git commit`, and `git push` are never checked.
Evidence: In Windows PowerShell 5.1 (the target shell), a non-zero native exit code does NOT throw under `$ErrorActionPreference='Stop'`; only `$LASTEXITCODE` reveals failure. The script explicitly checks `$LASTEXITCODE` for `git merge-base` and `git worktree remove`, but the sequence `git -C $closeoutPath mv -- "docs/tasks/active/$Task" $destination` -> `git -C $closeoutPath commit ...` -> `git -C $closeoutPath push origin "HEAD:refs/heads/$closeoutBranch"` -> unconditional JSON success output has no checks. Concrete failure modes: (a) if `git mv`/`git commit` fails (path absent in origin/main, dirty stage), `$closeoutCommit` silently falls back to the pre-commit detached HEAD (origin/main SHA) and a closeout branch containing NO archive move is pushed while the script reports success; (b) if the push fails (network/auth), the script still reports `durability='pushed closeout branch'`. Both violate fail-closed and the durable-representation reporting contract, and downstream guidance (merge closeout branch, then verify resolver reports ARCHIVED) silently breaks.
Suggested validation: Focused test that forces `git push` failure (e.g., unreachable origin ad-hoc remote or a pre-created remote branch with `--force` semantics disabled) and asserts non-zero exit + no ARCHIVE_CLOSEOUT_READY payload; second test forcing empty commit (pre-delete the active package from origin/main) asserting failure rather than success. Direct inspection: add `if ($LASTEXITCODE -ne 0) { Fail 'ARCHIVE_CLOSEOUT_PREPARE_FAILED' }` after mv/commit/push.
Confidence: 0.80

## Advisory findings

- **Diff snapshot corruption (process-level):** the reviewed `diff.patch` contains mojibake at multi-byte locations (`+?? Legacy Todos`, `+?ㄗmport ...`, `+??aram()`, `?` glyphs) caused by the gate's `cmd /c chcp 65001` -> `Out-String` pipeline mis-decoding UTF-8 on this host. The actual working-tree files are intact (verified: `docs/todos/README.md`, `scripts/opencode_structured_review_probe.mjs`, `tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1` all start with correct bytes). The final review snapshot generation in `ai_gate.ps1` should be made encoding-faithful so future reviews consume accurate diffs.
- **Unclassified flat package:** `docs/tasks/backend-default-runtime-mode/` (Status: Final formal package) remains at the legacy flat path and is neither moved into `docs/tasks/active/` nor archived. After merge the resolver reports MISSING for it. Spec migration authorizes explicit human classification and forbids guessing, so this is not provably a violation, but an explicit classification record for this package is missing.
- **Sparse failure-path coverage:** tests exercise classification/UTc/fail-closed-by-state paths but not the unchecked native-exit-code failure paths above; `test_archive_contract_rejects_collision_and_branch_collision` is token-based only.

## Test evidence gaps

- No focused test exercises push/commit/mv failure inside `task_archive.ps1` (the ARCH-1 gap).
- No focused test asserts the gate diff/status snapshots are byte-faithful (mojibake regression).
- Focused test suite was not executed in this review (read-only spec review); `tests.test_task_package_resolver`, `tests.test_task_archive`, `tests.test_task_start_behavioral`, `tests.test_workflow_scripts` are the nominated targets.

<!-- blackfire-gate-fingerprint: {"schema":1,"role":"spec-reviewer","hash":"31ed23d572c0f29a4b89c96e3f8bc896e588b691502cdf67995ea82b9203c050"} -->
