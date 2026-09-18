# gate-reviewer-output-contract-reliability

Status: Final

Resumption base: `main@f2e6503e88161d01fbd73dc4a60e5da7d98167b4`
Historical task branch: `task-gate-reviewer-output-contract-reliability@54b727319eb8088a86086f02b4be4a55aa2167d2`
Resumption review: [`RESUMPTION_REVIEW.md`](RESUMPTION_REVIEW.md)
Fresh Scout: [`CONTEXT.md`](CONTEXT.md)

## Goal

Make OpenCode reviewer outcomes machine-reliable without turning OpenCode implementation details into reviewer-authority requirements.

The workflow is:

```text
Gemini / Antigravity
implementation writer
        ↓
OpenCode independent reviewers
semantic review
        ↓
SDK adapter
attempt qualification
        ↓
versioned envelope
        ↓
Gate
routing + tests + transaction coordination
        ↓
canonical GitHub evidence
        ↓
ChatGPT / human
final semantic / architecture review
```

Responsibility is fixed:

```text
Reviewer      = semantic authority
Adapter       = attempt qualification authority
Gate          = orchestration authority
ChatGPT/human = final semantic safety net
```

This split is an architecture invariant.

## Core principle

The automation should verify only what materially contributes to trustworthy review authority.

It must not reject an otherwise grounded, schema-valid reviewer verdict merely because an internal OpenCode SSE event, step marker, finish string, or event-order detail is absent or delayed.

The authority question is intentionally small:

> Did a fresh reviewer session actually inspect repository evidence and return a valid structured PASS/BLOCK result through the supported SDK contract?

Everything else is either transport safety, cleanup safety, routing policy, or diagnostic evidence.

## Verified OpenCode 1.18.31 SDK contract

Pinned source/type inspection establishes for `@opencode-ai/sdk@1.18.31`:

- successful `session.prompt()` HTTP 200 data is:

```ts
{
  info: AssistantMessage
  parts: Array<Part>
}
```

- `AssistantMessage.id` is required `string`;
- `AssistantMessage.sessionID` is required `string`;
- `AssistantMessage.structured` is optional and is the authoritative structured-result field;
- generated client request behavior defaults to `throwOnError = false` unless configured as a request/client option;
- therefore production adapter must configure SDK error handling correctly and must not pass `throwOnError` as if it were prompt body data;
- an API/SDK failure that yields no successful `data.info` must be treated as transport/API-contract failure, not as reviewer lifecycle ambiguity;
- server source writes successful `StructuredOutput` into the assistant message `structured` field before returning the final assistant message;
- `info.structured` is therefore the authoritative success signal for structured reviewer output;
- completed `StructuredOutput` ToolPart events and step-finish events may remain useful diagnostics but are not independent hard authority requirements.

The production path remains pinned to OpenCode `1.18.31` and SDK `1.18.31`.

## Reviewer — semantic authority

`spec-reviewer` and `regression-reviewer` remain independent, read-only, bounded semantic reviewers.

They own:

- reading relevant task/repository evidence;
- understanding the implementation change;
- detecting blocking semantic / regression / architecture defects within role scope;
- producing exactly:

```json
{
  "verdict": "PASS | BLOCK",
  "blocking_findings": 0,
  "report_markdown": "..."
}
```

Only the reviewer/model decides semantic PASS vs BLOCK.

Neither Adapter nor Gate may:

- override trusted BLOCK into PASS;
- reinterpret `report_markdown` as machine authority;
- compare multiple trusted reviewer opinions to choose a preferred semantic result;
- become another semantic reviewer.

## Adapter — attempt qualification authority

Production adapter:

```text
scripts/opencode_structured_review.mjs
```

The adapter isolates OpenCode-specific mechanics from Gate.

It owns:

