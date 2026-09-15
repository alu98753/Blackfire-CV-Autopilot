# gate-payload-robustness-v1

Status: Final

## Goal

Make `scripts/ai_gate.ps1` resilient to the real production failure where a semantically valid reviewer header is wrapped in Markdown bold, while preserving strict rejection of ambiguous/contradictory payloads and durably retaining compact Gate attempt history across reruns.

This is a workflow reliability task. It changes Gate parsing and tracked verification evidence only. It does not change game/runtime behavior, reviewer semantic authority, reviewer sequencing, fallback policy, or timeout policy.

## Evidence basis

The `intent-routing-observability` production pilot demonstrated:

- reviewer semantics were `PASS` with `BLOCKING_FINDINGS: 0`;
- output used Markdown bold headers:
  - `**VERDICT: PASS**`
  - `**BLOCKING_FINDINGS: 0**`
- `Get-CanonicalReviewPayload` required literal raw `VERDICT:` at line start, so Gate classified the attempt as `PAYLOAD_EXTRACTION_FAILED` / infrastructure failure;
- a later successful rerun replaced canonical `EVIDENCE.md`, so prior failed-attempt provenance was no longer durably represented in the tracked task package.

Scout confirmed:

- parser normalization is localized to `Get-CanonicalReviewPayload` / `Test-ReviewVerdictStructure`;
- `$provenanceRecords` already contains the fields needed for durable attempt history;
- current duplicate-header rejection, PASS/BLOCK consistency checks, transaction-safe promotion, and rollback are existing invariants;
- the merged offline workflow harness contains the exact Markdown production-failure case and is the required regression safety net.

## Scope

### 1. Narrow payload normalization

Gate must accept exactly these two header forms:

#### Canonical raw form

```text
VERDICT: PASS|BLOCK
BLOCKING_FINDINGS: <non-negative integer>
```

#### Markdown-bold form

Both canonical header lines may be fully wrapped in Markdown bold markers:

```text
**VERDICT: PASS|BLOCK**
**BLOCKING_FINDINGS: <non-negative integer>**
```

The two lines must use the same accepted form within one header. Mixed raw/bold header lines are rejected.

Normalization requirements:

- normalization is limited to removing one complete outer `**...**` wrapper from each of the two header lines;
- after normalization, the existing semantic validator remains authoritative;
- matching remains line-anchored and deterministic;
- normalization must be applied uniformly when detecting multiple candidate headers, so ambiguity cannot disappear merely because one candidate was formatted differently;
- arbitrary inline Markdown/prose must never be converted into a verdict.

Explicitly **not accepted in v1**:

- Markdown headings such as `# VERDICT: PASS`;
- inline-code/backtick wrappers such as `` `VERDICT: PASS` ``;
- blockquotes;
- bullets/list prefixes;
- arbitrary leading prose or same-line prose around a header;
- arbitrary indentation or blank preamble invented as tolerance;
- partially/mismatched bold wrappers;
- only one line bolded while the other is raw.

This task fixes the observed bold-wrapper incident only. Broader formatting tolerance requires separate evidence and a new contract.

### 2. Semantic strictness after normalization

Existing semantic invariants remain unchanged:

- `PASS` is valid only when `BLOCKING_FINDINGS: 0`;
- `BLOCK` is valid only when `BLOCKING_FINDINGS >= 1`;
- malformed/contradictory combinations are rejected;
- multiple canonical or normalizable verdict headers in one final assistant message are rejected as ambiguous;
- one raw header plus one bold-normalizable header is still multiple competing headers and must be rejected;
- normalization must not make an otherwise ambiguous payload appear unique.

### 2.1 Structured reviewer message completion

When reviewer output uses structured JSON, the extractor must group assistant
text events by `messageID` and consider only message IDs with a corresponding
`step_finish` event. Synthetic assistant text or messages are excluded. The
selected message is the chronologically latest completed, non-synthetic
assistant message, and only text parts for that message ID are concatenated.

If no completed non-synthetic assistant message exists, extraction fails
infrastructurally. If the latest completed non-synthetic message is malformed
or lacks a verdict, it remains authoritative and Gate must not salvage an
older message containing a verdict. Tool-result content is not assistant
message text and is never used as verdict evidence.

