# gate-reviewer-output-contract-reliability

Status: Final

Resumption base: `main@f2e6503e88161d01fbd73dc4a60e5da7d98167b4`
Historical task branch: `task-gate-reviewer-output-contract-reliability@54b727319eb8088a86086f02b4be4a55aa2167d2`
Resumption review: [`RESUMPTION_REVIEW.md`](RESUMPTION_REVIEW.md)
Fresh Scout: [`CONTEXT.md`](CONTEXT.md)

## Goal

Make OpenCode reviewer outcomes machine-reliable while keeping Gate deliberately small, deterministic, and non-semantic.

The authoritative workflow is:

```text
Gemini / Antigravity
implementation writer
        ↓
OpenCode independent reviewers
semantic code review
        ↓
StructuredOutput + typed lifecycle evidence
        ↓
small SDK adapter
attempt qualification authority
        ↓
versioned deterministic envelope
        ↓
Gate
thin envelope validation + fallback routing + transaction coordination
        ↓
canonical GitHub evidence
        ↓
ChatGPT / human
final semantic + architecture review
```

Responsibility is intentionally split:

```text
Reviewer      = semantic authority
Adapter       = attempt qualification authority
Gate          = orchestration authority
ChatGPT/human = final semantic safety net
```

This responsibility split is an architecture invariant for this task.

## Core responsibility invariant

### Reviewer

The reviewer decides only semantic PASS/BLOCK for the candidate implementation.

### Adapter

The adapter decides whether one concrete OpenCode reviewer attempt is mechanically authoritative enough to become one of:

- `VALID_PASS`
- `VALID_BLOCK`
- a typed pre-authority failure classification

### Gate

Gate is exactly:

```text
Gate = thin adapter-envelope validator
     + fallback router
     + focused-test orchestrator
     + transaction coordinator
```

Gate is not:

```text
- a code reviewer
- an architecture reviewer
- a second semantic judge
- an OpenCode lifecycle reimplementation
- a StructuredOutput schema reimplementation
- a model reasoning evaluator
- a prose interpreter
- a replacement for final ChatGPT/human review
```

Gate may answer only these questions:

1. Did the adapter process return a supported, parseable machine envelope?
2. Is the adapter-owned classification supported by this Gate version?
3. Is cleanup/fallback safe according to the adapter/process boundary facts?
4. Is the current attempt terminal, or may bounded fallback continue?
5. Did required focused deterministic tests pass?
6. May canonical evidence be promoted transactionally?

If Gate logic materially recomputes OpenCode lifecycle, grounding, StructuredOutput schema, or PASS/BLOCK semantic consistency, that is architecture drift.

## Verified baseline

The completed `opencode-structured-review-provider-compatibility` task established:

- OpenCode is pinned to `1.18.31`.
- `@opencode-ai/sdk` is pinned to `1.18.31`.
- supported structured transport is official SDK v2 `session.prompt(... format: { type: "json_schema" })`.
- authoritative structured data is `promptResult.data.info.structured`.
- successful StructuredOutput settlement is represented by a typed ToolPart with `state.status == "completed"`.
- `finish == "tool-calls"` is not failure evidence by itself.
- `client.session.messages` has a decoder defect for this route and is not a production dependency.
- Big Pickle proved structured transport can succeed while repository grounding fails.
- MiMo proved the separate missing-StructuredOutput failure mode exists.
- SDK v2 typed event subscription can expose earlier same-session tool activity that final prompt response parts do not contain.

Live task evidence additionally established that OpenCode 1.18.31 + Big Pickle can produce a same-session grounded completed StructuredOutput with authoritative `info.structured` and a valid `VALID_BLOCK` adapter envelope. Remaining adapter teardown must allow that completed attempt to terminate naturally without leaving owned async resources alive.

## Final authority pipeline

```text
fresh isolated reviewer session
        ↓
typed same-session lifecycle events
        ↓
minimum repository grounding proof
        ↓
reviewer semantic judgment
        ↓
completed final StructuredOutput
        ↓
promptResult.data.info.structured
        ↓
adapter schema / consistency / lifecycle qualification
        ↓
adapter attempt classification
        ↓
versioned deterministic envelope
        ↓
Gate envelope-boundary validation
        ↓
terminal trusted verdict OR bounded fallback
        ↓
focused tests
        ↓
transactional canonical promotion
        ↓
final ChatGPT/human semantic review
```

