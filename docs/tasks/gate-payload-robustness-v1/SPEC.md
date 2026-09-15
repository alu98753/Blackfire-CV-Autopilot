# gate-payload-robustness-v1

Status: Draft

## Goal

Make `scripts/ai_gate.ps1` resilient to semantically valid reviewer verdict headers that are wrapped in common Markdown formatting, while preserving strict rejection of ambiguous or contradictory review payloads and improving durability of Gate attempt provenance across reruns.

This is a workflow reliability task. It changes Gate parsing/evidence behavior only; it does not change game/runtime behavior or reviewer semantic authority.

## Observed problem

The `intent-routing-observability` production pilot exposed a real infrastructure failure:

- the reviewer semantically concluded `PASS` with `BLOCKING_FINDINGS: 0`;
- the final header was emitted as Markdown bold (`**VERDICT: PASS**`, `**BLOCKING_FINDINGS: 0**`);
- `Get-CanonicalReviewPayload` / `Test-ReviewVerdictStructure` only accept raw canonical headers beginning with literal `VERDICT:`;
- Gate therefore classified the attempt as `PAYLOAD_EXTRACTION_FAILED` / infrastructure failure even though the semantic review itself was valid.

The pilot retrospective also confirmed that a later successful Gate rerun regenerates canonical `EVIDENCE.md`, so failed-attempt provenance is not durably retained in the tracked task package.

The newly merged `workflow-script-testing-harness` provides an offline regression baseline for current Gate/Scout behavior and must be extended before changing parser semantics.

## Initial scope

### Payload robustness

- Update Gate review-payload extraction/validation so a narrow, explicitly defined set of superficial Markdown wrappers around the canonical two-line header can be normalized and accepted.
- Keep semantic validation strict after normalization.
- Add/modify offline harness cases so the current Markdown-rejection baseline becomes the intended red→green regression test.
- Preserve rejection of malformed, contradictory, ambiguous, duplicated, or otherwise semantically unsafe verdict structures.

### Attempt provenance retention

- Preserve materially useful Gate attempt provenance across reruns so a successful rerun does not erase the fact that earlier normal candidates failed infrastructurally.
- Keep canonical current verdicts unambiguous: historical attempts are evidence, not current reviewer authority.
- Avoid turning `EVIDENCE.md` into an unbounded raw-log dump; retain compact structured attempt history or another tracked representation justified by Scout evidence.

## Known invariants

- ChatGPT + user remain contract owners; Gate reviewers remain read-only independent blocker detectors.
- Normal semantic `PASS` / `BLOCK` remains terminal for that reviewer role; model fallback remains infrastructure reliability, not review-shopping.
- Gate exit-code contract remains:
  - `0` = PASS
  - `1` = INFRASTRUCTURE_BLOCKED
  - `2` = CANDIDATE_BLOCKED
- `VERDICT: PASS` is valid only with `BLOCKING_FINDINGS: 0`.
- `VERDICT: BLOCK` is valid only with `BLOCKING_FINDINGS >= 1`.
- Multiple competing verdict headers must remain rejected as ambiguous.
- Parsing normalization must not reinterpret arbitrary prose as a verdict.
- Reviewer sequencing after infrastructure failure is unchanged in this task.
- Timeout, kill-confirmation, model ordering, fallback policy, reviewer prompts/step budgets, and focused-test semantics are unchanged unless Final SPEC explicitly narrows a behavior-neutral wording change needed for the parser contract.
- Historical/degraded/non-independent evidence must never masquerade as the current independent Gate PASS.
- Offline workflow harness remains the required regression safety net.
- Windows non-interactive execution policy remains authoritative: agent/tool PowerShell execution is routed through `cmd.exe /d /s /c`, with stdin closed from NUL where applicable.

## Non-goals