1. correct official `@opencode-ai/sdk/v2` client/request construction;
2. fresh one-shot reviewer session creation;
3. SDK error handling with `throwOnError` configured in the supported client/request option surface;
4. one bounded typed event subscription for repository-grounding evidence;
5. authoritative prompt-response success validation;
6. response `info.id` and `info.sessionID` validation against the requested fresh session;
7. current repository-grounding policy;
8. `info.structured` extraction;
9. exact review-object shape/type validation;
10. deterministic PASS/BLOCK cross-field validation;
11. adapter-owned async-resource teardown and cleanup safety;
12. bounded/redacted diagnostics;
13. final attempt classification;
14. exactly one deterministic versioned envelope.

The adapter must not:

- select fallback models;
- decide Gate final state;
- perform semantic code review;
- parse prose for verdict authority;
- query stale sessions to salvage a failed attempt;
- depend on compatibility-matrix routing at runtime.

## Minimal trusted-review authority contract

A reviewer attempt may become `VALID_PASS` or `VALID_BLOCK` only when all of the following are true:

```text
fresh isolated reviewer session
+ session.prompt successful under the SDK contract
+ response info.id exists
+ response info.sessionID matches the fresh session
+ same fresh session contains at least one completed model-initiated repository read/glob/grep
+ info.structured exists
+ structured review schema is valid
+ PASS/BLOCK cross-field semantics are valid
= trusted reviewer verdict
```

Cleanup safety is additionally required for the workflow to continue/promote safely, but OpenCode internal event trivia is not review authority.

## Grounding contract

The machine-verifiable minimum grounding proxy remains:

- at least one model-initiated permitted repository `read`, `glob`, or `grep`;
- the tool reaches `state.status == "completed"`;
- the evidence belongs to the same fresh reviewer session used by the prompt.

That is enough for this task.

The adapter may use typed events to observe this fact and may boundedly tolerate delivery lag before final qualification.

The adapter does **not** need to prove an exact event-order relation between the completed repository tool and a `StructuredOutput` ToolPart event.

Reason: the session is fresh/one-shot, grounding belongs to the same session, and successful `session.prompt()` returns the final assistant result whose `info.structured` is the authoritative structured outcome.

This grounding proxy proves only that the reviewer actually inspected repository evidence. It does not prove semantic coverage completeness.

A future `reviewer-bounded-context-infrastructure` task may replace HOW grounding is proven while preserving or strengthening this invariant.

## Structured result contract

The authoritative semantic object contains exactly:

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

The Adapter validates these mechanically before assigning `VALID_PASS` or `VALID_BLOCK`.

Gate does not repeat them.

Verdict-like strings inside `report_markdown` have zero machine authority.

## SDK success / failure contract

For this task, successful prompt transport means the SDK call resolves through the supported success contract and yields a real `data.info: AssistantMessage`.

Because `AssistantMessage.id` and `sessionID` are required by the pinned type contract:

- missing `data.info`;
- missing `info.id`;
- missing `info.sessionID`;
- mismatched `info.sessionID`;

must not be treated as normal successful review output.

A request/API error that would otherwise resolve with `data: undefined` under the generated client's default non-throwing behavior must be surfaced by correct `throwOnError` configuration and classified as transport/API failure.

`message_id == null` is therefore not an accepted success state and must not be explained as ordinary reviewer lifecycle nondeterminism.

## OpenCode details that are diagnostic only

The following may be retained in diagnostics, logs, tests, or envelopes if useful, but they must not independently decide reviewer verdict authority:

- final `step-finish` observation;
- `terminal_step`;
- completed `StructuredOutput` ToolPart event;
- `final_structured_message_identity` derived from event matching;
- exact event-order relation between grounding and StructuredOutput event;
- `finish` string;
- `event_count`;
- `completion_boundary` label;
- `repository_tool_called` when `completed_repository_tool` already proves the stronger fact.

Absence or delay of those diagnostics must not turn an otherwise successful, same-session grounded, schema-valid `info.structured` result into `LIFECYCLE_UNTRUSTWORTHY`.