Human-readable Markdown is presentation evidence only. It never carries machine verdict authority.

## Responsibility model

### 1. Reviewer — semantic authority

`spec-reviewer` and `regression-reviewer` are independent, read-only, bounded semantic reviewers.

They own:

- reading relevant task/repository evidence;
- understanding the implementation change;
- detecting blocking semantic, regression, and architecture defects within role scope;
- producing the canonical semantic object:

```json
{
  "verdict": "PASS | BLOCK",
  "blocking_findings": 0,
  "report_markdown": "..."
}
```

Only the reviewer/model decides semantic PASS vs BLOCK.

Neither adapter nor Gate may override a trusted BLOCK into PASS, choose a preferred reviewer opinion, or recover verdict authority from prose.

### 2. Adapter — attempt qualification authority

Production adapter:

```text
scripts/opencode_structured_review.mjs
```

The adapter isolates OpenCode-specific mechanics from Gate policy.

It owns:

1. official `@opencode-ai/sdk/v2` request construction;
2. fresh one-shot reviewer session creation;
3. typed event subscription established before prompt execution;
4. bounded same-session event collection;
5. final prompt/session/message identity qualification;
6. current grounding policy qualification;
7. ordering proof that completed model-initiated `read` / `glob` / `grep` occurs before accepted final StructuredOutput;
8. final completed StructuredOutput qualification;
9. authoritative `info.structured` extraction;
10. exact structured shape/type validation;
11. deterministic PASS/BLOCK cross-field validation;
12. teardown of adapter-owned async resources;
13. cleanup safety qualification;
14. bounded/redacted diagnostics;
15. final attempt classification;
16. emission of exactly one versioned deterministic machine envelope.

The adapter must not:

- select fallback models;
- choose PASS over BLOCK;
- decide Gate final state;
- parse `report_markdown` for verdict authority;
- promote canonical artifacts;
- query stale sessions to salvage a failed attempt;
- perform semantic code review;
- depend on compatibility-matrix routing at runtime.

### 3. Gate — orchestration authority

`scripts/ai_gate.ps1` remains the orchestration owner.

#### Thin envelope validation

Gate validates only the adapter/process boundary:

- adapter process completed normally enough to provide machine output;
- stdout contains one supported parseable envelope;
- supported `schema_version`;
- supported classification enum;
- minimum envelope sections / primitive field types required for routing exist;
- cleanup safety fact exists and is well typed;
- `VALID_PASS` / `VALID_BLOCK` includes structured payload sufficient for deterministic rendering.

Gate MUST NOT independently recompute:

- repository grounding qualification;
- lifecycle ordering/trust;
- final StructuredOutput completion qualification;
- exact three-field structured schema;
- `PASS -> blocking_findings == 0`;
- `BLOCK -> blocking_findings >= 1`;
- semantic-contradiction classification.

Those are adapter-owned deterministic qualifications.

Gate consumes the adapter classification subject to envelope-version/type validation.

#### Fallback routing

Gate owns:

- configured candidate ordering;
- bounded candidate invocation;
- fallback only before trusted verdict authority and only when cleanup/process termination is safe;
- immediate terminal stop after trusted `VALID_PASS` or `VALID_BLOCK`;
- anti-review-shopping.

#### Transaction coordination

Gate owns:

- focused deterministic test orchestration;
- candidate evidence staging;
- deterministic rendering from accepted machine fields;
- transactional canonical promotion;
- rollback on promotion failure;
- aggregate final state;
- external exit-code mapping.

### 4. Final ChatGPT / human review — semantic safety net

Final ChatGPT/human review remains mandatory after Gate evidence is available.

It may disagree with an automated PASS and may detect responsibility-boundary, coupling, state ownership, timing, testability, dead logic, technical debt, or architecture drift.

Therefore Gate PASS means workflow verification succeeded, not that the implementation is semantically correct.

## Grounding contract

A reviewer verdict must be grounded in repository evidence tied to the current candidate/task state.

For this task the machine-verifiable minimum proxy is:

- at least one model-initiated permitted repository `read`, `glob`, or `grep`;
- tool state reaches `completed`;
- event belongs to the same fresh reviewer session;
- it occurs before accepted final StructuredOutput.

The **adapter applies this grounding policy and emits the resulting attempt classification**.

Gate does not recompute grounding from raw lifecycle facts. Gate only routes on the adapter-owned classification.

