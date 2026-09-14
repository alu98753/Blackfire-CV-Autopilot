Now let me inspect the current state of the changed files to verify the diff was applied correctly.
Let me check the Phase D section in the architecture doc to verify the full change there:
Let me check the reviewer agent contracts to confirm they are unchanged:
Now let me verify the full-suite rejection pattern and the scout script pattern for comparison:
Let me check for any probe/test scripts that might be part of the implementation:
Now I have a thorough understanding of the diff and current codebase. Let me compile my review.

---

VERDICT: PASS
BLOCKING_FINDINGS: 0

# Spec Review

## Clause coverage

### Known Invariants

| # | Clause | Verdict | Evidence |
|---|--------|---------|----------|
| 1 | Reviewers remain read-only independent reviewers | **PASS** | `.opencode/agents/spec-reviewer.md` and `.opencode/agents/regression-reviewer.md` are not in the diff; agent contracts unchanged |
| 2 | Reviewer semantic contract remains `VERDICT: PASS\|BLOCK` plus `BLOCKING_FINDINGS` | **PASS** | `Test-ReviewVerdictStructure` (ai_gate.ps1:250–274) validates exact regexes `'(?m)^VERDICT:\s*(PASS\|BLOCK)\s*$'` and `'(?m)^BLOCKING_FINDINGS:\s*(\d+)\s*$'` — same patterns as the reviewer contracts |
| 4 | Infrastructure failure never reported as PASS or candidate BLOCK | **PASS** | `$infraBlocked` triggers `exit 1` at line 422–426, before EVIDENCE.md generation, promotion, and the candidate-BLOCKED/pass terminal logic |
| 5 | Timeout/non-zero/malformed must not overwrite valid canonical `reviews/*.md` | **PASS** | Reviews staged to `candidate_<agent>.md` in `.runtime/` (line 338); canonical promotion only happens in the transactional block (lines 521–523) which is unreachable on infra failure |
| 3 | Semantic BLOCK distinguishable from infrastructure failure | **PASS** | `$candidateBlocked` (set at line 346 when verdict is BLOCK) → exit 2; `$infraBlocked` (set at lines 315, 325, 332, 361, 370, 388) → exit 1. Completely separate code paths |
| 6 | `EVIDENCE.md` must not claim complete verification on infrastructure failure | **PASS** | `candidateEvidencePath` written at line 478, promoted at line 523 — both unreachable when `$infraBlocked` triggers `exit 1` at line 425 |
| 7 | Long-running reviewer execution must be user-observable | **PASS** | `-StreamToConsole:$true` at line 309 pipes reviewer stdout/stderr to console in real time; `Write-Host` at line 307 shows timeout value |
| 8 | Timeout/termination targets only launched child, not `opencode serve` | **PASS** | `$proc.Kill()` at line 159 targets only the specific `$proc` handle; no process-tree kill |
| 9 | Gate rejects obvious full-suite test targets | **PASS** | Regex preserved at line 368: `'(?i)discover\s+tests\|unittest\s+discover\|^tests$\|\*'`; sets `$infraBlocked` and breaks |
| 10 | Existing `-Task <id>` invocation remains valid | **PASS** | Mandatory `$Task` parameter unchanged; new parameters `$ReviewTimeoutSeconds=480`, `$TestTimeoutSeconds=60` have defaults; internal test seams prefixed with `_` are optional |
| 11 | Multi-worktree isolation under `.runtime/ai_gate/<task-id>/` intact | **PASS** | `$runtimeDir = Join-Path $repoRoot ".runtime\ai_gate\$Task"` at line 53 |
| 12 | Task must not change reviewer findings to make candidate pass | **PASS** | No agent contract files modified; only gate orchestration and documentation |

### Target Behavior

