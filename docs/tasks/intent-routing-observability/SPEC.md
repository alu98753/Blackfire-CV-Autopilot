# intent-routing-observability

Status: Draft

## Goal

Make intent-routing and in-flight-action decisions explainable from runtime evidence without changing validated navigation behavior. Operators/reviewers should be able to determine what intent was requested, what routing decision was made, what in-flight action/state constrained that decision, and why the router chose the resulting transition/outcome.

## Lightweight survey basis

This Draft is intentionally provisional pending OpenCode Scout evidence. It was seeded from latest `main`, the current greenfield architecture contract, precondition contracts, current navigation intent/routing implementation, nearby intent tests, and backlog/task artifacts. No production implementation is authorized while this spec remains Draft.

## Scope

- Define an observability contract for intent-routing decisions and relevant in-flight-action context.
- Identify the narrow runtime ownership point(s) where routing decisions can be observed without moving decision authority.
- Expose stable, structured diagnostic evidence sufficient to reconstruct the routing reason/path for a decision.
- Cover representative routing outcomes in focused tests, including interaction with an already committed/in-flight action where applicable.
- Preserve existing public behavior and routing semantics unless Scout proves an existing contract requires a narrowly documented correction before Finalization.

## Known invariants

- Intent/policy owns decision semantics; observability must not become a second policy engine.
- Execution/action ownership remains separate from intent selection/routing ownership.
- A committed/in-flight action is not implicitly cancelled or preempted merely because desired intent changes; existing explicit cancellation/safe-boundary semantics remain authoritative.
- Diagnostics must be passive: emitting/collecting evidence must not alter scheduling, routing, timing, retries, preconditions, or action lifecycle.
- Existing validated navigation behavior is preserved by default.
- Architecture contracts remain authoritative over convenient local instrumentation.

## Non-goals

- No redesign of navigation intent policy, planner, scheduler, or action lifecycle.
- No new recovery strategy, cancellation rule, preemption rule, or routing priority.
- No broad logging/telemetry framework rewrite.
- No UI/dashboard work.
- No unrelated cleanup/refactor of navigation modules.
- No production implementation before this SPEC is Final.

## Provisional acceptance criteria

1. For each instrumented routing evaluation, diagnostic evidence can identify the requested/active intent, resulting routing outcome, and a stable reason/category.
2. When an in-flight/committed action affects routing, the evidence identifies the relevant action/lifecycle constraint without transferring state ownership into the observer.
3. Observability is structured and testable rather than relying only on free-form log text.
4. Existing intent-routing/navigation tests continue to pass unchanged except for additions strictly required to assert the new observability contract.
5. Focused tests prove diagnostics are behavior-neutral and cover representative allow/defer/block/no-op or equivalent outcomes actually present in the current implementation.
6. No new routing policy decisions are duplicated in logging/observer code.
7. Final implementation remains within responsibility boundaries defined by the architecture contracts and Scout-confirmed code ownership.

## Uncertainty to resolve with Scout

- Exact current type/name representing the routing result and its reason taxonomy.
- Exact owner and lifecycle representation of the in-flight/committed action in current `main`.
- Whether an existing trace/event/diagnostic abstraction should be extended instead of introducing a new structure.
- Which tests are the canonical contract tests for routing + in-flight action interaction.
- Whether backlog wording implies required fields/sinks beyond the minimum evidence described above.
- Whether recent merged workflow/refactor tasks changed nearby ownership boundaries not obvious from the lightweight survey.

## Scout questions

1. Trace the complete path from desired/navigation intent through routing decision to execution/in-flight action ownership; name authoritative modules/types and state owners.
2. Enumerate current routing outcomes/reason codes and where each is produced.
3. Identify all existing diagnostics/events/logging around intent routing and action lifecycle; recommend the narrowest extension point.
4. Identify canonical tests and missing coverage needed to prove behavior preservation.
5. Check architecture/backlog/task docs for constraints that should tighten or change this Draft before Finalization.

## Lifecycle gate

Next step after remote-to-local synchronization: run `scripts/ai_scout.ps1 -Task intent-routing-observability`, commit and push the generated `CONTEXT.md`. Do not start production implementation while `Status: Draft`.