## Attempt classification

Adapter-owned classes remain machine-distinguishable:

- `GROUNDING_FAILED`
- `LIFECYCLE_UNTRUSTWORTHY`
- `STRUCTURED_TRANSPORT_FAILED`
- `STRUCTURED_OUTPUT_MISSING`
- `SCHEMA_INVALID`
- `SEMANTIC_CONTRADICTION`
- `INFRASTRUCTURE_FAILED`
- `VALID_PASS`
- `VALID_BLOCK`

Interpretation is narrowed as follows:

- `GROUNDING_FAILED`: prompt/session authority is otherwise usable, but no completed same-session repository grounding is observed;
- `LIFECYCLE_UNTRUSTWORTHY`: reserved for genuine session/provenance ambiguity that cannot be reduced to transport failure or missing grounding; it must not be used merely because step-finish or StructuredOutput event diagnostics are absent;
- `STRUCTURED_TRANSPORT_FAILED`: SDK/API/prompt contract did not complete successfully, including request errors or missing required success-response identity fields;
- `STRUCTURED_OUTPUT_MISSING`: successful prompt response exists but `info.structured` is absent;
- `SCHEMA_INVALID`: structured result shape/type invalid;
- `SEMANTIC_CONTRADICTION`: PASS/>0 or BLOCK/0;
- `INFRASTRUCTURE_FAILED`: adapter/server/process/cleanup infrastructure prevents safe workflow continuation;
- `VALID_PASS`: trusted grounded review says PASS;
- `VALID_BLOCK`: trusted grounded review says BLOCK.

Gate must not collapse these classes merely for routing convenience.

## Cleanup contract

The adapter owns every asynchronous resource it starts, including OpenCode server and event subscription/consumer.

Before the workflow may safely continue or promote, cleanup must establish:

- event subscription/consumer stop requested;
- consumer settles within a bounded deadline;
- owned server terminates;
- server exit is confirmed;
- no adapter-owned resource is knowingly left keeping Node alive.

The existing bounded teardown using abort + async-generator return + bounded settlement is retained unless pinned SDK evidence requires a narrower change.

An unconditional `process.exit(0)` is not an acceptable substitute for owned-resource teardown.

## Gate — orchestration authority

`scripts/ai_gate.ps1` remains deliberately small.

Gate validates only the adapter/process envelope boundary:

- adapter process completed normally enough to provide machine output;
- one supported envelope is parseable;
- supported `schema_version`;
- supported classification enum;
- minimum routing fields exist with expected primitive types;
- cleanup safety fact is present and well typed;
- `VALID_PASS` / `VALID_BLOCK` includes structured payload sufficient for deterministic rendering.

Gate MUST NOT recompute:

- grounding;
- OpenCode event ordering;
- StructuredOutput ToolPart completion;
- exact review-object schema;
- PASS/BLOCK cross-field consistency;
- semantic contradiction classification.

Gate owns:

- bounded configured candidate routing;
- fallback only before trusted verdict authority;
- cleanup-safe fallback;
- immediate stop after trusted `VALID_PASS` or `VALID_BLOCK`;
- anti-review-shopping;
- focused deterministic tests;
- evidence staging;
- transactional promotion / rollback;
- final state and external exit code.

## Fallback / anti-review-shopping

A trusted `VALID_PASS` or `VALID_BLOCK` is terminal for that reviewer role.

Safe fallback may continue after pre-authority classifications such as:

- `GROUNDING_FAILED`;
- genuine `LIFECYCLE_UNTRUSTWORTHY`;
- `STRUCTURED_TRANSPORT_FAILED`;
- `STRUCTURED_OUTPUT_MISSING`;
- `SCHEMA_INVALID`;
- `SEMANTIC_CONTRADICTION`;
- confirmed-safe infrastructure failure.

Unsafe/unconfirmed cleanup stops the chain.