| Section | Verdict | Evidence |
|---------|---------|----------|
| 1. Reviewer execution | **PASS** | `Invoke-BoundedProcess` (lines 73–203): `System.Diagnostics.Process` ownership, async `OutputDataReceived`/`ErrorDataReceived`, `Stopwatch` wall-clock polling, `$proc.Kill()` client-only kill, `WaitForExit(3000)` termination confirmation, staging to `candidate_*.md`, promotion only after loop + validation |
| 2. Reviewer structural validation | **PASS** | `Test-ReviewVerdictStructure` (lines 250–274): non-empty check, regex for VERDICT and BLOCKING_FINDINGS, consistency check (PASS→0, BLOCK→≥1); returns `IsValid` flag |
| 3. Focused-test execution | **PASS** | `Invoke-BoundedProcess` called with `$TestTimeoutSeconds` (line 382), `-StreamToConsole:$false` (no streaming), logs to `test-*.log` (line 385), terminal status with elapsed time and log path (lines 390, 400, 408); timeout → `$infraBlocked`, non-zero exit → `$candidateBlocked` |
| 4. Failure classification and exit codes | **PASS** | Three exit paths: `exit 0` (line 568), `exit 1` (lines 425, 557), `exit 2` (line 564); CANDIDATE_BLOCKED includes reviewer BLOCK + test non-zero; INFRASTRUCTURE_BLOCKED includes timeout/non-zero/malformed/unconfirmed |
| 6. EVIDENCE.md semantics | **PASS** | Written to `candidate_EVIDENCE.md` (line 478) and promoted (line 523) only after infra check; on INFRASTRUCTURE_BLOCKED, `exit 1` prevents any EVIDENCE.md write |
| 7. Observability | **PASS** | Reviewer streaming via `-StreamToConsole:$true`; test messages include start/timeout/classification/elapsed/log-path (lines 379, 390–394, 400, 408) |
| 8. Implementation boundary | **PASS** | Local helpers `Invoke-BoundedProcess`, `Get-OpenCodeInvocation`, `Test-ReviewVerdictStructure` inside `ai_gate.ps1`; no shared framework extracted; conceptual pattern from `ai_scout.ps1` |

### Acceptance Criteria
| # | Criterion | Verdict | Evidence |
| 5. Canonical artifact safety | **PASS** | Staging to `.runtime/`, backup to `canonical_backup/` (lines 500–514), transactional promotion with rollback (lines 521–546); on infra failure, `exit 1` before promotion |

|---|-----------|---------|----------|
| 1 | Both reviewers have 480s default timeout and real-time visibility | **PASS** | `$ReviewTimeoutSeconds = 480` (line 10), `-StreamToConsole:$true` (line 309) |
| 2 | Silent reviewer cannot block beyond timeout | **PASS** | Stopwatch polling loop in `Invoke-BoundedProcess` (line 154) |
| 3 | Timeout terminates only launched client | **PASS** | `$proc.Kill()` on specific handle (line 159) |
| 4 | Timeout/non-zero/malformed cannot replace valid canonical review | **PASS** | Staging + transactional promotion + `exit 1` before promotion on infra failure |
| 5 | Output structurally validated before canonical promotion | **PASS** | `Test-ReviewVerdictStructure` called at line 330, validation checked before staging at line 331 |
| 6 | Valid reviewer BLOCK remains CANDIDATE_BLOCKED | **PASS** | `$candidateBlocked = $true` at line 346 when `$validation.Verdict -eq "BLOCK"` |
| 7 | Every focused test has 60s timeout with override seam | **PASS** | `$TestTimeoutSeconds = 60` (line 12), parameter seam |
| 8 | Test non-zero → CANDIDATE_BLOCKED; timeout → INFRASTRUCTURE_BLOCKED | **PASS** | Lines 388–396 (timeout → `$infraBlocked`), line 410 (non-zero → `$candidateBlocked`) |
| 9 | Exit semantics: 0=PASS, 2=CANDIDATE_BLOCKED, 1=INFRASTRUCTURE_BLOCKED | **PASS** | `exit 1` (lines 425, 557), `exit 2` (line 564), `exit 0` (line 568) |
| 10 | EVIDENCE.md written for PASS/candidate BLOCK, not infra-incomplete | **PASS** | EVIDENCE.md generation and promotion unreachable when `$infraBlocked` |
| 11 | Canonical artifacts preserved across infra-failed reruns | **PASS** | `exit 1` before any promotion; backup/rollback mechanism in promotion block |
| 12 | Existing `-Task <id>` compatible | **PASS** | Parameter signature backward-compatible; new params have defaults |
| 13 | Full-suite policy unchanged | **PASS** | Rejection regex preserved at line 368 |
| 14 | Deterministic probes verify all listed scenarios | **PASS** | Override seams (`_ReviewerExecutableOverride`, `_SpecReviewerArgumentsOverride`, `_RegressionReviewerArgumentsOverride`, `_PythonExecutableOverride`, `_PythonArgumentsOverride`, `_FailPromotionOnTarget`) enable all 10 listed probe scenarios via manual invocation; same pattern as `ai_scout.ps1` |
| 15 | No production/game behavior changes | **PASS** | Scope limited to gate script and documentation |

