# gate-reviewer-output-contract-reliability

Status: Final

Resumption base: `main@f2e6503e88161d01fbd73dc4a60e5da7d98167b4`
Historical task branch: `task-gate-reviewer-output-contract-reliability@54b727319eb8088a86086f02b4be4a55aa2167d2`
Resumption review: [`RESUMPTION_REVIEW.md`](RESUMPTION_REVIEW.md)
Fresh Scout: [`CONTEXT.md`](CONTEXT.md)

## Goal

Make Gate reviewer outcomes machine-reliable on the verified OpenCode `1.18.31` + `@opencode-ai/sdk` `1.18.31` v2 route, while keeping distinct responsibility layers for repository grounding, lifecycle authority, structured transport, schema validity, semantic consistency, rendering, artifact promotion, and fallback policy.

The production authority path is:

```text
one-shot isolated reviewer session
        ↓
typed same-session event evidence for grounding
        ↓
final prompt response with completed StructuredOutput
        ↓
promptResult.data.info.structured
        ↓
fixed schema validation
        ↓
PASS/BLOCK cross-field semantic validation
        ↓
deterministic review/EVIDENCE rendering
        ↓
transactional canonical artifact promotion
```

Human-readable Markdown is presentation evidence. It is never the machine verdict transport.

## Verified baseline

The completed `opencode-structured-review-provider-compatibility` task established:

- OpenCode is pinned to `1.18.31`.
- `@opencode-ai/sdk` is pinned to `1.18.31`.
- The supported structured route is the official SDK v2 `session.prompt(... format: { type: "json_schema" })` path.
- The authoritative structured machine field is `promptResult.data.info.structured`.
- `StructuredOutput` is an OpenCode tool and a successful call appears as a typed `ToolPart` with `state.status == "completed"`.
- `finish == "tool-calls"` is not evidence of failure or max-step exhaustion by itself.
- `client.session.messages` is affected by the `OutputFormatJsonSchema` decoder defect and must not be a production dependency for this task.
- Big Pickle has proven structured transport but has also demonstrated a grounding-compliance failure by producing a valid structured review without repository `read` / `glob` / `grep`.
- MiMo has demonstrated a separate model-compliance failure by voluntarily ending a complex review without producing StructuredOutput.

Fresh pinned-source verification additionally established an important scope fact:

- `session.prompt()` ultimately returns the last assistant message from the one-shot session.
- OpenCode creates a new assistant message for successive model/tool steps.
- Therefore the final `promptResult.data.parts` is sufficient to prove facts about the final StructuredOutput message, but is not by itself sufficient to prove repository grounding that may have occurred in earlier assistant messages.
- SDK v2 exposes an official typed event subscription and typed `message.part.updated` events containing `sessionID` and `Part`. A production adapter can therefore observe the complete one-shot session lifecycle without relying on the broken `session.messages` decoder route.

## Final responsibility model

### 1. Evidence acquisition / grounding

The invariant is that a reviewer verdict must be grounded in repository evidence tied to the current candidate/task state.

For this task, the current machine-verifiable grounding proxy remains:

- at least one **model-initiated** permitted repository `read`, `glob`, or `grep` tool call;
- that tool call must reach `state.status == "completed"`;
- it must occur in the same isolated reviewer session before the accepted `StructuredOutput` finalization.

The reviewer prompts continue to require the supplied task descriptor, canonical SPEC, status snapshot, diff snapshot, and relevant repository files to be inspected. Gate does not attempt to prove semantic coverage completeness from tool count alone; the completed read/search requirement is a minimum anti-ungrounded-review proof.

This exact gesture is not a permanent architecture law. A future provenance-bearing deterministic Context Pack may replace or strengthen it only in `reviewer-bounded-context-infrastructure`, after that task proves an equivalent or stronger grounding contract. This task must not pre-implement that downstream design.

### 2. Lifecycle authority

Production lifecycle evidence must refer to the exact current one-shot reviewer session.

The Node adapter must:

- create a fresh isolated OpenCode session for one reviewer attempt;
- establish the official typed SDK-v2 event subscription before starting the review prompt;
- collect only lifecycle events belonging to that fresh session;
- preserve enough typed part data to prove completed grounding tools and final StructuredOutput settlement;
- bind the final prompt response to the same session and final assistant message;
- fail closed if event capture, identity consistency, or cleanup is not trustworthy.

Because the session is fresh and one-shot, prior stale review messages must not participate in verdict authority.

`client.session.messages` is not required and must not be used as a production fallback audit source in this task.

### 3. Semantic reviewer judgment

The reviewer/model alone owns the semantic decision `PASS` or `BLOCK` and the supporting `report_markdown`.

Infrastructure must not reinterpret prose to obtain a different verdict.

### 4. Structured result transport

The only authoritative model-result transport is the verified SDK-v2 JSON-Schema path:

```text
format.type = json_schema
        ↓
StructuredOutput tool
        ↓
completed ToolPart
        ↓
promptResult.data.info.structured
```

The accepted final assistant message must expose:

- a completed `StructuredOutput` ToolPart;
- a non-null `info.structured` machine object;
- internally consistent session/message identity.

No separate trailing assistant text turn is required.

No Markdown/JSON-code-fence/XML/free-text fallback protocol is allowed.

### 5. Schema validation

The fixed structured outcome remains:

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

OpenCode StructuredOutput is the primary schema-enforcement mechanism. The production boundary must nevertheless fail closed if the adapter envelope or returned object violates the fixed contract.

### 6. Cross-field semantic validation

Gate owns deterministic cross-field consistency:

- `PASS` requires `blocking_findings == 0`;
- `BLOCK` requires `blocking_findings >= 1`.

A contradiction is not a semantic verdict.

### 7. Human-readable rendering

Canonical `reviews/spec-review.md` and `reviews/regression-review.md` are deterministic renderings of an accepted machine result.

The renderer uses validated machine fields for verdict authority and reviewer `report_markdown` only for human-readable analysis.

Verdict-like strings inside `report_markdown` have zero machine authority.

A canonical review may use evidence-first prose with a deterministic Gate-generated verdict block appended at the end.

### 8. Artifact promotion / rollback

A trusted `PASS` and a trusted `BLOCK` are both canonical reviewer outcomes and are eligible for normal review/EVIDENCE promotion.

Any attempt that fails before trusted verdict authority must not overwrite existing canonical `reviews/*` or `EVIDENCE.md`.

Promotion remains transactional. Any promotion failure must roll back to the pre-Gate canonical state.

### 9. Attempt classification

Failure categories must preserve the layer that failed. Do not label every pre-verdict failure as infrastructure merely to simplify routing.

Required machine-distinguishable attempt categories are equivalent to:

- `GROUNDING_FAILED`
- `LIFECYCLE_UNTRUSTWORTHY`
- `STRUCTURED_TRANSPORT_FAILED`
- `STRUCTURED_OUTPUT_MISSING`
- `SCHEMA_INVALID`
- `SEMANTIC_CONTRADICTION`
- `INFRASTRUCTURE_FAILED`
- `VALID_PASS`
- `VALID_BLOCK`

Names may vary in implementation, but the distinctions may not be collapsed.

Examples:

- authoritative session evidence + no completed repository read/search -> `GROUNDING_FAILED`;
- event subscription/audit cannot prove the same-session lifecycle -> `LIFECYCLE_UNTRUSTWORTHY`;
- prompt/SDK/server transport fails -> `STRUCTURED_TRANSPORT_FAILED` or `INFRASTRUCTURE_FAILED` according to the actual failed layer;
- prompt completes but no accepted StructuredOutput machine result exists -> `STRUCTURED_OUTPUT_MISSING`;
- object shape/type invalid -> `SCHEMA_INVALID`;
- `PASS + blocking_findings > 0` -> `SEMANTIC_CONTRADICTION`.

