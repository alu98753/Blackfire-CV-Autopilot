# nemesis-user-intervention-lifecycle

Status: Draft

## Goal

Turn the existing `nemesis_action = "pause"` behavior into a bounded, operator-aware intervention lifecycle without coupling battle CV, pause ownership, Discord transport, and timeout recovery into one component.

When a configured nemesis is detected in pause mode, automation must pause, notify the operator repeatedly, and wait for a bounded grace period. If the operator explicitly resumes within that window, the intervention is acknowledged, pending automatic flee is cancelled, and the intervention notifications are retracted best-effort. If the grace period expires first, the lifecycle resolves as timeout, reuses the existing nemesis flee behavior, and then restores automation through the authoritative resume path.

The design must follow `docs/architecture/project_arch_greenfield_lite_v1.md`: dependencies flow downward, policy/orchestration must not absorb adapter-specific IO, and each mutable lifecycle has one authoritative owner.

## Lightweight survey evidence

Verified on task-start `main` commit `63d5c93ce88dda7bc580645f664f5efaa4adaf88`:

- `states/handlers/battle.py::_check_and_handle_nemesis_encounter()` owns current nemesis recognition and dispatches either `machine.pause()` or the existing `_run_nemesis_flee_subflow()`.
- `_run_nemesis_flee_subflow()` already owns the concrete game-side give-up flow and its existing dungeon/domain cleanup and state transition behavior.
- `states/state_machine.py` already owns authoritative `pause()`, `resume()`, `toggle_pause()`, `is_paused`, `pause_start_time`, and timer compensation. This task must reuse that ownership rather than create a parallel pause state.
- `utils/keyboard_listener.py::PauseController` already captures Ctrl+Space and drives the public pause/resume path.
- `ports/notification_port.py` already exposes `notify_alarm()` returning `NotificationResult.external_message_id` and `delete_message(message_id)` returning `DeleteResult`; the lifecycle must depend on this port rather than a Discord implementation.
- `project_arch_greenfield_lite_v1.md` requires downward dependencies and explicitly separates decision/orchestration from IO adapters.

This is intentionally a lightweight pre-Scout survey. Exact hook placement, threading/event semantics, focused test surface, and configuration ownership remain subject to Scout evidence.

## Scope

- Introduce the smallest coherent nemesis intervention lifecycle/coordinator needed to own one active intervention session.
- Keep nemesis visual detection in the existing battle-domain owner and keep the existing flee subflow as the concrete game action used on timeout.
- Keep pause/resume authority in `GameStateMachine`; do not duplicate pause state.
- Use `NotificationPort` for alarm dispatch and deletion only; no direct Discord adapter dependency in battle/lifecycle code.
- Support a configurable operator grace period.
- Support a configurable repeated-notification count; provisional default is 5 messages per intervention because the operator explicitly wants redundancy against a missed alert.
- Track only successfully returned external message IDs for later best-effort retraction.
- Resolve each intervention exactly once as either operator acknowledgement or timeout.
- On operator acknowledgement before the deadline: suppress/cancel timeout flee and best-effort delete all tracked intervention messages.
- On timeout: invoke the existing nemesis flee behavior exactly once, then restore automation through the authoritative `resume()` path if the automation is still paused.
- Add deterministic focused tests around lifecycle ownership, acknowledgement, timeout, duplicate starts, notification failures, deletion failures, and the acknowledgement/timeout race.
- Preserve the existing immediate `nemesis_action = "flee"` behavior.

## Architecture / responsibility boundary

The intended separation is:

- **Battle / nemesis detection owner**: detect a configured nemesis and request/start intervention; it does not own Discord delivery scheduling, grace-period state, or pause lifecycle state.
- **Intervention lifecycle owner**: own the active intervention identity/state, deadline, tracked notification IDs, and exactly-once terminal outcome. It coordinates through existing public ports/owners rather than becoming a second battle policy or pause implementation.
- **GameStateMachine pause owner**: remain authoritative for pause/resume state and timer compensation.
- **Existing nemesis flee action**: remain authoritative for concrete give-up clicks and existing dungeon/domain cleanup semantics.
- **NotificationPort**: remain the only outbound notification/delete abstraction used by the lifecycle; Discord-specific transport behavior stays below the port.
- **PauseController / user-input boundary**: provide evidence that a resume was user-originated without requiring the intervention lifecycle to poll keyboard state or infer intent from raw pause flags.

No component should gain a reverse dependency on a higher-level runtime object merely to complete this feature.

## Known invariants