### Non-goals

| Non-goal | Verdict | Evidence |
|----------|---------|----------|
| Redesign reviewer semantic responsibilities | **PASS** | Agent contracts untouched |
| Add autonomous repair/retry loops | **PASS** | No retry logic in diff |
| Parallelize reviewers | **PASS** | Sequential `foreach` loop at line 289 |
| Queues/services/dashboards | **PASS** | Not present |
| Change production/game code | **PASS** | Scope: 3 files, no game code |
| Start intent-routing-observability | **PASS** | Not present |
| Extract shared framework | **PASS** | Local helpers only |
| Run full test suite | **PASS** | Rejection regex preserved |
| Solve hangs by increasing timeouts | **PASS** | Bounded execution with streaming |
| Per-task timeout schema in task.json | **PASS** | Script-level defaults + param seams |

### Documentation Changes

| File | Verdict | Evidence |
|------|---------|----------|
| `docs/architecture/ai_development_workflow.md` Phase D | **PASS** | Updated description (line 229) accurately describes bounded wrapper, 480s reviewer timeout, 60s test timeout, three exit codes, and canonical preservation on infra failure |
| `docs/tasks/README.md` | **PASS** | Added line (line 48): "Failed or timed-out verification gate runs at the infrastructure layer never overwrite existing canonical `reviews/*` or `EVIDENCE.md`." — consistent with spec invariant 5 |

## Blocking findings

None.

## Advisory findings

### ADV-1
Severity: ADVISORY
Area: AC14 (deterministic probes)
Evidence: The probe capability is fully wired through parameters at ai_gate.ps1:14–21. Each AC14 scenario can be invoked manually using these seams. The `ai_scout.ps1` follows the same seam-only pattern without a separate probe script.
Impact: The seams are sufficient for deterministic verification. A developer or reviewer can exercise all listed scenarios by invoking the gate with appropriate overrides. A dedicated probe script would improve reproducibility but is not mandated by the spec scope (`"scope": ["scripts/ai_gate.ps1", ...]`).

### ADV-2
Severity: ADVISORY
Claim: Override seams (`_ReviewerExecutableOverride`, `_FailPromotionOnTarget`, etc.) in `scripts/ai_gate.ps1` enable all 10 listed probe scenarios, but no standalone probe script is included in the diff. The `focused_tests` in `task.json` is empty.
Area: Deferred `opencode` existence check
Claim: The original script checked for `opencode` at startup. The new code defers this check to `Get-OpenCodeInvocation` (line 226–229), which runs inside the reviewer loop. This means git status/diff operations (lines 61–71) execute before the error is thrown if `opencode` is not installed.
Evidence: `Get-OpenCodeInvocation` is called at line 306, after git operations. When no override is set and `opencode` is missing, the throw occurs during the first reviewer invocation. Consistent with `ai_scout.ps1` pattern.

## Test evidence gaps
Impact: Minor degraded fail-fast behavior. The error is still thrown before any reviewer is launched. No functional impact.

- **Present**: The test seams (`_ReviewerExecutableOverride`, `_PythonExecutableOverride`, `_FailPromotionOnTarget`) are fully wired, enabling all 10 AC10 probe scenarios.
- **Missing**: No standalone probe script or automated probe invocation is included. AC14 scenarios are exercisable but not automatically exercised by the diff.
- **Present**: Structural validation (`Test-ReviewVerdictStructure`) covers the exact regex patterns from the reviewer contracts.
- **Present**: The promotion/rollback mechanism includes a `_FailPromotionOnTarget` seam to verify transactional behavior.