- Do not change Gate reviewer sequencing or make later reviewer roles run after an infrastructure block.
- Do not change model candidates, fallback ordering, timeout values, step budgets, or retry counts.
- Do not add task.json schema linting; that is the next P2 task.
- Do not introduce degraded reviewer automation.
- Do not loosen semantic consistency rules for PASS/BLOCK.
- Do not accept arbitrary Markdown/prose patterns without a narrow normalization contract.
- Do not create multi-model voting/racing or review aggregation semantics.
- Do not change Scout behavior.
- Do not modify production/game runtime code.
- Do not run or require the product full test suite for this workflow-only task unless later evidence justifies it.

## Provisional acceptance criteria

1. Offline harness contains an explicit regression case derived from the production failure where Markdown-wrapped canonical headers are accepted after the change.
2. Raw canonical headers continue to pass unchanged.
3. Canonical `BLOCK` with blocking findings continues to produce candidate-blocked semantics.
4. PASS with non-zero blocking count remains rejected.
5. BLOCK with zero blocking count remains rejected.
6. Multiple canonical/normalized verdict headers remain rejected as ambiguous.
7. Malformed prose without a valid two-line verdict header remains rejected.
8. Normalization is narrow and deterministic; accepted superficial wrappers are explicitly documented in Final SPEC/tests.
9. Existing Gate exit codes, reviewer sequencing, fallback semantics, timeouts, focused-test semantics, and promotion rollback behavior remain unchanged.
10. Offline workflow harness passes without live AI/network use.
11. Gate attempt provenance from infrastructurally failed candidates is durably represented after a later successful rerun, with enough information to identify role, attempt index/type, model, outcome, and selection/fallback state where available.
12. Historical attempt provenance is clearly separated from current canonical reviewer verdicts/reviews.
13. Evidence retention remains bounded/structured and does not commit raw `.runtime` logs by default.
14. Existing canonical review promotion remains transaction-safe.
15. No production/game runtime behavior changes occur.

## Uncertainty to resolve with Scout

- Which exact Markdown wrappers should be accepted safely (bold `**`, headings `#`, backticks, leading/trailing whitespace) without creating ambiguous parser behavior.
- Whether normalization belongs entirely in `Get-CanonicalReviewPayload`, partly in `Test-ReviewVerdictStructure`, or in a small shared normalization helper.
- How to guarantee multiple/duplicated headers remain rejected after normalization.
- Whether the reviewer prompt should explicitly prohibit formatting in addition to parser tolerance, or whether that would be redundant/out of scope.
- The narrowest durable design for historical attempt provenance: append/merge into `EVIDENCE.md`, a separate tracked history artifact, or another bounded representation.
- How reruns should deduplicate/identify attempts so repeated Gate executions do not create misleading duplication.
- Which existing harness cases need to be split/added to test contradictory counts and ambiguous normalized headers.
- Whether current evidence promotion/rollback code can retain history without invasive refactoring.

## Scout questions

1. Trace `Get-CanonicalReviewPayload`, `Test-ReviewVerdictStructure`, candidate loop, provenance collection, evidence generation, and artifact promotion to identify the minimal safe change surface.
2. Propose the narrowest normalization grammar for superficial Markdown wrappers while keeping ambiguity rejection strict.
3. Identify concrete ambiguous/contradictory payload examples that must remain rejected.
4. Determine the best location for red→green and negative regression cases in `tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1`.
5. Trace why prior failed attempt provenance disappears after a successful rerun and recommend the smallest durable tracked representation.
6. Check whether history retention can reuse existing `$provenanceRecords` and promotion transaction boundaries without changing reviewer semantics.
7. Identify any architecture/workflow contract wording that would need clarification after the behavior change.
8. Flag any coupling between parser normalization and reviewer sequencing/fallback that should remain out of scope.

## Lifecycle gate

This SPEC remains Draft until OpenCode Scout pushes `CONTEXT.md` and ChatGPT + user re-check the evidence. Gemini/Antigravity must not implement parser/evidence changes while this SPEC is Draft.
