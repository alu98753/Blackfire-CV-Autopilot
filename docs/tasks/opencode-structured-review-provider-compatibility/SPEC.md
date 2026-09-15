# opencode-structured-review-provider-compatibility

Status: Final

## Goal

Identify and prove at least one `OpenCode version + provider + model` combination that can satisfy the machine-readable structured-review lifecycle required by the blocked `gate-reviewer-output-contract-reliability` task:

```text
read/search tool call
    -> successful tool result
    -> voluntary final assistant turn
    -> valid JSON-Schema structured_output
```

This is a compatibility / capability-evidence task. It determines where this lifecycle is actually supported. It must not weaken Blackfire's Gate contract merely to accommodate a provider/model limitation.

## Current baseline after launcher repair

Base branch: latest `main` at `6e562bad77ea0a89d494dbfe261752dfba329cf6` (`Merge task-opencode-launcher-version-compatibility`).

The launcher/version prerequisite is closed:

- production OpenCode is explicitly pinned to CLI `1.18.31`;
- Scout/Gate use parser-valid 1.18.31 invocation construction and no longer depend on `run --standalone`;
- process isolation remains owned by the PowerShell wrappers rather than an OpenCode run flag;
- version mismatch fails before normal model routing;
- a direct `opencode run --agent scout --model opencode/big-pickle` smoke test reached model execution successfully after preserving an incompatible local DB and allowing 1.18.31 to create fresh state;
- canonical Scout completed successfully with `opencode/mimo-v2.5-free` on the repaired task branch;
- the current text-verdict Gate completed successfully with `opencode/big-pickle` for both independent reviewer roles.

The last point is positive normal-reviewer runtime evidence but is **not** `PASS_PROVEN` for this task. The currently merged Gate still validates its present reviewer verdict/report contract; its successful Big Pickle run does not prove the target JSON-Schema `structured_output` lifecycle required by `gate-reviewer-output-contract-reliability`.

## Final structured-output mechanism

The compatibility target is the official OpenCode SDK JSON-Schema structured-output path used by the predecessor design, not CLI `opencode run --format json` JSONL text extraction.

The qualification probe MUST use the same essential mechanism as the predecessor adapter:

```text
official @opencode-ai/sdk
    -> session.create(...)
    -> session.prompt(..., format = { type: "json_schema", schema: OUTCOME_SCHEMA, ... })
    -> reviewer read/search tool interaction
    -> voluntary reviewer finalization
    -> response.data.info.structured_output
    -> JSON-Schema validation / semantic checks
```

`opencode run --format json` remains a raw event-stream mechanism and MUST NOT be treated as equivalent to JSON-Schema `structured_output`.

The fixed reviewer outcome schema remains:

```json
{
  "verdict": "PASS",
  "blocking_findings": 0,
  "report_markdown": "# Spec Review\n..."
}
```

Required shape rules:

- `verdict` is exactly `PASS` or `BLOCK`;
- `blocking_findings` is a non-negative integer;
- `report_markdown` is a string;
- no verdict is reconstructed from Markdown/prose;
- semantic consistency still requires `PASS -> blocking_findings == 0` and `BLOCK -> blocking_findings >= 1`.

## Qualification surface

The primary live capability probe MUST use an actual production reviewer agent contract rather than a simplified synthetic agent, because the capability being qualified is the real Gate lifecycle under production read-only reviewer permissions and step/finalization behavior.

Phase 1 should use `spec-reviewer` as the first qualification surface because it already embodies the required read/search-only interaction and bounded voluntary-finalization policy. A candidate may be called `PASS_PROVEN` once one bounded actual-reviewer probe demonstrates the complete lifecycle below.

Before recommending that candidate as the future Gate reviewer route, the same `OpenCode version + provider + model` combination MUST also be exercised successfully with `regression-reviewer`, so a route is not recommended solely from a role-specific success.

A dedicated minimal probe agent may be introduced only as a diagnostic aid to localize a failure. Success on such a diagnostic agent is not sufficient for `PASS_PROVEN` and cannot qualify a production Gate route.

## Historical compatibility evidence