- At most one active intervention exists for one nemesis encounter; repeated battle ticks must not emit another notification burst or arm another timeout for the same active session.
- An intervention has one terminal outcome only: operator acknowledgement or timeout. A resume/timeout race must never both acknowledge and flee.
- Programmatic timeout recovery must not be mistaken for operator acknowledgement.
- Timeout recovery must not use `toggle_pause()`; it must use explicit authoritative resume semantics so a race cannot toggle the system back into pause.
- Code must never clear `is_paused` directly to bypass `GameStateMachine.resume()` and its timer compensation.
- Notification send/delete is an auxiliary side effect. Delivery or deletion failure must not block acknowledgement, flee, or resume lifecycle completion.
- Only successful sends with a usable `external_message_id` may enter deletion bookkeeping.
- Existing `nemesis_action = "flee"` remains behaviorally unchanged.
- Existing nemesis detection thresholds/templates/check-count behavior are not changed by this task unless Scout discovers an implementation-blocking contradiction.
- Existing battle flee cleanup/cooldown/state-transition semantics remain authoritative and behavior-preserving.
- No real-time sleep-based test should be required if existing clock/event seams can support deterministic tests.

## Non-goals

- No redesign of nemesis CV/template matching or battle strategy.
- No rewrite of `_run_nemesis_flee_subflow()` beyond the minimum interface change, if any, required to call it safely from the lifecycle owner.
- No redesign of the repository-wide pause system or keyboard hotkey policy.
- No Discord transport rewrite, webhook migration, retry framework, or new notification backend.
- No new global event bus/statechart framework merely for this task.
- No unrelated `BattleHandler` cleanup/refactor.
- No changes to shared Python environment management.
- No production implementation while this SPEC remains Draft.

## Provisional acceptance criteria

1. A configured nemesis with `nemesis_action = "pause"` starts exactly one intervention session and pauses through the existing authoritative pause API.
2. The session requests the configured number of operator alarms; provisional default is 5.
3. Only successful notification results containing a usable external message ID are retained for cleanup.
4. If the operator explicitly resumes before the grace deadline, the active intervention resolves `ACKNOWLEDGED` exactly once, pending timeout/flee cannot subsequently execute, and all tracked intervention messages are deleted best-effort.
5. If the deadline wins first, the intervention resolves `TIMED_OUT` exactly once, the existing nemesis flee behavior executes exactly once, and automation is explicitly resumed afterward if it remains paused.
6. A near-simultaneous operator resume and timeout has one deterministic winner; tests prove that the losing path performs no terminal side effect.
7. A repeated nemesis detection while the same intervention is active does not send another burst, reset the deadline, or create another timeout owner.
8. Notification send failures and delete failures are observable but do not prevent the core intervention state from reaching its terminal outcome.
9. Programmatic resume caused by timeout cleanup is not interpreted as a user acknowledgement.
10. Existing direct `nemesis_action = "flee"` behavior and existing pause timer-compensation behavior remain green.
11. Production code does not make `BattleHandler` own Discord-specific IO, raw keyboard polling, background timeout loops, or duplicate pause state.
12. Focused tests use deterministic seams where available and cover acknowledgement, timeout, duplicate start, notification partial failure, deletion failure, and the acknowledgement/timeout race.

## Uncertainty for Scout

Scout must resolve these implementation facts before this SPEC becomes Final:

- Where the lifecycle coordinator belongs under the current Greenfield-lite dependency graph and whether an existing lifecycle/orchestration abstraction should be extended rather than adding a new module.
- The exact Ctrl+Space callback path from `PauseController` into `GameStateMachine`, and the smallest clean mechanism for distinguishing **user-originated resume** from **programmatic resume** without creating a reverse dependency.
- Whether the paused main execution path blocks on `resume_event.wait()` (or equivalent) such that the timeout owner must live outside the paused agent loop, and which existing scheduling/threading primitive is the correct owner.
- Whether the existing injected `clock` is sufficient for grace deadlines/tests or whether a narrowly scoped scheduler/event seam is required.
- Existing notification adapter rate-limit/delete behavior relevant to a five-message burst. The requirement is repeated delivery; exact burst/spacing policy remains provisional until Scout evidence.
- Whether timeout-completed interventions should also retract their alarm messages. The explicit product requirement only mandates retraction when the user returns within the grace period, so timeout cleanup is intentionally unresolved in Draft.
- Exact configuration keys/default location and whether this belongs in existing game/nemesis config normalization or a dedicated runtime settings block.
- Exact focused test modules already covering battle pause/resume/notification behavior.

## Scout evidence requested

Scout should remain read-only and report:

- ownership/call graph for nemesis detection -> pause -> Ctrl+Space resume;
- paused-loop blocking/concurrency behavior;
- notification implementation semantics for repeated send and delete;
- available clock/event/test seams;
- nearest relevant tests and architecture contracts;
- recommended smallest implementation surface consistent with Greenfield-lite;
- any invariant or hidden coupling that contradicts this Draft.

## Completion gate

This SPEC is **Draft**. Do not start production implementation. After Scout pushes `CONTEXT.md`, ChatGPT and the user will re-read the Draft, Scout evidence, actual code/tests, and architecture contracts, then converge this document to `Status: Final` before Gemini/Antigravity implementation is allowed.