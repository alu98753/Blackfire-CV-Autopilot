# nemesis-user-intervention-lifecycle

Status: Final

## Goal

Turn the existing `nemesis_action = "pause"` behavior into a bounded, operator-aware intervention lifecycle without coupling battle CV, pause ownership, Discord transport, and timeout recovery into one component.

When a configured nemesis is detected in pause mode, automation must pause, notify the operator repeatedly, and wait for a bounded grace period. If the operator explicitly resumes within that window, the intervention is acknowledged, pending automatic flee is cancelled, and all intervention notifications are retracted best-effort. If the grace period expires first, the lifecycle resolves as timeout, reuses the existing nemesis flee behavior, reduces the repeated intervention notifications to one retained record, and then restores automation through the authoritative resume path.

The design must follow `docs/architecture/project_arch_greenfield_lite_v1.md`: dependencies flow downward, policy/orchestration must not absorb adapter-specific IO, and each mutable lifecycle has one authoritative owner.

## Scout-confirmed evidence

Verified from the task branch after Scout:

- `states/handlers/battle.py::_check_and_handle_nemesis_encounter()` owns current nemesis recognition and dispatches either `machine.pause()` or the existing `_run_nemesis_flee_subflow()`.
- `_run_nemesis_flee_subflow()` already owns the concrete game-side give-up flow and its existing dungeon/domain cleanup and state transition behavior.
- `states/state_machine.py` owns authoritative `pause()`, `resume()`, `toggle_pause()`, `is_paused`, `pause_start_time`, `resume_event`, and timer compensation.
- Current `GameStateMachine.resume()` sets `just_resumed_from_user = True` for every resume, so the implementation needs a minimal explicit resume-origin seam to distinguish operator resume from programmatic timeout recovery.
- `runtime/loop.py::on_pause_toggle()` is the existing Ctrl+Space user boundary. When paused, it calls the authoritative resume path.
- `states/handlers/base.py` and other low-level paths may block on `resume_event.wait()`. Therefore a nemesis grace timeout cannot depend on the paused handler loop continuing to tick; its deadline owner must live outside that blocked execution path.
- `utils/keyboard_listener.py::PauseController` already owns Ctrl+Space detection; the intervention lifecycle must not add raw keyboard polling.
- `ports/notification_port.py` already exposes `notify_alarm()` returning `NotificationResult.external_message_id` and `delete_message(message_id)` returning `DeleteResult`; the lifecycle must depend on this port rather than a Discord implementation.
- Existing tests cover nemesis pause, legacy nemesis config compatibility, pause/resume timer compensation, PauseController behavior, and existing dungeon/domain nemesis flee behavior. New focused coverage is required for the intervention lifecycle and races.
- `project_arch_greenfield_lite_v1.md` requires downward dependencies and separates decision/orchestration from IO adapters. The intervention lifecycle is a bounded cross-cutting session, not a new `ActiveIntent`, navigation state, battle strategy, or global event/statechart framework.

## Scope

- Introduce the smallest coherent nemesis intervention lifecycle/coordinator needed to own one active intervention session.
- Keep nemesis visual detection in the existing battle-domain owner and keep the existing flee subflow as the concrete game action used on timeout.
- Keep pause/resume authority in `GameStateMachine`; do not duplicate pause state.
- Add the smallest explicit resume-origin seam needed to distinguish operator Ctrl+Space resume from programmatic timeout recovery. Existing callers that do not need the distinction should preserve existing behavior.
- Use `NotificationPort` for alarm dispatch and deletion only; no direct Discord adapter dependency in battle/lifecycle code.
- Support a configurable operator grace period.
- Support a configurable repeated-notification count with default `5` messages per intervention.
- Track only successfully returned external message IDs for later best-effort cleanup.
- Resolve each intervention exactly once as either `ACKNOWLEDGED` or `TIMED_OUT`.
- On operator acknowledgement before the deadline: atomically win `ACKNOWLEDGED`, suppress/cancel timeout flee, and best-effort delete all tracked intervention messages.
- On timeout: atomically win `TIMED_OUT`, invoke the existing nemesis flee behavior exactly once, best-effort reduce successfully sent repeated notifications to one retained message, then restore automation through an explicit programmatic `resume()` path if the automation is still paused.
- Preserve the existing immediate `nemesis_action = "flee"` behavior.
- Add deterministic focused tests around lifecycle ownership, acknowledgement, timeout, duplicate starts, notification failures, deletion failures, retained-timeout-message cleanup, and the acknowledgement/timeout race.

## Architecture / responsibility boundary

The intended separation is:

