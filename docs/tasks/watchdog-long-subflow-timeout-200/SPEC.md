# watchdog-long-subflow-timeout-200

Status: Final

## Goal

Make the in-process `ExceptionWatchdog` long-subflow timeout policy explicit, single-sourced, and consistent with long-running navigation progress semantics.

This task has two coupled goals:

1. Change the `ExceptionWatchdog` long-subflow no-progress threshold from 90 seconds to 200 seconds, with exactly one runtime-policy source of truth.
2. Establish and apply one coherent `notify_ui_progress()` contract for same-state long-running workflows so legitimate forward movement, including dungeon card-list pagination, refreshes watchdog progress consistently instead of being misclassified as a stuck state.

## Scout-confirmed current state

Scout confirmed that `states/exceptions/watchdog.py` currently reads `long_subflow_timeout_sec` with a literal `90.0` fallback, while `config/exception_features.json` does not define that key. `config.py` separately supplies an exception-feature default containing `battle_stuck_timeout_sec`, and no distinct production consumer of `battle_stuck_timeout_sec` was found. The greedy known-target dungeon path dispatches `CardListNavigator.swipe_towards_target(...)` without calling `notify_ui_progress()`, while nearby alignment/reset paths already report progress.

Scout also confirmed `GameStateMachine.notify_ui_progress()` is the canonical state-machine progress signal. No second production progress API was found; direct `last_state_change` writes are limited to initialization/transition, watchdog timestamp repair, relaunch reset, and the canonical progress method.

## Architecture parent and ownership

- `docs/architecture/exception_subsystem_architecture.md` owns the ExceptionWatchdog / popup-recovery / relaunch responsibility boundary.
- `states/exceptions/watchdog.py` owns in-process stuck detection and escalation decisions.
- `GameStateMachine.notify_ui_progress()` remains the single progress-reporting authority for meaningful same-state progress.
- Business/navigation handlers own evidence that their workflow made meaningful progress and may report it through `notify_ui_progress()`; they do not own watchdog timeout policy.
- `config/exception_features.json` is the canonical runtime-policy owner for the long-subflow timeout value.

## Required implementation

### A. Long-subflow timeout SSOT

- Define `long_subflow_timeout_sec = 200.0` in `config/exception_features.json`.
- That JSON value is the only runtime-policy source that defines the numeric 200-second long-subflow threshold.
- Remove the hardcoded `90.0` fallback from the `ExceptionWatchdog` long-subflow read. Do not replace it with a Python `200.0` fallback.
- Remove the stale `battle_stuck_timeout_sec` exception-feature setting from `config/exception_features.json` and the corresponding exception-feature default in `config.py`, because Scout found no distinct live production consumer.
- The required long-subflow key must be validated when the exception configuration is consumed/initialized so a missing or invalid value fails explicitly rather than silently selecting another numeric policy. The implementation may use the existing `JsonConfigManager` mechanism plus narrow caller-side validation; a broad config-manager redesign is not required.
- Existing last-known-good reload behavior may remain for a previously valid snapshot. The important invariant is that the system must never invent an independent long-subflow numeric fallback when no valid canonical value exists.
- Preserve existing long-subflow state membership and `COLLECT_ONLY` dynamic timeout behavior.

### B. Unified `notify_ui_progress()` contract

`notify_ui_progress()` reports meaningful forward progress while the machine intentionally remains in the same state. It is valid when at least one of these is true:

- an internal iterator/index/phase advances;
- a confirmed business/UI step completes;
- a bounded navigation operation is successfully dispatched toward a known target and the normal contract treats that dispatch as forward progress;
- pagination/alignment/reset intentionally advances the workflow toward its target.

It must not be called merely because a loop iterated, time passed, a template was absent, a retry slept, or a failed/no-op action was reissued. Genuine no-progress paths must still accumulate watchdog age and recover.

For known-target dungeon card pagination, successful dispatch of `CardListNavigator.swipe_towards_target(...)` is sufficient progress evidence. Call the canonical progress notification immediately after the swipe dispatch succeeds and before the bounded sleep/return. Do **not** add next-frame visible-range/index confirmation, frame-diff verification, or a new perception subsystem for this task.

Existing primary-card alignment and dungeon reset paths that already call the canonical progress API are consistent with this contract and do not need redesign merely for uniformity.

### C. Documentation and focused tests

- Update `docs/architecture/exception_subsystem_architecture.md` so active architecture no longer describes the long-subflow policy as 90 seconds and documents the same-state progress contract above.
- Update active focused watchdog tests that encode 90/91/95-second long-subflow assumptions to test the configured 200-second boundary.
- Add focused coverage for the known-target dungeon swipe progress notification.
- Prove periodic valid progress refreshes watchdog age while genuine no-progress beyond the configured threshold still enters the existing recovery path.
- Historical/task-story prose containing old values does not need mass rewriting unless it presents itself as current normative runtime behavior.