### 3. Durable attempt history

Add one tracked historical artifact under the task package:

```text
docs/tasks/<task-id>/ATTEMPT_HISTORY.md
```

Responsibility boundary:

- `EVIDENCE.md` remains the canonical summary of the **current Gate run** and current selected reviewer verdicts;
- `reviews/spec-review.md` / `reviews/regression-review.md` remain the current canonical reviewer reports;
- `ATTEMPT_HISTORY.md` is historical observability only and must never be interpreted as current review authority.

Each Gate run that reaches normal evidence generation/promotion must append one compact run section containing:

- Gate run timestamp;
- branch;
- candidate HEAD;
- role;
- attempt index;
- attempt type;
- model;
- elapsed seconds;
- outcome;
- selected/fallback status.

The artifact must use existing `$provenanceRecords`; do not reconstruct history from raw logs or parse previous `EVIDENCE.md` Markdown.

History requirements:

- previous tracked history survives later successful reruns;
- current run records are appended in execution order;
- raw `.runtime` logs are not committed;
- do not copy full reviewer prose into history;
- a rerun must create a distinct run section even if the same HEAD/model combination is repeated; repeated executions are real historical events, not deduplication errors;
- history remains append-only from the perspective of successful canonical promotion;
- no pruning/rotation policy is introduced in v1.

### 4. Transaction-safe promotion

`ATTEMPT_HISTORY.md` becomes part of the same canonical promotion/rollback transaction as:

- `reviews/spec-review.md`;
- `reviews/regression-review.md`;
- `EVIDENCE.md`.

If promotion fails, all canonical artifacts, including prior attempt history, must be restored to their exact pre-Gate state.

Infrastructure failures that occur before normal evidence promotion must continue to leave canonical artifacts untouched. This task does not change that fail-safe contract.

### 5. Offline regression harness

Update `tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1` through real Gate invocation and existing override seams.

Required parser cases:

1. raw canonical PASS -> Gate exit `0`;
2. Markdown-bold PASS -> Gate exit `0` (red→green change from P0 baseline);
3. raw canonical BLOCK with blocking>=1 -> Gate exit `2`;
4. PASS with non-zero blocking -> rejected / infrastructure blocked;
5. BLOCK with zero blocking -> rejected / infrastructure blocked;
6. malformed prose -> rejected;
7. duplicated raw headers -> rejected as ambiguous;
8. duplicated bold-normalizable headers -> rejected as ambiguous;
9. one raw + one bold-normalizable competing header -> rejected as ambiguous;
10. mixed-line raw/bold header -> rejected;
11. heading/backtick/non-contract wrappers remain rejected.

Required history cases:

12. first successful Gate run creates `ATTEMPT_HISTORY.md`;
13. later successful rerun appends a new run without deleting earlier history;
14. failed candidate followed by fallback success records both attempts with correct selected/fallback meaning;
15. simulated promotion failure restores the previous `ATTEMPT_HISTORY.md` exactly, together with existing evidence/reviews.

The harness must remain offline, deterministic, and free of live OpenCode/network dependencies.

## Known invariants

- ChatGPT + user remain contract owners.
- OpenCode Gate reviewers remain read-only independent blocker detectors.
- Normal semantic `PASS` / `BLOCK` remains terminal for that reviewer role.
- Model fallback remains infrastructure reliability, not semantic review-shopping.
- Gate exit codes remain:
  - `0` = PASS
  - `1` = INFRASTRUCTURE_BLOCKED
  - `2` = CANDIDATE_BLOCKED
- Reviewer role sequencing remains unchanged.
- Model candidates/order, timeout values, retry counts, kill-confirmation behavior, prompts, step budgets, and focused-test semantics remain unchanged.
- Degraded/manual evidence must never masquerade as a current independent Gate PASS.
- Current canonical verdict authority remains separate from historical attempt observability.
- Offline workflow harness is required before Gate.
- Windows non-interactive execution policy is authoritative: agent/tool PowerShell execution uses `cmd.exe /d /s /c`, with stdin closed from NUL where applicable.
- No production/game behavior changes.

## Non-goals