Fallback must never seek a more favorable semantic answer after trusted PASS/BLOCK.

## Gate final states

Gate exposes exactly:

```text
PASSED                    -> exit 0
CANDIDATE_BLOCKED         -> exit 2
VERIFICATION_UNAVAILABLE  -> exit 1
```

`VERIFICATION_UNAVAILABLE` means sufficient trusted authority could not be obtained safely. It is not synonymous with infrastructure failure.

Examples:

- all candidates `GROUNDING_FAILED`;
- successful prompt responses without StructuredOutput;
- SDK transport failures exhaust candidates;
- genuine session/provenance ambiguity;
- unsafe cleanup stops fallback.

Candidate exhaustion before trusted verdict authority must never become semantic BLOCK.

## Canonical artifacts

`reviews/spec-review.md` and `reviews/regression-review.md` are deterministic renderings of accepted reviewer results.

`EVIDENCE.md` is the canonical verification summary after transactional promotion.

Runs that terminate before promotion must preserve prior trusted canonical artifacts.

Raw per-attempt diagnostics remain task-namespaced under:

```text
.runtime/ai_gate/<task>/
```

## Required preservation

Preserve where compatible:

- OpenCode `1.18.31` pin;
- SDK `1.18.31` pin;
- Windows `cmd.exe /d /s /c` launcher and `< NUL`;
- repository cwd;
- fresh one-shot reviewer session;
- typed event grounding observation;
- schema/cross-field validation in Adapter;
- bounded async stdout/stderr draining;
- timeout / termination confirmation;
- cleanup-safe fallback;
- focused-test orchestration and full-suite rejection;
- trusted PASS/BLOCK terminality;
- task-namespaced runtime diagnostics;
- candidate staging;
- transactional promotion and rollback;
- external `0 / 2 / 1` contract;
- no prose verdict authority;
- no production dependency on `client.session.messages`;
- no direct reviewer `opencode run --format json` transport;
- no Gate auto-commit/push/merge.

## Required removals / simplifications

The production authority path must not require:

1. final `step-finish` as reviewer authority;
2. `terminal_step == true` as reviewer authority;
3. a completed `StructuredOutput` ToolPart event when authoritative `info.structured` is already present;
4. `final_structured_message_identity` event matching as an additional hard requirement;
5. exact grounding-before-StructuredOutput event ordering;
6. `finish` value as reviewer authority;
7. event-count or completion-boundary labels as reviewer authority;
8. trailing assistant text after StructuredOutput;
9. `client.session.messages` fallback;
10. prose/header/regex verdict recovery;
11. duplicate Gate qualification of adapter-owned facts.

These details may remain diagnostic where useful.

## Reviewer-agent contract

`.opencode/agents/spec-reviewer.md` and `.opencode/agents/regression-reviewer.md` must:

- remain read-only;
- preserve role boundaries;
- preserve step ceilings (`8`, `10`);
- remain bounded blocker detectors;
- perform repository grounding before finalization;
- use StructuredOutput as the machine result;
- keep `report_markdown` concise and evidence-based;
- not require textual verdict headers or trailing text turns.

## Scope

Primary implementation surface:

- `scripts/opencode_structured_review.mjs`
- `scripts/ai_gate.ps1` only if the envelope/routing boundary requires a narrow compatibility change;
- `.opencode/agents/spec-reviewer.md` / `regression-reviewer.md` only for contract-aligned wording;
- `tests/test_workflow_scripts.py`;
- `tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1`;
- small deterministic fixtures/helpers as needed;
- this task package.

## Non-goals

- changing OpenCode or SDK away from `1.18.31`;
- reopening provider/version exploration;
- implementing resumable verification checkpoints in this task;
- implementing `reviewer-bounded-context-infrastructure`;
- weakening the requirement that reviewers actually inspect repository evidence;
- changing reviewer step budgets/timeouts;
- changing Scout behavior;
- changing game/runtime behavior;
- running the full product suite by default;
- replacing final ChatGPT/human semantic review;
- turning Gate into semantic or lifecycle qualification engine.

