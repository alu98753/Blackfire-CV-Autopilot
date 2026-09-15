# opencode-structured-review-provider-compatibility

Status: Final

## Goal

Identify and prove at least one `OpenCode version + provider + model` combination that can satisfy the machine-readable structured-review lifecycle required by the blocked `gate-reviewer-output-contract-reliability` task:

```text
read/search tool call
    -> successful tool result
    -> voluntary final assistant turn
    -> valid JSON-Schema structured result
```

This is a compatibility / capability-evidence task. It determines where this lifecycle is actually supported. It must not weaken Blackfire's Gate contract merely to accommodate a provider/model limitation.

## Current baseline

Base branch: `main` after `opencode-launcher-version-compatibility` merged.

Production OpenCode remains explicitly pinned to CLI `1.18.31`. The launcher/version prerequisite is closed:

- Scout/Gate use parser-valid 1.18.31 invocation construction;
- process isolation belongs to the PowerShell wrappers rather than an OpenCode run flag;
- version mismatch fails before normal model routing;
- current text-verdict Gate can execute/finalize with Big Pickle;
- canonical Scout can execute with MiMo.

Those are normal-runtime facts only. They are not proof of the target JSON-Schema structured-review lifecycle.

## Final structured-output mechanism

The compatibility target is the official OpenCode SDK JSON-Schema structured-output path used by the predecessor design, not CLI `opencode run --format json` JSONL text extraction.

The essential qualification mechanism is:

```text
official version-matched OpenCode SDK/runtime
    -> session.create(...)
    -> session.prompt(..., format = { type: "json_schema", schema: OUTCOME_SCHEMA, ... })
    -> reviewer read/search tool interaction
    -> successful tool result
    -> voluntary reviewer finalization
    -> official machine structured-result field
    -> fixed JSON-Schema validation / semantic checks
```

`opencode run --format json` remains a raw event-stream mechanism and MUST NOT be treated as equivalent to JSON-Schema structured output.

The fixed reviewer outcome schema remains:

```json
{
  "verdict": "PASS",
  "blocking_findings": 0,
  "report_markdown": "# Spec Review\n..."
}
```

Required shape/semantic rules:

- `verdict` is exactly `PASS` or `BLOCK`;
- `blocking_findings` is a non-negative integer;
- `report_markdown` is a string;
- no verdict is reconstructed from Markdown/prose;
- `PASS -> blocking_findings == 0`;
- `BLOCK -> blocking_findings >= 1`.

### Version-native official result normalization

The task is qualifying the OpenCode structured-output capability across versions, and upstream machine-field naming is not stable across every candidate runtime. The probe MAY normalize only a version-native **official SDK/server machine structured-result field** into the task's canonical evidence value before applying the unchanged schema and semantic checks.

Known allowed mappings for this investigation are:

- current 1.18.x path already exercised by this task/predecessor contract: `response.data.info.structured_output`;
- evidence-selected 1.14.41 source contract: assistant `info.structured`.

This is transport-version normalization only. It does not weaken the structured-output requirement.

The following remain forbidden as result sources:

- free-form assistant prose or Markdown;
- JSON code fences or embedded JSON text;
- regex verdict extraction;
- earlier/stale messages used to salvage a failed authoritative attempt;
- synthetic diagnostic-agent success presented as production qualification.

If a future alternate runtime exposes neither a verified official structured machine field nor an equivalent official SDK result documented in that runtime, it cannot be qualified by inventing a fallback parser.

## Qualification surface

The primary live capability probe MUST use an actual production reviewer agent contract rather than a simplified synthetic agent, because the capability being qualified is the real Gate lifecycle under production read-only reviewer permissions and step/finalization behavior.

`spec-reviewer` is the first qualification role. Before recommending a candidate as the future Gate reviewer route, the exact same `OpenCode version + provider + model` combination MUST also succeed with `regression-reviewer`.

A dedicated minimal probe agent may be used only as a diagnostic aid. Success on that agent is not `PASS_PROVEN`.

## Capability classification contract

A candidate is `PASS_PROVEN` only when one bounded live probe using an actual production reviewer agent demonstrates all of:

```text
1. reviewer performs at least one required read/search tool call
2. the tool result is successfully returned to the reviewer
3. reviewer voluntarily leaves the tool-calling loop before forced max-step finalization
4. reviewer emits the requested machine-readable structured result
5. OpenCode exposes the verified official structured machine field for that runtime
6. normalized payload validates against the fixed reviewer JSON Schema
7. PASS/BLOCK cross-field semantics are internally consistent
```

The following are NOT `PASS_PROVEN`:

- ordinary prose/Markdown final output;
- current text-Gate `VERDICT: PASS` success;
- `finish = tool-calls` with no valid final structured result;
- forced max-step finalization;
- provider `tool_choice` rejection;
- transport/fetch failure;
- lifecycle evidence that cannot be audited reliably;
- missing or malformed structured result;
- schema-invalid or semantically contradictory structured result;
- a schema-valid payload produced without the required read/search lifecycle;
- success only on a simplified diagnostic agent;
- metadata/provider documentation without bounded live proof.

Failure classes must remain mechanically distinguishable. Existing classes include `FAIL_FINALIZATION`, `FAIL_TOOL_CHOICE`, `FAIL_TOOL_RESULT`, `FAIL_TRANSPORT`, `FAIL_LIFECYCLE_AUDIT`, `FAIL_SCHEMA`, `FAIL_MISSING_STRUCTURED_OUTPUT`, and concrete infrastructure failures.

## Phase 1 — production-pinned 1.18.31 — completed

The task freshly re-probed the required Phase 1 candidates after launcher/local-state repair:

1. `opencode/big-pickle`
2. `opencode/mimo-v2.5-free`

Post-audit-fix authoritative results:

- Big Pickle / `spec-reviewer`: prompt-response lifecycle evidence available; no permitted read/search lifecycle; forced `finish = tool-calls`; no structured result. Not `PASS_PROVEN`.
- MiMo / `spec-reviewer`: session-message lifecycle retrieval failed with the upstream-style `Expected OutputFormatJsonSchema, got {"type":"json_schema", ...}` response-shape error. Correctly fail-closed as `FAIL_LIFECYCLE_AUDIT`; no claim is made that the model chose no tool. Not `PASS_PROVEN`.

Therefore Phase 1 is complete with:

```text
OpenCode 1.18.31: PASS_PROVEN = 0
```

No `regression-reviewer` attempt was required because no Phase 1 candidate passed the first role.

Fresh evidence remains tracked in `EVIDENCE.md`, `MODEL_CAPABILITY_MATRIX.md`, and bounded per-attempt records.

## Phase 2 research amendment — 2026-09-16

Deep upstream research materially changed the version-selection hypothesis. The original Final SPEC spoke only about a newer-version probe. That restriction is superseded by this evidence amendment: **Phase 2 may test one evidence-selected alternate OpenCode version, older or newer, in reversible isolation.**

The detailed upstream evidence and selection rationale are tracked in:

`docs/tasks/opencode-structured-review-provider-compatibility/PHASE2_RESEARCH.md`

Key findings:

1. upstream OpenCode issue #26929 reports the same `Expected OutputFormatJsonSchema` read-back failure on 1.14.48 and identifies it as a regression; a reproducer states `1.14.41` was the last working version in their environment;
2. related upstream evidence shows the persisted output-format encoding defect survived through later 1.x releases, including 1.18.x;
3. upstream PR #37541 contains a direct fix (`Schema.Class` -> `Schema.Struct`) but remains unmerged, so a blind upgrade has no evidence advantage for this exact defect;
4. tagged 1.14.41 source already contains the structured-output tool/schema lifecycle and an official assistant machine field `structured`;
5. newer/current development paths still have separate forced-`tool_choice` compatibility defects, so newest-version preference is not a valid qualification strategy.

### Selected first alternate runtime

Phase 2 candidate #1 is exactly:

```text
OpenCode CLI:          1.14.41
@opencode-ai/sdk:      1.14.41
candidate order:       opencode/big-pickle, then opencode/mimo-v2.5-free
first role:            spec-reviewer
second role:           regression-reviewer only after the exact combination passes spec-reviewer
```

This is an evidence-driven downgrade probe, not a production downgrade decision.

### Required Phase 2 isolation

The 1.14.41 probe MUST NOT modify production OpenCode installation, global package state, repository production pin, or user OpenCode data.

Required isolation boundary:

1. create/use an ignored `.runtime/` task directory or OS temporary directory;
2. install exact `opencode-ai@1.14.41` and `@opencode-ai/sdk@1.14.41` only into that runtime;
3. prepend only that runtime's `node_modules/.bin` to the child environment `PATH`, so the version-matched SDK launches the version-matched CLI;
4. record and verify both CLI and SDK versions before each live attempt;
5. use `OPENCODE_DB=:memory:` where supported; if the older runtime cannot safely use memory DB, stop and establish an equally isolated task-local state before continuing;
6. disable automatic runtime upgrade through configuration supported by the selected version;
7. keep the SDK/session repository directory pointed at the actual task worktree so `.opencode/agents/spec-reviewer.md` / `regression-reviewer.md` remain the production contracts under test;
8. attempts remain bounded and non-interactive;
9. caller environment is restored after each probe;
10. temporary runtime dependencies are never committed.

Production `scripts/opencode_contract.ps1` remains authoritative at `1.18.31` for normal Scout/Gate execution. Do not modify or bypass it for production workflow commands.

### Phase 2 execution order and stop conditions

Run only after deterministic tests for the alternate-runtime seam pass.

Then:

1. one bounded `1.14.41 + opencode/big-pickle + spec-reviewer` attempt;
2. if not `PASS_PROVEN`, one bounded `1.14.41 + opencode/mimo-v2.5-free + spec-reviewer` attempt;
3. if either is `PASS_PROVEN`, immediately test the exact same version/provider/model with `regression-reviewer`;
4. only if the same combination passes both roles may it become the recommended future Gate route;
5. if both first-role candidates fail, STOP and return evidence to ChatGPT/user before selecting another runtime.

Do not begin a broad version sweep. Do not automatically test 2.x/dev builds. Do not build the unmerged upstream PR unless ChatGPT + user explicitly select that as a later diagnostic step.

## Phase 3 — recommendation, not silent production migration

If an alternate version obtains a candidate that passes both production reviewer roles, record outcome `(b) viable only on an isolated alternate version` and recommend a separate follow-up task for production launcher/bootstrap/pin migration and regression evidence.

That follow-up may be an upgrade or downgrade. This compatibility task itself MUST NOT change the production `1.18.31` pin.

If no authorized evaluated combination succeeds, record outcome `(c) no authorized viable route proven` and identify the next external dependency/runtime/provider to test. Do not weaken Gate semantics.

## Scope

In scope:

- preserve fresh Scout and Phase 1 evidence;
- maintain the bounded official-SDK compatibility probe;
- deterministic coverage of schema, semantics, lifecycle audit, redaction, and alternate-runtime/state seams;
- execute the selected isolated 1.14.41 runtime probe under the exact production reviewer contract;
- normalize only verified version-native official machine structured-result fields;
- classify attempts by reproducible evidence;
- update bounded compatibility evidence/matrix;
- recommend only a route live-proven with both production reviewer roles.

Allowed change surfaces:

- `docs/tasks/opencode-structured-review-provider-compatibility/`
- `scripts/opencode_structured_review_probe.mjs` and minimal related helper code
- `tests/workflow_scripts/` and the existing focused Python wrapper
- `.opencode/` only if a diagnostic config is genuinely required; production reviewer semantics must remain unchanged
- package metadata only where necessary for the repository's existing 1.18.31 probe tooling; alternate 1.14.41 dependency contents belong in ignored temporary runtime state, not a production pin change
- `docs/architecture/ai_development_workflow.md` only if a durable compatibility-qualification rule must be documented

The predecessor branch's structured-review adapter remains reference evidence only; do not silently merge the blocked predecessor implementation into production.

## Known invariants

1. Machine verdict authority comes from validated structured fields, not free-form prose.
2. No Markdown/prose verdict fallback may be introduced.
3. A valid semantic PASS/BLOCK remains terminal; normal reviewer fallback remains infrastructure-only.
4. Reviewers remain independent and read-only.
5. Provider credentials remain local and MUST NOT be committed.
6. Paid/API-cost probes require explicit user authorization before execution.
7. Metadata/documentation is only a prefilter; `PASS_PROVEN` requires the bounded live complete lifecycle.
8. Current text-verdict Gate success is not structured-output proof.
9. Historical attempt classifications remain distinct from fresh attempts; never overwrite prior evidence.
10. No production/game behavior changes are in scope.
11. Do not change production OpenCode pin inside this task.
12. Do not merge or resume the blocked `gate-reviewer-output-contract-reliability` implementation until this task establishes a viable reviewer capability route and the predecessor later obtains its own fresh Gate evidence.
13. CLI JSONL output is not a substitute for SDK JSON-Schema structured output.
14. Diagnostic-agent success cannot qualify a production route.
15. Version/state probing must be reversible and must not destroy/mutate production user state.
16. Missing lifecycle evidence fails closed; it must never be reclassified as model no-tool behavior merely because an audit endpoint failed.
17. Alternate-runtime compatibility must use a version-matched CLI and SDK unless concrete upstream evidence explicitly justifies a cross-version pair.