- Do not accept headings, backticks, blockquotes, bullets, arbitrary indentation, arbitrary prose, or general Markdown formatting.
- Do not build a general Markdown parser.
- Do not change reviewer prompt wording solely to suppress Markdown output; parser robustness is the owned fix here.
- Do not change Gate reviewer sequencing after infrastructure failure.
- Do not change model candidates, fallback order, timeout values, step budgets, or retry counts.
- Do not add task.json schema linting.
- Do not introduce degraded reviewer automation.
- Do not add multi-model voting/racing or semantic aggregation.
- Do not change Scout behavior.
- Do not commit raw runtime logs.
- Do not parse old `EVIDENCE.md` as a persistence database.
- Do not add ATTEMPT_HISTORY pruning/rotation in v1.
- Do not modify production/game runtime code.
- Do not require the product full test suite.

## Acceptance criteria

1. Exact production-style bold header `**VERDICT: PASS**` + `**BLOCKING_FINDINGS: 0**` is accepted and produces normal PASS semantics.
2. Raw canonical PASS remains accepted unchanged.
3. Canonical BLOCK with blocking findings retains exit code `2` behavior.
4. PASS/non-zero and BLOCK/zero remain invalid.
5. Multiple competing raw, bold, or mixed raw+bold headers remain rejected as ambiguous.
6. Mixed-line raw/bold headers are rejected.
7. Heading/backtick/other wrappers remain rejected.
8. Arbitrary prose is not reinterpreted as a verdict.
9. Normalization is narrowly implemented and does not weaken semantic consistency checks.
10. Existing Gate sequencing/fallback/timeout/focused-test semantics remain unchanged.
11. `ATTEMPT_HISTORY.md` is created from existing `$provenanceRecords` and clearly labeled historical/non-authoritative.
12. Successful reruns append history rather than replacing prior run sections.
13. History preserves role, attempt index/type, model, elapsed, outcome, and selected/fallback status where available.
14. No raw runtime logs or full reviewer prose are committed into history.
15. `EVIDENCE.md` continues to describe only the current run/current canonical reviewer result.
16. `ATTEMPT_HISTORY.md` participates in the same promotion/rollback transaction; simulated promotion failure restores prior history exactly.
17. Infrastructure failures before promotion continue to leave canonical tracked artifacts untouched.
18. Offline harness covers the required parser/history cases and passes without network/live AI use.
19. `scripts/ai_scout.ps1` remains unchanged.
20. No production/game code changes occur.

## Expected change surface

Expected:

```text
scripts/ai_gate.ps1
tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1
docs/tasks/gate-payload-robustness-v1/*
```

Expected unchanged:

```text
scripts/ai_scout.ps1
production/game code
```

`docs/tasks/BACKLOG.md` should only be updated during task closeout if lifecycle state needs synchronization; it is not required for the implementation patch.

## Verification contract

Before running the independent Gate, Writer must run the offline harness using the Windows execution policy:

```text
cmd.exe /d /s /c "powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tests\workflow_scripts\Invoke-WorkflowScriptHarness.ps1 < NUL"
```

All cases must pass and no disposable fixture/runtime artifacts may remain.

Then commit and push the implementation candidate.

Only after the implementation commit exists, run independent Gate:

```text
cmd.exe /d /s /c "powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\ai_gate.ps1 -Task gate-payload-robustness-v1 < NUL"
```

Push refreshed `EVIDENCE.md`, `ATTEMPT_HISTORY.md`, and `reviews/*` after Gate.

The canonical Gate evidence must reference the committed implementation HEAD, not an uncommitted working-tree candidate.

## Writer instructions

1. Read Final SPEC, CONTEXT, current `ai_gate.ps1`, merged workflow harness, and workflow architecture contract.
2. Extend regression tests before or together with parser/history changes so the red→green contract is explicit.
3. Implement the smallest coherent parser normalization and attempt-history patch.
4. Do not broaden accepted Markdown grammar beyond this Final SPEC.
5. Do not modify Scout, model routing, sequencing, timeout, prompts, or product code.
6. Run the offline harness through `cmd.exe /d /s /c ... < NUL`.
7. Inspect diff/status and verify no fixture leaks.
8. Commit/push implementation before Gate.
9. Run Gate against the committed candidate, then push canonical evidence/reviews/history.
10. Do not declare completion until harness and Gate both pass.
