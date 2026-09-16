# gate-reviewer-output-contract-reliability

Status: Final

Resumption base: `main@f2e6503e88161d01fbd73dc4a60e5da7d98167b4`
Historical task branch: `task-gate-reviewer-output-contract-reliability@54b727319eb8088a86086f02b4be4a55aa2167d2`
Resumption review: [`RESUMPTION_REVIEW.md`](RESUMPTION_REVIEW.md)
Fresh Scout: [`CONTEXT.md`](CONTEXT.md)

## Goal

Make OpenCode reviewer outcomes machine-reliable while keeping the Gate deliberately small, deterministic, and non-semantic.

The architectural intent is no longer "reviewer -> Gate -> another reviewer". The intended workflow is:

```text
Gemini / Antigravity
implementation writer
        ↓
OpenCode independent reviewers
semantic code review
        ↓
StructuredOutput + lifecycle evidence
        ↓
small SDK adapter
mechanical OpenCode integration only
        ↓
Gate
protocol validator + fallback router + transaction coordinator
        ↓
canonical GitHub evidence
        ↓
ChatGPT / human
final semantic + architecture review
```

The reviewer owns the semantic PASS/BLOCK judgment.

The Gate does **not** review code and does **not** decide whether the reviewer reasoning is correct. The Gate only decides whether the reviewer attempt is trustworthy enough for its PASS/BLOCK to be accepted into the workflow.

This distinction is an architecture invariant for this task.

## Core responsibility invariant

The Gate is exactly:

```text
Gate = protocol validator
     + fallback router
     + transaction coordinator
```

The Gate is not:

```text
- a code reviewer
- an architecture reviewer
- a second semantic judge
- a model reasoning evaluator
- a prose interpreter
- a replacement for final ChatGPT/human review
```

The Gate may answer only these five questions:

1. **Was the reviewer attempt real and trustworthy enough to evaluate?**
2. **Is the reviewer machine output valid?**
3. **If the attempt is invalid before verdict authority, may the workflow safely fall back to another reviewer candidate?**
4. **Did the required deterministic focused tests pass?**
5. **May canonical evidence be promoted transactionally?**

If implementation logic asks the Gate to answer anything materially broader than those five questions, that is an architecture smell and must be justified explicitly against this SPEC.

## Why Gate still exists when StructuredOutput exists

StructuredOutput solves only the machine-output-format problem.

A model can still produce a schema-valid object without having performed a trustworthy review. For example, compatibility evidence already proved that a model can return a valid structured PASS/BLOCK shape without repository `read` / `glob` / `grep` grounding.

Therefore:

```text
StructuredOutput answers:
"What machine-readable result did the reviewer return?"

Gate answers:
"Is this reviewer result authorized to enter the workflow?"
```

The Gate does not create or reinterpret the verdict.

A reviewer says:

```text
PASS or BLOCK
```

The Gate says only:

```text
ACCEPTED trusted verdict
or
REJECTED attempt classification
```

The accepted reviewer verdict remains the reviewer verdict.

## Verified baseline

The completed `opencode-structured-review-provider-compatibility` task established:

- OpenCode is pinned to `1.18.31`.
- `@opencode-ai/sdk` is pinned to `1.18.31`.
- The supported structured route is official SDK v2 `session.prompt(... format: { type: "json_schema" })`.
- The authoritative structured machine field is `promptResult.data.info.structured`.
- `StructuredOutput` is an OpenCode tool and successful settlement is represented by a typed `ToolPart` with `state.status == "completed"`.
- `finish == "tool-calls"` is not evidence of failure or max-step exhaustion by itself.
- `client.session.messages` has an `OutputFormatJsonSchema` decoder defect and must not be a production dependency for this task.
- Big Pickle demonstrated that structured transport can succeed while repository grounding fails.
- MiMo demonstrated the separate failure mode of ending without producing StructuredOutput.

Pinned-source verification additionally established:

- `session.prompt()` ultimately returns the last assistant message from the one-shot session.
- OpenCode can create multiple assistant messages across model/tool steps.
- therefore final `promptResult.data.parts` proves final StructuredOutput facts but may not contain earlier grounding calls;
- SDK v2 exposes typed event subscription and `message.part.updated` events containing `sessionID` and typed `Part` data;
- a production adapter can observe same-session grounding and finalization without relying on `session.messages`.

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
completed StructuredOutput
        ↓
promptResult.data.info.structured
        ↓
adapter mechanical envelope
        ↓
Gate protocol validation
        ↓
