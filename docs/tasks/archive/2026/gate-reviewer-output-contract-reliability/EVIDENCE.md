# Verification Evidence

Task: `gate-reviewer-output-contract-reliability`

Closure decision date: 2026-09-16

Immutable resumption base: `f2e6503e88161d01fbd73dc4a60e5da7d98167b4`

Live Gate implementation HEAD: `186734bc4c73b214b84388d53133887451e67aa9`

## Core infrastructure evidence

The final live production Gate successfully reached both independent OpenCode reviewers through the pinned OpenCode `1.18.31` / `@opencode-ai/sdk` `1.18.31` path.

Accepted reviewer attempts:

- `spec-reviewer | model=opencode/big-pickle | classification=VALID_BLOCK | selected=true`
- `regression-reviewer | model=opencode/big-pickle | classification=VALID_BLOCK | selected=true`

The external Gate result was:

```text
AI verification gate CANDIDATE_BLOCKED
```

This is intentionally preserved as the factual result. It is not rewritten as `PASSED`.

The important infrastructure conclusion is that both reviewers reached trusted machine-qualified semantic authority. Earlier failures that prevented that point — SDK/transport failure, premature headers timeout, outer-process timeout racing the 480-second reviewer deadline, missing envelope, and owned-resource teardown concerns — no longer prevented review completion.

Final timeout hierarchy at the live run:

```text
Reviewer AI execution deadline = 480s
HTTP transport timeout          = 510s
Gate outer adapter timeout      = 540s
```

The transport path uses Node global `fetch` with an adapter-owned Undici `6.28.1` `Agent`, preserving Node `Request` compatibility and AbortSignal behavior. Local compatibility probes verified localhost `200 OK`, response-body consumption, behavioral abort, and Agent close.

## Deterministic verification before the final live Gate

The focused deterministic workflow set reached:

```text
18 tests OK
Node syntax:       PASS
PowerShell syntax: PASS
git diff --check:  PASS
```

The transport-specific compatibility probes also verified:

- Node global `Request` + `globalThis.fetch` + owned Undici dispatcher;
- headers/body transport timeout strictly greater than the reviewer AI budget;
- bounded `agent.close()` with `destroy()` fallback;
- behavioral abort propagation;
- natural resource cleanup without `process.exit()`.

## Final live Gate reviewer findings

The now-working Gate surfaced downstream correctness findings rather than failing infrastructurally.

### Spec reviewer

- verdict: `BLOCK`
- blocking findings: `1`
- principal finding: malformed/partial failure-envelope cleanup safety can become invisible to the Gate because `Test-Envelope` rejects the envelope before the Gate consults `cleanup.safe`; an exit-0 invalid envelope with unsafe cleanup can therefore incorrectly proceed to fallback.

### Regression reviewer

- verdict: `BLOCK`
- blocking findings: `2`
- one finding matched the cleanup-safe fallback corner above;
- the second reported apparent Stage 8 removals when reviewing a diff against the moving `origin/main` ref.

The Stage 8 finding was determined to be review-baseline contamination rather than an actual task-branch game/runtime change: the task branch's immutable resumption base is `f2e6503e...`, while `origin/main` advanced afterward with Stage 8 / Dungeon 8 work. Comparing this task from its immutable base does not include those game/runtime files in the task changes.

## Focused-test result from the final live Gate

The final live Gate reported:

```text
tests.test_opencode_structured_review_probe: FAIL (exit=1)
tests.test_workflow_scripts:                FAIL (exit=-1)
```

These results occurred after both reviewer roles had already reached trusted `VALID_BLOCK` authority. They are not converted into a false PASS and are not used to claim the entire Gate implementation is semantically complete.

Focused-test orchestration robustness discovered here is deferred with the other Gate-orchestration findings described below.

## Explicit deferral decision

The user and ChatGPT/human final reviewer explicitly narrowed closure to the core reviewer-output reliability objective instead of expanding this task indefinitely after reliable review execution began exposing new Gate correctness concerns.

Deferred follow-up task:

`gate-immutable-review-baseline-contract`

The follow-up owns the generalized contract for:

- immutable task review baselines and provenance;
- reproducible Gate diff snapshots;
- eliminating moving-`origin/main` contamination;
- cleanup-safe fail-closed fallback for malformed/partial failure envelopes;
- related Gate-orchestration consistency;
- focused-test orchestration robustness exposed by the final live Gate.

No claim is made that those deferred findings are fixed by this task.

## Full suite

The full product suite was **not run**, by explicit user decision for this closure.

## Final human / ChatGPT assessment

Core reviewer-output infrastructure objective: **MET**.

The production workflow now demonstrably reaches trusted independent reviewer authority through the supported pinned SDK path. The semantic `BLOCK` results are evidence that the infrastructure is functioning well enough to surface downstream issues rather than failing before review authority exists.

Task status: **COMPLETED WITH EXPLICIT DEFERRALS**.

Follow-up: `gate-immutable-review-baseline-contract`.
