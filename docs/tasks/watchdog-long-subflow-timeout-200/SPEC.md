# watchdog-long-subflow-timeout-200

Status: Draft

## Goal

Make the in-process `ExceptionWatchdog` long-subflow timeout policy explicit, single-sourced, and consistent with long-running navigation progress semantics.

This task has two coupled goals:

1. Change the `ExceptionWatchdog` long-subflow no-progress threshold from 90 seconds to 200 seconds, with exactly one runtime-policy source of truth.
2. Establish and apply one coherent `notify_ui_progress()` contract for same-state long-running workflows so legitimate forward movement, including dungeon card-list pagination, refreshes watchdog progress consistently instead of being misclassified as a stuck state.

## Problem statement

Current `main` contains a configuration/implementation drift:

- `states/exceptions/watchdog.py` reads `long_subflow_timeout_sec` with a hardcoded `90.0` fallback.
- `config/exception_features.json` exposes `battle_stuck_timeout_sec = 90.0`, not `long_subflow_timeout_sec`.
- `config.py` separately embeds an exception-feature default containing `battle_stuck_timeout_sec = 90.0`.

Therefore the active long-subflow threshold is not actually governed by the checked-in configuration key that appears to describe it. The runtime currently falls back to a code literal.

A second issue exists in same-state progress reporting. The state machine already exposes `notify_ui_progress()` as the mechanism for valid progress that should refresh `last_state_change`, but usage is incomplete. In particular, the greedy dungeon navigation path can intentionally swipe the horizontal dungeon card list toward a known target and remain in `NAVIGATING` without refreshing watchdog progress. A legal long navigation can therefore exceed the long-subflow timeout even while the UI is progressing.

## Architecture parent and ownership

- `docs/architecture/exception_subsystem_architecture.md` owns the ExceptionWatchdog / popup-recovery / relaunch responsibility boundary.
- `states/exceptions/watchdog.py` owns in-process stuck detection and escalation decisions.
- `GameStateMachine.notify_ui_progress()` owns the state-machine-level signal that meaningful same-state progress occurred.
- Business/navigation handlers own the evidence that their workflow made meaningful progress; they may report that fact through `notify_ui_progress()` but must not redefine watchdog timeout policy.
- `config/exception_features.json` is the provisional canonical runtime-policy owner for exception-watchdog timing values in this task.

## Scope

### A. Long-subflow timeout SSOT

- Introduce/use `long_subflow_timeout_sec = 200.0` as the single authoritative configured value for the ExceptionWatchdog long-subflow threshold.
- `config/exception_features.json` must be the only source that defines the numeric 200-second long-subflow policy.
- Production Python code must not contain a second `200.0` fallback/default for the same policy.
- Tests and architecture docs may assert/describe the configured behavior, but must not become alternate runtime-policy sources.
- Remove or migrate the stale/misleading `battle_stuck_timeout_sec` exception-watchdog setting if Scout confirms it has no distinct live consumer.
- Missing/malformed required long-subflow timeout configuration must not silently substitute an independently duplicated numeric default. Prefer explicit validation/fail-fast behavior or another mechanism that preserves one policy authority.

### B. Unified `notify_ui_progress()` contract

Define one project-level rule for when same-state work may refresh watchdog progress.

`notify_ui_progress()` SHOULD be called when the workflow has performed or observed meaningful forward progress while remaining in the same state, including at least:

- an internal iterator/index/phase advances;
- a confirmed business/UI step completes;
- a bounded navigation operation intentionally moves the workflow toward its target;
- a horizontal/vertical pagination or alignment action is dispatched toward a known target and the code path treats that action as successful progress.

For this task, dungeon card-list pagination toward a known target does **not** require an additional next-frame visible-range/index confirmation before reporting progress. The user has explicitly accepted the weaker evidence requirement because this action is known to move the list in normal operation. The implementation should therefore use a consistent, simple progress notification point rather than add a new perception/verification subsystem.

`notify_ui_progress()` MUST NOT be used merely because a loop iterated, time passed, a template was absent, a retry slept, or an action was re-issued with no workflow advancement signal. Repeated no-op/error paths must still be able to accumulate watchdog age and recover.

### C. Call-site consistency

- Survey existing `notify_ui_progress()` call sites and nearby long-running handler paths.
- Normalize only the call sites needed to make the above contract coherent, with special focus on navigation/card pagination and existing long-subflow implementations.
- Avoid a broad unrelated handler refactor.
- If there are semantically equivalent wrapper/helper methods, converge on one state-machine progress-reporting authority rather than introducing another timer-reset API.

### D. Documentation/tests

- Update the exception subsystem architecture documentation so the long-subflow policy and progress-reporting contract no longer describe the old 90-second behavior.
- Update focused watchdog behavior tests from the old 90-second assumptions to the new 200-second configured contract.
- Add focused regression coverage proving dungeon card pagination reports progress and does not allow stale `last_state_change` to trigger a false watchdog timeout during legitimate navigation.
- Preserve recovery behavior when no progress occurs beyond the configured threshold.

## Known invariants

