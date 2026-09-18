# Regression Review

Gate-accepted verdict: BLOCK
Blocking findings: 2

# Regression Review

## Behavior-preservation assessment

The diff intentionally changes the task-package layout (`docs/tasks/active/<task-id>/` + `docs/tasks/archive/<year>/<task-id>/`), the reviewer-model contract (`models.review` must be a single explicit `provider/model` string; arrays/null/defaults invalid), and the post-integration closeout flow (new `task_archive.ps1` + resolver). Flat-layout path construction was removed from `task_start.ps1` / `ai_scout.ps1` / `ai_gate.ps1` and replaced with resolver calls; renames of legacy packages to `archive/2026/` are 100% similarity renames (no content drift). Snapshot mojibake (`??`/`?ㄗmport`) verified as diff.patch generation artifacts, not repository corruption ??actual files are clean. The pre-existing Gate candidate-fallback, Scout multi-candidate, and reviewer staging/promotion behaviors were NOT preserved for the candidate-array path: the harness still instantiates array configs the new gate rejects, and `task_archive.ps1` introduces a false-success closeout path on native-command failure.

## Blocking findings

### H1
Severity: BLOCKING
Regression / invariant: Focused workflow-harness tests now fail under the changed candidate-resolution contract (SPEC acceptance #15 "Focused deterministic tests pass").
Location: scripts/ai_gate.ps1:25-35 vs tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1:361-405
Claim: `Gate valid structured BLOCK returns 2`, `Gate valid structured PASS is terminal`, `Gate pre-authority failure falls back to next candidate`, `Gate safe transport envelope falls back with exit zero`, and `Gate catastrophic adapter failure has no envelope` set `models.review` to a two-element array and invoke the gate without `-ReviewModel`/`-_ReviewCandidatesOverride`; the new `Resolve-Candidates` throws `candidate arrays are not allowed` before any reviewer runs, so the gate exits 1 (not 2/0) and the expected reviewer marker files are never created.
Evidence: New `Resolve-Candidates` (`ai_gate.ps1:29-30`) throws when `$raw -isnot [string]`; old implementation returned `@($raw | ForEach-Object ...)` for arrays, which is exactly what the pre-existing harness cases (unchanged by this diff, per diff.patch) depend on. `tests/test_workflow_scripts.py::test_windows_workflow_harness` (line 381-386) executes the full harness with 240s timeout and asserts exit 0, so the task's own focused suite fails.
Suggested validation: Run `tests.test_workflow_scripts` (or the harness directly). Update the harness cases to either pass `-ReviewModel <single-string>` or assert the new single-candidate config contract; verify exit codes and markers as expected.
Confidence: 0.92

### H2
Severity: BLOCKING
Regression / invariant: `task_archive.ps1` can emit `ARCHIVE_CLOSEOUT_READY` / `durability="pushed closeout branch"` while the push or the archive move actually failed, violating SPEC "must not claim archival completion unless the archive move is durably represented in repository history" and "report exactly what repository state changed".
Location: scripts/task_archive.ps1:44-55
Claim: Under PowerShell 5.1, native `git` exit codes are not checked after `git worktree add`, `git mv`, `git commit`, or `git push`; any of these failures is silently followed by `finally { git worktree remove ... }` and then unconditional emission of the ARCHIVE_CLOSEOUT_READY JSON with exit 0. On push failure the local closeout commit is destroyed by the worktree removal, yet the script reports a pushed closeout branch; on `git mv` failure the closeout branch is created pointing at plain origin/main HEAD with no archive move, still reported as ready.
Evidence: Only the `finally` block checks `$LASTEXITCODE` (task_archive.ps1:52-53). `$ErrorActionPreference='Stop'` does not make PowerShell 5.1 throw on native exit codes elsewhere in the script. Tests only cover the success path and pre-worktree fail-closed paths (tests/test_task_archive.py:1470-1501), so this false-success path is unexercised.
Suggested validation: Add a focused harness case blocking the push (e.g., pre-create `refs/heads/archive/<task>-<year>` on origin after the ls-remote check, or point origin at an unreachable URL) and assert non-zero exit + no ARCHIVE_CLOSEOUT_READY payload; likewise for a failing `git mv`.
Confidence: 0.85

## Advisory findings

- `task_archive.ps1:47,35` hardcodes `docs/tasks/active/$Task` and `docs/tasks/archive/$year/$Task` literals instead of consuming `Get-TaskPackageRelativePath` / resolver outcome; functionally identical today but duplicates path semantics the SPEC assigns to one owner (invariant "Task-package path semantics have one implementation owner").
- `task_package_resolver.ps1:2` `Set-StrictMode -Version Latest` leaks into dot-sourced callers (`ai_gate.ps1`, `ai_scout.ps1` previously ran without strict mode); no concrete failure found in scanned code, but the scope side effect is a latent risk for future edits.
- New `Resolve-Candidates` truncates `_ReviewCandidatesOverride` to its first element (`ai_gate.ps1:26`); previously all override values formed the candidate list. The harness's `$reviewBase` passes `'first','second'` and still passes only because cases assert the first model; multi-candidate fallback through the CLI override is silently gone.
- `task_archive.ps1:12-14` requires the invoking worktree to be clean and at `origin/main` HEAD; the skill text does not state that `task_archive.ps1` must run from the canonical permanent `main` worktree. Running it from the task worktree fails closed (ARCHIVE_REQUIRES_CANONICAL_MAIN_AT_ORIGIN_MAIN), but the documentation gap should be closed.

<!-- blackfire-gate-fingerprint: {"schema":1,"role":"regression-reviewer","hash":"16f68e9fcdde25012042a433db69eadc14b183bdc611d48c5eba862d54aaad93"} -->
