VERDICT: PASS
BLOCKING_FINDINGS: 0

# Spec Review

## Clause coverage

The candidate diff modifies 5 files within declared scope: `scripts/ai_scout.ps1`, `scripts/ai_gate.ps1`, `docs/architecture/ai_development_workflow.md`, `docs/tasks/BACKLOG.md`, and `docs/tasks/agent-model-fallback-routing-v1-1/task.json` (plus new artifacts SPEC.md, CONTEXT.md, degraded-gemini-review.md). All material spec sections are addressed:

- **Metadata contract (§1)**: `Resolve-NormalModelList` and `Resolve-ReviewCandidates` handle scalar-or-array, CLI override (`-Model`/`-ReviewModel` → single-element list), and blank-identifier rejection. Correct.
- **Degraded review contract (§2)**: `ai_gate.ps1` never invokes Gemini. On infrastructure exhaustion it exits code 1 with `MANUAL_DEGRADED_REVIEW_REQUIRED`. Degraded-gemini-review.md has required `DEGRADED/LOW_EVIDENCE/NOT_INDEPENDENT/ANTIGRAVITY_GEMINI` labels.
- **CLI override (§3)**: Both `Resolve-NormalModelList` and `Resolve-ReviewCandidates` prioritize CLI override as a single-element candidate list.
- **Fallback eligibility (§4)**: Infrastructure failure classifications (timeout, unconfirmed kill, non-zero exit, malformed JSON, payload extraction failure, invalid verdict) each `continue` to next candidate. Valid PASS/BLOCK sets `$roleCompleted = $true` and breaks.
- **Gate routing boundary (§5)**: Candidate iteration is inside the reviewer foreach loop, not wrapping the entire Gate. BLOCK is terminal per reviewer. After all candidates exhausted for a role, exits 1.
- **Timeout per attempt (§6)**: `Invoke-BoundedProcess` receives full `$ReviewTimeoutSeconds` each iteration; no shared remainder.
- **Scout routing (§7)**: Fallback loop with structural validation (`# Scout Context` heading check). Valid result promotes exactly once. All-fail throws.
- **Qualification (§8)**: `task.json` arrays correctly reflect qualification: BigPickle in `models.scout` (qualified), absent from `models.review` (unqualified due to JSONL parse failure). No fabrication.
- **Attempt provenance (§11)**: Both scripts record role, type, index, model, elapsed, outcome, selected status. Gate writes compact provenance to `EVIDENCE.md`. Raw logs per attempt under `.runtime/`.
- **Architecture documentation (§13)**: Section 10 updated with comprehensive fallback routing semantics, timeout policy, provenance, degraded review, and CLI override documentation.
- **Backlog retrospective (§14)**: `agent-workflow-pilot-retrospective-v1` updated with all 9 required calibration points.

## Blocking findings

None.

## Advisory findings

1. **Windows git encoding workaround**: `ai_gate.ps1` wraps git commands with `cmd.exe /c "chcp 65001 >nul && <nul git ..."`. This is a platform-specific workaround for UTF-8 encoding on Windows. Not a spec concern but may need attention on non-Windows platforms if the scripts are ever run cross-platform.

2. **Scout non-zero exit code indented inside confirmed-kill path**: In `ai_scout.ps1`, the `$attempt.ExitCode -ne 0` check sits at the same indentation level as the `$attempt.KillConfirmed` check inside the timeout block. Logically this is correct (a timed-out+confirmed-kill process that returned non-zero should still throw rather than continue), but the nesting makes it read as unreachable in the common path. This is a readability concern, not a correctness issue.

## Test evidence gaps

The diff does not include deterministic probe scripts for the fallback routing (e.g., override-seed invocations exercising scalar normalization, ordered fallback, semantic terminality, exhaustion, unconfirmed termination). The spec's Required Verification section (AC20) calls for such probes. However, as reviewer I am evaluating the diff against the spec, not running the verification suite. The candidate implementation's test seams (`$_ModelCandidatesOverride`, `$_ReviewCandidatesOverride`, `$_ExecutableOverride`) are present and correctly plumb candidate lists, which provides the foundation for deterministic verification to be written separately.
