# gate-reviewer-output-contract-reliability

Status: Final

## Goal

Make Gate reviewer outcomes machine-reliable without coupling PASS/BLOCK semantics to the textual placement or formatting of human-readable Markdown.

The required responsibility boundary is:

```text
reviewer semantic judgment
    -> OpenCode JSON-Schema structured outcome
    -> deterministic Gate semantic validation
    -> deterministic human-readable review rendering
```

Human review Markdown is presentation evidence, not the machine transport protocol for verdict authority.

## Observed problem

`gate-payload-robustness-v1` exposed repeated cases where the reviewer completed a useful semantic review but Gate could not obtain a canonical verdict reliably from free-form assistant text.

Observed failure modes include:

1. reviewer output affected by forced max-step finalization;
2. incomplete/unclosed trailing assistant messages;
3. semantically valid reviews whose verdict appeared after the review body rather than at the beginning;
4. Markdown-format variation around the verdict header.

`gate-reviewer-step-budget-reliability` already addressed reviewer step ceilings and voluntary finalization. This task must not reopen that policy. The remaining architecture defect is that Gate still derives machine verdict semantics from free-form reviewer prose.

## Final architecture decision

The canonical machine path MUST use OpenCode SDK JSON-Schema structured output rather than `opencode run --format json` assistant-text extraction.

OpenCode CLI `--format json` is a raw JSON event stream. It is not the canonical semantic output contract for this task. The adapter MUST request SDK structured output with `format.type = "json_schema"`, obtain the validated `structured_output`, and convert SDK/transport/validation failures into deterministic infrastructure failure.

The minimal reviewer outcome contract is:

```json
{
  "verdict": "PASS",
  "blocking_findings": 0,
  "report_markdown": "# Spec Review\n..."
}
```

Required schema rules:

- `verdict` is required and is exactly `PASS` or `BLOCK`;
- `blocking_findings` is required and is a non-negative integer;
- `report_markdown` is required and is a string;
- no machine verdict may be reconstructed from `report_markdown`;
- Gate applies the semantic cross-field invariant after schema validation:
  - `PASS` requires `blocking_findings == 0`;
  - `BLOCK` requires `blocking_findings >= 1`.

The model owns semantic judgment and supporting review prose. OpenCode structured-output validation owns shape/type validity. Gate owns semantic consistency, routing/fallback policy, artifact promotion, and deterministic rendering.

A structured-output validation exhaustion such as OpenCode `StructuredOutputError`, missing `structured_output`, adapter crash/non-zero exit, timeout, malformed adapter transport, or semantic contradiction is an infrastructure failure for that candidate attempt. Normal candidate fallback may proceed only under the existing infrastructure-failure routing rules. A valid semantic PASS or BLOCK remains terminal and MUST NOT trigger review-shopping.

## Adapter boundary

Introduce one small one-shot adapter at:

```text
scripts/opencode_structured_review.mjs
```

The adapter is an infrastructure boundary, not a second reviewer. It MUST:

1. receive the reviewer role, candidate model, review prompt, and repository working directory from Gate;
2. use the official OpenCode SDK to create/use the required one-shot client/server lifecycle;
3. request the fixed JSON-Schema outcome above;
4. use the selected repository reviewer agent contract and selected candidate model;
5. return exactly one deterministic machine-readable adapter result to Gate on success;
6. return non-zero / deterministic infrastructure diagnostics on SDK failure, structured-output validation exhaustion, missing outcome, or teardown failure that makes completion untrustworthy;
7. close any process-local OpenCode server/client resources before exit;
8. never reinterpret review prose and never search prior/partial messages for a verdict.

A long-lived shared `opencode serve` process is NOT required by this contract and MUST NOT become a new global mutable dependency.

The adapter may require repository-local Node package metadata for the official SDK. If so, `package.json` / lockfile and explicit bootstrap support are in scope. Task execution MUST NOT silently download/install dependencies. `scripts/bootstrap_opencode.ps1` remains the explicit installation boundary and may be extended to install/verify the pinned local SDK dependency.

