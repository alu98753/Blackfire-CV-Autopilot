# Regression Review

Gate-accepted verdict: PASS
Blocking findings: 0

# Regression Review

## Behavior-preservation assessment

The diff migrates the task-package layout from flat `docs/tasks/<task-id>/` to `docs/tasks/active/<task-id>/` plus `docs/tasks/archive/<year>/<task-id>/`, and makes reviewer-model selection a single-explicit-string contract. Grounded inspection confirms:

- `scripts/task_start.ps1`, `scripts/ai_scout.ps1`, `scripts/ai_gate.ps1` now obtain the canonical active path from `task_package_resolver.ps1` (`Resolve-TaskPackage -RequireActive` / `Get-TaskPackageGitPath`); grep across `*.ps1` finds no surviving reconstruction of the flat `docs\tasks\<task>\` path. Remote preflight (`cat-file -e "$remoteRef:$taskGitPath/SPEC.md"`) and local post-attachment checks both use the resolver-derived path. Startup fail-closed guarantees (`TASK_PACKAGE_MISSING`/`TASK_PACKAGE_INVALID`) are preserved with the new path in messages.
- `ai_gate.ps1` `Resolve-Candidates` now fails fast on null/array/empty/malformed `models.review` per the SPEC's approved reviewer-model contract; all in-repo fixtures (`Invoke-WorkflowScriptHarness.ps1`, `task.json`) were updated to single `provider/model` strings, and harness cases were reworked from candidate-fallback semantics to no-fallback `VERIFICATION_UNAVAILABLE` (exit 1) semantics. Fingerprint/reuse, promotion rollback, and terminal PASS/BLOCK handling are unchanged in structure; the harness splits the monolithic run into five gated groups matching `task.json` focused_tests.
- `task_archive.ps1` preserves canonical-main cleanliness (requires clean status, HEAD == origin/main after fetch, dispatch failure codes for dirty worktree/unproven integration/ambiguous boundary/collisions) and performs the move only in a temporary detached worktree, with plain `git worktree remove` (no `--force`) in the finally. No local cleanup or destructive git operations are present.
- Existing archived packages (~31) are pure 100%-similarity renames with no content modifications; no tracked artifact is dropped.

## Blocking findings

None.

## Advisory findings

- **Diff snapshot fidelity (evidence quality):** `diff.patch` lines 1122, 1290, 1790 render `+#`-style first-line changes as mojibake (`+?? Legacy Todos`, `+?ㄗmport ?圳, `+??aram(`). Actual working-tree files read cleanly (`# Legacy Todos`, `import { execFile?圳, `param(`), so this is the gate's `chcp 65001`/cmd/`Out-String` snapshot pipeline transcribing leading UTF-8 BOM bytes, not file corruption. The snapshot artifact given to reviewers is partially garbled and the same artifact is hashed into review fingerprints; consider stripping/normalizing BOMs before snapshot generation.
- **`task_archive.ps1` bypasses the resolver for move paths:** `git mv` source (`docs/tasks/active/$Task`, line 56) and destination (`docs/tasks/archive/$year/$Task`, line 39) are literal paths while the script dot-sources the resolver. SPEC decision 3 declares the resolver the single owner of path semantics; currently identical, this is silent-drift risk (same as prior regression-review note).
- **Probe hardcodes an archived package path:** `opencode_structured_review_probe.mjs` QUALIFICATION/SMOKE prompts reference `docs/tasks/archive/2026/opencode-structured-review-provider-compatibility/?圳, valid only because this diff archives that package; any future re-archive or cleanup of that package silently breaks probe prompts.
- **Encoded newline/whitespace churn:** `branch_completion_workflow/SKILL.md` diff shows an odd byte fragment (`worktree??觔t temp-main??) in a Manual-fallback sentence; verify the committed file's intended wording during final review.
- **Unverified (bounded review):** remaining legacy flat directories under `docs/tasks/` (the spec-review mentioned five unclassified packages) and stale `docs/tasks/<task-id>/` prose outside the `active/archive` paths were not exhaustively confirmed; acceptance criterion 12/13 verification should re-scan after merge.

## Suggested validation

Run the focused tests in `task.json` (`test_task_package_resolver`, `test_task_archive`, `test_task_start_behavioral`, `test_task_cleanup_behavioral`, five `test_workflow_scripts` group cases) on a clean clone; confirm the resolver reports exactly one ACTIVE package for this task and that `Resolve-TaskPackage` throws `TASK_MALFORMED` for a mismatched `task.json` id under `RequireActive`.

<!-- blackfire-gate-fingerprint: {"schema":1,"role":"regression-reviewer","hash":"175be8cd856b998e60b573a54130867b5bc73e23f7055d1608e69bed5c08c2a0"} -->
