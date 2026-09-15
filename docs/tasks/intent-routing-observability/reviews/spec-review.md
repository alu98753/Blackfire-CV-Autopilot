VERDICT: PASS
BLOCKING_FINDINGS: 0

# Spec Review

## Clause coverage

- **Structured diagnostic (Scope/AC 1??)**: `RoutingDiagnostic` / `RoutingInFlightDiagnostic` are `@dataclass(frozen=True)` in `states/navigation_routing.py`, exposing intent id, scene, decision kind, decision action (optional), `ReasonCode` reason, `ProgressStatus`, and observed in-flight lifecycle fields ??using existing authoritative enums/types only (no parallel taxonomy).
- **Canonical source / snapshot semantics**: `NavigationRoutingContext.to_diagnostic()` maps `self.observed_action` (the pre-`observe()` snapshot) directly; no re-read of mutable `navigation_progress.in_flight` during construction or logging. `resolve_navigation_context()` itself is untouched, preserving the meaningful snapshot ordering.
- **Logging migration (AC 8)**: `NavigationDecisionExecutor.execute()` consumes `context.to_diagnostic().format_log_message(now)`; the old free-form field reconstruction was removed. Logging no longer independently decides/reinterprets reasons.
- **Behavior neutrality (AC 9 / invariants)**: Diagnostic construction is pure field reads; no `observe()`, `begin()`, `defer()`, `take_recovery_intent()`, policy re-resolution, or mutation. Dispatch and `_begin_action` logic in the executor are unchanged apart from the log line.
- **Non-goals**: No edits to `navigation_intent.py`, `navigation_table.py`, `navigation_progress.py`; no new reason codes, no serialization of the whole machine, no telemetry backend.
- **Required tests (AC 4??, 10)**: New observability module covers IDLE (no in-flight), WAITING (`IN_FLIGHT_ACTION_WAITING` + evidence), TIMED_OUT (observed action retained + `TIMED_OUT`), DEFERRED representation (direct-construction fallback, documented), and logging-source proof; runtime-ports tests gain structured-diagnostic assertions for WAITING/TIMED_OUT.

## Blocking findings

None.

## Advisory findings

1. `format_log_message(now=None)` silently computes age against `0.0` (clamped to 0.0s) when no clock is supplied; production always passes `_monotonic_now`, and only tests/external callers could hit the degenerate default. Non-blocking; a `now` default of `0.0` mirrors the previous `max(0.0, ...)` behavior.
2. Production imports `SceneId` from `utils.scene_types` (line 33) while the new test imports it from `utils.scene_snapshot`; both may be re-exports, but I could not complete a direct verification of `utils.scene_types` before step budget expired. Evidence.md reports 32 passing focused tests, which would be impossible if the module-level `scene: SceneId` annotation failed at import ??low risk, but worth one glance.
3. DEFERRED coverage is via a manually constructed `NavigationRoutingContext` rather than the full public routing path; the spec explicitly permits this fallback when no production behavior change is warranted, and EVIDENCE.md documents the test boundary.

## Test evidence gaps

- EVIDENCE.md records 32 focused tests passing (runtime ports, navigation intent, navigation progress, routing observability); I did not execute the suite (read-only contract) and cannot independently rerun it.
- No assertion-based proof was reviewed for the pre-`observe()` snapshot ordering beyond the diff showing `resolve_navigation_context()` unmodified and `to_diagnostic()` reading only `context.observed_action`; a downstream reviewer should read lines 230??90 of `navigation_routing.py` to close this gap.