The predecessor investigation previously recorded, under the then-current 1.18.31 environment:

- `opencode/big-pickle`: `FAIL_FINALIZATION` (`finish: tool-calls`, no structured output);
- `opencode/mimo-v2.5-free`: `FAIL_FINALIZATION` (`finish: tool-calls`, no structured output);
- Muse Spark 1.2/1.3 contributor free: `FAIL_TOOL_CHOICE`;
- Nemotron 3.5 Lightning free: `FAIL_TRANSPORT`;
- explicit `StructuredOutput` permission allow did not change the MiMo result in an A/B probe;
- Qwen3-Coder-Next, Kimi K2.5/K3, MiniMax M2.5, and GLM-5.3-Flash were not locally selectable in that environment and were not authorized for paid probing.

That census ended with `PASS_PROVEN = 0`.

These observations remain historical evidence only. Big Pickle and MiMo MUST be re-probed on the repaired launcher/version/local-state baseline before this task draws a fresh capability conclusion. Historical classifications must remain separately identifiable from fresh attempts.

## Capability classification contract

A candidate is `PASS_PROVEN` only when one bounded live probe using an actual production reviewer agent demonstrates the complete lifecycle:

```text
1. reviewer performs at least one required read/search tool call
2. the tool result is successfully returned to the reviewer
3. reviewer voluntarily leaves the tool-calling loop before forced max-step finalization
4. reviewer emits the requested machine-readable structured result
5. OpenCode exposes response.data.info.structured_output
6. the payload validates against the fixed reviewer JSON Schema
7. PASS/BLOCK cross-field semantics are internally consistent
```

The following are NOT `PASS_PROVEN`:

- ordinary prose/Markdown final output;
- current Gate `VERDICT: PASS` success without the target JSON-Schema lifecycle;
- `finish = tool-calls` with no structured output;
- forced max-step finalization;
- provider `tool_choice` rejection;
- transport/fetch failure;
- missing or malformed `structured_output`;
- schema-invalid or semantically contradictory structured output;
- a schema-valid payload produced without the required read/search lifecycle;
- success only on a simplified diagnostic agent;
- metadata or provider documentation claiming support without bounded live proof.

Failure classes should remain mechanically distinguishable, including at least `FAIL_FINALIZATION`, `FAIL_TOOL_CHOICE`, `FAIL_TRANSPORT`, `FAIL_SCHEMA`, `FAIL_MISSING_STRUCTURED_OUTPUT`, and concrete infrastructure/capability failures discovered during probing.

## Investigation order

### Phase 1 — Re-prove the pinned production baseline

Start with production OpenCode `1.18.31` and re-run the exact official-SDK JSON-Schema capability probe against the authorized locally available/free candidates in this order:

1. `opencode/big-pickle`
2. `opencode/mimo-v2.5-free`

The current text-Gate success makes these high-value re-tests because normal reviewer execution/finalization now works on the repaired baseline, while structured-output capability remains unproven.

Each attempt must be bounded, non-interactive, repository-directory-scoped, and must preserve enough diagnostics to distinguish provider/model capability failure from launcher/version/local-state failure without committing secrets or unnecessarily large raw payloads.

### Phase 2 — Isolated OpenCode version probes only if 1.18.31 remains `PASS_PROVEN = 0`

Only if all authorized Phase 1 candidates fail the target lifecycle may the task evaluate a newer OpenCode version.

A newer-version probe MUST be isolated from production state and MUST NOT modify the repository production pin. The preferred isolation boundary is an explicitly invoked temporary/one-shot OpenCode/SDK environment with isolated database/state (for example a temporary package/runtime context plus memory or task-local state), while preserving the same repository directory, reviewer contract, model, schema, tool-use requirement, and bounded lifecycle.

Production `scripts/opencode_contract.ps1` remains authoritative for normal Scout/Gate execution. Test-only seams such as `_OpenCodeVersionOverride` may be used only for deterministic harness coverage; they must not be misrepresented as proving a live newer-version runtime.

The exact newer version selected for Phase 2 should be the smallest justified candidate based on concrete OpenCode release/runtime evidence available at probe time. Do not perform a broad uncontrolled version sweep.

