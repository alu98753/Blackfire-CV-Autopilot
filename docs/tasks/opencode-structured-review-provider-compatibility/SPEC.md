# opencode-structured-review-provider-compatibility

Status: Draft

## Goal

Identify and prove at least one `OpenCode version + provider + model` combination that can satisfy the machine-readable structured-review lifecycle required by the blocked `gate-reviewer-output-contract-reliability` task:

```text
read/search tool call
    -> successful tool result
    -> voluntary final assistant turn
    -> valid JSON-Schema structured_output
```

This is a compatibility / capability-evidence task. It must determine where this lifecycle is actually supported; it must not weaken Blackfire's Gate contract merely to accommodate a provider/model limitation.

## Current baseline after launcher repair

Base branch: latest `main` at `6e562bad77ea0a89d494dbfe261752dfba329cf6` (`Merge task-opencode-launcher-version-compatibility`).

The launcher/version prerequisite is now closed:

- production OpenCode is explicitly pinned to CLI `1.18.31`;
- Scout/Gate use parser-valid 1.18.31 invocation construction and no longer depend on `run --standalone`;
- process isolation remains owned by the PowerShell wrappers rather than an OpenCode run flag;
- version mismatch fails before normal model routing;
- a direct `opencode run --agent scout --model opencode/big-pickle` smoke test reached model execution successfully after preserving an incompatible local DB and allowing 1.18.31 to create fresh state;
- canonical Scout completed successfully with `opencode/mimo-v2.5-free`;
- the current text-verdict Gate completed successfully with `opencode/big-pickle` for both independent reviewer roles.

The last point is important but is **not** `PASS_PROVEN` for this task. The currently merged Gate still validates its present reviewer verdict/report contract; its successful Big Pickle run does not itself prove the target JSON-Schema `structured_output` lifecycle required by `gate-reviewer-output-contract-reliability`.

## Historical compatibility evidence

The predecessor investigation previously recorded, under the then-current 1.18.31 environment:

- `opencode/big-pickle`: `FAIL_FINALIZATION` (`finish: tool-calls`, no structured output);
- `opencode/mimo-v2.5-free`: `FAIL_FINALIZATION` (`finish: tool-calls`, no structured output);
- Muse Spark 1.2/1.3 contributor free: `FAIL_TOOL_CHOICE`;
- Nemotron 3.5 Lightning free: `FAIL_TRANSPORT`;
- explicit `StructuredOutput` permission allow did not change the MiMo result in an A/B probe;
- Qwen3-Coder-Next, Kimi K2.5/K3, MiniMax M2.5, and GLM-5.3-Flash were not locally selectable in that environment and were not authorized for paid probing.

That census ended with `PASS_PROVEN = 0`.

These observations remain useful historical evidence, but Big Pickle / MiMo must be re-probed on the repaired launcher/version/local-state baseline before the task treats the old finalization failures as current capability conclusions. Do not silently rewrite historical classifications; record fresh attempts separately.

## Capability classification contract

A candidate is `PASS_PROVEN` only when one bounded live probe demonstrates the complete lifecycle:

```text
1. reviewer performs at least one required read/search tool call
2. the tool result is successfully returned to the reviewer
3. reviewer voluntarily leaves the tool-calling loop before forced max-step finalization
4. reviewer emits the requested machine-readable structured result
5. OpenCode exposes a `structured_output` payload
6. that payload validates against the task's JSON Schema
```

The following are NOT `PASS_PROVEN`:

- ordinary prose/Markdown final output;
- current Gate `VERDICT: PASS` success without the target JSON-Schema lifecycle;
- `finish = tool-calls` with no structured output;
- forced max-step finalization;
- provider `tool_choice` rejection;
- transport/fetch failure;
- malformed structured output;
- a schema-valid payload produced without the required semantic read/search lifecycle;
- metadata or provider documentation claiming support without a bounded live proof.

Recommended failure classes should remain mechanically distinguishable, including at least `FAIL_FINALIZATION`, `FAIL_TOOL_CHOICE`, `FAIL_TRANSPORT`, `FAIL_SCHEMA`, and other concrete infrastructure/capability failures discovered by Scout.

## Investigation order

### Phase 1 — Re-prove the pinned production baseline

Start with production OpenCode `1.18.31` and re-run the exact structured capability probe against the locally available/free candidates, prioritizing:

1. `opencode/big-pickle`
2. `opencode/mimo-v2.5-free`

The new current-Gate success makes these high-value re-tests: they now demonstrably support normal reviewer execution/finalization on the repaired baseline, but structured-output capability remains unproven.

### Phase 2 — Isolated OpenCode version probes if 1.18.31 remains `PASS_PROVEN = 0`

If all authorized 1.18.31 candidates fail the target lifecycle, do **not** weaken the Gate contract. Instead, evaluate newer OpenCode versions in an isolated compatibility probe using the same capability contract.

