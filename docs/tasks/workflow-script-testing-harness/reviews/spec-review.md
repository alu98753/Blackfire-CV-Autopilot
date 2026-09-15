VERDICT: PASS
BLOCKING_FINDINGS: 0

# Spec Review

## Clause coverage

Evidence reviewed: `task.json`, `SPEC.md` (Final), `status.txt` (`?? tests/workflow_scripts/`), `diff.patch` (docs-only: `CONTEXT.md`, `SPEC.md`, `task.json`), and the full working-tree harness `tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1` (127 lines, the only file under `tests/workflow_scripts/`).

- **Scope/structure (AC 1, 14, 15, 17):** `Invoke-WorkflowScriptHarness.ps1` exists as the stable one-command entry point; plain PowerShell, dependency-free (no Pester); production scripts untouched (diff contains no `scripts/` changes). Surface matches "Expected change surface".
- **Offline/no-live-AI (AC 2):** All child processes are local fake executables (`fake-reviewer.cmd`, `fake-scout.cmd`, `fake-test.cmd` wrapping `.ps1` helpers under `.runtime-fixtures`); every Gate/Scout invocation passes executable overrides. No network/model use.
- **Exit contract (AC 3):** Harness exits `1` when `$failed -gt 0`, else `0`; per-case PASS/FAIL printed via `Run-Case`.
- **Gate coverage (AC 4–8):** PASS→0, BLOCK→2 (exit-code contract `0/1/2` split: PASS, malformed→1, Markdown-rejection→1), candidate selection via `_ReviewCandidatesOverride` (asserts `Model: override-one`), focused-test execution via `_PythonExecutableOverride`/task.json `focused_tests`, and promotion rollback via `_FailPromotionOnTarget 'evidence'` preserving prior `EVIDENCE.md`. Malformed/`BLOCK` cases use structurally valid/invalid reviewer payloads through the same fake reviewer.
- **Scout coverage (AC 9–11):** success+promotion of `# Scout Context`-structured output; malformed output → failure + context preserved; non-zero child failure; bounded `-TimeoutSeconds 1`/sleep case with context-preservation assertion (no elapsed-time assertions — spec-compliant).
- **Fixture isolation/cleanup (AC 12, 13):** Unique `docs/tasks/workflow-harness-fixture-<timestamp>-<pid>/` disposable task package; harness-level `finally` removes `$fixtureDir`, `$helperDir`, and `.runtime/ai_gate|ai_scout/<fixtureId>` even on assertion failure (cases catch via `Run-Case`); canonical real-task artifacts are never touched.
- **Known invariants:** No parser/routing/timeout/promotion logic duplicated; helpers are fixtures only; behavior-preservation respected (no production edits in patch).

## Blocking findings

None.

## Advisory findings

- **ADV-1 (delivery gap):** `status.txt` shows `tests/workflow_scripts/` as untracked (`??`), and `diff.patch` (baseline `origin/main`) contains only the three docs files — the harness implementation is absent from the patch. The file exists in the working tree and I reviewed it, but it must be staged/committed or the merged patch will not deliver AC 1. Confirm staging before merge.
- **ADV-2 (unverified seam compatibility):** I could not read `ai_gate.ps1`/`ai_scout.ps1` before step exhaustion, so the exact override parameter names (`-_ReviewerExecutableOverride`, `-ReviewTimeoutSeconds`, `-_ReviewCandidatesOverride`, `-_FailPromotionOnTarget`, scout `-TimeoutSeconds`) and the `Model: <candidate>` EVIDENCE.md format are asserted by the harness but not yet cross-checked against production code. All names are consistent with the CONTEXT.md seam inventory, but AC 16 (the command passes) is the authoritative check.
- **ADV-3 (verification contract evidence):** The patch carries no record of the Writer having run `.\tests\workflow_scripts\Invoke-WorkflowScriptHarness.ps1` as required before Gate. This is a process-evidence gap, not a spec violation in the code itself.
- **ADV-4 (stale `$LASTEXITCODE` risk):** `Invoke-Script` relies on `$LASTEXITCODE` after a pipeline with `Out-Null`; a native-launch failure that doesn't throw would fall through to `$LASTEXITCODE`. Low risk because `ExitCode` is set by the `-File` child, but a defensive explicit capture is possible.

## Test evidence gaps

- No executed harness run results are present (AC 16 / Verification contract) — evidence is the passing run recorded by the Writer.
- Fallback reachability: the fake reviewer's `fail`/exit-7 mode appears reachable only if Gate passes candidate names (`first`/`second` from the fixture task.json) as reviewer arguments in cases 5–6; unverified against `ai_gate.ps1` invocation semantics.
- Cross-version PowerShell behavior (`Get-Process $PID .Path` as the child interpreter) untested; acceptable since it runs on the user's Windows PowerShell.

## Recommendations for next steps

1. Confirm `tests/workflow_scripts/**` is staged so the candidate patch actually contains the harness (ADV-1).
2. Run `.\tests\workflow_scripts\Invoke-WorkflowScriptHarness.ps1` once and record output/exit code as the AC 16 evidence; investigate any case that fails (especially the `Model:` assertion and rollback case).
3. Verify seam parameter names in `scripts/ai_gate.ps1`/`scripts/ai_scout.ps1` against the override names used by the harness (ADV-2).