### 10. Model fallback / review-shopping prevention

A trusted `VALID_PASS` or `VALID_BLOCK` is strictly terminal for that reviewer role. No later model may be invoked after either result.

Fallback is allowed only before verdict authority exists. The bounded configured candidate chain may continue after:

- `GROUNDING_FAILED`;
- `LIFECYCLE_UNTRUSTWORTHY`, when process/session teardown is proven safe;
- `STRUCTURED_TRANSPORT_FAILED`, when teardown is proven safe;
- `STRUCTURED_OUTPUT_MISSING`;
- `SCHEMA_INVALID`;
- `SEMANTIC_CONTRADICTION`;
- other mechanically proven attempt/infrastructure failures whose termination/cleanup is confirmed.

This is not review-shopping because no trusted semantic PASS/BLOCK exists yet.

An unconfirmed timeout/termination or unsafe cleanup is terminal for the chain; do not launch another reviewer candidate.

### 11. Gate final-state semantics

Attempt classification and Gate final state are separate concepts.

Gate exposes exactly these top-level semantic outcomes:

- `PASSED`: both reviewer roles reached trusted PASS outcomes and focused tests passed;
- `CANDIDATE_BLOCKED`: at least one trusted reviewer BLOCK or focused-test failure blocks the candidate;
- `VERIFICATION_UNAVAILABLE`: Gate could not obtain the trusted reviewer/test authority needed to decide PASS/BLOCK safely.

`VERIFICATION_UNAVAILABLE` is **not** synonymous with infrastructure failure. It is the aggregate Gate state used when verification authority is unavailable after bounded routing. Its evidence must preserve the exact root attempt classifications that caused exhaustion or termination.

Examples that may end as `VERIFICATION_UNAVAILABLE`:

- all configured reviewer candidates end in `GROUNDING_FAILED`;
- one candidate ends in `STRUCTURED_OUTPUT_MISSING` and the next in `SCHEMA_INVALID`;
- an SDK/transport/infrastructure failure prevents any trusted verdict;
- lifecycle authority cannot be proven;
- cleanup becomes unsafe and further fallback must stop.

The external exit-code contract remains unchanged for compatibility:

```text
0 = PASSED
2 = CANDIDATE_BLOCKED
1 = VERIFICATION_UNAVAILABLE
```

The implementation must not emit `INFRASTRUCTURE_BLOCKED` as the top-level Gate state merely because no trusted reviewer verdict was obtained. `INFRASTRUCTURE_FAILED` remains an attempt/root-cause classification only when infrastructure actually failed.

If every configured candidate for a reviewer role is exhausted before verdict authority, Gate returns `VERIFICATION_UNAVAILABLE` / exit code `1` and preserves canonical artifacts.

Existing outer degraded-review handling may still be invoked after exit `1`, but degraded Gemini evidence remains non-independent and has no Gate PASS authority.

## Final completion / max-step semantics

The historical `voluntary final assistant turn` invariant is removed.

The correct structured-output completion invariant is:

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

- `finish == "tool-calls"` is valid and must not be rejected by itself.
- `finish == "stop"` does not make a missing StructuredOutput valid.
- configured step count remains a safety ceiling, not a coverage quota.
- no standalone `finalization_voluntary` boolean is required for verdict authority.
- no dedicated typed max-step-exhausted field exists in the verified message/part contract used here; do not recreate the old finish-string heuristic.
- a completed valid StructuredOutput is accepted even if it occurs on the configured final model step, provided all grounding/lifecycle/transport/schema/semantic invariants pass.
- a system-forced or model-finished path that does not produce an accepted StructuredOutput remains non-authoritative and is already rejected by the structured-result contract.

Step-count / finish metadata may be recorded diagnostically, but it must not override an otherwise valid StructuredOutput verdict or manufacture verdict authority when StructuredOutput is absent.

## Node adapter boundary

Introduce one small production adapter:

```text
scripts/opencode_structured_review.mjs
```

It is infrastructure integration, not a reviewer and not a policy engine.

