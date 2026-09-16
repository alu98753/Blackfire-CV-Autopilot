# Gate reviewer output contract resumption review

Task: `gate-reviewer-output-contract-reliability`

Status: Evidence-driven resumption survey
Date: 2026-09-16

Continuation branch: `task-gate-reviewer-output-contract-reliability-resume`
Base: `main@f2e6503e88161d01fbd73dc4a60e5da7d98167b4`
Historical branch preserved untouched: `task-gate-reviewer-output-contract-reliability@54b727319eb8088a86086f02b4be4a55aa2167d2`

## 1. Historical architecture summary

The historical task correctly identified the central architecture defect: Gate must not derive PASS/BLOCK authority from the placement or formatting of free-form Markdown. Its intended flow was:

```text
reviewer semantic judgment
    -> OpenCode JSON-Schema structured outcome
    -> deterministic Gate semantic validation
    -> deterministic human-readable rendering
```

It also established durable rules that remain valuable:

- `PASS` requires `blocking_findings == 0`;
- `BLOCK` requires `blocking_findings >= 1`;
- `report_markdown` is presentation evidence, not a verdict parser input;
- a valid semantic PASS or BLOCK is terminal and must not trigger review-shopping;
- invalid/untrustworthy reviewer attempts must not overwrite canonical review artifacts;
- canonical review rendering and promotion remain deterministic Gate responsibilities.

However, the historical implementation and model matrix were built around assumptions that have since been invalidated by the completed OpenCode compatibility task.

The historical branch is therefore evidence/spec history, not an implementation baseline.

## 2. Current verified baseline

The merged compatibility task established the following production baseline:

```text
OpenCode 1.18.31
+ @opencode-ai/sdk 1.18.31 official v2 transport
+ opencode/big-pickle
        -> format.type = json_schema
        -> OpenCode StructuredOutput tool
        -> HTTP 200
        -> promptResult.data.info.structured
        -> schema-valid structured object
```

Verified lifecycle facts:

1. `promptResult.data.parts` is a typed same-attempt response surface when it contains a complete internally consistent lifecycle for that returned assistant message.
2. Tool parts expose `part.type == "tool"`, `part.tool`, and `part.state.status`.
3. A successfully settled tool is observable as `part.state.status == "completed"`.
4. `StructuredOutput` itself is represented as a ToolPart.
5. A completed `StructuredOutput` call can therefore naturally end with `finish == "tool-calls"`.
6. `finish == "tool-calls"` is not evidence of max-step exhaustion by itself.
7. `client.session.messages` is affected by the `OutputFormatJsonSchema` decoder defect and is not the preferred source when the prompt response already proves the lifecycle facts required by the contract.
8. Fresh Attempt 021 proved a valid structured semantic review can still fail formal qualification because no repository `read` / `glob` / `grep` occurred. That is a grounding/tool-choice failure, not a lifecycle-source failure.
9. MiMo demonstrated the distinct failure mode of voluntarily stopping a complex review without invoking `StructuredOutput`, leaving `info.structured` absent.

Pinned OpenCode `v1.18.31` source additionally proves:

- `UserMessage.format` accepts `OutputFormatJsonSchema`;
- `AssistantMessage` exposes optional `structured` and `finish` fields;
- `ToolPart` has a typed `ToolState`, including `status: "completed"`;
- `StepFinishPart.reason` is a generic string, not a dedicated max-step enum;
- JSON-schema mode injects a `StructuredOutput` tool whose source contract says required research/tool work happens before calling it and that the tool supplies the final answer;
- JSON-schema mode sets tool choice to required;
- the runtime computes `isLastStep` internally from `step >= agent.steps` and injects `MAX_STEPS_PROMPT` on that step.

No dedicated typed `max_steps_exhausted` field was found in the exposed message/part contract during this lightweight survey. Therefore the old inference `finish == "tool-calls" -> forced finalization` is invalid. Whether exact step-count evidence can safely establish exhaustion from the response surface remains a Scout question.

## 3. Assumption-by-assumption audit of the historical Final SPEC