## Known invariants

- `ExceptionWatchdog` remains the owner of in-process stuck detection and recovery escalation.
- `UnexpectedPopupRecoveryHandler` / exception subflows remain the owner of popup recovery; business handlers must not add ad-hoc recovery policy.
- `notify_ui_progress()` reports progress only; it does not decide navigation intent, completion, preemption, recovery, routing, or task success.
- A progress notification may refresh watchdog timing/stuck memory but must not alter actual state, desired intent, in-flight action lifecycle, or task completion semantics.
- Real no-progress conditions must still eventually trigger the existing watchdog recovery path.
- `COLLECT_ONLY` keeps its dynamic cooldown-derived timeout semantics.
- Process-external Supervisor heartbeat timeout is a separate lifecycle contract and is unchanged.
- Battle HP-stall detection and battle hard-duration cap are separate contracts and are unchanged.
- Behavior outside watchdog timing/progress reporting is behavior-preserving.
- Numeric runtime policy must not be duplicated across JSON and Python under the guise of synchronization.

## Non-goals

- No change to `runtime/supervisor.py` heartbeat watchdog semantics or `[supervisor].watchdog_timeout`.
- No change to battle HP-stall detection or battle hard-cap semantics.
- No change to `COLLECT_ONLY` dynamic timeout formula.
- No redesign of PopupRecovery retry/escalation policy.
- No new frame-to-frame movement detector solely to prove a card swipe moved.
- No redesign of navigation intent/routing policy, dungeon target selection, card-index inference, or in-flight action lifecycle.
- No global audit/refactor of every existing `notify_ui_progress()` call site. Scout established the current inventory; this task changes only the concrete inconsistent path(s) required by this contract.
- No new timer-reset/progress API parallel to `GameStateMachine.notify_ui_progress()`.

## Acceptance criteria

1. ExceptionWatchdog long-subflow no-progress threshold is 200 seconds in normal runtime behavior.
2. `config/exception_features.json` contains the sole runtime definition of that numeric 200-second policy.
3. `states/exceptions/watchdog.py` has no independent 90/200 numeric fallback for `long_subflow_timeout_sec`.
4. Missing/invalid canonical long-subflow configuration fails explicitly when no valid snapshot exists; it does not silently substitute another numeric threshold.
5. The unused/misleading `battle_stuck_timeout_sec` exception-feature policy is removed from active runtime configuration/defaults.
6. Existing long-subflow state membership is unchanged.
7. `notify_ui_progress()` remains the sole state-machine API for reporting meaningful same-state progress.
8. Known-target dungeon `swipe_towards_target(...)` reports progress immediately after successful dispatch, without next-frame movement confirmation.
9. Existing equivalent alignment/reset progress paths remain behaviorally valid and do not gain a second progress mechanism.
10. Periodic legitimate same-state progress prevents a false watchdog timeout even when `NAVIGATING` itself persists longer than 200 seconds.
11. No-progress `NAVIGATING`/long-subflow execution beyond the configured threshold still triggers the existing first-stage recovery behavior.
12. Short-state timeout, `COLLECT_ONLY`, Supervisor heartbeat, battle stall detection, battle hard cap, popup retry/escalation, navigation intent, and dungeon target selection remain unchanged.
13. Focused tests cover config authority/validation, threshold boundary behavior, canonical progress refresh, dungeon swipe integration, and genuine no-progress recovery.

## Expected implementation surface

Primary production/config surface:

- `config/exception_features.json`
- `config.py`
- `states/exceptions/watchdog.py`
- `states/handlers/navigation.py`

`states/state_machine.py`, `states/handlers/base.py`, and `utils/config_manager.py` are reference/evidence surfaces; edit them only if the smallest coherent implementation requires a narrow validation seam and does not create a second policy/progress owner.

Documentation/tests:

- `docs/architecture/exception_subsystem_architecture.md`
- `tests/test_behavior_global_watchdog.py`
- the smallest existing/new dungeon navigation test module that can prove the known-target swipe calls the canonical progress API

## Completion gate

Gemini/Antigravity may now implement the smallest coherent patch satisfying this Final SPEC. After implementation, run the task focused tests and `scripts/ai_gate.ps1 -Task watchdog-long-subflow-timeout-200`; push implementation plus Gate evidence/reviews. ChatGPT then performs final semantic/architecture review from GitHub before merge.