- **Battle / nemesis detection owner**: detect a configured nemesis and request/start intervention; it does not own Discord delivery scheduling, grace-period state, raw keyboard state, timeout loops, or pause lifecycle state.
- **Intervention lifecycle owner**: own the active intervention identity/state, deadline owner, tracked notification IDs, and exactly-once terminal outcome. It coordinates through existing public ports/owners rather than becoming a second battle policy or pause implementation.
- **GameStateMachine pause owner**: remain authoritative for pause/resume state, `resume_event`, and timer compensation.
- **Runtime / PauseController user-input boundary**: remain authoritative for detecting Ctrl+Space. A user-originated resume must be conveyed explicitly to the intervention lifecycle; the lifecycle must not infer operator intent from raw pause flags or poll the keyboard itself.
- **Existing nemesis flee action**: remain authoritative for concrete give-up clicks and existing dungeon/domain cleanup semantics.
- **NotificationPort**: remain the only outbound notification/delete abstraction used by the lifecycle; Discord-specific transport behavior stays below the port.
- **Deadline owner**: use a narrowly scoped one-shot timer/scheduler mechanism that can fire while normal paused execution is blocked. Do not put a sleep/poll loop inside `BattleHandler`.

No component should gain a reverse dependency on a higher-level runtime object merely to complete this feature. The intervention lifecycle must not become a second `ActiveIntent`, second `InFlightAction`, or global event framework.

## Final lifecycle semantics

### Start

```text
nemesis detected with nemesis_action = "pause"
  -> start one intervention session
  -> authoritative machine.pause()
  -> send configured N alarms (default 5)
  -> remember only successful usable external message IDs
  -> arm one bounded grace deadline
```

Repeated battle ticks or duplicate start requests for the same active intervention must not send another burst, reset the deadline, or create another timeout owner.

### Operator acknowledgement

```text
Ctrl+Space user resume
  -> authoritative resume with user-origin evidence
  -> lifecycle attempts atomic ACTIVE -> ACKNOWLEDGED claim
  -> only the successful claimant owns acknowledgement side effects
  -> timeout/flee can no longer execute
  -> delete every tracked intervention message best-effort
```

The implementation may order the authoritative resume call and lifecycle notification according to the smallest safe integration seam, but the externally observable invariant is that a user resume which wins before timeout resolves the session once as `ACKNOWLEDGED`, prevents later flee, and clears all tracked intervention notifications.

### Timeout

```text
grace deadline fires
  -> lifecycle attempts atomic ACTIVE -> TIMED_OUT claim
  -> only the successful claimant owns timeout side effects
  -> execute existing nemesis flee exactly once
  -> from the successfully sent intervention messages, delete all but one best-effort
  -> retain one intervention message as the timeout/history record
  -> if still paused, authoritative programmatic resume
```

The timeout-side programmatic resume must be explicitly distinguishable from a user-originated resume and must not be interpreted as acknowledgement.

### Race rule

`ACKNOWLEDGED` and `TIMED_OUT` compete for one terminal transition from `ACTIVE`. The transition must be atomic: exactly one path can win. The losing path performs no terminal side effect.

Examples:

- User resume wins first -> all messages deleted; timeout callback later becomes a no-op; no flee.
- Timeout wins first -> flee executes once; notifications reduce to one retained record; a later user-resume signal cannot convert the session to `ACKNOWLEDGED` or repeat/delete the timeout outcome.

## Resume-origin contract

The implementation must make the origin of a resume explicit at the authoritative resume boundary, using the smallest compatible API change. Conceptually:

```python
resume(user_initiated=True)   # Ctrl+Space / operator resume
resume(user_initiated=False)  # nemesis timeout recovery
```

The exact parameter name may differ, but these semantics are required:

- Ctrl+Space resume is user-originated.
- Nemesis timeout recovery is programmatic.
- Programmatic resume must not set or trigger user-acknowledgement semantics.
- Existing pause-duration compensation and `resume_event.set()` behavior remain authoritative and behavior-preserving.
- Do not directly clear `is_paused` or bypass `GameStateMachine.resume()`.
- Do not use `toggle_pause()` for timeout recovery.

## Notification policy

- Repeated alarm count is configurable; default is `5`.
- Repeated delivery is required for redundancy, but this SPEC does not require a specific burst-vs-spacing transport policy. Implementation should use the smallest bounded behavior supported by the existing adapter and must not build a new retry/rate-limit framework in this task.
- Notification send/delete is auxiliary. Failure must never block the core intervention lifecycle.
- Only successful notification results with a usable `external_message_id` are tracked.
- `ACKNOWLEDGED`: delete all tracked intervention messages best-effort.
- `TIMED_OUT`: retain exactly one successfully sent intervention message when at least one usable message ID exists; delete all other tracked intervention messages best-effort.
- If zero usable message IDs were produced, timeout/flee/resume still proceed normally.
- No message-edit capability is required by this task. The retained timeout record may remain one of the original alarm messages unless an already-existing port capability can update it without expanding scope.

## Known invariants

