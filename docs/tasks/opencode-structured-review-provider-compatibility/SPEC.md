# opencode-structured-review-provider-compatibility

Status: Draft

## Goal

Identify and prove at least one OpenCode version + provider + model combination that can satisfy the Gate structured-review runtime contract required by `gate-reviewer-output-contract-reliability`:

```text
read/search tool call
    -> successful tool result
    -> voluntary final assistant turn
    -> valid JSON-Schema structured_output
```

This task is a compatibility/evidence task. It must not weaken the existing Gate semantic contract merely to accommodate a model/provider limitation.

## Lightweight survey baseline

Base branch: latest `main` at `ade1ea1297510207faa48f41c81a66aa5eb9dec7`.

Relevant architecture on `main` already requires role-specific bounded live qualification, infrastructure-only fallback, terminal valid PASS/BLOCK semantics, no review-shopping, local credentials, and explicit bootstrap boundaries.

The blocked predecessor task is `gate-reviewer-output-contract-reliability`. Its branch evidence at commit `40dc16cc0653fec60ef4ad11d7ba839e2b283b5d` records a pinned OpenCode 1.18.31 capability census with no `PASS_PROVEN` reviewer candidate.

Known evidence from that task includes:

- `opencode/big-pickle`: `FAIL_FINALIZATION` (`finish: tool-calls`, no structured output);
- `opencode/mimo-v2.5-free`: `FAIL_FINALIZATION` (`finish: tool-calls`, no structured output);
- Muse Spark 1.2/1.3 contributor free: `FAIL_TOOL_CHOICE`;
- Nemotron 3.5 Lightning free: `FAIL_TRANSPORT`;
- explicit `StructuredOutput` permission allow did not change the MiMo failure in an A/B probe;
- Qwen3-Coder-Next, Kimi K2.5/K3, MiniMax M2.5, and GLM-5.3-Flash were not locally selectable in that pinned environment and were not authorized for paid probing.

## Scope

Provisional scope:

- establish a bounded compatibility-probe harness or diagnostic seam if needed;
- inspect local OpenCode model/provider metadata and actual runtime behavior;
- evaluate newer OpenCode versions only in isolated compatibility probes before changing the repository pin;
- evaluate authenticated provider/model combinations only with explicit user authorization before any paid API use;
- classify candidates by reproducible capability evidence rather than marketing claims;
- produce tracked compatibility evidence and a recommendation for a `PASS_PROVEN` Gate reviewer route;
- if a compatible version/provider/model is proven, define the smallest safe follow-up change required to unblock `gate-reviewer-output-contract-reliability`.

Possible change surfaces, subject to Scout evidence:

- `docs/tasks/opencode-structured-review-provider-compatibility/`
- diagnostic/probe helpers under `scripts/` or `tests/workflow_scripts/`
- `package.json` / lockfile / bootstrap only if a version-isolated probe requires them and the Final SPEC approves it
- `docs/architecture/ai_development_workflow.md` only if compatibility ownership or qualification rules need clarification

## Known invariants

1. The predecessor Gate contract remains authoritative: machine verdict authority comes from validated structured fields, not free-form prose.
2. No Markdown/prose verdict fallback may be introduced.
3. A valid semantic PASS/BLOCK remains terminal; model fallback is infrastructure-only.
4. Reviewers remain independent and read-only.
5. Provider credentials remain local and must not be committed.
6. Paid/API-cost probes require explicit user authorization before execution.
7. Compatibility metadata is only a prefilter; `PASS_PROVEN` requires a bounded live probe of the complete lifecycle.
8. No production/game behavior changes are in scope.
9. Do not change the production OpenCode pin merely because a newer version appears promising; first prove compatibility in isolation.
10. Do not merge the blocked predecessor task until it obtains its required fresh real independent Gate PASS.

## Non-goals

- weakening JSON-Schema structured-output requirements;
- restoring free-form verdict parsing;
- changing Gate PASS/BLOCK semantics;
- increasing reviewer budgets or timeouts as a compatibility workaround;
- silently authenticating providers or installing dependencies during normal Gate execution;
- broad unrelated workflow refactoring;
- modifying production/game automation behavior;
- merging or closing `gate-reviewer-output-contract-reliability` inside this task.

## Provisional acceptance criteria

1. A reproducible compatibility probe exercises the complete required lifecycle: tool call -> tool result -> final assistant turn -> valid JSON-Schema structured output.
2. At least one candidate is classified `PASS_PROVEN`, OR the task produces sufficient evidence that no evaluated authorized candidate/version satisfies the contract and records the next external dependency explicitly.
3. Any recommended Gate reviewer route contains only `PASS_PROVEN` candidates.
4. Version/provider/model qualification evidence is tracked without secrets, raw credentials, or unbounded provider payloads.
5. No paid probe is performed without explicit user approval.
6. No predecessor Gate semantics are weakened.
7. Focused deterministic checks for any probe tooling pass.

## Uncertainty to resolve in Scout

- whether OpenCode 1.18.31 itself is the limiting factor, provider adapters are the limiting factor, or both;
- which newer OpenCode versions materially changed `json_schema`, `tool_choice`, structured-output retry/finalization, or provider handling;
- which authenticated providers/models are realistically available to the user without introducing unnecessary cost;
- whether a compatibility probe should run against repository reviewer agents or a smaller dedicated probe agent;
- whether any repository pin/bootstrap change belongs in this task or should become a separate implementation task after compatibility is proven;
- how to preserve a clean responsibility boundary between diagnostic qualification and production Gate routing.
