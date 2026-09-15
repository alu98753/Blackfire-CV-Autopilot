Now let me read the scoped implementation files:
Now let me look at the in-flight action types and existing tests:
Let me check the key test files for routing context and in-flight interaction coverage:
I have enough information to produce the report. Here is the scout output:

---

# Scout Context

## Relevant files and symbols
1. **`states/navigation_intent.py`** ??Defines the core decision types: `ActionDecision` (routing result), `ReasonCode` (20 reason codes), `DecisionKind` (CLICK/DELEGATE/WAIT), `NavigationIntentPolicy.resolve()` (pure routing decision entry point).
2. **`states/navigation_routing.py`** ??`NavigationRoutingContext` (dataclass bundling scene + intent + decision + progress + observed action), `resolve_navigation_context()` (orchestrator that builds the context and is the natural observation point), `NavigationDecisionExecutor.execute()` (already has `[IntentRouting]` free-form logging at lines 238??61).
3. **`states/navigation_table.py`** ??`NavigationEdge` and `NavigationTable.next_edge()`; the table is the static adjacency map that produces edge-matched decisions. Relevant for understanding which `ReasonCode` paths exist.
4. **`states/navigation_progress.py`** ??`InFlightAction` (dataclass: intent_id, action_id, expected, source_frame_id, issued_at, deadline, attempt, expected_tab), `NavigationProgress` (owns in-flight lifecycle, `observe()`, `begin()`, `defer()`), `ProgressStatus` enum. This is the in-flight action owner.
5. **`tests/test_behavior_runtime_ports.py`** ??Imports `resolve_navigation_context` and `NavigationRoutingContext`; most direct integration test of the routing context assembly path.
6. **`tests/test_behavior_navigation_intent.py`** ??Tests for `NavigationIntentPolicy.resolve()`; covers decision surface but not structured diagnostics.

## Current control flow
1. External caller invokes `resolve_navigation_context(machine, scene_info)` in `navigation_routing.py`.
2. This builds an `IntentSnapshot` via `build_intent_snapshot()`, creates a `SceneSnapshot`, and obtains `NavigationProgress` from `machine.navigation_progress`.
3. `progress.observe()` returns a `ProgressStatus` (IDLE/WAITING/PROGRESSED/TIMED_OUT/DEFERRED).
4. Based on `ProgressStatus`: if DEFERRED ??recovery intent; if WAITING ??short-circuit with `IN_FLIGHT_ACTION_WAITING` reason; otherwise ??`_select_available_intent()` ??`NavigationIntentPolicy.resolve()` ??returns `ActionDecision`.
5. The result is bundled into a `NavigationRoutingContext` dataclass and returned.
6. `NavigationDecisionExecutor.execute()` consumes the context, logs free-form `[IntentRouting]` info, and dispatches the decision to handlers.

**Key ownership boundary**: `NavigationProgress` owns in-flight state. `NavigationIntentPolicy` owns decision semantics. `resolve_navigation_context()` is the orchestration point where both converge. `NavigationDecisionExecutor.execute()` is the execution boundary.

## Existing safety mechanisms
- `NavigationRoutingContext` is already a frozen-style dataclass that bundles all routing evidence ??it is the natural structured diagnostic host.
- `ActionDecision` already carries structured `reason: ReasonCode`, `kind: DecisionKind`, `action: ActionId`, `expected: PostconditionId`.
- `ProgressStatus` already captures the in-flight relationship state (IDLE/WAITING/PROGRESSED/TIMED_OUT/DEFERRED).
- `NavigationDecisionExecutor.execute()` already logs 12 fields at the `[IntentRouting]` tag ??but as free-form `logging.info()`, not as a testable structured diagnostic.
- `NavigationProgress._postcondition_met()` is passive and testable.

## Existing tests
- `tests/test_behavior_runtime_ports.py` ??Tests `resolve_navigation_context()` integration; directly tests the routing context assembly including in-flight interaction paths.
- `tests/test_behavior_navigation_intent.py` ??Unit tests for `NavigationIntentPolicy.resolve()` covering edge-matched and fallback decisions.
- `tests/test_behavior_navigation_progress.py` ??Tests `NavigationProgress.observe()`, timeout, defer, recovery paths.
- `tests/test_behavior_navigation_table.py` ??Tests `NavigationTable.next_edge()` adjacency matching.
- `tests/test_behavior_navigation_scenarios.py` ??Scenario-level navigation behavior tests.
- **Gap**: No existing test asserts on structured diagnostic output of routing decisions. All current tests validate decision outcomes, not observability evidence.

## Regression and architecture risks
- **Diagnostic passivity is critical**: Any observer/emitter must not alter scheduling, routing, timing, retries, or action lifecycle (spec invariant). The current logging in `NavigationDecisionExecutor.execute()` is already post-decision and passive ??safe to migrate to structured form.
- **Ownership boundary**: `NavigationProgress` owns in-flight state; diagnostics must read it but never mutate it. The `observed_action` field in `NavigationRoutingContext` already captures a snapshot reference.
- **No logging framework rewrite needed**: The spec explicitly excludes this as a non-goal. The narrowest path is adding a structured diagnostic accessor/method to `NavigationRoutingContext` (or a new small dataclass) and replacing the free-form log calls with structured evidence emission.
- **Test preservation**: Existing tests do not assert on log output, so restructuring diagnostics is unlikely to break them. New tests must only ADD assertions for the diagnostic contract.

## Uncertainty
- Whether a new `RoutingDiagnostic` dataclass should be introduced or `NavigationRoutingContext` should gain a diagnostic accessor method ??the code supports either, but the spec's "stable structured diagnostic evidence" phrasing may prefer a dedicated type.
- Whether the `REACH_TOWN` goal edges and `TOWN_SUBFLOW` paths (visible in `navigation_table.py` and `navigation_routing.py` recovery logic) need explicit diagnostic coverage or are out of scope for the initial observability pass.
- Whether `focused_tests` field in `task.json` being empty means test authoring is fully unconstrained or if there are external test priorities not visible in the repo.
## Minimal proposed change surface

1. **`states/navigation_routing.py`** ??Add a structured diagnostic dataclass (e.g., `RoutingDiagnostic`) or method on `NavigationRoutingContext` that produces machine-readable evidence from the existing context fields. Migrate the `NavigationDecisionExecutor.execute()` `[IntentRouting]` logging to consume this structured diagnostic.
2. **`tests/test_behavior_routing_observability.py`** (new) ??Assert that each representative routing outcome produces diagnostic evidence with requested intent, routing outcome, reason code, and in-flight constraint when applicable. Cover IDLE, WAITING (in-flight), TIMED_OUT, DEFERRED, and normal edge-matched paths.
3. **No changes** to `navigation_intent.py`, `navigation_table.py`, or `navigation_progress.py` ??the decision types, tables, and progress lifecycle remain untouched.

## Recommendation
**GO WITH SPEC CHANGES** ??The repository already has all the building blocks for structured observability: `NavigationRoutingContext` bundles routing evidence, `ActionDecision` carries structured reason codes, and `ProgressStatus` captures in-flight state. The gap is purely: (a) a structured diagnostic accessor/emit path, and (b) test assertions for it. However, the spec should be updated to: (1) clarify that the existing `NavigationRoutingContext` is the canonical observation point (it is currently unnamed in the spec), (2) specify whether `TOWN_SUBFLOW`/recovery paths are in-scope for initial coverage, and (3) confirm the `focused_tests` empty state means test authoring is open-ended. These are minor spec refinements; the implementation surface is small and safe.