This is a minimum anti-ungrounded-review condition, not proof of semantic coverage completeness.

A future `reviewer-bounded-context-infrastructure` task may replace HOW grounding is proven while preserving or strengthening the grounding invariant.

## Structured result contract

The authoritative semantic object contains exactly:

```json
{
  "verdict": "PASS | BLOCK",
  "blocking_findings": 0,
  "report_markdown": "..."
}
```

Shape/type requirements:

- exactly these three fields;
- `verdict` is `PASS` or `BLOCK`;
- `blocking_findings` is a non-negative integer;
- `report_markdown` is a string.

Cross-field invariants:

```text
PASS  -> blocking_findings == 0
BLOCK -> blocking_findings >= 1
```

**The adapter validates these invariants mechanically before assigning `VALID_PASS` or `VALID_BLOCK`.**

Gate does not repeat them. Gate validates the versioned adapter-envelope boundary and routes on the adapter-owned classification.

Verdict-like strings inside `report_markdown` have zero machine authority.

## Lifecycle / completion contract

Adapter qualification for trusted verdict authority requires:

```text
same-session grounding evidence
+ trustworthy typed lifecycle observation
+ accepted final-message identity
+ completed final StructuredOutput ToolPart
+ non-null info.structured
+ valid structured schema
+ valid PASS/BLOCK cross-field semantics
+ safe owned-resource teardown
= VALID_PASS or VALID_BLOCK
```

Consequences:

- `finish == "tool-calls"` is neutral and cannot be rejected by itself;
- `finish == "stop"` does not validate missing StructuredOutput;
- step count is a safety ceiling, not a coverage quota;
- no trailing assistant text turn is required;
- final prompt parts alone cannot prove earlier grounding;
- same-session and final-message identity are fail-closed authority boundaries;
- valid completed StructuredOutput may occur on the configured final model step;
- cleanup includes adapter-owned async resources, not only server process termination.

## Adapter teardown / cleanup contract

The adapter owns every asynchronous resource it starts, including the OpenCode server process and event subscription / consumer.

Before emitting an envelope with `cleanup.safe == true`, the adapter must mechanically establish the required owned-resource teardown state.

Required behavior:

- explicitly cancel/abort/close the event subscription or stream using supported pinned SDK semantics where available;
- stop and bounded-await the consumer task;
- terminate the owned OpenCode server;
- confirm server termination;
- ensure no adapter-owned stream/socket/timer remains capable of keeping Node alive;
- emit exactly one envelope;
- naturally terminate with exit code 0 after a valid envelope, including `VALID_BLOCK`.

An unconditional `process.exit(0)` is not an acceptable substitute for owned-resource teardown.

If owned-resource teardown cannot be proven safe, the attempt must not be represented as safely reusable for fallback.

## Attempt classification

Adapter-owned attempt classifications remain machine-distinguishable:

- `GROUNDING_FAILED`
- `LIFECYCLE_UNTRUSTWORTHY`
- `STRUCTURED_TRANSPORT_FAILED`
- `STRUCTURED_OUTPUT_MISSING`
- `SCHEMA_INVALID`
- `SEMANTIC_CONTRADICTION`
- `INFRASTRUCTURE_FAILED`
- `VALID_PASS`
- `VALID_BLOCK`

Examples:

- authoritative lifecycle but no completed grounding -> `GROUNDING_FAILED`;
- current-session/final-message lifecycle cannot be proven -> `LIFECYCLE_UNTRUSTWORTHY`;
- SDK/prompt/server transport fails -> appropriate transport/infrastructure classification;
- no accepted StructuredOutput -> `STRUCTURED_OUTPUT_MISSING`;
- invalid structured shape/type -> `SCHEMA_INVALID`;
- PASS with blocking findings or BLOCK with zero findings -> `SEMANTIC_CONTRADICTION`;
- all adapter authority checks pass + reviewer PASS -> `VALID_PASS`;
- all adapter authority checks pass + reviewer BLOCK -> `VALID_BLOCK`.

Gate must not collapse these classes merely for routing convenience.

## Fallback / anti-review-shopping

Fallback is allowed only while no trusted semantic verdict exists.

A trusted `VALID_PASS` or `VALID_BLOCK` is terminal for that reviewer role.

Safe bounded fallback may continue after pre-authority classifications such as:

- `GROUNDING_FAILED`;
- `LIFECYCLE_UNTRUSTWORTHY`;
- `STRUCTURED_TRANSPORT_FAILED`;
- `STRUCTURED_OUTPUT_MISSING`;
- `SCHEMA_INVALID`;
- `SEMANTIC_CONTRADICTION`;
- confirmed-safe process/infrastructure failures.

Fallback requires cleanup/process termination to be safe for that attempt.

Unconfirmed termination or unsafe cleanup stops the chain.

Fallback must never be used to seek a more favorable semantic result after trusted PASS/BLOCK.

## Gate final-state semantics

Attempt classification and Gate final state are different concepts.

Gate exposes exactly:

- `PASSED`: both reviewer roles reached trusted PASS and required focused tests passed;
- `CANDIDATE_BLOCKED`: at least one trusted BLOCK or focused-test failure blocks the candidate;
- `VERIFICATION_UNAVAILABLE`: sufficient trusted reviewer/test authority could not be obtained safely.

External compatibility:

```text
0 = PASSED
2 = CANDIDATE_BLOCKED
1 = VERIFICATION_UNAVAILABLE
```

`VERIFICATION_UNAVAILABLE` is not synonymous with infrastructure failure.

Examples include:

- all candidates `GROUNDING_FAILED`;
- `STRUCTURED_OUTPUT_MISSING` followed by `SCHEMA_INVALID` with no candidates left;
- lifecycle authority cannot be proven;
- transport prevents trusted review;
- unsafe cleanup stops fallback.

Candidate exhaustion before trusted verdict authority returns `VERIFICATION_UNAVAILABLE` / exit 1 and must not be relabeled semantic BLOCK or generic infrastructure-blocked.

## Canonical artifacts

### `reviews/spec-review.md` / `reviews/regression-review.md`

Canonical review files are deterministic human-readable renderings of accepted reviewer results.

They contain reviewer `report_markdown`, deterministic verdict metadata from accepted machine fields, and optional compact provenance.

### `EVIDENCE.md`

`EVIDENCE.md` remains the canonical verification summary after transactional promotion.

It records, where applicable:

- Gate final state;
- task / branch / HEAD / base ref;
- accepted reviewer role/model/attempt;
- accepted verdict/blocking count;
- prior attempt classifications;
- focused-test results;
- pointers to review files.

For runs that terminate before transactional promotion, prior trusted canonical artifacts must remain untouched. Root classifications remain available in task-namespaced runtime diagnostics and, when the workflow produces/promotes a canonical evidence summary, must remain distinguishable rather than being collapsed to `INFRASTRUCTURE_BLOCKED`.

### `.runtime/ai_gate/<task>/`

Raw failed-attempt output and bounded diagnostics are ephemeral / git-ignored.

## Required removals

The authoritative production reviewer path must not contain:

1. `Get-FinalAssistantMessageFromStructuredJson()` verdict extraction;
2. `Get-CanonicalReviewPayload()`;
3. regex/header-based `Test-ReviewVerdictStructure()`;
4. direct reviewer transport through `opencode run --format json`;
5. free-text `VERDICT:` / `BLOCKING_FINDINGS:` authority;
6. trailing voluntary final-text requirements;
7. `finish == "tool-calls"` failure heuristics;
8. rules equating all reviewer failures with infrastructure failure;
9. Gate semantic code/architecture review;
10. Gate scoring/reinterpreting reviewer reasoning;
11. Gate duplication of adapter grounding/lifecycle/schema/cross-field qualification.

No hidden compatibility path may retain PASS/BLOCK authority.

## Required preservation

Preserve stable orchestration behavior where compatible:

- bounded child-process execution;
- async stdout/stderr draining;
- timeout handling;
- kill/termination confirmation;
- non-interactive stdin;
- candidate ordering and bounded fallback;
- git status/diff snapshots;
- focused-test orchestration and full-suite rejection;
- trusted BLOCK terminality;
- candidate staging;
- canonical backup;
- transactional promotion;
- rollback;
- task-namespaced runtime diagnostics;
- external `0 / 1 / 2` contract.

## Reviewer-agent contract

`.opencode/agents/spec-reviewer.md` and `.opencode/agents/regression-reviewer.md` must:

- remain read-only;
- preserve role boundaries;
- preserve step ceilings (`8`, `10`);
- remain bounded blocker detectors;
- require repository grounding before finalization;
- perform needed research before StructuredOutput;
- use StructuredOutput as the machine result;
- keep `report_markdown` concise and evidence based;
- not require verdict headers or a trailing text turn.