## Required deterministic verification

Focused offline deterministic tests must cover at least:

### SDK / Adapter

1. SDK failure/non-success cannot silently become `message_id = null` lifecycle failure;
2. supported error handling makes API/prompt failure surface as transport failure;
3. successful prompt result with `info.id` and matching `info.sessionID`, completed same-session grounding, and valid `info.structured` -> `VALID_PASS` / `VALID_BLOCK`;
4. successful prompt result with no same-session grounding -> `GROUNDING_FAILED`;
5. successful prompt result with missing `info.structured` -> `STRUCTURED_OUTPUT_MISSING`;
6. invalid structured shape/type -> `SCHEMA_INVALID`;
7. PASS/>0 and BLOCK/0 -> `SEMANTIC_CONTRADICTION`;
8. missing final step-finish alone does not invalidate an otherwise trusted result;
9. missing StructuredOutput ToolPart event alone does not invalidate an otherwise trusted `info.structured` result;
10. exact grounding-vs-StructuredOutput event ordering is not required;
11. `finish == "tool-calls"` remains diagnostic/neutral;
12. event consumer teardown remains bounded and adapter exits naturally after one envelope.

### Gate

13. `VALID_PASS` / `VALID_BLOCK` terminality prevents later candidate invocation;
14. safe pre-authority classifications may fall back;
15. unsafe cleanup stops fallback;
16. candidate exhaustion -> `VERIFICATION_UNAVAILABLE` / exit 1;
17. malformed/unsupported envelope fails closed;
18. canonical promotion/rollback remains transactional;
19. Gate does not rederive adapter grounding/schema/semantic classifications.

Tests must not require a live provider/model.

Focused targets remain:

```text
tests.test_opencode_structured_review_probe
tests.test_workflow_scripts
```

The full product suite remains user-only under repository policy.

## Acceptance criteria

1. Reviewer semantic authority comes only from valid structured machine fields, never prose.
2. Adapter is the single attempt-qualification authority.
3. Gate remains thin orchestration.
4. Production uses the supported OpenCode/SDK `1.18.31` route.
5. SDK error handling is configured on the supported client/request option surface so API failure cannot masquerade as lifecycle ambiguity.
6. A successful 200 prompt result is expected to contain required `AssistantMessage.id` and `sessionID`; absence is transport/API-contract failure, not ordinary lifecycle failure.
7. Same-fresh-session completed repository grounding remains mandatory.
8. `info.structured` is the authoritative StructuredOutput success field.
9. Step-finish, final StructuredOutput ToolPart event, exact event ordering, finish string, event count, and completion-boundary labels are not independent reviewer-authority requirements.
10. Review schema and PASS/BLOCK cross-field invariants remain adapter-validated.
11. Adapter-owned resources tear down boundedly and valid envelope execution exits naturally.
12. Attempt classes remain distinguishable.
13. Trusted PASS/BLOCK are terminal; no review shopping.
14. Pre-authority fallback is bounded and cleanup-safe only.
15. Gate final states remain `PASSED`, `CANDIDATE_BLOCKED`, `VERIFICATION_UNAVAILABLE` with exits `0 / 2 / 1`.
16. Canonical artifacts are transactionally promoted and preserved on pre-promotion failure.
17. No production `session.messages`, prose verdict parsing, or direct reviewer `opencode run --format json` authority path returns.
18. Final ChatGPT/human semantic/architecture review remains mandatory before merge.

## Implementation handoff

This SPEC is Final.

This amendment intentionally removes over-strict OpenCode lifecycle/event details from reviewer verdict authority and records the pinned SDK success/error contract discovered during live validation.

Gemini/Antigravity may implement the smallest coherent patch satisfying this contract.

OpenCode Scout/reviewers remain read-only.