### Phase 3 — Recommendation, not silent production upgrade

If 1.18.31 obtains a candidate that passes both production reviewer roles, record outcome `(a) viable on 1.18.31` and recommend that route to the predecessor task.

If only an isolated newer version obtains a candidate that passes both reviewer roles, record outcome `(b) viable only on an isolated newer version` and recommend a separate follow-up task for production launcher/bootstrap/pin upgrade and regression evidence.

If no authorized evaluated combination succeeds, record outcome `(c) no authorized viable route proven` and identify the next external dependency such as a specific newer version or authenticated/paid provider. Do not weaken Gate semantics.

## Scope

In scope:

- preserve fresh Scout evidence from the repaired baseline;
- inspect and reuse the predecessor official-SDK JSON-Schema mechanism as the capability target;
- establish a bounded, reproducible live compatibility probe using the production reviewer agent contract;
- re-probe OpenCode 1.18.31 Big Pickle and MiMo in the required order;
- use minimal diagnostic tooling only when needed to classify a failure;
- evaluate a newer OpenCode version only after Phase 1 remains `PASS_PROVEN = 0`, and only with reversible isolated state/runtime;
- classify attempts by reproducible evidence rather than marketing/model metadata;
- produce a tracked compatibility matrix/evidence summary without credentials or unbounded raw provider responses;
- recommend only reviewer routes that are live-proven under both production reviewer roles.

Allowed change surfaces:

- `docs/tasks/opencode-structured-review-provider-compatibility/`
- `.opencode/` only if a diagnostic agent/config is genuinely required; production reviewer semantics must remain unchanged
- diagnostic/probe helpers under `scripts/` or `tests/workflow_scripts/`
- `package.json` / lockfile only if required to reproduce the official SDK probe and only without changing the production OpenCode CLI pin
- `docs/architecture/ai_development_workflow.md` only if a durable compatibility qualification rule must be documented

The predecessor branch's `scripts/opencode_structured_review.mjs` is evidence/reference for the required SDK mechanism. This task may reuse its design or introduce an equivalent task-local probe, but must not silently merge the blocked predecessor implementation into production.

## Known invariants

1. Machine verdict authority in the predecessor design comes from validated structured fields, not free-form prose.
2. No Markdown/prose verdict fallback may be introduced.
3. A valid semantic PASS/BLOCK remains terminal; normal reviewer fallback remains infrastructure-only.
4. Reviewers remain independent and read-only.
5. Provider credentials remain local and must never be committed.
6. Paid/API-cost probes require explicit user authorization before execution.
7. Metadata is only a prefilter; `PASS_PROVEN` requires the bounded live complete lifecycle.
8. Current text-verdict Gate PASS is positive reviewer-runtime evidence, not proof of target structured-output compatibility.
9. Historical Big Pickle/MiMo structured failures must be re-tested on the repaired baseline before drawing a fresh conclusion.
10. No production/game behavior changes are in scope.
11. Do not change the production OpenCode pin merely because a newer version appears promising; first prove compatibility in isolation.
12. Do not merge or continue production implementation of `gate-reviewer-output-contract-reliability` until this task establishes the required reviewer capability route and that predecessor obtains its own fresh independent Gate evidence.
13. `opencode run --format json` JSONL output is not a substitute for SDK JSON-Schema `structured_output`.
14. A diagnostic-agent success alone cannot qualify a production reviewer route.
15. Version/state probing must be reversible and must not destroy or mutate the user's production OpenCode state.

## Non-goals

- fixing OpenCode launcher compatibility again;
- treating current Gate PASS as equivalent to JSON-Schema `PASS_PROVEN`;
- weakening JSON-Schema structured-output requirements;
- restoring free-form verdict parsing;
- changing predecessor Gate PASS/BLOCK semantics;
- increasing reviewer budgets/timeouts as a compatibility workaround;
- silently authenticating providers or spending paid API budget;
- silently upgrading the production OpenCode pin;
- broad workflow refactoring;
- modifying production/game automation behavior;
- merging/closing `gate-reviewer-output-contract-reliability` inside this task;
- broad provider/version benchmarking unrelated to obtaining one defensible Gate-compatible route.