| Historical assumption / decision | Decision now | Reason |
| --- | --- | --- |
| Machine verdict authority must be independent of Markdown placement | **KEEP** | Still the core defect in current `main`, where `ai_gate.ps1` parses free-form JSONL text and verdict headers. |
| Fixed structured fields: `verdict`, `blocking_findings`, `report_markdown` | **KEEP** | Proven by live C3 transport and deterministic validation tests. |
| `PASS -> 0`, `BLOCK -> >=1` cross-field invariant | **KEEP** | Deterministic semantic invariant remains valid. |
| `report_markdown` has zero machine verdict authority | **KEEP** | Required to prevent prose from redefining machine state. |
| Historical adapter using root `createOpencode(...)` request shape | **REMOVE / REPLACE** | Proven production path is official SDK v2 transport and its flat request shape. |
| Official result field `info.structured_output` | **REMOVE / REPLACE** | Proven v2 machine field is `promptResult.data.info.structured`. |
| A valid review requires a separate voluntary final assistant text turn after tools | **REMOVE** | `StructuredOutput` is itself the final structured response tool; a separate text turn is not the correct v2 abstraction. |
| `finish == "tool-calls"` proves forced finalization | **REMOVE** | Directly contradicted by pinned source and live lifecycle evidence. |
| Forced max-step completion must not become verdict authority | **KEEP, detection OPEN** | The invariant is still sound, but its old detector is not. A trustworthy positive signal must be mechanically defined. |
| Reviewer must perform `read` / `glob` / `grep` | **REVISE** | The real invariant is repository grounding / provenance, not the specific UI gesture. Model-initiated repo tools are the current proxy until a stronger provenance-bearing input contract exists. |
| Missing/invalid structured output should not be treated as PASS/BLOCK | **KEEP** | MiMo demonstrates this remains a real distinct failure. |
| All non-verdict failures can be collapsed into infrastructure failure | **REVISE** | Grounding, lifecycle, transport, schema, semantic contradiction, and process infrastructure must remain separately machine-classified. |
| Fallback is allowed only under the old broad infrastructure bucket | **OPEN POLICY QUESTION** | Safe fallback should depend on whether an authoritative semantic verdict was accepted, not on mislabeling every invalid attempt as infrastructure. |
| Valid structured BLOCK is terminal | **KEEP** | Current routing already stops after a valid BLOCK; a trusted BLOCK is candidate evidence, not a reason to shop for another reviewer. |
| Gate deterministically renders canonical review Markdown | **KEEP** | Presentation remains downstream of validated machine fields. |
| Canonical review/EVIDENCE promotion is transactional | **KEEP** | Current `main` already protects rollback and preserves prior canonical evidence on infra failure. |
| SDK installation/bootstrap is a primary unresolved task risk | **REMOVE from primary scope** | `main` already pins `@opencode-ai/sdk` 1.18.31 in repository package metadata and the compatibility task established the transport. |
| Historical model matrix is current qualification truth | **REMOVE** | It predates C3 and incorrectly classified `tool-calls` finalization. Preserve it only as historical evidence. |

## 4. Corrected responsibility-layer model

The resumed task should converge on a machine-verifiable contract with these independent layers. A failure in one layer must not masquerade as another.

### Layer 1 — Evidence acquisition / grounding

Question answered: **What repository evidence was available to the reviewer, and why can Gate trust its provenance/freshness?**

Minimum invariant:

> Gate must not trust reviewer semantic judgment unless it can mechanically prove that the review was grounded in evidence tied to the candidate repository state and canonical task contract.

Today, a completed model-initiated `read` / `glob` / `grep` against the repository is the existing proxy for this invariant. It is not necessarily the final architecture.

A future deterministic Context Pack may satisfy the same invariant without mandatory model-initiated discovery only if it can prove at least:

- exact task/spec identity;
- base/head/diff identity;
- evidence provenance for included repository facts;
- deterministic bounded selection/truncation metadata;
- freshness / stale-pack rejection;
- delivery of that pack to the exact reviewer attempt;
- explicit uncertainty/omission metadata;
- retained bounded reviewer verification capability when supplied evidence is insufficient or suspicious.

Until such infrastructure exists and is qualified, do not silently delete the current repository-tool grounding requirement.

### Layer 2 — Lifecycle authority

Question answered: **Does the evidence belong to this exact review attempt, and is the attempt observably complete enough to evaluate?**

Candidate requirements for the final contract:

- prompt/session/message identity is internally consistent;
- lifecycle parts used for classification belong to the same returned attempt/message;
- relevant ToolParts have settled typed states rather than pending/running states;
- a terminal `step-finish` exists for the authoritative returned message;
- no fatal assistant error invalidates the attempt;
- if another lifecycle source is needed, it must itself be trustworthy and same-attempt.

This layer MUST NOT depend on whether the reviewer chose the correct repository tools. Attempt 021 proves those are separate questions.

### Layer 3 — Semantic reviewer judgment

Question answered: **What did the reviewer judge?**

Only the reviewer/model owns `PASS` vs `BLOCK` and the supporting report. Gate/adapter must not reinterpret prose to manufacture a verdict.

### Layer 4 — Structured result transport

Question answered: **Did the official OpenCode structured-output mechanism deliver a machine result?**

Production candidate path:

```text
format.type = json_schema
-> StructuredOutput ToolPart completed
-> promptResult.data.info.structured present
```

A separate final assistant text turn is not required.

### Layer 5 — Schema validation