It owns mechanical SDK facts:

1. official `@opencode-ai/sdk/v2` request construction;
2. fresh one-shot session creation;
3. typed event subscription and bounded same-session event collection;
4. prompt execution with the fixed JSON schema;
5. final prompt-response identity checks;
6. extraction of `info.structured` and final StructuredOutput ToolPart facts;
7. bounded extraction of completed `read` / `glob` / `grep` lifecycle evidence;
8. process/server/session teardown and cleanup trust;
9. bounded deterministic JSON envelope returned to Gate;
10. bounded/redacted diagnostics.

The adapter must not:

- select fallback models;
- decide whether a semantic PASS is preferable to BLOCK;
- parse `report_markdown` for verdict authority;
- promote canonical artifacts;
- query old/stale messages to salvage a failed attempt;
- depend on the diagnostic compatibility matrix at runtime.

Compatibility-probe pure helpers/constants may be factored into a small production-safe shared module if that reduces duplication, but production code must not import diagnostic matrix execution/routing logic from `opencode_structured_review_probe.mjs`.

## Gate boundary

`scripts/ai_gate.ps1` remains the orchestration/policy authority. It owns:

- candidate order and bounded fallback;
- failure classification from adapter facts;
- current grounding policy;
- schema fail-closed checks at the process boundary;
- cross-field semantic validation;
- trusted PASS/BLOCK terminality;
- focused-test orchestration;
- deterministic Markdown/EVIDENCE rendering;
- Gate final-state mapping and existing external exit-code compatibility;
- transactional promotion/rollback.

Production Gate must invoke the structured-review adapter. It must not directly use `opencode run --format json` as its reviewer-verdict transport after this task.

The production invocation boundary should therefore become conceptually:

```text
ai_gate.ps1
    ↓
node scripts/opencode_structured_review.mjs <role/model/task/attempt inputs>
    ↓
bounded deterministic adapter envelope
```

Gate should know reviewer role/model/task/policy facts; it should not own OpenCode SDK session/event/StructuredOutput protocol details.

## Required removals

The following old abstractions are obsolete and must be removed from the authoritative production Gate path, not preserved as compatibility verdict fallbacks:

1. `Get-FinalAssistantMessageFromStructuredJson()` as reviewer-verdict extraction;
2. `Get-CanonicalReviewPayload()` and all scanning/salvage of `VERDICT:` headers from prose;
3. the regex/header-based form of `Test-ReviewVerdictStructure()`;
4. direct production reviewer invocation through `opencode run --format json`;
5. the reviewer prompt contract requiring free text to begin with `VERDICT:` / `BLOCKING_FINDINGS:`;
6. the separate `voluntary final assistant text turn` requirement;
7. any heuristic equating `finish == "tool-calls"` with max-step failure;
8. any top-level rule equivalent to "all reviewer candidate failures are infrastructure failures".

The semantic invariants formerly embedded inside old text parsing must survive in structured form. In particular, removing `Test-ReviewVerdictStructure()` does **not** remove `PASS -> blocking_findings == 0` or `BLOCK -> blocking_findings >= 1`; those move to structured machine validation.

No free-text compatibility path may retain PASS/BLOCK authority after migration.

## Required preservation

The task is a contract/transport cleanup, not a rewrite of the mature Gate orchestration machinery. Preserve existing behavior and implementation where compatible with the Final contract, especially:

- bounded child-process execution;
- timeout handling;
- kill/termination confirmation;
- non-interactive stdin behavior;
- candidate ordering and bounded fallback machinery;
- git status/diff snapshot generation;
- focused-test orchestration and full-suite rejection policy;
- valid BLOCK terminality;
- candidate staging before canonical promotion;
- canonical backup;
- transactional promotion;
- rollback on promotion failure;
- task-namespaced runtime diagnostics;
- the external `0 / 1 / 2` exit-code contract;
- `EVIDENCE.md` as the canonical human-readable verification summary.

