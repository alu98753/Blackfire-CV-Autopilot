VERDICT: PASS
BLOCKING_FINDINGS: 0

# Regression Review

## Behavior-preservation assessment

The diff modifies 8 files: 3 agent contracts, 2 automation scripts, 1 architecture doc, 1 backlog doc, and creates task metadata (SPEC, CONTEXT.md, EVIDENCE.md, task.json). All core behavioral invariants are preserved:

- **Agent roles remain separate and read-only.** Scout is evidence-only; spec-reviewer and regression-reviewer are independent sequential bounded blocker detectors. V2 `permissions` correctly deny `edit`, `shell`, `subagent`, `execute`, `external_directory`, `webfetch`, `websearch` and allow only `read`, `glob`, `grep` across all three agents.
- **Step budgets match spec:** Scout `steps: 6`, both reviewers `steps: 5` — verified in current repo state.
- **Gate semantic contract unchanged.** `VERDICT: PASS|BLOCK` + `BLOCKING_FINDINGS` header, exit codes 0/1/2, focused-test rejection, transaction-safe promotion, and rollback are all preserved (no modifications to those code paths).
- **Scout prompt deduplication achieved.** `ai_scout.ps1` now delegates to the agent contract (`"Strictly follow the file and word budget limits defined in the scout agent contract"`), eliminating the previously duplicated 10-file / 1500-word numbers.
- **Invocation isolation strengthened.** Both scripts now use `--standalone` and explicit `$psi.WorkingDirectory = $repoRoot`. `ai_scout.ps1` adds `RedirectStandardInput` + `StandardInput.Close()`. `ai_gate.ps1` reviewer invocations now also add `--standalone` and `--format json` with `WorkingDirectory` set on `Invoke-BoundedProcess`.
- **No game/runtime files changed.**
- **Untracked game-doc files in status snapshot are pre-existing** — confirmed unrelated to this diff.

## Blocking findings

None.

## Advisory findings

1. **`--format json` added to gate reviewer invocations (not explicitly in SPEC).** `ai_gate.ps1` line 233 adds `"--format", "json"` to `Get-OpenCodeInvocation`. The SPEC requires invocation isolation but does not mention structured output. The gate script builds a proper JSONL extraction pipeline (`Get-FinalAssistantMessageFromStructuredJson`, `Get-CanonicalReviewPayload`) gated behind an `IsStructured` flag, so this is architecturally coherent and improves deterministic output parsing. Only a runtime probe could verify the OpenCode `--format json` contract is satisfied on the target model.

2. **`Test-ReviewVerdictStructure` now requires header at line 1.** The regex changed from `(?m)^VERDICT:` (multiline, anywhere) to `\AVERDICT:` (absolute start). This is more strict but consistent with the reviewer contracts that require "first two lines remain exactly the machine-readable header." `Get-CanonicalReviewPayload` uses `(?m)^VERDICT:` to extract the payload starting from the header match index, then passes that substring to `Test-ReviewVerdictStructure` — the chain is correct. However, any future direct call to `Test-ReviewVerdictStructure` with preamble text would fail. This is a deliberate tightening, not a regression.

3. **BACKLOG.md and CONTEXT.md/EVIDENCE.md are outside declared `task.json` scope** but within the diff. These are administrative/editorial (roadmap condensation, task activation metadata). No behavioral contract is altered.

**Confidence: 0.92** — the diff is architecturally sound, all spec invariants are satisfied, and the new structured output pipeline is well-factored. The only residual uncertainty is runtime verification of `--format json` with the target model, which is an expected follow-up probe.