An isolated version probe must not silently mutate the repository production pin or destroy the user's existing OpenCode data. Version/state isolation strategy must be established by Scout/Final SPEC before execution.

A newer version is only a compatibility candidate after the same tool-call -> tool-result -> voluntary-final -> JSON-Schema structured-output lifecycle is `PASS_PROVEN`.

### Phase 3 — Recommendation, not silent production upgrade

If a newer OpenCode version is required for `PASS_PROVEN`, this task should produce a compatibility matrix and a concrete recommended version/provider/model route. Changing the production repository pin is not automatic; it requires an explicit follow-up implementation decision with launcher/bootstrap/regression evidence.

## Scope

Provisional scope:

- re-establish current evidence after `opencode-launcher-version-compatibility` merged;
- run canonical Scout on the repaired branch baseline before Final SPEC;
- inspect OpenCode agent/provider/model configuration and the structured-output execution path relevant to the target contract;
- establish a bounded, reproducible compatibility probe or diagnostic seam if needed;
- live-probe authorized candidates under the exact capability classification contract;
- evaluate newer OpenCode versions only through reversible/isolated probes when 1.18.31 has no `PASS_PROVEN` candidate;
- classify results by reproducible evidence rather than marketing/model metadata;
- produce tracked compatibility evidence without credentials or unbounded raw provider payloads;
- recommend at least one `PASS_PROVEN` route, or explicitly record that no authorized evaluated combination satisfies the contract and identify the next external dependency.

Possible change surfaces, subject to Scout evidence:

- `docs/tasks/opencode-structured-review-provider-compatibility/`
- `.opencode/` reviewer/agent configuration needed to understand the runtime contract
- diagnostic/probe helpers under `scripts/` or `tests/workflow_scripts/`
- `package.json` / lockfile / bootstrap only if an isolated version probe genuinely requires them and Final SPEC approves it
- `docs/architecture/ai_development_workflow.md` only if compatibility ownership/qualification rules need clarification

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
- merging/closing `gate-reviewer-output-contract-reliability` inside this task.

## Provisional acceptance criteria

1. Canonical Scout is rerun successfully after synchronizing this branch with the launcher/version fix now on `main`, producing fresh `CONTEXT.md` evidence.
2. The task defines one reproducible bounded probe that exercises the complete required lifecycle: read/search tool call -> successful tool result -> voluntary final assistant turn -> valid JSON-Schema `structured_output`.
3. OpenCode 1.18.31 Big Pickle and MiMo are re-probed under the repaired baseline before concluding that 1.18.31 has no viable candidate, unless Scout finds a concrete reason one probe cannot be run.
4. At least one evaluated authorized `OpenCode version + provider + model` combination is classified `PASS_PROVEN`, OR tracked evidence demonstrates `PASS_PROVEN = 0` for the authorized evaluated set and names the next external dependency/version/provider to test.
5. If 1.18.31 remains `PASS_PROVEN = 0`, any newer OpenCode version is tested in isolation before any production pin change is proposed.
6. Any recommended future Gate reviewer route contains only `PASS_PROVEN` candidates.
7. Compatibility evidence distinguishes model/provider capability failure from launcher/version/local-state infrastructure failure.
8. No paid probe is executed without explicit user approval.
9. No secrets, credentials, or unnecessarily large raw provider responses are committed.
10. No predecessor Gate semantics are weakened to manufacture compatibility.
11. Focused deterministic checks for any probe tooling introduced by this task pass.
12. Final SPEC clearly states whether the outcome is: (a) viable on 1.18.31, (b) viable only on an isolated newer version, or (c) no authorized viable route proven.

## Uncertainty to resolve in Scout

- what exact OpenCode 1.18.31 code/config path owns `structured_output` after tool use;
- whether the earlier Big Pickle/MiMo `finish = tool-calls` results reproduce after launcher + DB-state repair;
- whether a minimal dedicated probe agent or the actual reviewer agent is the better qualification surface while preserving the same lifecycle semantics;
- whether any provider adapter requires a materially different `tool_choice` / structured-output mechanism;
- which newer OpenCode versions materially changed structured-output finalization/provider handling if 1.18.31 still fails;
- the safest reversible method for multi-version/state-isolated probes on this Windows environment;
- which additional authenticated providers/models are available to the user without unnecessary cost;
- whether a production pin upgrade, if required, should be a separate follow-up task (default) or explicitly added to this task only after Final SPEC review.

## Workflow state

This SPEC remains `Status: Draft`.

Next lifecycle step after remote -> local synchronization is canonical Scout:

```powershell
scripts/ai_scout.ps1 -Task opencode-structured-review-provider-compatibility
```

Scout is evidence provider only. Do not begin compatibility implementation/probe tooling changes until ChatGPT + user re-read the fresh `CONTEXT.md` and promote this SPEC to `Status: Final`.