- At most one active intervention exists for one nemesis encounter.
- An intervention has one terminal outcome only: `ACKNOWLEDGED` or `TIMED_OUT`.
- A resume/timeout race must never both acknowledge and flee.
- Terminal-state ownership must be claimed before terminal side effects are executed.
- Programmatic timeout recovery must not be mistaken for operator acknowledgement.
- Timeout recovery must not use `toggle_pause()`.
- Code must never clear `is_paused` directly to bypass `GameStateMachine.resume()` and its timer compensation.
- Notification send/delete failure must not block acknowledgement, flee, or resume lifecycle completion.
- Existing `nemesis_action = "flee"` remains behaviorally unchanged.
- Existing nemesis detection thresholds/templates/check-count behavior remain unchanged.
- Existing battle flee cleanup/cooldown/state-transition semantics remain authoritative and behavior-preserving.
- The timeout owner must remain capable of firing while the normal paused handler execution is blocked.
- If timeout has already won its terminal claim, later user-resume evidence must not revert the session or cause flee to execute again.
- If the existing flee operation itself reports/fails unexpectedly after `TIMED_OUT` has already been claimed, the session must not return to `ACTIVE` or become `ACKNOWLEDGED`; recovery/logging must remain fail-safe and must not duplicate the flee action.
- Tests should not require real wall-clock sleeps where an injected timer/clock/event seam can make behavior deterministic.

## Non-goals

- No redesign of nemesis CV/template matching or battle strategy.
- No rewrite of `_run_nemesis_flee_subflow()` beyond the minimum interface change, if any, required to invoke it safely from the lifecycle owner.
- No redesign of the repository-wide pause system or keyboard hotkey policy.
- No raw keyboard polling inside intervention code.
- No Discord transport rewrite, webhook migration, generic retry framework, rate-limit framework, or new notification backend.
- No message-edit feature requirement.
- No new global event bus/statechart framework merely for this task.
- No new `ActiveIntent` / navigation arbitration concept for the intervention.
- No unrelated `BattleHandler` cleanup/refactor.
- No changes to shared Python environment management.

## Acceptance criteria

1. A configured nemesis with `nemesis_action = "pause"` starts exactly one intervention session and pauses through the existing authoritative pause API.
2. The session requests the configured number of operator alarms; default is `5`.
3. Only successful notification results containing a usable external message ID are retained for cleanup bookkeeping.
4. A user Ctrl+Space resume before the grace deadline is explicitly represented as user-originated and can resolve the active intervention as `ACKNOWLEDGED`.
5. If acknowledgement wins, the intervention resolves exactly once, pending timeout/flee cannot subsequently execute, and all tracked intervention messages are deleted best-effort.
6. If the deadline wins first, the intervention resolves `TIMED_OUT` exactly once and the existing nemesis flee behavior executes exactly once.
7. After timeout wins, all successfully tracked intervention notifications except one are deleted best-effort; one retained message remains when at least one usable message ID exists.
8. After timeout handling, automation is explicitly resumed through the authoritative programmatic resume path if it remains paused.
9. A programmatic timeout resume is not interpreted as a user acknowledgement and does not set equivalent user-acknowledgement semantics.
10. A near-simultaneous operator resume and timeout has one deterministic atomic winner; tests prove that the losing path performs no terminal side effect.
11. A repeated nemesis detection/start attempt while the same intervention is active does not send another notification burst, reset the deadline, or create another timeout owner.
12. Notification send failures and delete failures are observable but do not prevent the core intervention state from reaching its terminal outcome.
13. If no notification send yields a usable message ID, acknowledgement/timeout/flee/resume behavior still completes correctly.
14. Existing direct `nemesis_action = "flee"` behavior remains green.
15. Existing pause timer-compensation and `resume_event` behavior remain green for both user and programmatic resume.
16. Production code does not make `BattleHandler` own Discord-specific IO, raw keyboard polling, a background sleep loop, duplicate pause state, or terminal race arbitration.
17. The deadline mechanism can fire while paused execution is blocked and is bounded to the active intervention session.
18. If timeout has already claimed `TIMED_OUT` and the flee operation later fails, the session does not revert to `ACTIVE`, does not become `ACKNOWLEDGED`, and does not execute flee twice.
19. Focused tests cover acknowledgement, timeout, duplicate start, notification partial failure, deletion failure, zero usable notification IDs, timeout retention of one message, programmatic-vs-user resume origin, and the acknowledgement/timeout race.

## Expected minimal implementation surface

Scout evidence supports the following minimal surface, subject to implementation-level naming choices:

- a small nemesis intervention lifecycle/coordinator module responsible for active-session state, deadline ownership, notification IDs, and exactly-once terminal arbitration;
- `states/handlers/battle.py` changes only at the nemesis pause dispatch boundary plus the minimum callback/interface exposure needed to reuse the existing flee subflow;
- `states/state_machine.py` minimal resume-origin support while preserving pause/resume/timer-compensation authority;
- `runtime/loop.py` or the existing user-input composition boundary forwards user-originated resume evidence without adding a reverse dependency from lower layers;
- existing `NotificationPort` reused unchanged unless implementation uncovers a strictly necessary compatibility adjustment;
- configuration adds bounded nemesis intervention grace-period and repeated-alarm-count settings in the nearest existing nemesis/runtime configuration owner;
- focused tests in a dedicated nemesis intervention test module plus only the smallest required regression updates to existing pause/nemesis tests.

## Completion gate

This SPEC is **Final**.

Production implementation may now begin, but must follow this document and the existing architecture contracts. Gemini/Antigravity is the v1 production implementation writer. OpenCode Scout/reviewers remain read-only. After implementation is pushed, run `scripts/ai_gate.ps1 -Task nemesis-user-intervention-lifecycle`, then perform the final semantic/architecture review from GitHub before merge.