Wording such as `After the header, return Markdown with:` is stale and should be replaced with wording that directly describes `report_markdown` content.

## Scope

Primary implementation surface:

- `scripts/ai_gate.ps1`
- `scripts/opencode_structured_review.mjs`
- `.opencode/agents/spec-reviewer.md`
- `.opencode/agents/regression-reviewer.md`
- `tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1`
- structured adapter fixtures/helpers under `tests/workflow_scripts/` as needed
- `tests/test_workflow_scripts.py`
- `docs/architecture/ai_development_workflow.md`
- this task package

Dependency/version churn is out of scope.

## Non-goals

- changing OpenCode away from `1.18.31`;
- reopening provider/version exploration;
- implementing `reviewer-bounded-context-infrastructure`;
- weakening grounding;
- adding a long-lived global OpenCode session/server owner;
- restoring trailing final-text requirements;
- treating `finish: tool-calls` as exhaustion;
- parsing verdict authority from prose/Markdown/older messages;
- changing Scout behavior;
- changing game/runtime behavior;
- changing reviewer step budgets/timeouts;
- running the full product suite by default;
- replacing final ChatGPT/human review;
- turning Gate into a semantic or qualification reviewer.

## Forbidden shortcuts

Implementation MUST NOT:

1. recover PASS/BLOCK from `report_markdown` or raw assistant text;
2. use `client.session.messages` as production audit fallback;
3. use final prompt-response parts alone as proof of earlier grounding;
4. infer forced finalization from finish strings;
5. relabel adapter grounding/schema/semantic failure classes as infrastructure merely for routing;
6. invoke another candidate after trusted PASS/BLOCK;
7. promote trusted canonical reviewer artifacts from a pre-authority attempt;
8. silently change/install OpenCode/SDK versions;
9. couple production execution to compatibility-matrix routing;
10. retain regex/free-text verdict fallback;
11. emit top-level `INFRASTRUCTURE_BLOCKED` for generic exhaustion;
12. duplicate SDK/session/event mechanics inside Gate;
13. duplicate adapter grounding/schema/semantic qualification inside Gate;
14. re-review implementation semantics inside Gate;
15. reject/accept a trusted verdict because Gate disagrees with reasoning;
16. compare trusted semantic verdicts from multiple candidates to choose a preferred result;
17. hide incomplete async cleanup behind unconditional `process.exit(0)`.

## Complexity / architecture budget

This task must make Gate more deterministic and conceptually smaller.

```text
REMOVE from Gate:
OpenCode lifecycle qualification
StructuredOutput schema qualification
PASS/BLOCK cross-field qualification
semantic-looking reviewer logic

KEEP behind adapter:
SDK/session/event mechanics
grounding qualification
final-message/StructuredOutput qualification
schema + cross-field validation
attempt classification
owned-resource cleanup qualification

KEEP in Gate:
thin envelope checks
fallback routing
focused-test orchestration
transactional promotion / rollback
final state / exit mapping
```

A significant increase in Gate semantic or OpenCode-specific branching is a review smell.

## Required deterministic verification

Existing `tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1` must be evolved rather than replaced.

Focused offline deterministic verification must cover at least:

### Adapter qualification

1. grounded structured PASS -> `VALID_PASS`;
2. grounded structured BLOCK -> `VALID_BLOCK`;
3. valid completed StructuredOutput with `finish == "tool-calls"` is valid;
4. earlier same-session grounding can precede final-message StructuredOutput;
5. missing grounding -> `GROUNDING_FAILED`;
6. event/session/final-message identity mismatch -> `LIFECYCLE_UNTRUSTWORTHY`;
7. missing StructuredOutput / `info.structured` -> `STRUCTURED_OUTPUT_MISSING`;
8. invalid structured shape/type -> `SCHEMA_INVALID`;
9. PASS/>0 and BLOCK/0 -> `SEMANTIC_CONTRADICTION`;
10. adapter-owned event consumer / subscription teardown settles boundedly;
11. safe cleanup allows natural adapter exit 0 after one envelope;
12. unsettled/unsafe owned-resource cleanup is not marked safe.

### Gate routing / orchestration