## Human-readable rendering decision

Canonical `reviews/spec-review.md` and `reviews/regression-review.md` are produced by a deterministic Gate-side renderer from the validated structured outcome.

The renderer MUST NOT parse `report_markdown` to determine verdict semantics.

Detailed review files SHOULD use evidence-first presentation with a deterministic verdict section appended at the end, for example:

```text
<validated report_markdown>

## Verdict
VERDICT: PASS
BLOCKING_FINDINGS: 0
```

The exact heading text may differ if implementation keeps existing report headings coherent, but the verdict block MUST be generated from structured machine fields rather than copied from model prose.

`EVIDENCE.md` remains status-first because it is a Gate summary/dashboard artifact. Its PASS/BLOCK fields likewise come only from validated structured fields.

If `report_markdown` itself contains text such as `VERDICT: BLOCK`, that text has zero machine authority and MUST NOT alter Gate outcome.

## Scope

Primary change surface:

- `.opencode/agents/spec-reviewer.md`
- `.opencode/agents/regression-reviewer.md`
- `scripts/ai_gate.ps1`
- `scripts/opencode_structured_review.mjs` (new)
- `scripts/bootstrap_opencode.ps1` if required for explicit SDK dependency installation/verification
- `package.json` / repository lockfile if required for the official SDK dependency
- `tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1`
- test fixtures/helpers under `tests/workflow_scripts/` as needed
- `docs/architecture/ai_development_workflow.md`
- `docs/tasks/gate-reviewer-output-contract-reliability/`

The existing free-form verdict extractors in `ai_gate.ps1` may be deleted or retained only for unrelated legacy/test seams. They MUST NOT remain an authoritative fallback path for Gate reviewer verdicts after this task.

## Known invariants

1. OpenCode reviewers remain independent, read-only blocker detectors.
2. Reviewer semantic authority is unchanged: the reviewer decides PASS or BLOCK from grounded repository/spec evidence.
3. `PASS` requires `blocking_findings == 0`; `BLOCK` requires `blocking_findings >= 1`.
4. Forced max-step finalization remains an infrastructure failure and is never a verdict source.
5. Partial/incomplete assistant output, tool-result text, synthetic trailing output, stale output, or older messages must never be searched to salvage a verdict.
6. Infrastructure/model fallback must not become semantic review-shopping.
7. Canonical `reviews/*` and `EVIDENCE.md` remain protected on infrastructure failure according to existing transactional promotion semantics.
8. Human-readable Markdown layout cannot redefine machine verdict semantics.
9. Reviewer timeout policy remains unchanged.
10. Reviewer model routing/order remains unchanged unless required only to pass the selected model identifier through the new adapter.
11. Reviewer step budgets remain `spec: 8`, `regression: 10`.
12. No production/game behavior changes.
13. Windows non-interactive execution remains bounded with explicit repository working directory and closed stdin. PowerShell/non-interactive child execution from local agents continues through `cmd.exe /d /s /c` where applicable.
14. Provider credentials remain local and MUST NOT be committed.
15. The adapter must not introduce singleton task/session state that can collide across worktrees.

## Non-goals

- changing reviewer model routing policy or candidate order;
- changing reviewer timeout values;
- changing reviewer step budgets;
- accepting forced-finalization output as valid evidence;
- broadening regex/parser tolerance for free-form verdict prose;
- implementing JSON-in-Markdown, XML-in-Markdown, fenced-block, or arbitrary prose parsing as a fallback verdict protocol;
- changing Scout behavior, including the separate observed Scout artifact-promotion/forced-finalization weaknesses;
- making Scout auto-commit/push `CONTEXT.md`;
- implementing `task.json` schema linting;
- modifying production/game code;
- closing or merging `gate-payload-robustness-v1` inside this task;
- introducing a permanently running shared OpenCode server;
- running the full product test suite by default.