ACCEPTED reviewer PASS/BLOCK
or typed attempt rejection
        ↓
focused tests
        ↓
transactional canonical promotion
        ↓
GitHub evidence
        ↓
final ChatGPT/human semantic review
```

Human-readable Markdown is presentation evidence only. It is never the machine verdict transport.

## Responsibility model

### 1. Reviewer — semantic authority

`spec-reviewer` and `regression-reviewer` are small, independent, read-only semantic reviewers.

Their job is to:

- inspect the relevant task contract and repository evidence;
- understand the implementation change;
- detect blocking semantic / architecture / regression defects within their role;
- produce `PASS` or `BLOCK` plus evidence-based `report_markdown`.

Only the reviewer/model decides semantic PASS vs BLOCK.

Neither the adapter nor Gate may override a trusted reviewer BLOCK into PASS or reinterpret prose into a different verdict.

The reviewer is still intentionally bounded. It is not expected to perform an exhaustive audit of the entire repository.

### 2. Adapter — OpenCode mechanical integration

Introduce one small production adapter:

```text
scripts/opencode_structured_review.mjs
```

The adapter exists only to isolate OpenCode-specific SDK/session/event/StructuredOutput mechanics from PowerShell Gate policy.

It owns:

1. official `@opencode-ai/sdk/v2` request construction;
2. fresh one-shot reviewer session creation;
3. typed event subscription established before review execution;
4. bounded same-session event collection;
5. prompt execution with the fixed JSON schema;
6. final prompt-response/session/message identity checks;
7. extraction of `info.structured`;
8. extraction of final completed `StructuredOutput` ToolPart facts;
9. extraction of completed model-initiated `read` / `glob` / `grep` lifecycle evidence;
10. teardown / cleanup trust;
11. bounded/redacted diagnostics;
12. emission of one deterministic machine envelope to Gate.

The adapter must not:

- select fallback models;
- decide whether PASS is preferable to BLOCK;
- decide final Gate state;
- parse `report_markdown` for verdict authority;
- promote canonical artifacts;
- query stale/older sessions to salvage a failed attempt;
- perform semantic review;
- depend on compatibility-matrix routing logic at runtime.

### 3. Gate — verification orchestrator

`scripts/ai_gate.ps1` remains the orchestration owner, but its responsibility is intentionally narrow.

It owns only:

#### Protocol validation

- confirm the adapter envelope is well-formed;
- apply the current grounding policy;
- distinguish lifecycle / transport / structured-result / schema / semantic-consistency failure classes;
- apply deterministic PASS/BLOCK cross-field invariants;
- accept or reject reviewer verdict authority.

#### Fallback routing

- select configured reviewer candidates in bounded order;
- invoke another candidate only when the current attempt never reached trusted verdict authority and cleanup is proven safe;
- stop immediately after trusted PASS or trusted BLOCK;
- prevent semantic review-shopping.

#### Transaction coordination

- orchestrate focused deterministic tests;
- stage candidate evidence;
- render canonical review/EVIDENCE deterministically from accepted machine fields;
- promote canonical artifacts transactionally;
- rollback on promotion failure;
- map the final workflow state to the existing external exit codes.

Gate must not:

- inspect implementation code to decide correctness;
- judge architecture quality;
- score reviewer reasoning quality;
- compare two semantic reviewer opinions and choose the preferred one;
- recover a verdict from prose;
- manufacture PASS/BLOCK from partial evidence;
- become a second AI reviewer encoded in PowerShell rules.

### 4. Final ChatGPT / human review — semantic safety net

Final ChatGPT/human review remains the last semantic/architecture review after Gate evidence is available on GitHub.

This stage may:

- disagree with a trusted reviewer PASS;
- detect responsibility-boundary / coupling / state-ownership / timing / testability / dead-logic / technical-debt / architecture-drift problems;
- request implementation correction before merge.

Therefore Gate PASS does **not** mean "the code is correct".

It means only:

> the automated independent reviewer + deterministic focused-test workflow produced trustworthy canonical evidence and did not produce a trusted blocker.

## Grounding contract

The invariant is that a reviewer verdict must be grounded in repository evidence tied to the current candidate/task state.

For this task, the current machine-verifiable minimum grounding proxy remains:

- at least one **model-initiated** permitted repository `read`, `glob`, or `grep` call;
- the call reaches `state.status == "completed"`;
- it belongs to the same fresh isolated reviewer session;
- it occurs before the accepted `StructuredOutput` finalization.

This proves only a minimum anti-ungrounded-review condition. Gate does not attempt to prove semantic coverage completeness by counting tools.

The invariant is **grounding/provenance**, not permanent loyalty to `read/glob/grep`.

A future `reviewer-bounded-context-infrastructure` task may replace or strengthen this proxy with a provenance-bearing deterministic Context Pack. That downstream task must preserve or improve the grounding invariant; this task must not pre-implement it.

## Structured result contract

The authoritative semantic object is exactly:

```json
{
  "verdict": "PASS | BLOCK",
  "blocking_findings": 0,
  "report_markdown": "..."
}
```

Required shape/type rules:

- exactly these three fields;
- `verdict` is `PASS` or `BLOCK`;
- `blocking_findings` is a non-negative integer;
- `report_markdown` is a string.

Cross-field invariants:

```text
PASS  -> blocking_findings == 0
BLOCK -> blocking_findings >= 1
```

Gate validates those invariants mechanically.

Gate does not decide whether the reviewer's textual reasoning is persuasive enough. That belongs to final semantic review.

Verdict-like strings inside `report_markdown` have zero machine authority.

## Lifecycle / completion contract

Trusted verdict authority requires:

```text
same-session grounding evidence
+ trustworthy lifecycle observation
+ completed final StructuredOutput ToolPart
+ non-null info.structured
+ valid schema
+ valid cross-field semantics
= trusted reviewer verdict
```

Consequences:

- `finish == "tool-calls"` is valid and must not be rejected by itself;
- `finish == "stop"` does not validate a missing StructuredOutput;
- step count is a safety ceiling, not a coverage quota;
- no `finalization_voluntary` boolean is required;
- do not infer max-step exhaustion from finish strings;
- a valid completed StructuredOutput may be accepted even on the configured final model step if all authority invariants pass;
- a system/model path without accepted StructuredOutput remains non-authoritative.

Step/finish metadata may remain diagnostic only.

## Attempt classification

Attempt classification is about **why a reviewer attempt is or is not authoritative**.

Required machine-distinguishable classes are equivalent to:

- `GROUNDING_FAILED`
- `LIFECYCLE_UNTRUSTWORTHY`
- `STRUCTURED_TRANSPORT_FAILED`
- `STRUCTURED_OUTPUT_MISSING`
- `SCHEMA_INVALID`
- `SEMANTIC_CONTRADICTION`
- `INFRASTRUCTURE_FAILED`
- `VALID_PASS`
- `VALID_BLOCK`

These classes must not be collapsed merely to make routing convenient.

Examples:

- authoritative session + no completed repository read/search -> `GROUNDING_FAILED`;
- same-session lifecycle cannot be proven -> `LIFECYCLE_UNTRUSTWORTHY`;
- SDK/prompt/server transport fails -> `STRUCTURED_TRANSPORT_FAILED` or `INFRASTRUCTURE_FAILED` according to the actual failed layer;
- no accepted StructuredOutput -> `STRUCTURED_OUTPUT_MISSING`;
- invalid object shape/type -> `SCHEMA_INVALID`;
- `PASS + blocking_findings > 0` -> `SEMANTIC_CONTRADICTION`;
- all authority checks pass and reviewer says PASS -> `VALID_PASS`;
- all authority checks pass and reviewer says BLOCK -> `VALID_BLOCK`.

## Fallback / anti-review-shopping

Fallback is allowed only while no trusted semantic verdict exists.

A trusted `VALID_PASS` or `VALID_BLOCK` is terminal for that reviewer role.

Bounded fallback may continue after pre-authority failures such as:

- `GROUNDING_FAILED`;
- `LIFECYCLE_UNTRUSTWORTHY`, only with safe cleanup;
- `STRUCTURED_TRANSPORT_FAILED`, only with safe cleanup;
- `STRUCTURED_OUTPUT_MISSING`;
- `SCHEMA_INVALID`;
- `SEMANTIC_CONTRADICTION`;
- mechanically proven process/infrastructure failures with confirmed safe termination.

An unconfirmed timeout/termination or unsafe cleanup is terminal for the chain.

Fallback must never be used to seek a more favorable answer after trusted PASS/BLOCK.

## Gate final-state semantics

Attempt classification and Gate final state are separate concepts.

Gate exposes exactly these top-level outcomes:

- `PASSED`: both reviewer roles reached trusted PASS outcomes and required focused tests passed;
- `CANDIDATE_BLOCKED`: at least one trusted reviewer BLOCK or focused-test failure blocks the candidate;
- `VERIFICATION_UNAVAILABLE`: Gate could not obtain enough trusted reviewer/test authority to decide safely.

`VERIFICATION_UNAVAILABLE` is not synonymous with infrastructure failure.

Examples:

- all candidates `GROUNDING_FAILED`;
- one candidate `STRUCTURED_OUTPUT_MISSING`, another `SCHEMA_INVALID`;
- transport/infrastructure prevented trusted review;
- lifecycle authority could not be proven;
- cleanup became unsafe and fallback stopped.

External exit-code compatibility remains:

```text
0 = PASSED
2 = CANDIDATE_BLOCKED
1 = VERIFICATION_UNAVAILABLE
```

`INFRASTRUCTURE_FAILED` is an attempt/root-cause classification, not the generic top-level state.

If every candidate is exhausted before verdict authority, Gate returns `VERIFICATION_UNAVAILABLE` / exit 1 and preserves canonical trusted artifacts.

Existing degraded Gemini review may still run after exit 1, but it remains non-independent because Gemini is also the implementation writer. It may provide useful evidence to final ChatGPT/human review, but it has no Gate PASS authority.

## Canonical artifacts

### `reviews/spec-review.md` / `reviews/regression-review.md`

Canonical review files are deterministic human-readable renderings of an **accepted reviewer result**.

They contain:

- reviewer `report_markdown`;
- deterministic Gate-generated verdict metadata derived from accepted machine fields;
- optional compact provenance.

They must not contain raw lifecycle dumps as normal review content.

### `EVIDENCE.md`

`EVIDENCE.md` remains the workflow verification summary and records at least:

- Gate final state;
- task, branch, HEAD, base ref;
- accepted reviewer role/model/attempt when applicable;
- accepted reviewer verdict/blocking count when applicable;
- compact grounding/lifecycle/transport/schema status;
- prior fallback attempt classifications;
- exact root classifications for `VERIFICATION_UNAVAILABLE`;
- focused-test results;
- pointers to detailed review files.

It must not describe pure model-compliance exhaustion as `INFRASTRUCTURE_BLOCKED`.

### `.runtime/ai_gate/<task>/`

Raw failed-attempt output and bounded diagnostics remain ephemeral / git-ignored.

## Required removals

The following old abstractions are obsolete and must disappear from the authoritative production reviewer path:

1. `Get-FinalAssistantMessageFromStructuredJson()` as verdict extraction;
2. `Get-CanonicalReviewPayload()`;
3. regex/header-based `Test-ReviewVerdictStructure()`;
4. direct production reviewer transport via `opencode run --format json`;
5. free-text `VERDICT:` / `BLOCKING_FINDINGS:` reviewer protocol;
6. separate voluntary final assistant text requirement;
7. any `finish == "tool-calls"` max-step failure heuristic;
8. any rule equivalent to "all reviewer failures are infrastructure failures";
9. any Gate logic that performs semantic code/architecture review;
10. any Gate logic that scores or reinterprets reviewer reasoning quality.

Removing the old parser does not remove semantic invariants. PASS/0 and BLOCK/>=1 move to structured machine validation.

No hidden text compatibility path may retain PASS/BLOCK authority.

## Required preservation

Preserve stable, already-useful orchestration behavior where compatible with this Final contract:

- bounded child-process execution;
- timeout handling;
- kill/termination confirmation;
- non-interactive stdin behavior;
- candidate ordering and bounded fallback machinery;
- git status/diff snapshots;
- focused-test orchestration and full-suite rejection policy;
- trusted BLOCK terminality;
- candidate staging;
- canonical backup;
- transactional promotion;
- rollback on promotion failure;
- task-namespaced runtime diagnostics;
- external `0 / 1 / 2` exit-code contract;
- `EVIDENCE.md` as the canonical verification summary.

Do not opportunistically redesign these areas unless the adapter boundary makes a narrowly necessary change unavoidable.

## Reviewer-agent contract changes

`.opencode/agents/spec-reviewer.md` and `.opencode/agents/regression-reviewer.md` must:

- remain read-only;
- preserve existing role boundaries;
- preserve step ceilings (`8`, `10`);
- preserve bounded blocker detection and early-stop behavior;
- explicitly require repository grounding before finalization;
- perform all needed research before StructuredOutput;
- stop requiring free-text `VERDICT:` / `BLOCKING_FINDINGS:` headers;
- keep `report_markdown` concise and evidence-based;
- not require a trailing assistant text turn after StructuredOutput.

## Scope

Primary implementation surface:

- `scripts/ai_gate.ps1`
- `scripts/opencode_structured_review.mjs` (new)
- `.opencode/agents/spec-reviewer.md`
- `.opencode/agents/regression-reviewer.md`
- `tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1`
- structured adapter fixtures/helpers under `tests/workflow_scripts/` as needed
- `tests/test_workflow_scripts.py` (new)
- `scripts/opencode_structured_review_probe.mjs` / tests only if a small pure helper extraction is clearly justified
- `docs/architecture/ai_development_workflow.md`
- this task package

The existing SDK pin in `package.json` is baseline. Dependency/version churn is out of scope.

## Non-goals

- changing OpenCode away from `1.18.31`;
- reopening provider/version exploration;
- implementing `reviewer-bounded-context-infrastructure`;
- eliminating reviewer read/search capability;
- weakening grounding because output format is valid;
- adding a long-lived global OpenCode session/server state owner;
- restoring trailing final-text requirements;
- treating `finish: tool-calls` as exhaustion;
- parsing verdict authority from prose/Markdown/JSON fences/XML/older messages;
- changing Scout behavior;
- changing game/runtime behavior;
- changing reviewer step budgets/timeouts;
- running the full product test suite by default;
- replacing final ChatGPT/human semantic review;
- turning Gate into a semantic reviewer.

## Forbidden shortcuts

Implementation MUST NOT:

1. recover PASS/BLOCK from `report_markdown` or raw assistant text;
2. use `client.session.messages` as production audit fallback;
3. use final prompt-response parts alone as proof of earlier grounding;
4. call missing read/search a lifecycle failure when lifecycle itself is authoritative;
5. infer forced finalization from finish strings;
6. relabel grounding/schema/semantic failures as infrastructure to permit fallback;
7. invoke another candidate after trusted PASS/BLOCK;
8. promote canonical trusted reviewer artifacts from a pre-authority attempt;
9. silently change/install OpenCode/SDK versions;
10. couple production execution to compatibility-matrix routing;
11. retain hidden regex/free-text verdict fallback;
12. emit top-level `INFRASTRUCTURE_BLOCKED` for generic reviewer exhaustion;
13. duplicate SDK session/event protocol logic inside `ai_gate.ps1`;
14. re-review implementation semantics inside Gate;
15. reject/accept a trusted reviewer verdict because Gate disagrees with its reasoning;
16. compare trusted semantic verdicts from multiple candidates to select a preferred result.

## Complexity / architecture budget

This task must make Gate **more deterministic and conceptually smaller**, not turn it into a larger semantic policy engine.

The expected direction is:

```text
REMOVE from ai_gate.ps1:
CLI JSONL reviewer parsing
assistant-text extraction
VERDICT header salvage
regex verdict authority
OpenCode-specific session/event details
semantic-looking reviewer logic