- `ExceptionWatchdog` remains the owner of in-process stuck detection and recovery escalation.
- `UnexpectedPopupRecoveryHandler` / exception subflows remain the owner of popup recovery; business handlers must not add ad-hoc recovery policy.
- `notify_ui_progress()` reports progress; it does not decide navigation intent, completion, preemption, recovery, or routing.
- A same-state progress notification resets watchdog progress age but must not alter the actual state, desired intent, in-flight action lifecycle, or task completion semantics.
- Real no-progress conditions must still eventually trigger the existing watchdog recovery path.
- `COLLECT_ONLY` keeps its dynamic cooldown-derived timeout semantics.
- Process-external Supervisor heartbeat timeout is a separate lifecycle contract and is not changed by this task.
- Battle-specific stall detection and the battle hard-duration cap are separate contracts and are not changed by this task.
- Behavior outside watchdog timing/progress reporting is behavior-preserving by default.
- Numeric policy must not be duplicated across config and Python fallback constants under the guise of “synchronization”; one source owns it.

## Non-goals

- No change to `runtime/supervisor.py` heartbeat watchdog semantics or `[supervisor].watchdog_timeout`.
- No change to battle HP-stall detection or battle hard-cap semantics.
- No change to `COLLECT_ONLY` dynamic timeout formula.
- No redesign of PopupRecovery retry/escalation policy.
- No new frame-to-frame movement detector solely to prove a card swipe moved.
- No redesign of navigation intent/routing policy, dungeon target selection, card-index inference, or in-flight action lifecycle.
- No global rewrite of all handlers merely to rename progress APIs.

## Provisional acceptance criteria

1. The ExceptionWatchdog long-subflow threshold is 200 seconds in normal runtime behavior.
2. Exactly one runtime-policy source defines that 200-second value; there is no matching hardcoded Python fallback/default for the same policy.
3. `states/exceptions/watchdog.py` obtains the long-subflow threshold from the canonical configuration contract and does not silently fall back to an independent 200/90 literal.
4. The stale `battle_stuck_timeout_sec` exception-feature key is either removed/migrated or Scout provides evidence that it has a distinct valid owner; no misleading duplicate timing key remains unexplained.
5. Existing long-subflow state membership remains behaviorally unchanged unless Scout identifies an actual mismatch that must be surfaced to the spec owner.
6. `notify_ui_progress()` has a documented, testable contract distinguishing meaningful same-state progress from no-op/retry/time-passing paths.
7. Dungeon card-list pagination toward a known target refreshes watchdog progress through the canonical progress API without requiring a next-frame movement confirmation.
8. Existing alignment/pagination paths that already report equivalent valid progress are normalized to the same contract rather than using direct timer mutation.
9. A long-running `NAVIGATING` flow with periodic legitimate pagination progress does not trigger ExceptionWatchdog solely because the state itself has remained `NAVIGATING` for more than 200 seconds.
10. A `NAVIGATING` or other long-subflow flow with no reported progress beyond 200 seconds still triggers the existing first-stage recovery behavior.
11. Short-state timeout behavior, COLLECT_ONLY dynamic timeout, Supervisor heartbeat timeout, battle stall detection, and battle hard cap remain unchanged.
12. Focused tests cover threshold boundary behavior, config authority, progress refresh, pagination integration, and no-progress recovery.

## Uncertainty for Scout

Scout should resolve, without changing this Draft SPEC:

- all live readers/writers/usages of `battle_stuck_timeout_sec`, `long_subflow_timeout_sec`, and other exception-watchdog timing keys;
- whether `JsonConfigManager` currently supports treating `long_subflow_timeout_sec` as a required key without a duplicated numeric Python fallback, and the smallest fail-fast/validation mechanism if not;
- the complete current `notify_ui_progress()` call-site set and any direct `last_state_change` mutations serving the same purpose;
- which navigation/card alignment/pagination paths already notify and which do not;
- the smallest focused test surface that proves progress notifications reset watchdog age without masking genuine no-progress recovery;
- any architecture/test conflict with changing the documented long-subflow threshold from 90 to 200 seconds.

If Scout finds that `battle_stuck_timeout_sec` has a distinct live responsibility unrelated to the long-subflow ExceptionWatchdog, preserve that responsibility and report it rather than deleting it speculatively.

## Expected implementation surface

Likely production/config surfaces:

- `config/exception_features.json`
- `config.py`
- `states/exceptions/watchdog.py`
- `states/state_machine.py`
- `states/handlers/navigation.py`
- potentially a very small number of other existing `notify_ui_progress()` call sites identified by Scout

Likely documentation/tests:

- `docs/architecture/exception_subsystem_architecture.md`
- `tests/test_behavior_global_watchdog.py`
- focused navigation/card behavior tests identified by Scout

This list is provisional; Scout should localize the exact surface.

## Completion boundary

This SPEC remains **Draft**. OpenCode Scout may inspect and create `CONTEXT.md`; Gemini/Antigravity must not implement production changes until ChatGPT + user review Scout evidence and promote this SPEC to `Status: Final`.
