# intent-routing-observability

Status: Final

## Goal

Make intent-routing decisions explainable from stable, structured runtime evidence without changing validated navigation behavior. A caller/test/reviewer must be able to determine the selected intent, scene, resulting decision, reason, progress relationship, and the relevant pre-existing in-flight action snapshot from the same routing evaluation.

## Evidence and ownership

Scout confirmed the current ownership boundaries:

- `NavigationIntentPolicy` / `ActionDecision` own routing decision semantics and the existing `ReasonCode` taxonomy.
- `NavigationProgress` owns in-flight action lifecycle and `ProgressStatus`.
- `resolve_navigation_context()` is the canonical orchestration/observation point where scene, intent, decision, progress status, and the pre-observation in-flight action converge into `NavigationRoutingContext`.
- `NavigationDecisionExecutor.execute()` is the execution boundary and currently emits `[IntentRouting]` free-form logs.

Observability must attach to these existing facts; it must not infer or recompute policy.

## Scope

- Add a small immutable structured routing-diagnostic representation in `states/navigation_routing.py`, derived from a completed `NavigationRoutingContext`.
- Make `NavigationRoutingContext` the canonical source from which that diagnostic snapshot is obtained.
- The diagnostic contract must expose, at minimum:
  - active/selected intent id;
  - observed scene;
  - decision kind;
  - decision action when present;
  - decision reason (`ReasonCode` value);
  - progress status;
  - relevant observed in-flight action identity and lifecycle evidence when one existed at the start of the routing evaluation, including action id, expected postcondition, attempt, and stable timing/lifecycle fields already available from `InFlightAction` where useful.
- Adapt the existing `[IntentRouting]` logging path to consume the structured diagnostic rather than independently reconstructing routing facts.
- Add focused observability tests covering representative normal routing and in-flight lifecycle outcomes.
- Preserve all existing routing, progress, recovery, cancellation/preemption, execution, and state-machine behavior.

## Required semantic detail

`resolve_navigation_context()` currently snapshots `progress.in_flight` before calling `progress.observe()`. This ordering is meaningful: `observe()` may advance, time out, defer, or otherwise mutate progress lifecycle state. The observability contract must therefore preserve `NavigationRoutingContext.observed_action` as evidence of the action that was in flight when this routing evaluation began. Diagnostics must not re-read mutable `NavigationProgress.in_flight` later and present that as if it were the same observation.

The diagnostic is a snapshot/view of facts already decided by the authoritative owners. It is not a new state owner and is not authoritative input to later policy decisions.

## Recovery / TOWN_SUBFLOW boundary

Recovery and `TOWN_SUBFLOW` remain behaviorally in scope only insofar as the generic diagnostic representation must faithfully represent any `NavigationRoutingContext` produced by existing routing code. This task does **not** redesign or expand those flows, and it does not require exhaustive scenario coverage for every intent/recovery branch.

Focused coverage must include a DEFERRED/recovery-produced context if it can be constructed through the existing public routing path without changing production behavior. Otherwise the generic diagnostic mapping may be covered directly and the limitation documented in test/evidence artifacts.

## Known invariants

- `NavigationIntentPolicy` remains the sole owner of normal routing decision semantics.
- `NavigationProgress` remains the sole owner of in-flight lifecycle state.
- Observability must not become a second policy engine or duplicate routing conditionals/reason selection.
- A desired-intent change does not implicitly cancel or preempt a committed action; existing explicit lifecycle semantics remain authoritative.
- Diagnostic creation/emission is passive: it must not alter scheduling, routing, timing, retries, preconditions, recovery, relaunch behavior, action lifecycle, clicks, or transitions.
- Diagnostic construction must not call `progress.observe()`, `take_recovery_intent()`, `begin()`, `defer()`, or otherwise mutate machine/progress state.
- Existing `ActionDecision`, `ReasonCode`, `ProgressStatus`, and `InFlightAction` remain authoritative data sources; do not introduce parallel enums/taxonomies for observability.
- Existing validated navigation behavior is preserved.