Do not opportunistically redesign these areas unless the structured adapter contract makes a narrowly necessary change unavoidable.

## Required additions / replacements

Add only the minimum new machinery required by the Final contract:

- one small SDK-v2 structured reviewer adapter;
- typed event-stream lifecycle collection for the fresh one-shot reviewer session;
- a bounded deterministic adapter envelope;
- structured object/schema validation at the Gate boundary;
- explicit attempt classifications;
- an explicit current grounding-policy abstraction whose present implementation is completed same-session model-initiated `read` / `glob` / `grep`;
- deterministic rendering from accepted structured machine fields;
- top-level `VERIFICATION_UNAVAILABLE` state distinct from root `INFRASTRUCTURE_FAILED` attempt classification.

The grounding abstraction must make it possible for a later task to replace `MODEL_REPO_TOOLS` with an equivalent proven provenance mechanism such as a verified Context Pack without rewriting unrelated Gate orchestration.

## Reviewer-agent contract changes

`.opencode/agents/spec-reviewer.md` and `.opencode/agents/regression-reviewer.md` must be updated to match SDK-v2 structured finalization.

Required changes:

- preserve read-only permissions and existing role boundaries;
- preserve step ceilings (`8` and `10`);
- preserve early-stop / bounded-blocker behavior;
- explicitly require repository grounding before finalization;
- require all needed research/tool use before StructuredOutput;
- remove the obsolete requirement that the final free-text response begin with `VERDICT:` / `BLOCKING_FINDINGS:`;
- keep the human report structure concise and evidence-based inside `report_markdown`;
- do not require a separate trailing assistant text turn after StructuredOutput.

## Canonical artifacts

### `reviews/spec-review.md` / `reviews/regression-review.md`

Contain:

- reviewer `report_markdown` rendered as human-readable Markdown;
- deterministic verdict block generated from accepted machine fields.

They must not contain raw lifecycle dumps as normal content.

### `EVIDENCE.md`

Remains status-first and records at least:

- Gate final state: `PASSED`, `CANDIDATE_BLOCKED`, or `VERIFICATION_UNAVAILABLE`;
- task, branch, HEAD, base ref;
- accepted reviewer role/model/attempt index when a trusted verdict exists;
- final verdict and blocking count from accepted machine fields when applicable;
- accepted grounding/lifecycle/transport/schema/semantic status;
- compact fallback provenance for prior failed attempts;
- exact root attempt classification(s) when final state is `VERIFICATION_UNAVAILABLE`;
- focused-test results;
- pointers to detailed review files.

`EVIDENCE.md` must not describe a pure grounding/model-compliance exhaustion as `INFRASTRUCTURE_BLOCKED`.

### `.runtime/ai_gate/<task>/`

Holds failed-attempt raw output and detailed bounded diagnostics. These remain ephemeral/git-ignored unless a later explicit contract promotes a bounded diagnostic artifact.

## Scope

Primary implementation surface:

- `scripts/ai_gate.ps1`
- `scripts/opencode_structured_review.mjs` (new)
- `.opencode/agents/spec-reviewer.md`
- `.opencode/agents/regression-reviewer.md`
- `tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1`
- structured adapter fixtures/helpers under `tests/workflow_scripts/` as needed
- `tests/test_workflow_scripts.py` (new focused unittest wrapper for the deterministic workflow harness)
- `scripts/opencode_structured_review_probe.mjs` and its deterministic tests only if a small pure helper extraction is needed
- `docs/architecture/ai_development_workflow.md`
- `docs/tasks/gate-reviewer-output-contract-reliability/`

The already-pinned SDK dependency in `package.json` is the baseline; dependency/version churn is not part of this task.

## Non-goals

