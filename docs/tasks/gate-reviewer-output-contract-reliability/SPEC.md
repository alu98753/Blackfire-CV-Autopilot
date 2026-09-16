# gate-reviewer-output-contract-reliability

Status: Draft

Resumption base: `main@f2e6503e88161d01fbd73dc4a60e5da7d98167b4`
Historical task branch: `task-gate-reviewer-output-contract-reliability@54b727319eb8088a86086f02b4be4a55aa2167d2`
Resumption review: [`RESUMPTION_REVIEW.md`](RESUMPTION_REVIEW.md)

## Goal

Define the correct machine-verifiable Gate reviewer contract now that OpenCode `1.18.31` structured transport and typed lifecycle behavior are known, then localize the minimum implementation needed to make Gate enforce that contract without conflating grounding, lifecycle, transport, schema, semantic judgment, rendering, artifact promotion, or fallback policy.

The intended responsibility boundary is provisionally:

```text
repository/task evidence grounding
        ↓
authoritative same-attempt lifecycle
        ↓
reviewer semantic judgment
        ↓
OpenCode StructuredOutput / SDK v2 machine result
        ↓
schema + cross-field validation
        ↓
deterministic human rendering
        ↓
transactional canonical artifact promotion
```

This SPEC is intentionally Draft. No production implementation may begin until fresh Scout evidence is pushed and ChatGPT + user converge this contract to `Status: Final`.

## Why the historical Final SPEC was reopened

The historical task correctly identified that reviewer verdict authority must not depend on free-form Markdown placement, but material upstream evidence changed several assumptions after that SPEC became Final.

The completed `opencode-structured-review-provider-compatibility` task proved the production-pinned OpenCode route can transport a JSON-Schema structured review through official SDK v2 and exposed a different lifecycle shape than the historical task assumed.

The historical branch remains preserved as evidence. It is not an implementation baseline for this resumption.

## Current proven facts

1. Production OpenCode remains pinned to `1.18.31`.
2. `@opencode-ai/sdk` remains pinned to `1.18.31`.
3. The verified structured-review path is:

```text
OpenCode 1.18.31
+ @opencode-ai/sdk 1.18.31 official v2
+ format.type = json_schema
        ↓
OpenCode StructuredOutput tool
        ↓
HTTP 200
        ↓
promptResult.data.info.structured
```

4. `promptResult.data.parts` can be a trustworthy typed same-attempt lifecycle surface when its message/session identity and lifecycle are complete and internally consistent.
5. `StructuredOutput` itself appears as `part.type == "tool"`, and successful settlement is observable through `part.state.status == "completed"`.
6. `finish == "tool-calls"` does **not** by itself prove forced max-step finalization. A completed `StructuredOutput` can legitimately end with that finish reason.
7. The historical requirement for a separate final assistant text turn after tool use is not the correct SDK-v2 structured-output abstraction.
8. `client.session.messages` is affected by an `OutputFormatJsonSchema` decoder defect on this route and is not the preferred lifecycle source when the same prompt response already provides the facts the contract requires.
9. Fresh compatibility Attempt 021 proved a distinct grounding failure: Big Pickle produced a lifecycle-authoritative, schema-valid, semantically valid structured review while issuing zero repository `read` / `glob` / `grep` calls. That attempt classified as `FAIL_TOOL_CHOICE` under the compatibility probe.
10. MiMo demonstrated a distinct structured-result failure on a complex review: it voluntarily stopped without invoking `StructuredOutput`, leaving the required structured machine result absent.
11. Current `main` Gate still derives reviewer verdicts from `opencode run --format json` assistant text and `VERDICT` / `BLOCKING_FINDINGS` parsing. Therefore the original machine-transport defect remains real even though transport feasibility is now proven.

## Still-valid invariants

1. OpenCode reviewers remain independent, read-only blocker detectors.
2. Reviewer semantic authority is unchanged: only the reviewer/model decides PASS or BLOCK from grounded evidence.
3. Gate must never reconstruct PASS/BLOCK from `report_markdown` or arbitrary assistant prose.
4. Required structured fields remain:

```json
{
  "verdict": "PASS | BLOCK",
  "blocking_findings": 0,
  "report_markdown": "..."
}
```

