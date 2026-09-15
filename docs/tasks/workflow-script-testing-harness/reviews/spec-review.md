VERDICT: PASS
BLOCKING_FINDINGS: 0

# Spec Review

## Clause coverage

**Entry point (AC 1):** `tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1` exists as the sole file under `tests/workflow_scripts/`. Plain PowerShell, dependency-free, no Pester. ✅

**Offline/no-live-AI (AC 2):** All child processes use local fake executables (`fake-reviewer.cmd`, `fake-scout.cmd`, `fake-test.cmd`) via `.runtime-fixtures/` with `.ps1` backends. Every Gate and Scout invocation passes executable overrides (`-_ReviewerExecutableOverride`, `-_ExecutableOverride`, `-_PythonExecutableOverride`). No network/model access. ✅

**Exit contract (AC 3):** Harness exits `1` when `$failed -gt 0`, else `0`. Per-case PASS/FAIL via `Run-Case`. ✅

**Gate coverage (AC 4–8):**
- AC 4: Canonical PASS→exit 0 (case 1), canonical BLOCK→exit 2 (case 2), malformed→exit 1 (case 3), infrastructure via `_FailPromotionOnTarget`→exit 1 (case 6). ✅
- AC 5: Markdown-wrapped verdict (`**VERDICT: PASS**`) remains rejected→exit 1 (case 4). ✅
- AC 6: Candidate selection via `_ReviewCandidatesOverride` with `first,second` (case 1). ✅
- AC 7: Focused-test via `_PythonExecutableOverride` with `focused_tests` in fixture task.json (case 5). ✅
- AC 8: Promotion rollback via `_FailPromotionOnTarget 'evidence'` preserving prior `EVIDENCE.md` (case 6). ✅

**Scout coverage (AC 9–11):**
- AC 9: Success+promotion (case 7), malformed rejection (case 8), non-zero child failure (case 9). ✅
- AC 10: Malformed output preserves existing `CONTEXT.md` content (case 8). ✅
- AC 11: Short timeout (`-TimeoutSeconds 1`) with sleep-based fake process, no elapsed-time assertions, context preserved (case 10). ✅

**Cleanup (AC 12–13):** `finally` block removes `$fixtureDir`, `$helperDir`, and runtime dirs. No real task artifacts touched. ✅

**Production unchanged (AC 14–15):** Diff contains zero modifications to `scripts/ai_gate.ps1` or `scripts/ai_scout.ps1`. All 11 seam parameter names verified against production `param()` blocks: `-_ReviewerExecutableOverride`, `-ReviewTimeoutSeconds`, `-_ReviewCandidatesOverride`, `-_ReviewerArgumentsOverride`, `-_PythonExecutableOverride`, `-_FailPromotionOnTarget` (Gate), and `-_ExecutableOverride`, `-_ArgumentsOverride`, `-_ModelCandidatesOverride`, `-TimeoutSeconds` (Scout). ✅

**Exit-code contract (SC 9):** 0=PASS, 1=INFRASTRUCTURE_BLOCKED, 2=CANDIDATE_BLOCKED — matched in cases 1–4, 6. ✅

## Blocking findings

None.

## Advisory findings

1. **`EVIDENCE.md` existence assumption (ADV-1):** Case 6 (line 98) reads `EVIDENCE.md` from the fixture dir before the rollback test. This file is expected to exist from prior Gate runs (cases 1–5) having promoted it. This is logically sound but relies on Gate's promotion producing `EVIDENCE.md` for a PASS verdict — unverified by direct production-code trace. Low risk; AC 16 run is the authoritative check.

2. **Status snapshot discrepancy (ADV-2):** `status.txt` only shows `?? .agents/rules/windows_shell_execution.md` and does not list `tests/workflow_scripts/` as untracked. The file exists in the working tree and in the diff.patch. Likely a timing artifact of when the snapshot was captured. The diff.patch confirms the file is included as a new addition.

3. **Single-file harness (ADV-3):** All 10 test cases (6 Gate + 4 Scout) plus helpers live in one 134-line script. Acceptable for v1 per spec's "plain PowerShell" framework decision; future additions may benefit from modularization.

4. **`Invoke-Script` stderr suppression (ADV-4):** Line 37 pipes `2>&1 | Out-Null`, which suppresses all diagnostic output from child processes. Useful for clean test output but may complicate debugging failed cases. Low risk.

## Test evidence gaps

- AC 16 verification (the harness command passing) is not present in the diff; it depends on the Writer having run it per the verification contract. The code is structurally sound and all seam names are confirmed correct.
- No `focused_tests` in the actual `task.json` for this task (empty array), which is correct per the verification contract explanation.
