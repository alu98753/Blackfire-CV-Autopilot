# Regression Review

Gate-accepted verdict: PASS
Blocking findings: 0

# Regression Review

## Behavior-preservation assessment

The diff intentionally preserves the workflow contracts that must not change:
- task_cleanup.ps1 is untouched (local-cleanup-only boundary intact, acceptance criterion 10; its behavioral tests are unchanged and still listed in focused_tests).
- Worktree-topology, branch-exclusivity, gate resume/cache/fingerprint, and cleanup safety logic in ai_gate.ps1 is unchanged except for the taskDir resolution, prompt paths, excludes, and the reviewer-model policy.
- Runtime game behavior is untouched (no non-docs/scripts-tests files changed).
- Start/Scout/Gate no longer independently construct the active package root: task_start.ps1 uses Get-TaskPackageGitPath for remote cat-file/show checks and local post-attachment validation; ai_scout.ps1 and ai_gate.ps1 both resolve through Resolve-TaskPackage -RequireActive and fail closed (TASK_MISSING/TASK_ARCHIVED/TASK_MALFORMED) without any fallback to legacy or archive paths. Verified by full read of both scripts plus repo-wide grep: no production script still builds `docs\tasks\<task>` literally.
- Resolver classifications ACTIVE/ARCHIVED/MISSING/AMBIGUOUS_ARCHIVE/MALFORMED are implemented and exercised by the new focused resolver tests; Git-path consumers (git cat-file -e, ls-tree, status/diff excludes) share the same canonical relative path string.
- Archive command fails closed: requires clean canonical main at origin/main, exactly one clean task worktree whose tip is an ancestor of origin/main, exactly one first-parent merge boundary containing task HEAD, UTC year from the integration commit, destination and closeout-branch collision checks, and a pushed temp closeout branch (HEAD:refs/heads/archive/<task>-<year>); the canonical main worktree is never mutated (move/commit/push happen in a temp detached worktree). `ARCHIVE_CLOSEOUT_READY` is explicitly not `ARCHIVED`, matching the SPEC's remote-closeout handoff design.
- Current task bootstrap is coherent: the package is fully tracked at docs/tasks/active/task-lifecycle-active-archive/ (SPEC, task.json, CONTEXT.md, EVIDENCE.md, reviews), Gate/Scout resolve it as ACTIVE, and the workflow snapshot (empty status.txt; diff generated against origin/main with active-path excludes) was produced by the migrated gate itself.

## Blocking findings

None.

## Advisory findings

1. **Dot-sourced Set-StrictMode changes caller scope.** task_package_resolver.ps1 runs `Set-StrictMode -Version Latest` at top level; because all four callers dot-source it, strict mode now activates in ai_gate.ps1 / ai_scout.ps1 / task_archive.ps1 (task_start already set it). No uninitialized-variable landmines were found in the exercised paths, but access to optional/absent task.json keys (e.g. `$config.scope` in Get-ReviewFingerprint, `$config.models` in scout) now throws PropertyNotFoundException instead of yielding $null. Both outcomes fail closed, but the failure mode changed; a focused test pinning the malformed-task.json behavior would harden this.

2. **Unmigrated legacy flat packages remain in main.** docs/tasks/ still contains flat packages (backend-default-runtime-mode, cli-io-mode-contract-cleanup, domain-common-template-decoupling, domain-lobby-primary-start-boundary, foreground-demo-mode-isolation, generic-domain-catalog-expansion), one of which (domain-lobby-primary-start-boundary) is merged into this branch's history. They are neither active/ nor archived/, so the resolver reports MISSING for them. This is consistent with per-branch human-classified migration, but should be explicitly classified (migrate or archive on their owning branches) before claiming acceptance criterion 12/14 fully closed.

3. **task_archive.ps1 hardcodes the move source.** It dotsources the resolver but uses the literal `docs/tasks/active/$Task` for `git mv` instead of `Get-TaskPackageRelativePath`. Today the paths are identical, but the resolver is the declared single owner of path semantics; using the function would prevent future silent drift (minor).

4. **Cosmetic byte-level changes.** BOM was inserted at the start of scripts/opencode_structured_review_probe.mjs, docs/todos/README.md, and Invoke-WorkflowScriptHarness.ps1 (Node strips the .mjs BOM per spec; PowerShell 5.1 tolerates BOM on .ps1); trailing newlines added to several files; scout throw line has an over-indented block. Style-only, no behavior impact.

5. **Scout cmd/bat override quoting.** `Invoke-ScoutProcessAttempt` now routes .cmd/.bat overrides through `cmd.exe /d /s /c` with a hand-built quoted argument string; the harness exercises it with simple args, but quoting edge cases (embedded quotes) differ from the previous CreateProcess quoting. Test-only surface (uses `_ExecutableOverride`).

<!-- blackfire-gate-fingerprint: {"schema":1,"role":"regression-reviewer","hash":"3cd4bc27b567e9277929a15b3fca5334c1356c60e1e62efe5612b2c0bc66caf7"} -->