5. `PASS` requires `blocking_findings == 0`.
6. `BLOCK` requires `blocking_findings >= 1`.
7. A grounded, lifecycle-authoritative, transport-valid, schema-valid, semantically consistent PASS or BLOCK is terminal for that reviewer role. A valid BLOCK must not trigger reviewer shopping.
8. Canonical `reviews/*` and `EVIDENCE.md` must not be overwritten by an attempt that never reaches trusted verdict authority.
9. Canonical artifact promotion remains transactional with rollback on promotion failure.
10. Reviewer timeout policy and process isolation remain bounded and non-interactive.
11. Reviewer step budgets remain `spec-reviewer: 8`, `regression-reviewer: 10` unless later evidence explicitly requires a separate task or Final-SPEC change.
12. Provider credentials remain local and must never be committed.
13. No production/game behavior changes are in scope.
14. OpenCode version/provider exploration is closed unless new concrete evidence invalidates the verified `1.18.31` baseline.
15. Task/session state must remain worktree-safe and task-namespaced; no new global mutable singleton may be introduced.

## Invalidated historical assumptions

The resumed task MUST NOT preserve these merely because they appeared in the old Final SPEC or matrix:

- root-SDK `createOpencode(...)` as the production adapter contract;
- `info.structured_output` as the proven SDK-v2 result field;
- `finish == "tool-calls"` as proof of max-step exhaustion;
- a required sequence of repository tool call -> tool result -> separate voluntary final assistant text turn -> structured output;
- historical model-matrix conclusions that predate the C3 SDK-v2 evidence;
- classifying grounding/tool-choice failure as lifecycle-source untrustworthiness merely because `session.messages` cannot be decoded.

## Draft machine-verifiable authority model

The exact implementation is not Final, but the contract must preserve the following separations.

### 1. Evidence acquisition / grounding

Gate must mechanically prove that reviewer judgment was grounded in evidence tied to the candidate repository state and canonical task contract.

Today, completed model-initiated repository `read` / `glob` / `grep` is the existing qualification proxy. The invariant is **grounding/provenance**, not necessarily that exact gesture forever.

Do not remove the current grounding requirement during this task unless the Final SPEC proves an alternative evidence contract already exists and is sufficient.

A future provenance-bearing deterministic Context Pack could potentially satisfy the same invariant, but that infrastructure belongs to `reviewer-bounded-context-infrastructure`, not this task.

### 2. Lifecycle authority

Gate/adapter must distinguish whether lifecycle evidence belongs to the exact current attempt and is complete/trustworthy enough to classify.

Grounding compliance is a separate layer: an authoritative lifecycle can prove that the model chose **not** to acquire required evidence.

### 3. Semantic reviewer judgment

The reviewer owns PASS/BLOCK and supporting report content. Infrastructure must not reinterpret prose to invent a different verdict.

### 4. Structured result transport

The production candidate contract is official SDK v2 JSON-Schema structured output, with a completed `StructuredOutput` lifecycle and machine result at `promptResult.data.info.structured`.

A separate trailing text response is not required.

### 5. Schema validation

The machine object must contain exactly the fixed fields and allowed types required by this task.

### 6. Cross-field semantic validation

Gate must deterministically reject contradictory machine fields such as `PASS + blocking_findings > 0` or `BLOCK + blocking_findings == 0`.

### 7. Human-readable rendering

Canonical review Markdown is generated deterministically from validated machine fields plus reviewer-provided `report_markdown`. Verdict-like text inside the report has zero machine authority.

### 8. Artifact promotion / rollback

Trusted PASS and trusted BLOCK are eligible canonical reviewer outcomes. Failures before verdict authority preserve prior canonical review artifacts. Promotion itself remains transactional.

### 9. Infrastructure failure

Process launch failure, timeout, unsafe termination, SDK/server failure, adapter crash, malformed adapter envelope, or required lifecycle-source failure are infrastructure failures distinct from model behavior.

### 10. Model fallback / review-shopping prevention

A trusted semantic PASS or BLOCK is terminal. Fallback must never be used to seek a more favorable verdict.

Whether non-authoritative model-compliance failures such as grounding failure, missing StructuredOutput, schema invalidity, or semantic contradiction are eligible for the bounded candidate fallback chain remains an explicit Draft policy question. They must not be relabeled as infrastructure merely to make fallback convenient.

## Draft failure taxonomy

The Final SPEC should converge explicit machine classes equivalent in responsibility to:

- `GROUNDING_FAILED`
- `LIFECYCLE_UNTRUSTWORTHY`
- `STRUCTURED_TRANSPORT_FAILED`
- `STRUCTURED_OUTPUT_MISSING`
- `SCHEMA_INVALID`
- `SEMANTIC_CONTRADICTION`
- `INFRASTRUCTURE_FAILED`
- `VALID_PASS`
- `VALID_BLOCK`