## Non-goals

- No redesign of navigation intent policy, navigation table, scheduler, planner, progress lifecycle, recovery policy, cancellation, or preemption.
- No changes to `states/navigation_intent.py`, `states/navigation_table.py`, or `states/navigation_progress.py` unless an implementation-blocking fact contradicting Scout evidence is discovered; such a contradiction requires stopping and returning to the spec owner.
- No telemetry backend, persistence layer, metrics pipeline, dashboard, tracing framework, or broad logging rewrite.
- No new reason-code taxonomy merely for diagnostics.
- No unrelated navigation cleanup/refactor.
- No behavior change disguised as observability.

## Acceptance criteria

1. A stable structured diagnostic can be obtained from each completed `NavigationRoutingContext` without consulting mutable routing/progress state again.
2. It identifies active intent, scene, decision kind/action/reason, and `ProgressStatus` using existing authoritative values.
3. If an action was in flight at the start of evaluation, the diagnostic identifies that observed action and relevant lifecycle evidence; if none existed, those fields are explicitly absent/`None` rather than inferred.
4. WAITING with an in-flight action reports `IN_FLIGHT_ACTION_WAITING` and the corresponding observed action evidence.
5. TIMED_OUT routing preserves the existing `ACTION_TIMEOUT_RETRY` behavior and exposes the timed-out observed action plus `TIMED_OUT` status.
6. A representative normal/IDLE edge-matched decision is observable without in-flight evidence.
7. DEFERRED/recovery context is representable by the same diagnostic contract, subject to the focused-test boundary above.
8. Existing `[IntentRouting]` runtime logging is sourced from the structured diagnostic contract; logging code does not independently decide or reinterpret routing reasons.
9. Diagnostic construction and logging are behavior-neutral: no extra progress mutation, policy evaluation, action begin, click, transition, recovery, or relaunch is introduced.
10. Existing focused navigation behavior tests remain green; new tests assert the structured contract rather than only parsing free-form log text.

## Required focused tests

At minimum run/add coverage around:

- `tests/test_behavior_runtime_ports.py` for `resolve_navigation_context()` integration and WAITING/TIMED_OUT behavior;
- a focused routing-observability test module (new or a narrowly scoped existing module) for structured diagnostic mapping;
- existing navigation intent/progress tests touched by the change surface as appropriate.

Required cases:

- IDLE normal routing context;
- WAITING with pre-existing `InFlightAction`;
- TIMED_OUT with the original observed action retained in diagnostic evidence;
- diagnostic with no observed action;
- DEFERRED/recovery representation when practical through the existing public path;
- proof that existing execution result/decision semantics are unchanged while logging consumes the structured diagnostic.

## Forbidden shortcuts

- Do not parse the `[IntentRouting]` string and call that the structured contract.
- Do not serialize the whole mutable machine or `NavigationProgress` object.
- Do not re-run `NavigationIntentPolicy.resolve()` to build diagnostics.
- Do not read `navigation_progress.in_flight` during later execution/log emission to reconstruct what happened during routing; use the context's captured `observed_action`.
- Do not add routing/recovery decisions inside a diagnostic/logging helper.
- Do not change existing reason codes or lifecycle transitions merely to make observability easier.

## Expected implementation surface

Primary production surface:

- `states/navigation_routing.py`

Expected tests:

- `tests/test_behavior_runtime_ports.py`
- optional new focused `tests/test_behavior_routing_observability.py`

`states/navigation_intent.py`, `states/navigation_table.py`, and `states/navigation_progress.py` are evidence/reference surfaces, not expected production edit targets.

## Completion gate

Gemini/Antigravity may now implement the smallest coherent patch satisfying this Final SPEC. After implementation, run the repository-prescribed focused tests and `scripts/ai_gate.ps1 -Task intent-routing-observability`; push implementation plus `EVIDENCE.md` and reviewer artifacts. ChatGPT then performs final semantic/architecture review from GitHub before any merge.