MOVE behind adapter:
SDK request/session/event/StructuredOutput mechanics

KEEP in ai_gate.ps1:
validation policy
fallback routing
focused-test orchestration
transactional evidence promotion
```

A significant increase in Gate complexity or semantic branching is a review smell.

Implementation is not required to reduce raw line count mechanically, because structured classifications/tests may add explicit code. The requirement is responsibility reduction: OpenCode protocol complexity moves behind the adapter and semantic review remains outside Gate.

Final review must explicitly check whether Gate still answers only the five allowed questions defined at the top of this SPEC.

## Required deterministic verification

Existing `tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1` must be evolved rather than replaced by a parallel harness.

Add:

```text
tests/test_workflow_scripts.py
```

Focused offline deterministic verification must cover at least:

1. grounded structured PASS -> accepted reviewer PASS -> `PASSED` / exit 0;
2. grounded structured BLOCK -> terminal accepted BLOCK -> `CANDIDATE_BLOCKED` / exit 2, no fallback;
3. valid completed StructuredOutput with `finish == "tool-calls"` is accepted;
4. earlier same-session completed read/search satisfies grounding even when final prompt response contains only StructuredOutput;
5. structured output without same-session completed read/search -> `GROUNDING_FAILED`;
6. event/session identity mismatch or incomplete lifecycle -> `LIFECYCLE_UNTRUSTWORTHY`;
7. missing StructuredOutput / `info.structured` -> `STRUCTURED_OUTPUT_MISSING`;
8. invalid structured shape/type -> `SCHEMA_INVALID`;
9. PASS/>0 and BLOCK/0 -> `SEMANTIC_CONTRADICTION`;
10. verdict-like `report_markdown` text cannot change the machine outcome;
11. stale/other-session output cannot override the current attempt;
12. pre-authority failure may fall back when cleanup is safe;
13. unsafe/unconfirmed termination stops fallback -> `VERIFICATION_UNAVAILABLE` / exit 1;
14. trusted PASS/BLOCK never invokes a later candidate;
15. pre-authority attempts preserve prior canonical trusted reviewer artifacts;
16. promotion failure rolls back canonical state;
17. reviewer step budgets and OpenCode `1.18.31` pin remain enforced;
18. existing structured-review probe tests remain passing;
19. candidate exhaustion through non-infrastructure failures -> `VERIFICATION_UNAVAILABLE`, not infrastructure-blocked;
20. `EVIDENCE.md` preserves true root classifications;
21. production Gate invokes the structured adapter rather than direct `opencode run --format json` reviewer transport;
22. legacy free-text `VERDICT:` output has zero verdict authority;
23. adapter facts can be mechanically accepted/rejected without any semantic code/architecture evaluation inside Gate;
24. final Gate logic still maps cleanly to protocol validation, fallback routing, test orchestration, and transaction coordination only.

The tests must not require a live provider/model.

## Focused test targets

`task.json` must declare:

```text
tests.test_opencode_structured_review_probe
tests.test_workflow_scripts
```

The full product test suite remains user-only under repository policy.

## Acceptance criteria

1. Reviewer semantic PASS/BLOCK authority comes only from accepted StructuredOutput machine fields.
2. Gate does not generate, reinterpret, or semantically re-review PASS/BLOCK.
3. Gate can be accurately described as `protocol validator + fallback router + transaction coordinator`.
4. Gate implementation answers only the five allowed questions defined by this SPEC.
5. OpenCode-specific SDK/session/event mechanics are isolated behind the small adapter boundary.
6. Production uses OpenCode `1.18.31` + SDK `1.18.31` official v2 structured transport and `info.structured`.
7. Fresh one-shot session + typed event evidence proves same-session grounding.
8. Production does not depend on broken `client.session.messages` decoding.
9. Current grounding policy requires completed same-session model-initiated `read` / `glob` / `grep` before StructuredOutput.
10. `finish == "tool-calls"` is not treated as failure/exhaustion by itself.
11. Valid StructuredOutput may be terminal on the configured final model step when all other authority conditions pass.
12. Grounding/lifecycle/transport/missing-output/schema/semantic-contradiction/infrastructure remain distinguishable attempt classes.
13. Trusted PASS and BLOCK are both terminal and cannot trigger semantic review-shopping.
14. Pre-authority fallback is bounded and only allowed with trustworthy cleanup.
15. Gate final states are `PASSED`, `CANDIDATE_BLOCKED`, `VERIFICATION_UNAVAILABLE`.
16. External exit compatibility remains `0 / 2 / 1` respectively.
17. Canonical reviews/EVIDENCE derive reviewer verdict state only from accepted machine fields.
18. Pre-authority attempts preserve prior canonical trusted reviewer artifacts.
19. Promotion/rollback remains transactional.
20. Reviewer agents remain independent read-only bounded blocker detectors with 8/10 step ceilings.
21. Direct production reviewer transport through `opencode run --format json` is removed.
22. Old text extraction/header/regex verdict authority is removed.
23. Stable bounded-process, timeout, focused-test, candidate-routing, staging, promotion, rollback behavior is preserved where compatible.
24. `reviewer-bounded-context-infrastructure` remains downstream and may later replace HOW grounding is proven without redefining the grounding invariant.
25. No game/runtime behavior changes occur.
26. Gate PASS remains only workflow-verification success, not final semantic approval; final ChatGPT/human semantic/architecture review remains mandatory before merge.
27. Final semantic review explicitly checks that Gate has not grown into a second reviewer or absorbed OpenCode adapter responsibilities.

## Implementation handoff

This SPEC is Final.

Gemini/Antigravity may implement the smallest coherent patch satisfying this contract.

OpenCode Scout/reviewers remain read-only.

Do not implement `reviewer-bounded-context-infrastructure` inside this task.

After implementation and focused deterministic tests pass, run the normal real Gate validation for this task. A trusted BLOCK remains a legitimate reviewer result requiring implementation correction. Pre-authority exhaustion remains `VERIFICATION_UNAVAILABLE` and must never be relabeled PASS.