## Non-goals

- fixing OpenCode upstream bugs in this repository;
- changing normal Gate reviewer routing;
- changing reviewer timeout or step budgets as a workaround;
- weakening structured-output schema/semantic requirements;
- restoring free-form verdict parsing;
- silently authenticating providers or spending paid API budget;
- silently upgrading or downgrading production OpenCode;
- broad provider/version benchmarking;
- broad workflow refactoring;
- modifying production/game automation behavior;
- merging/closing the blocked predecessor task inside this task.

## Required evidence and verification

Each fresh live attempt MUST record enough bounded evidence to answer:

- OpenCode CLI version;
- SDK version;
- runtime isolation method;
- provider/model;
- reviewer role;
- lifecycle-audit source;
- whether required read/search tool call occurred;
- whether a successful tool result returned;
- whether finalization was voluntary or forced;
- finish reason when available;
- exact official structured machine field used (`structured_output`, `structured`, or another future explicitly verified field);
- whether structured result existed;
- schema validation result;
- semantic validation result;
- final classification;
- bounded/redacted diagnostic on failure.

Probe tooling MUST retain deterministic offline coverage for:

- argument/config construction;
- fixed schema validation;
- PASS/BLOCK cross-field validation;
- successful lifecycle audit;
- lifecycle retrieval failure/malformed response fail-closed behavior;
- missing/malformed structured-result classification;
- bounded credential redaction;
- production-vs-alternate runtime selection;
- version-matched CLI/SDK verification;
- environment/PATH/state restoration.

Live provider/model calls are evidence runs, not deterministic unit tests.

## Acceptance criteria

1. Fresh canonical Scout evidence exists after launcher/version repair.
2. The task uses one reproducible bounded official-SDK JSON-Schema probe with actual production reviewer agents.
3. Phase 1 on 1.18.31 Big Pickle and MiMo is preserved as `PASS_PROVEN = 0` with post-audit-fix evidence.
4. Phase 2 first probes the evidence-selected isolated `1.14.41` CLI + SDK pair rather than performing an uncontrolled version sweep.
5. At least one authorized evaluated combination becomes `PASS_PROVEN`, OR tracked evidence demonstrates no viable route for the evaluated set and identifies the next concrete dependency/runtime/provider.
6. A future Gate route is recommended only after the same exact candidate combination passes both `spec-reviewer` and `regression-reviewer` under the complete lifecycle.
7. Version-native official structured-result normalization never uses prose/Markdown/regex or stale-message fallback and still validates the unchanged fixed schema.
8. Compatibility evidence distinguishes provider/model capability failure from lifecycle-audit/runtime/version/local-state infrastructure failure.
9. No paid probe is executed without explicit user approval.
10. No secrets, credentials, temporary runtimes, or unnecessarily large provider payloads are committed.
11. Focused deterministic checks for the probe tooling pass.
12. Final evidence records exactly one outcome category: `(a) viable on 1.18.31`, `(b) viable only on an isolated alternate version`, or `(c) no authorized viable route proven`.
13. Production OpenCode remains pinned to `1.18.31` throughout this task.

## Workflow state

This SPEC remains `Status: Final` after the Phase 2 evidence amendment.

Phase 1 is complete with `PASS_PROVEN = 0`.

The next task-local action is:

1. synchronize this amended Final SPEC and `PHASE2_RESEARCH.md` into the dedicated worktree;
2. have the sole implementation writer add only the minimal alternate-runtime isolation/version-native-result normalization seam plus deterministic coverage;
3. execute the bounded 1.14.41 Phase 2 probe in the order and stop conditions above;
4. commit/push bounded evidence;
5. return to ChatGPT for semantic review before any additional runtime candidate or production migration decision.
