# gate-reviewer-output-contract-reliability

Status: Draft

## Goal

Make Gate reviewer outcomes machine-reliable without forcing human-readable review Markdown to place `VERDICT` at a particular textual position.

The desired responsibility boundary is:

```text
reviewer semantic judgment
    -> machine-readable validated outcome
    -> deterministic Gate validation
    -> deterministic human-readable review rendering
```

Human report layout must not be the transport protocol for PASS/BLOCK.

## Observed problem

`gate-payload-robustness-v1` exposed repeated cases where the reviewer completed a useful semantic review but the Gate could not obtain a canonical verdict reliably from free-form assistant text.

Observed failure modes include:

1. reviewer output affected by forced max-step finalization;
2. incomplete/unclosed trailing assistant messages;
3. a semantically valid review whose `VERDICT: PASS` / `BLOCKING_FINDINGS: 0` block appeared after the review body instead of at the beginning;
4. prior Markdown-format variation around the verdict header.

The step-budget failure is already handled by `gate-reviewer-step-budget-reliability`; this task must not reopen that fix.

The remaining architectural problem is that Gate currently uses the placement and formatting of free-form Markdown as part of its machine contract.

## Human-readable report decision

For human readers, both styles are legitimate:

- status-first is useful for dashboards / PR summaries;
- evidence-first and verdict-last is natural for review reports where the conclusion follows the reasoning.

This task therefore does **not** define semantic correctness by whether the verdict appears at the top or bottom of Markdown.

Provisional UX preference: canonical `reviews/*.md` may present the detailed assessment first and a clear verdict section at the end, as long as the machine verdict is obtained independently and rendered deterministically.

## Provisional architecture direction

Prefer a structured reviewer result over parser tolerance.

A minimal conceptual result is:

```json
{
  "verdict": "PASS",
  "blocking_findings": 0,
  "report_markdown": "# Spec Review\n..."
}
```

The exact schema is not Final yet.

Gate should validate machine fields deterministically, then render/store the human-readable review deterministically. The model should own semantic judgment and evidence, not Markdown protocol placement.

OpenCode currently documents JSON-Schema structured output in its SDK, including schema validation and bounded validation retries. However, the repository currently invokes `opencode run --format json`, whose documented CLI `--format json` mode is a stream of raw JSON events rather than an explicit JSON-Schema flag. Scout must establish the smallest supported integration path instead of assuming an SDK migration is required.

If native structured output is not practical in the current Windows/non-interactive workflow, Final SPEC may choose a narrower transport contract. Any fallback must remain deterministic and must not become an arbitrary search for PASS/BLOCK anywhere in model prose.

## Provisional scope

Likely change surface:

- `.opencode/agents/spec-reviewer.md`
- `.opencode/agents/regression-reviewer.md`
- `scripts/ai_gate.ps1`
- `tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1`
- `docs/architecture/ai_development_workflow.md`
- `docs/tasks/gate-reviewer-output-contract-reliability/`

If Scout proves a small dedicated adapter is required, its exact path must be added explicitly before Final SPEC.

## Known invariants

1. OpenCode reviewers remain independent, read-only blocker detectors.
2. Reviewer semantic authority is unchanged: the reviewer decides PASS or BLOCK from grounded evidence.
3. Semantic consistency remains strict:
   - `PASS` requires `blocking_findings == 0`;
   - `BLOCK` requires `blocking_findings >= 1`.
4. Forced max-step finalization remains an infrastructure failure and is never a verdict source.
5. Partial/incomplete assistant output, tool-result text, synthetic trailing output, or older messages must never be searched to salvage a verdict.
6. Infrastructure/model fallback must not become semantic review-shopping.
7. Canonical `reviews/*` and `EVIDENCE.md` must remain protected on infrastructure failure.
8. Human-readable Markdown layout must not silently redefine machine verdict semantics.
9. Existing `gate-payload-robustness-v1` parser/extractor work is a downstream task and must not be duplicated or weakened here merely to make its current Gate pass.
10. No production/game behavior changes.
11. Windows non-interactive execution continues to use `cmd.exe /d /s /c` and closed stdin where appropriate.

## Non-goals

- changing reviewer model routing/order;
- changing reviewer timeout values;
- changing the recently established reviewer step budgets (`spec: 8`, `regression: 10`);
- accepting forced-finalization output as valid evidence;
- broadening free-form regex parsing until arbitrary prose happens to pass;
- changing Scout behavior;
- implementing `task.json` schema linting;
- modifying production/game code;
- closing or merging `gate-payload-robustness-v1` inside this task.

## Provisional acceptance criteria

1. Gate obtains PASS/BLOCK from a machine contract that is independent of where the human review displays its verdict.
2. A reviewer may produce evidence-first / verdict-last human presentation without causing infrastructure failure solely because of Markdown ordering.
3. Machine validation deterministically rejects missing, malformed, contradictory, or ambiguous verdict data.
4. `PASS + blocking_findings > 0` and `BLOCK + blocking_findings == 0` remain invalid.
5. Forced max-step, incomplete output, synthetic trailing output, and stale/older verdicts remain non-authoritative.
6. Canonical review Markdown is produced by a deterministic boundary rather than relying on the model to place a magic two-line header correctly.
7. Existing read-only reviewer and fail-safe artifact promotion semantics remain intact.
8. Deterministic offline workflow coverage demonstrates at least:
   - valid PASS structured outcome;
   - valid BLOCK structured outcome;
   - contradictory semantic fields rejected;
   - missing/invalid structured outcome fails infrastructurally;
   - human report body may contain ordinary prose without being parsed for verdict semantics;
   - earlier/stale PASS cannot override a later authoritative malformed/failing outcome;
   - forced/incomplete output is not salvaged.
9. Full product test suite is not required by default; workflow harness/focused verification is sufficient unless Final SPEC discovers a broader dependency.
10. A fresh real Gate run for this task produces canonical PASS evidence before merge.

## Uncertainty / Scout questions

1. Can the currently installed OpenCode CLI expose JSON-Schema structured output directly, or is that capability available only through SDK/server APIs?
2. If an SDK/API adapter is required, what is the smallest dependency and process model compatible with the existing Windows non-interactive workflow?
3. Do the configured free models used by this repository support OpenCode structured output consistently?
4. What exact OpenCode event/result carries `structured_output`, validation errors, and retry exhaustion?
5. Should the structured schema contain one `report_markdown` field or structured review sections that are rendered by Gate?
6. Should canonical Markdown place the verdict at the end, or should `EVIDENCE.md` remain status-first while detailed `reviews/*.md` are evidence-first? This is a presentation decision, not a machine-validation decision.
7. Which existing P1 parser/extractor functions remain necessary as compatibility paths after structured output becomes authoritative?
8. Can the change be implemented without introducing a long-lived `opencode serve` process?

## Scout objective

Localize the smallest supported transport/validation boundary for reliable reviewer outcomes. Scout should inspect current OpenCode invocation, agent contracts, Gate extraction/validation, workflow harness seams, and architecture contract. It should not implement the solution or reopen model routing, timeout, or step-budget policy.