13. adapter envelope `VALID_PASS` can produce `PASSED` / exit 0 when both roles/tests pass;
14. adapter envelope `VALID_BLOCK` is terminal and produces `CANDIDATE_BLOCKED` / exit 2;
15. trusted PASS/BLOCK mechanistically proves no later candidate invocation;
16. `GROUNDING_FAILED` with safe cleanup may fall back;
17. `STRUCTURED_OUTPUT_MISSING` with safe cleanup may fall back;
18. `SCHEMA_INVALID` with safe cleanup may fall back;
19. `SEMANTIC_CONTRADICTION` with safe cleanup may fall back;
20. unsafe/unconfirmed cleanup stops fallback -> `VERIFICATION_UNAVAILABLE` / exit 1;
21. exhaustion of safe pre-authority classifications -> `VERIFICATION_UNAVAILABLE` / exit 1;
22. root attempt classifications remain distinguishable in runtime/provenance evidence;
23. verdict-like Markdown cannot change machine outcome;
24. legacy free-text `VERDICT:` has zero authority;
25. malformed/unsupported envelope fails closed;
26. unsupported `schema_version` fails closed;
27. pre-authority attempts preserve prior canonical trusted artifacts;
28. promotion failure rolls back canonical state;
29. reviewer step budgets and OpenCode 1.18.31 pin remain enforced;
30. production Gate invokes the structured adapter rather than direct reviewer `opencode run --format json` transport;
31. Gate does not independently derive grounding/schema/semantic classifications from raw adapter facts.

The tests must not require a live provider/model.

## Focused test targets

`task.json` must continue to declare:

```text
tests.test_opencode_structured_review_probe
tests.test_workflow_scripts
```

The full product suite remains user-only under repository policy.

## Acceptance criteria

1. Reviewer semantic PASS/BLOCK authority comes only from accepted StructuredOutput machine fields.
2. Adapter is the single attempt-qualification authority for lifecycle, grounding, StructuredOutput, schema, cross-field semantics, cleanup, and classification.
3. Gate does not recompute adapter qualification logic.
4. Gate is accurately described as thin envelope validator + fallback router + focused-test orchestrator + transaction coordinator.
5. OpenCode-specific SDK/session/event mechanics remain isolated behind adapter.
6. Production uses OpenCode 1.18.31 + SDK 1.18.31 official v2 structured transport and `info.structured`.
7. Fresh one-shot session + typed event evidence proves same-session grounding and final-message StructuredOutput authority.
8. Production does not depend on `client.session.messages`.
9. Current grounding policy requires completed same-session model-initiated `read` / `glob` / `grep` before accepted StructuredOutput.
10. `finish == "tool-calls"` is neutral.
11. Adapter-owned async resources terminate boundedly; valid envelope execution exits naturally with code 0.
12. Attempt failure classes remain distinguishable.
13. Trusted PASS and BLOCK are terminal and cannot trigger semantic review-shopping.
14. Pre-authority fallback is bounded and cleanup-safe only.
15. Final states remain `PASSED`, `CANDIDATE_BLOCKED`, `VERIFICATION_UNAVAILABLE`.
16. External exits remain `0 / 2 / 1` respectively.
17. Canonical reviews derive verdict state only from accepted machine fields.
18. Pre-authority attempts preserve prior trusted canonical review artifacts.
19. Promotion/rollback remains transactional.
20. Reviewer agents remain independent read-only bounded blocker detectors with 8/10 step ceilings.
21. Direct production reviewer transport through `opencode run --format json` remains removed.
22. Old text/header/regex verdict authority remains removed.
23. Stable bounded-process, timeout, candidate-routing, focused-test, staging, promotion, and rollback behavior is preserved where compatible.
24. `reviewer-bounded-context-infrastructure` remains downstream.
25. No game/runtime behavior changes occur.
26. Gate PASS is workflow-verification success only; final ChatGPT/human semantic/architecture review remains mandatory.
27. Final review explicitly checks that Gate has not absorbed adapter qualification responsibilities.

## Implementation handoff

This SPEC is Final.

This Final amendment resolves the stale responsibility split that previously assigned duplicate grounding/schema/cross-field qualification to Gate. Historical reviewer findings based only on that stale duplicate responsibility are not implementation requirements.

Gemini/Antigravity may implement the smallest coherent patch satisfying this amended contract.

OpenCode Scout/reviewers remain read-only.

Do not implement `reviewer-bounded-context-infrastructure` inside this task.

After implementation and focused deterministic tests pass, run a bounded local adapter termination check first. Then stop for ChatGPT pre-live review before the next real Gate execution.
