Now let me read the current state of the key files to verify the diff was applied correctly:
VERDICT: PASS
BLOCKING_FINDINGS: 0

# Spec Review


**Agent contracts (Acceptance criteria 1-2):** All three agent frontmatter blocks migrated from legacy `permission` to V2 `permissions` with broad deny + narrow allow for `read`, `glob`, `grep`, and explicit deny for `edit`, `shell`, `subagent`, `execute`, `external_directory`, `webfetch`, `websearch`. Scout has `steps: 6`; both reviewers have `steps: 5`. Prompt body updated to bounded-blocker-detector semantics with early-stop guidance and concise PASS output budget (300-600 words). Spec clause 3.1 (Scout contract), 3.2 (Reviewer contracts), 3.3 (Read-only boundary) all satisfied.

**Scout prompt deduplication (Acceptance criterion 3):** `ai_scout.ps1` prompt replaced hardcoded "10 files" / "1500 words" with "Strictly follow the file and word budget limits defined in the scout agent contract." Single authoritative surface in `scout.md`. Spec clause 3.4 satisfied.

## Clause coverage
**Formal invocation isolation (Acceptance criteria 4-5):** `ai_scout.ps1` adds `--standalone` to both PowerShell-wrapper and direct-binary code paths, adds `$psi.WorkingDirectory = $repoRoot`, adds `$psi.RedirectStandardInput = $true` + `$proc.StandardInput.Close()`. `ai_gate.ps1` adds `--standalone` to `Get-OpenCodeInvocation`, adds `$psi.WorkingDirectory = $repoRoot` to `Invoke-BoundedProcess` (stdin close was already present). Override seams preserved. Spec clause 3.5 satisfied.

**Gate semantics (Acceptance criterion 6):** `Test-ReviewVerdictStructure`, exit code logic (0/1/2), focused-test rejection, transaction-safe promotion, and rollback all remain untouched in the diff. Spec invariant 5-6 preserved.

**Workflow documentation (Acceptance criterion 12):** `ai_development_workflow.md` updated: Scout description reflects `steps: 6`, 5-6/8 file budgets, 600-800/1000 word budgets; reviewer descriptions reflect `steps: 5`, bounded blocker detector, concise output; Phase B and Phase D descriptions reflect `--standalone` isolation.

**No game/runtime changes (Acceptance criterion 14):** No game files touched.
## Blocking findings


None.

## Advisory findings

1. **BACKLOG.md out of declared scope:** The diff includes significant editorial reorganization of `docs/tasks/BACKLOG.md` (condensing the roadmap, moving this task to Active). This file is not in `task.json` scope or SPEC production change surface. Changes are administrative/editorial and do not alter any behavioral contract or invariant. Not blocking.

2. **Runtime verification probes (AC 7-13) not in this diff:** Acceptance criteria 7-13 require runtime probes (read-only boundary proof, orphan-process check, real Scout/Gate smoke runs). These are separate verification activities expected to run after the contract changes land, not part of the contract-hardening diff itself.

## Test evidence gaps

The diff implements all structural/contractual changes correctly in the agent configs and scripts. Runtime verification evidence (read-only permission probe, standalone lifecycle probe, real Scout/Gate smoke runs) is expected as follow-up verification, not as part of this patch. The `CONTEXT.md` Scout output is included as evidence of a successful real Scout run.