## Forbidden shortcuts

The implementation MUST NOT:

1. search `report_markdown` or raw assistant text for the first/last/unique `VERDICT` token;
2. accept a JSON code fence or delimiter embedded in free-form Markdown as equivalent to SDK structured output;
3. fall back from failed structured output to the old Markdown verdict parser;
4. recover a verdict from earlier messages/events after the authoritative structured attempt fails;
5. classify schema/semantic failure as PASS or BLOCK;
6. promote candidate review artifacts when an infrastructure failure should preserve prior canonical evidence;
7. invoke a different model after a valid semantic PASS or BLOCK;
8. silently install the SDK/dependencies during `ai_gate.ps1` execution.

## Required focused verification

Deterministic offline workflow coverage MUST demonstrate at least:

1. valid structured PASS -> Gate PASS path;
2. valid structured BLOCK -> Gate candidate-blocked path;
3. `PASS + blocking_findings > 0` rejected infrastructurally;
4. `BLOCK + blocking_findings == 0` rejected infrastructurally;
5. missing `structured_output` rejected;
6. malformed adapter result / non-zero adapter exit rejected;
7. structured-output validation exhaustion represented as infrastructure failure;
8. arbitrary prose and verdict-like strings inside `report_markdown` cannot alter machine verdict;
9. evidence-first / verdict-last canonical review rendering succeeds;
10. stale/earlier PASS cannot override a later authoritative malformed/failing attempt;
11. forced/incomplete output is not salvaged;
12. normal infrastructure candidate fallback still works;
13. valid semantic PASS/BLOCK remains terminal and does not fall through to another candidate;
14. canonical review/EVIDENCE promotion rollback semantics remain intact;
15. the adapter/structured-output path itself is exercised by a deterministic test seam rather than leaving only the legacy `_ReviewerExecutableOverride` free-text path covered.

The existing workflow harness may be refactored to provide an adapter-result fixture seam. Tests should remain deterministic and offline; they must not require a live model/provider.

## Acceptance criteria

1. Gate obtains reviewer PASS/BLOCK exclusively from validated machine-readable structured fields, never Markdown placement.
2. Reviewer human prose may naturally be evidence-first and verdict-last without affecting machine outcome.
3. OpenCode JSON-Schema validation is the canonical shape/type boundary; Gate then enforces cross-field semantic consistency deterministically.
4. Missing, malformed, contradictory, ambiguous, or exhausted structured output is classified as infrastructure failure, not a semantic verdict.
5. The model cannot change machine verdict by placing verdict-like text anywhere in `report_markdown`.
6. Canonical review Markdown is rendered deterministically from structured fields plus human report content.
7. `EVIDENCE.md` remains deterministic/status-first and obtains reviewer status only from structured fields.
8. Existing read-only reviewer permissions, candidate fallback policy, timeout policy, step budgets, and fail-safe artifact promotion semantics remain intact.
9. The official SDK dependency/process lifecycle is explicit, reproducible, non-interactive during Gate execution, and does not require a long-lived shared OpenCode server.
10. Workflow architecture documentation is updated so future code does not reintroduce free-form Markdown as verdict transport.
11. Deterministic workflow harness coverage passes for the cases listed above.
12. No production/game behavior changes occur.
13. A fresh real `scripts/ai_gate.ps1 -Task gate-reviewer-output-contract-reliability` run completes with canonical PASS evidence before merge.

## Follow-up debt discovered during Scout

Scout exposed two separate workflow weaknesses:

- `ai_scout.ps1` writes/promotes `CONTEXT.md` but does not itself commit/push it;
- Scout structural validation can currently accept output containing preamble/forced-max-step text as long as a Scout heading is later present.

These are real workflow debts but are explicitly outside this task. They should be handled by a separate Scout reliability task rather than coupled to Gate reviewer outcome transport.