Question answered: **Does the returned machine object have exactly the allowed fields/types?**

Required object remains:

```json
{
  "verdict": "PASS | BLOCK",
  "blocking_findings": 0,
  "report_markdown": "..."
}
```

No extra machine fields should silently become verdict authority.

### Layer 6 — Cross-field semantic validation

Question answered: **Are machine fields internally consistent?**

- PASS requires `blocking_findings == 0`.
- BLOCK requires `blocking_findings >= 1`.

A contradiction is not a PASS/BLOCK result.

### Layer 7 — Human-readable rendering

Question answered: **How is a trusted machine result presented to humans?**

Gate renders canonical Markdown deterministically from validated machine fields plus `report_markdown`. Verdict-like prose inside `report_markdown` remains non-authoritative.

### Layer 8 — Artifact promotion / rollback

Question answered: **When may canonical `reviews/*` and `EVIDENCE.md` change?**

A trusted PASS or BLOCK may be promoted. A trusted BLOCK is terminal and should be promoted as candidate-blocking evidence. Attempts that fail before verdict authority must not overwrite prior canonical trusted review artifacts. Existing transactional rollback semantics should remain.

### Layer 9 — Infrastructure fallback

Question answered: **Did process/SDK/transport execution fail independently of reviewer semantics?**

Examples:

- launch failure;
- timeout / unsafe termination;
- adapter crash;
- SDK/server failure;
- malformed adapter envelope;
- unusable lifecycle source when the contract needs data unavailable from the authoritative prompt response.

These remain mechanically eligible for bounded model fallback under existing anti-shopping rules.

### Layer 10 — Model fallback / review-shopping prevention

The stronger invariant is:

> Fallback may occur only when no authoritative semantic verdict has been accepted from the current attempt.

Therefore a grounded, lifecycle-authoritative, transport-valid, schema-valid, semantically consistent PASS **or BLOCK** is terminal.

The Final SPEC must explicitly decide whether non-authoritative model-compliance failures such as `GROUNDING_FAILED` or `STRUCTURED_OUTPUT_MISSING` are eligible for the same bounded candidate fallback chain. If allowed, Gate must classify them separately from infrastructure and must not inspect/use their semantic verdict as a candidate decision before falling back. This is safer than relabeling model behavior as infrastructure merely to preserve fallback.

## 5. Corrected failure taxonomy hypothesis

Provisional machine classes:

| Class | Meaning | Semantic verdict authority? | Candidate artifact promotion? | Fallback hypothesis |
| --- | --- | ---: | ---: | --- |
| `GROUNDING_FAILED` | Required provenance/grounding proof absent | No | No | Open: likely eligible if bounded and verdict ignored |
| `LIFECYCLE_UNTRUSTWORTHY` | Same-attempt completion cannot be proven | No | No | Yes |
| `STRUCTURED_TRANSPORT_FAILED` | SDK/official structured route failed | No | No | Yes |
| `STRUCTURED_OUTPUT_MISSING` | Transport completed but model omitted StructuredOutput/result | No | No | Open: likely eligible as model-compliance failure |
| `SCHEMA_INVALID` | Structured object shape/type invalid | No | No | Open: likely eligible because no valid verdict exists |
| `SEMANTIC_CONTRADICTION` | PASS/BLOCK fields contradict invariant | No | No | Open: likely eligible because no valid verdict exists |
| `INFRASTRUCTURE_FAILED` | Process/server/timeout/teardown/adapter envelope failure | No | No | Yes |
| `VALID_PASS` | All authority layers satisfied, PASS/0 | Yes | Yes | No; terminal |
| `VALID_BLOCK` | All authority layers satisfied, BLOCK/>=1 | Yes | Yes | No; terminal |

This table is a hypothesis for Scout/Final-SPEC convergence. It deliberately separates cause from routing policy.

## 6. Max-step / completion semantics

The old `finalization_voluntary` model must be replaced with a narrower machine question: **is the attempt complete and non-forced under evidence we can actually prove?**

Verified now:

- `finish == "tool-calls"` is neutral; it can be the normal completion reason for `StructuredOutput`.
- `finish == "stop"` does not prove structured-output compliance; MiMo stopped voluntarily without returning the required machine result.
- a completed `StructuredOutput` ToolPart plus valid `info.structured` is a legitimate terminal structured-result shape.

Not yet verified:

- whether the production response surface exposes a trustworthy positive typed signal for max-step exhaustion;
- whether counting complete step-start/step-finish pairs against the configured reviewer ceiling is always sufficient;
- whether the adapter can distinguish a StructuredOutput call made on the internally injected last-step path from one made before exhaustion without consulting untrusted prose.

Until Scout resolves this from current code/source and available lifecycle surfaces, do not retain the historical `finish` regex as a substitute.

## 7. Canonical artifact hypothesis