Names may change. The invariant is that failures from different responsibility layers remain distinguishable and cannot masquerade as one another.

## Draft max-step / completion contract

Still valid:

- forced max-step completion must not silently become verdict authority;
- the reviewer step count is a safety ceiling rather than a coverage target.

Invalid:

- inferring forced finalization from `finish == "tool-calls"`.

Open:

- what exact typed/mechanical evidence positively proves max-step exhaustion in OpenCode `1.18.31` SDK v2;
- whether step-count evidence from authoritative parts is sufficient and under what identity/completeness checks;
- whether a completed `StructuredOutput` at the configured final step can ever be trusted, and how that differs from a system-forced text-only max-step path.

Until resolved, implementation must fail closed rather than restore the historical finish-string heuristic.

## Draft scope

Likely production change surface after Final SPEC:

- `scripts/ai_gate.ps1`
- one small OpenCode SDK-v2 structured review adapter, likely `scripts/opencode_structured_review.mjs`
- `.opencode/agents/spec-reviewer.md`
- `.opencode/agents/regression-reviewer.md`
- deterministic workflow tests / fixtures under `tests/workflow_scripts/`
- workflow-level Python test wrapper(s) where needed
- `docs/architecture/ai_development_workflow.md`
- this task package

Existing compatibility probe code/tests are evidence and may inform reusable mechanisms, but this task must not copy diagnostic code wholesale into production without a clear responsibility-boundary reason.

## Non-goals

- changing OpenCode away from `1.18.31` without a new concrete blocker;
- reopening provider/version compatibility exploration;
- implementing `reviewer-bounded-context-infrastructure` or a Context Pack;
- eliminating reviewer read/search capability;
- weakening repository grounding merely because a model can emit plausible structured prose without reading files;
- preserving a historical voluntary-final-text-turn abstraction that does not match SDK v2;
- treating `finish: tool-calls` as max-step exhaustion;
- parsing JSON/Markdown/XML embedded in free-form assistant prose as a fallback verdict protocol;
- recovering PASS/BLOCK from older or partial messages after the authoritative attempt fails;
- changing Scout behavior;
- changing game/runtime behavior;
- running or accepting Gate while this SPEC is Draft;
- merging the task while this SPEC is Draft.

## Provisional adapter / Gate responsibility split

### Adapter should own only mechanical SDK facts

Potential responsibilities to validate after Scout:

- exact reviewer role/model/directory request construction;
- SDK-v2 one-shot session/process lifecycle;
- authoritative prompt-response identity checks;
- bounded lifecycle/tool-state extraction;
- official `info.structured` extraction;
- bounded SDK/transport diagnostics;
- deterministic machine envelope to Gate;
- teardown/cleanup proof required for trustworthy completion.

The adapter must not choose a more favorable semantic verdict, own model routing, promote canonical artifacts, or reinterpret review prose.

### Gate should remain orchestration/policy authority

Potential responsibilities to validate after Scout:

- candidate routing and fallback policy;
- grounding/lifecycle/transport/schema/semantic classification;
- cross-field invariant enforcement;
- anti-review-shopping terminality;
- focused-test integration;
- deterministic review/EVIDENCE rendering;
- artifact promotion / rollback;
- exit-code mapping.

## Canonical artifact hypothesis

`reviews/spec-review.md` and `reviews/regression-review.md` should remain human-readable rendered artifacts based on a trusted structured result. They may include compact accepted-attempt provenance, but must not become raw lifecycle dumps.

`EVIDENCE.md` should remain status-first and should record enough accepted-attempt provenance to explain which role/model/attempt produced the canonical result, plus grounding/validation classification, focused tests, branch/head/base identity, and pointers to detailed reviews.

Raw failed-attempt output and transport diagnostics should remain ephemeral under `.runtime/ai_gate/<task>/` unless the Final SPEC explicitly promotes a bounded diagnostic artifact.

## Fresh Scout questions

Fresh Scout must localize, within its normal bounded budget:

1. Which current `scripts/ai_gate.ps1` functions/branches must change to replace CLI JSONL/free-text verdict parsing with a structured adapter result while preserving timeout, routing, focused tests, exit codes, and transactional promotion?
2. Which current deterministic workflow tests encode header-first/free-form reviewer behavior, and what is the smallest test seam for structured adapter envelopes?
3. What exact current evidence proves grounding for a reviewer attempt, and does production need any earlier assistant-message history beyond the authoritative prompt response?
4. If earlier history is required, what trustworthy same-attempt typed source is available without relying on the broken `session.messages` decoder route?
5. What exact lifecycle signal can OpenCode `1.18.31` expose to positively prove max-step exhaustion? Is there a dedicated typed signal, a safe step-count proof, or no sufficient signal?
6. Does a successful production `StructuredOutput` always appear as a completed ToolPart plus `info.structured` on the same returned assistant message?
7. Which current reviewer prompt clauses are obsolete because they demand a separate final text/header, and which grounding clauses remain necessary?
8. Which existing Gate tests already protect valid BLOCK terminality, candidate fallback behavior, infrastructure rollback, and canonical artifact promotion?
9. Can any compatibility-probe transport/lifecycle helper be reused without coupling production Gate to diagnostic matrix logic?
10. What is the minimum coherent implementation surface that settles this Gate contract while leaving bounded-context infrastructure downstream?

## Provisional focused verification

Before Final SPEC, deterministic evidence should at minimum keep the already-merged OpenCode structured-review probe contract healthy:

```text
tests.test_opencode_structured_review_probe
```

After Scout, the Final SPEC must name the exact Gate-focused test targets. Expected cases include, subject to localization:

- valid grounded structured PASS;
- valid grounded structured BLOCK and terminal no-fallback behavior;
- `finish == "tool-calls"` with completed StructuredOutput not falsely classified as max-step exhaustion;
- authoritative lifecycle with missing required grounding classified as grounding failure, not lifecycle failure;
- missing StructuredOutput/result;
- invalid schema;
- PASS/BLOCK cross-field contradiction;
- verdict-like strings in `report_markdown` having zero machine authority;
- stale/earlier output unable to override the authoritative attempt;
- infrastructure fallback remaining bounded;
- canonical artifact preservation on attempts without trusted verdict authority;
- transaction rollback on promotion failure.

## Provisional acceptance criteria

1. Gate verdict authority no longer depends on free-form Markdown placement or `VERDICT` regex extraction.
2. The production structured route uses the verified OpenCode `1.18.31` + `@opencode-ai/sdk` `1.18.31` v2 contract rather than the obsolete historical SDK shape.
3. Lifecycle authority and grounding compliance are separately machine-verifiable.
4. `finish == "tool-calls"` is not treated as max-step exhaustion without stronger evidence.
5. A completed StructuredOutput lifecycle and `info.structured` can be accepted as the terminal structured-result mechanism when all other authority layers pass.
6. Missing/untrusted grounding, lifecycle, structured result, schema, semantic consistency, and process infrastructure failures remain distinguishable.
7. Trusted PASS and trusted BLOCK are both terminal semantic results; fallback never becomes review-shopping.
8. The Final SPEC explicitly defines which pre-verdict failure classes are fallback-eligible rather than hiding that policy inside implementation details.
9. Canonical review Markdown and `EVIDENCE.md` derive verdict state only from accepted structured fields.
10. Attempts that never reach trusted verdict authority preserve prior canonical reviewer artifacts.
11. Existing transactional promotion/rollback semantics and focused-test integration remain intact.
12. Deterministic offline tests exercise the structured adapter/Gate seam and all accepted failure classifications named by the Final SPEC.
13. No game/runtime behavior changes occur.
14. `reviewer-bounded-context-infrastructure` remains downstream and consumes this task's grounding contract rather than redefining it.
15. A fresh Scout is completed and incorporated before this SPEC can become Final.

## Unresolved policy questions

1. What exact positive signal is sufficient to classify max-step exhaustion under the pinned SDK-v2 lifecycle?
2. Is mandatory model-initiated `read` / `glob` / `grep` required for the current production Gate, or can some already-existing deterministic provenance source satisfy grounding before the future Context Pack task? No policy change is authorized while this remains unresolved.
3. Which non-authoritative model-compliance failures are eligible for candidate fallback without becoming review-shopping?
4. Should schema/cross-field validation be duplicated at adapter and Gate boundaries for defense in depth, or should one layer be canonical while the other only validates the adapter envelope?
5. What exact provenance belongs in canonical `reviews/*` versus `EVIDENCE.md` versus `.runtime` diagnostics?
6. Which compatibility-probe helpers are appropriate to reuse in production without importing probe-only matrix responsibilities?

## Historical evidence handling

The historical Final SPEC, historical CONTEXT, historical model matrix, and historical implementation remain available on:

```text
task-gate-reviewer-output-contract-reliability@54b727319eb8088a86086f02b4be4a55aa2167d2
```

They must be consulted as history, not copied wholesale. Fresh Scout output will replace historical localization authority for this resumed task.