- changing OpenCode away from `1.18.31`;
- reopening provider/version compatibility exploration;
- implementing `reviewer-bounded-context-infrastructure` or a Context Pack;
- eliminating reviewer read/search capability;
- weakening grounding because a model can emit plausible structured prose;
- adding a long-lived shared OpenCode server/global mutable session;
- restoring a separate final assistant text-turn requirement;
- treating `finish: tool-calls` as max-step exhaustion;
- parsing verdict authority from Markdown, JSON fences, XML, regex, or older messages;
- changing Scout behavior;
- changing game/runtime behavior;
- changing reviewer step budgets or review timeout values;
- running the repository full suite by default;
- redesigning stable timeout/test/promotion/rollback machinery unrelated to the structured-review contract.

## Forbidden shortcuts

Implementation MUST NOT:

1. recover PASS/BLOCK from `report_markdown` or raw assistant text;
2. use `client.session.messages` as a production audit fallback for this route;
3. accept final prompt-response parts as proof of earlier grounding without same-session event evidence;
4. classify missing read/search as lifecycle-source untrustworthiness when the lifecycle itself is authoritative;
5. infer forced finalization solely from `finish` strings;
6. convert grounding/schema/semantic failures into `INFRASTRUCTURE_FAILED` merely to enable fallback;
7. invoke another model after a trusted PASS or BLOCK;
8. promote canonical artifacts from an attempt that never reached verdict authority;
9. silently install/change OpenCode or SDK versions during Gate execution;
10. couple production Gate execution to compatibility-matrix candidate logic;
11. retain a hidden free-text/regex verdict fallback after the structured migration;
12. emit top-level `INFRASTRUCTURE_BLOCKED` for candidate exhaustion whose true root cause is grounding/model-compliance/schema/semantic failure;
13. duplicate OpenCode session/event protocol logic inside `ai_gate.ps1` instead of keeping it behind the adapter boundary.

## Required deterministic verification

Existing `tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1` is the current Gate workflow harness and must be evolved rather than replaced by an unrelated parallel harness.

Add a Python unittest wrapper at:

```text
tests/test_workflow_scripts.py
```

so the task can declare deterministic workflow coverage through `task.json`.

Focused verification must cover at least:

1. valid grounded structured PASS -> trusted PASS / `PASSED` / exit 0;
2. valid grounded structured BLOCK -> terminal BLOCK / `CANDIDATE_BLOCKED` / exit 2 with no fallback;
3. `finish == "tool-calls"` + completed StructuredOutput + valid machine fields is accepted;
4. earlier same-session completed read/search observed through event evidence satisfies the current grounding proxy even when the final prompt response contains only StructuredOutput;
5. final prompt response with StructuredOutput but no same-session completed read/search -> `GROUNDING_FAILED`;
6. event/session identity mismatch or incomplete lifecycle capture -> `LIFECYCLE_UNTRUSTWORTHY`;
7. missing StructuredOutput / missing `info.structured` -> `STRUCTURED_OUTPUT_MISSING`;
8. invalid object shape/type -> `SCHEMA_INVALID`;
9. `PASS + blocking_findings > 0` and `BLOCK + blocking_findings == 0` -> `SEMANTIC_CONTRADICTION`;
10. verdict-like text inside `report_markdown` cannot change machine outcome;
11. stale/earlier output from another message/session cannot override the accepted attempt;
12. pre-authority failure can fall back to the next configured candidate when cleanup is proven;
13. unconfirmed termination/unsafe cleanup stops fallback immediately and yields `VERIFICATION_UNAVAILABLE` / exit 1;
14. valid PASS/BLOCK never falls through to another candidate;
15. attempts without verdict authority preserve prior canonical reviews/EVIDENCE;
16. promotion failure rolls back canonical artifacts;
17. current reviewer step budgets and OpenCode `1.18.31` pin remain enforced;
18. existing structured-review probe tests continue to pass;
19. all candidates exhausted by non-infrastructure model-compliance failures yield top-level `VERIFICATION_UNAVAILABLE`, not `INFRASTRUCTURE_BLOCKED`;
20. `EVIDENCE.md` preserves the exact root classifications that led to `VERIFICATION_UNAVAILABLE`;
21. the production Gate invocation seam targets the structured adapter rather than direct `opencode run --format json` reviewer transport;
22. legacy `VERDICT:` text/regex output has zero reviewer-verdict authority.