Minimal recommended split:

### Node adapter output to Gate

One deterministic machine envelope containing only bounded mechanical facts, for example:

- role / model / attempt index;
- session/message identity;
- lifecycle-source identity and trust result;
- bounded ToolPart summary needed for grounding/lifecycle classification;
- structured-output presence;
- raw structured outcome object;
- schema-validation result;
- bounded transport/SDK diagnostics.

The adapter must not choose a different semantic verdict from model fields and must not own model-fallback policy or artifact promotion.

### `scripts/ai_gate.ps1`

Gate should own:

- reviewer candidate routing;
- policy classification across grounding/lifecycle/transport/schema/semantic layers;
- fallback eligibility and anti-review-shopping terminality;
- deterministic cross-field semantic validation if not already redundantly checked by the adapter;
- focused-test integration;
- canonical rendering;
- artifact promotion / rollback;
- exit-code mapping.

### Canonical `reviews/*`

Human-readable deterministic rendering of validated `report_markdown` plus a Gate-generated verdict section. Optional compact provenance may be included, but raw lifecycle dumps should not become canonical review prose.

### `EVIDENCE.md`

Status-first summary of accepted reviewer outcomes, selected model/attempt provenance, validation/grounding classification, focused tests, task/base/head identity, and pointers to detailed reviews.

Ephemeral raw output and failed-attempt diagnostics remain under `.runtime/ai_gate/<task>/` unless a future spec explicitly promotes a bounded diagnostic artifact.

## 8. Exact questions fresh Scout must localize

Fresh Scout must answer only the implementation-localization questions needed to finalize this contract:

1. In current `ai_gate.ps1`, which functions/branches must be replaced to move from CLI JSONL/free-text verdict parsing to one structured adapter envelope while preserving timeout, routing, tests, exit codes, and transactional promotion?
2. Which current workflow tests assert free-form/header-first behavior, and what is the smallest deterministic test seam for structured adapter results?
3. Does current Gate need any data from earlier assistant messages to prove grounding, or can required grounding be supplied/proven through the final prompt response for the current reviewer execution shape?
4. If earlier messages are required, what same-attempt typed source is available without relying on the broken `session.messages` decoder path?
5. What exact lifecycle facts can current OpenCode 1.18.31 v2 expose to positively prove max-step exhaustion? Is there a dedicated signal, complete step-count proof, or no trustworthy proof available?
6. Does a successful `StructuredOutput` call always correspond to a completed ToolPart + `info.structured` on the same returned message in the production SDK v2 path?
7. Which reviewer prompt clauses are obsolete because they require a separate final assistant text turn/header-first response, and which grounding clauses remain necessary?
8. Which current promotion/fallback tests already protect valid BLOCK terminality and rollback, and which need adaptation rather than duplication?
9. Can the compatibility probe's already-tested transport/lifecycle helpers be reused safely, or should production adapter logic remain separate to avoid diagnostic/production coupling?
10. What is the smallest production change surface that leaves `reviewer-bounded-context-infrastructure` entirely downstream?

## 9. Relationship to reviewer-bounded-context-infrastructure

Responsibility order remains:

```text
gate-reviewer-output-contract-reliability
    owns WHAT evidence/authority must be proven
        ↓
reviewer-bounded-context-infrastructure
    owns HOW to provide that evidence efficiently
```

The downstream Draft already proposes a provenance-bearing bounded Context Pack and explicitly asks whether formal review qualification can eventually rely on pack provenance plus optional targeted verification.

This upstream task must not design or implement the pack. It should define the acceptance boundary the pack would have to satisfy before model-initiated repository discovery could cease to be mandatory.

## 10. Recommended minimal new scope

Primary production scope after Final SPEC should be limited to:

- `scripts/ai_gate.ps1`;
- one small SDK-v2 structured review adapter (historical filename may be reused, implementation must not be copied wholesale);
- `.opencode/agents/spec-reviewer.md`;
- `.opencode/agents/regression-reviewer.md`;
- deterministic workflow tests / fixtures;
- `docs/architecture/ai_development_workflow.md`;
- task artifacts.

Use the merged compatibility probe/tests as evidence and regression coverage where useful. Do not reopen version/provider exploration and do not migrate the diagnostic probe into production wholesale without a responsibility-boundary reason.

## 11. Must NOT be implemented yet

While the active SPEC is Draft:

- no production Gate rewrite;
- no reviewer prompt changes;
- no adapter implementation copied/cherry-picked from the historical branch;
- no Context Pack implementation;
- no removal of grounding requirements;
- no max-step policy weakening based on `finish` strings;
- no model/provider/version churn;
- no Gate run as acceptance evidence;
- no merge.

The next allowed step after these remote artifacts are pushed is fresh Scout localization from the synchronized continuation worktree.