Do not implement resumable verification checkpoints or `reviewer-bounded-context-infrastructure` inside this task.

After implementation and focused deterministic tests pass, stop for ChatGPT pre-live review before another full live Gate run.

## Closure amendment — 2026-09-16

This closure amendment is authoritative for task completion and supersedes the earlier Scope, deterministic-verification, and acceptance-criteria wording only where they conflict with the decisions below.

### Final task scope

The completed scope is the reviewer-output reliability path and the minimum supporting workflow surface actually changed during implementation:

- `.gitignore` runtime-artifact hygiene;
- `.opencode/agents/spec-reviewer.md` and `.opencode/agents/regression-reviewer.md` contract wording;
- `package.json` / `package-lock.json` for the pinned direct Undici transport dependency;
- `scripts/opencode_structured_review.mjs`;
- `scripts/ai_gate.ps1` changes required to consume the adapter contract and keep the 480s / 510s / 540s timeout hierarchy coherent;
- deterministic workflow tests and harness support;
- architecture/task documentation for this reviewer-output contract.

The immutable resumption baseline for this task is `f2e6503e88161d01fbd73dc4a60e5da7d98167b4`; `task.json` records that SHA rather than the moving `origin/main` ref.

### Core objective closure

The core infrastructure objective is met.

The final live Gate execution reached both independent OpenCode reviewers through the pinned OpenCode `1.18.31` / SDK `1.18.31` path and obtained machine-qualified trusted outcomes:

```text
spec-reviewer       -> VALID_BLOCK
regression-reviewer -> VALID_BLOCK
```

That live result proves the failures that originally prevented trusted reviewer authority were resolved: the supported SDK transport path completed, reviewer grounding and structured output were qualified, the adapter emitted trusted envelopes, the Gate consumed those envelopes, and the earlier transport/outer-process timeout races no longer prevented review completion.

`CANDIDATE_BLOCKED` is therefore preserved as the factual Gate result; it is not rewritten as `PASSED`. For this task, the trusted semantic BLOCKs are evidence that the reviewer-output infrastructure became reliable enough to surface downstream correctness findings.

### Explicitly deferred findings

The live reviewers exposed additional Gate-orchestration correctness work after reviewer-output reliability was established. Those findings are intentionally deferred to the follow-up task:

`gate-immutable-review-baseline-contract`

That follow-up owns the generalized contract for:

- immutable task review baselines and baseline provenance;
- eliminating moving-`origin/main` diff contamination and false out-of-scope findings;
- reproducible Gate diff snapshots;
- cleanup-safe fail-closed fallback semantics for malformed/partial failure envelopes, including the `cleanup.safe == false` corner discovered by the live review;
- related Gate-orchestration consistency revealed while making review snapshots reproducible;
- focused-test orchestration robustness discovered by the final live Gate run.

Accordingly, earlier Gate verification item 15 / acceptance criterion 14 are considered satisfied only for the validated-envelope paths already covered by this task. The malformed/partial failure-envelope cleanup corner is explicitly deferred rather than silently treated as complete.

### Verification and test closure

Before the final live Gate run, the task's deterministic transport/workflow checks reached 18 passing tests, with Node syntax, PowerShell syntax, and `git diff --check` passing for the implemented timeout hierarchy. The final live Gate then reached both reviewers successfully but reported focused-test failures/timeouts after reviewer authority had already been established.

Those focused-test orchestration results are recorded as evidence, not converted into a false PASS. The user explicitly chose not to run the full product suite for this closure. No claim is made that the deferred Gate-orchestration findings are fixed in this task.

### Closure status

Core reviewer-output infrastructure objective: **MET**.

Deferred Gate semantic/orchestration work: **TRACKED IN `gate-immutable-review-baseline-contract`**.

Full product suite: **NOT RUN by explicit user decision**.

Task closure: **COMPLETED WITH EXPLICIT DEFERRALS**.