The tests must be deterministic/offline and must not require a live provider/model.

## Focused test targets

`task.json` must declare:

```text
tests.test_opencode_structured_review_probe
tests.test_workflow_scripts
```

The full product test suite remains user-only under repository policy.

## Acceptance criteria

1. Gate obtains reviewer PASS/BLOCK authority only from the accepted structured machine object, never from free-form Markdown placement.
2. Production uses OpenCode `1.18.31` + `@opencode-ai/sdk` `1.18.31` official v2 structured transport and `info.structured`.
3. A fresh one-shot session plus typed event evidence proves earlier same-session grounding independently from final prompt-response transport.
4. Production does not depend on the broken `client.session.messages` decoder path.
5. Current grounding policy requires at least one completed same-session model-initiated `read` / `glob` / `grep` before StructuredOutput; removing/replacing this proxy is deferred to bounded-context infrastructure.
6. `finish == "tool-calls"` is not treated as failure or max-step exhaustion by itself.
7. A completed StructuredOutput with valid schema/semantics is terminal even on the configured final model step when all other authority layers pass.
8. Missing grounding, lifecycle authority, structured output, schema validity, semantic consistency, and infrastructure are machine-distinguishable attempt failure layers.
9. Trusted PASS and trusted BLOCK are both terminal; no semantic review-shopping occurs.
10. Pre-authority failures may use bounded candidate fallback only when cleanup/termination is trustworthy, while retaining their true classification.
11. Gate final state is separately classified as `PASSED`, `CANDIDATE_BLOCKED`, or `VERIFICATION_UNAVAILABLE`; candidate exhaustion is not automatically called infrastructure failure.
12. External exit-code compatibility remains `0 = PASSED`, `2 = CANDIDATE_BLOCKED`, `1 = VERIFICATION_UNAVAILABLE`.
13. Canonical reviews and `EVIDENCE.md` derive verdict state only from accepted machine fields and record compact provenance.
14. `EVIDENCE.md` records exact root attempt classifications when verification is unavailable and does not mislabel non-infrastructure exhaustion as `INFRASTRUCTURE_BLOCKED`.
15. Attempts without verdict authority preserve prior canonical artifacts.
16. Promotion/rollback and focused-test behavior remain transaction-safe.
17. Reviewer agents remain independent, read-only bounded blocker detectors with existing 8/10 step ceilings.
18. Direct production reviewer transport through `opencode run --format json` is removed in favor of the SDK-v2 adapter boundary.
19. `Get-FinalAssistantMessageFromStructuredJson`, `Get-CanonicalReviewPayload`, and regex/header-based verdict parsing no longer have production reviewer-verdict authority and should be removed with their obsolete tests/seams.
20. Stable bounded-process, timeout, focused-test, candidate-routing, staging, promotion, rollback, and exit-code behavior is preserved unless narrowly required by the new adapter contract.
21. Deterministic offline tests cover the adapter/Gate seam, failure taxonomy, top-level unavailable semantics, and removal of free-text verdict authority.
22. `reviewer-bounded-context-infrastructure` remains downstream: this task defines WHAT grounding proof is required today; the downstream task may later define HOW equivalent provenance can be supplied more efficiently.
23. No game/runtime behavior changes occur.
24. After implementation and deterministic focused tests pass, `scripts/ai_gate.ps1 -Task gate-reviewer-output-contract-reliability` must be run as the normal real Gate validation. A real trusted BLOCK remains a legitimate terminal review result requiring implementation correction; pre-authority reviewer exhaustion remains `VERIFICATION_UNAVAILABLE` and must not be relabeled PASS.

## Implementation handoff

This SPEC is Final. Gemini/Antigravity may implement the smallest coherent patch satisfying this contract.

OpenCode Scout/reviewers remain read-only. Do not implement `reviewer-bounded-context-infrastructure` inside this task.