## Required evidence and verification

Tracked evidence MUST make each fresh live attempt independently auditable enough to answer:

- OpenCode version;
- SDK/runtime version if distinct;
- provider/model;
- reviewer role;
- whether a required read/search tool call occurred;
- whether a successful tool result returned;
- whether finalization was voluntary or forced;
- finish reason when available;
- whether `structured_output` existed;
- whether schema and semantic validation passed;
- final classification;
- bounded failure diagnostic when not passing.

Any probe helper introduced by this task MUST have deterministic offline coverage for argument construction, schema validation, classification, bounded error redaction, and version/state isolation seams as applicable. Live provider/model calls are evidence runs, not deterministic unit tests.

## Acceptance criteria

1. Fresh canonical Scout evidence exists after synchronization with the launcher/version repair.
2. The task defines and uses one reproducible bounded probe using the official OpenCode SDK `json_schema` structured-output mechanism and an actual production reviewer agent.
3. OpenCode 1.18.31 Big Pickle and MiMo are freshly re-probed under the repaired baseline before concluding that 1.18.31 has no viable candidate, unless a concrete infrastructure blocker makes one probe impossible.
4. At least one evaluated authorized `OpenCode version + provider + model` combination is classified `PASS_PROVEN`, OR tracked evidence demonstrates `PASS_PROVEN = 0` for the authorized evaluated set and identifies the next external dependency/version/provider to test.
5. A future Gate route is recommended only after the same candidate combination succeeds with both `spec-reviewer` and `regression-reviewer` under the complete lifecycle.
6. If 1.18.31 remains `PASS_PROVEN = 0`, any newer OpenCode version is tested in reversible isolation before any production pin change is proposed.
7. Compatibility evidence distinguishes model/provider capability failure from launcher/version/local-state infrastructure failure.
8. No paid probe is executed without explicit user approval.
9. No secrets, credentials, or unnecessarily large raw provider responses are committed.
10. No predecessor Gate semantics are weakened to manufacture compatibility.
11. Focused deterministic checks for probe tooling introduced by this task pass.
12. Final task evidence records exactly one outcome category: (a) viable on 1.18.31, (b) viable only on an isolated newer version, or (c) no authorized viable route proven.
13. The production OpenCode CLI pin remains `1.18.31` throughout this task unless a separate explicitly authorized follow-up task changes it.

## Final resolved decisions from Scout

- `structured_output` means the official SDK JSON-Schema response (`session.prompt(... format.type = "json_schema")` -> `response.data.info.structured_output`), not CLI JSONL text events.
- Qualification uses the actual production reviewer agent contract; `spec-reviewer` is the first live qualification role and `regression-reviewer` is required before recommending the route.
- A minimal dedicated agent is diagnostic-only and cannot produce `PASS_PROVEN` by itself.
- Phase 1 uses the production-pinned OpenCode 1.18.31 baseline and re-tests Big Pickle then MiMo.
- Phase 2 is allowed only when Phase 1 remains `PASS_PROVEN = 0`, and must use isolated runtime/state without changing the production pin.
- Any production OpenCode pin upgrade, if required by the result, is a separate follow-up implementation task by default.
- Additional paid/authenticated provider probes remain blocked until the user gives explicit authorization.

## Remaining runtime uncertainty

The following cannot be resolved statically and are intentionally delegated to the bounded live probe:

- whether repaired local state changes Big Pickle/MiMo structured finalization behavior;
- whether either 1.18.31 candidate now voluntarily exits tool use and emits valid `structured_output`;
- if both still fail, which newer OpenCode version first resolves the lifecycle without introducing a provider-specific incompatibility.

These are compatibility evidence questions, not reasons to reopen the architecture contract.

## Workflow state

This SPEC is `Status: Final`.

Production implementation of the blocked predecessor remains paused. The next task-local step is to synchronize this Final SPEC into the dedicated worktree, then implement only the minimal bounded compatibility-probe/evidence surface needed to execute Phase 1. Do not run paid probes or mutate the production OpenCode pin.
