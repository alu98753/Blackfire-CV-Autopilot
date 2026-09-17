# nemesis-user-intervention-lifecycle

Status: Final

## Goal

Turn the existing `nemesis_action = "pause"` behavior into a bounded, operator-aware intervention lifecycle without coupling battle CV, pause ownership, Discord transport, timeout recovery, and game-side flee IO into one component.

When a configured nemesis is detected in pause mode, automation pauses, notifies the operator repeatedly, and waits for a bounded grace period. If the operator explicitly resumes within that window, the intervention resolves as acknowledgement, pending automatic flee is cancelled, and all intervention notifications are retracted best-effort. If the grace period expires first, the lifecycle resolves as timeout, reduces the repeated intervention notifications to one retained record, runs the existing nemesis flee behavior exactly once on the authoritative runtime execution path, and then continues normal automation.

The design must follow `docs/architecture/project_arch_greenfield_lite_v1.md`: dependencies flow downward, policy/orchestration must not absorb adapter-specific IO, and each mutable lifecycle has one authoritative owner.

## Scout-confirmed and implementation-confirmed evidence

- `states/handlers/battle.py::_check_and_handle_nemesis_encounter()` owns nemesis recognition and dispatches either pause-mode intervention or the existing `_run_nemesis_flee_subflow()`.
- `_run_nemesis_flee_subflow()` owns the concrete game-side give-up flow and existing dungeon/domain cleanup/state-transition behavior.
- `GameStateMachine` owns authoritative `pause()`, `resume()`, `toggle_pause()`, `is_paused`, `pause_start_time`, `resume_event`, and timer compensation.
- `runtime/loop.py::on_pause_toggle()` is the existing Ctrl+Space user boundary.
- `PauseController` owns Ctrl+Space detection; intervention code must not poll raw keyboard state.
- `NotificationPort` already provides `notify_alarm()` with `external_message_id` and `delete_message()`.
- Paused execution can block on `resume_event.wait()` in handlers/actions. In particular, game IO such as `MouseController.click()` is pause-gated. Therefore a background timer may claim timeout, but must not directly execute the existing flee callback while `resume_event` remains cleared.
- The authoritative runtime loop remains alive while paused and is the correct serialized handoff point for timeout-owned game recovery.
- The intervention lifecycle is a bounded cross-cutting session, not a new `ActiveIntent`, `InFlightAction`, battle strategy, or global event/statechart framework.

## Scope

- Introduce the smallest coherent nemesis intervention lifecycle/coordinator needed to own one active intervention session.
- Keep visual nemesis detection in the existing battle owner.
- Keep the existing flee subflow authoritative for concrete game-side retreat behavior.
- Keep pause/resume authority in `GameStateMachine`; do not duplicate pause state.
- Add the smallest explicit resume-origin seam required to distinguish user Ctrl+Space resume from programmatic timeout recovery.
- Use `NotificationPort` only; no Discord-specific dependency in battle/lifecycle code.
- Support configurable operator grace period.
- Support configurable repeated-notification count with default `5`.
- Track only successful usable external message IDs.
- Resolve each intervention exactly once as `ACKNOWLEDGED` or `TIMED_OUT`.
- Preserve existing immediate `nemesis_action = "flee"` behavior.
- Add deterministic focused tests for lifecycle ownership, races, timeout recovery serialization, notification cleanup, and real pause-gate behavior.

## Architecture / responsibility boundary

- **Battle / nemesis detection owner**: detects the configured nemesis and requests intervention. It does not own notification transport policy, raw keyboard polling, timeout threads, terminal arbitration, or duplicate pause state.
- **Intervention lifecycle owner**: owns session identity/state, deadline owner, tracked notification IDs, exactly-once terminal claim, and the narrow pending-timeout-recovery handoff state.
- **GameStateMachine pause owner**: remains authoritative for pause/resume state, `resume_event`, and timer compensation.
- **Runtime loop**: remains the authoritative serialized execution path for timeout-owned game recovery once the deadline owner has claimed `TIMED_OUT`.
- **PauseController / user-input boundary**: remains authoritative for detecting Ctrl+Space and asks the lifecycle whether user resume may proceed.
- **Existing nemesis flee action**: remains authoritative for concrete give-up clicks and existing cleanup semantics.
- **NotificationPort**: remains the only outbound alarm/delete abstraction.
- **Deadline owner**: is a narrowly scoped one-shot timer/scheduler that may claim timeout while normal paused execution is blocked, but it must not execute game-side flee IO itself.

No reverse dependency on a higher-level runtime object should be introduced merely to complete this feature. No new global event bus, scheduler framework, second `ActiveIntent`, or second `InFlightAction` is allowed.

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
Ctrl+Space user resume request
  -> lifecycle attempts atomic ACTIVE -> ACKNOWLEDGED claim
  -> only successful claimant owns acknowledgement side effects
  -> cancel/neutralize timeout
  -> delete every tracked intervention message best-effort
  -> authoritative resume(user_initiated=True)
```

A user resume that loses to an already-claimed timeout must not resume automation early or interfere with timeout-owned recovery.

### Timeout claim and serialized recovery

The grace timer owns only deadline arbitration:

```text
grace deadline fires
  -> lifecycle attempts atomic ACTIVE -> TIMED_OUT claim
  -> if successful:
       retain one tracked notification as history
       mark timeout recovery pending
       return from timer/background context
```

The background deadline callback must not execute mouse/capture/game-side flee IO.

The authoritative runtime loop then serializes the recovery before any normal `step()` may continue:

```text
runtime observes pending timeout recovery
  -> authoritative resume(user_initiated=False)
       # releases existing resume_event/action/capture gates
  -> execute existing nemesis flee callback exactly once
  -> delete all tracked timeout notifications except the retained one best-effort
  -> mark timeout recovery complete
  -> only then may the runtime loop continue to normal automation
```

If timer creation/start fails after the intervention has paused, the lifecycle must use the same atomic `TIMED_OUT` claim and pending-recovery handoff. It must not leave an indefinitely paused `ACTIVE` session and must not execute a second timeout recovery implementation.

### Race rule

`ACKNOWLEDGED` and `TIMED_OUT` compete for exactly one atomic terminal transition from `ACTIVE`.

- User claim wins first -> timeout becomes a no-op; no flee; all tracked messages are deleted.
- Timeout claim wins first -> user resume is blocked while timeout recovery is pending/in-progress; existing flee executes once on the runtime path; one notification remains; user input cannot convert the outcome to `ACKNOWLEDGED`.
- The losing terminal path performs no terminal side effect.

## Resume-origin contract

Conceptually:

```python
resume(user_initiated=True)   # Ctrl+Space/operator acknowledgement
resume(user_initiated=False)  # timeout-owned runtime recovery
```

Required semantics:

- Programmatic timeout resume must not set or trigger user-acknowledgement semantics.
- Existing pause-duration compensation and `resume_event.set()` remain authoritative and behavior-preserving.
- Do not directly clear `is_paused`.
- Do not bypass `GameStateMachine.resume()`.
- Do not use `toggle_pause()` for timeout recovery.

## Notification policy

- Alarm count is configurable; default `5`.
- Exact burst-vs-spacing transport policy is not part of this task.
- Send/delete failure is auxiliary and must not block lifecycle resolution.
- Track only successful sends with usable `external_message_id`.
- `ACKNOWLEDGED`: delete all tracked messages best-effort.
- `TIMED_OUT`: retain exactly one successfully tracked message when available; delete the rest best-effort during serialized timeout recovery.
- Zero usable message IDs must not prevent acknowledgement/timeout/flee/resume behavior.
- No message-edit feature is required.

## Known invariants

- At most one active intervention exists for one nemesis encounter.
- One terminal outcome only: `ACKNOWLEDGED` or `TIMED_OUT`.
- Terminal ownership is claimed before terminal side effects.
- Timer/background context never performs existing game-side flee IO.
- Timeout recovery is serialized on the authoritative runtime execution path.
- Normal runtime `step()` must not execute concurrently with timeout-owned flee recovery.
- User Ctrl+Space cannot resume normal automation while timeout recovery is pending or in progress.
- Programmatic timeout recovery is not user acknowledgement.
- Timeout recovery never uses `toggle_pause()`.
- No code directly clears `is_paused` to bypass authoritative resume/timer compensation.
- Existing immediate `nemesis_action = "flee"` remains unchanged.
- Existing nemesis detection thresholds/templates/check-count behavior remain unchanged.
- Existing battle flee cleanup/cooldown/state transitions remain authoritative.
- If flee fails after timeout claim, session does not return to `ACTIVE`, does not become `ACKNOWLEDGED`, and does not execute flee twice.
- Tests should avoid real wall-clock sleeps when injected timer/Event/Barrier seams can make behavior deterministic.

## Non-goals

- No nemesis CV/template redesign.
- No battle strategy redesign.
- No rewrite of `_run_nemesis_flee_subflow()` beyond the minimum callback/interface exposure required.
- No repository-wide pause/hotkey redesign.
- No raw keyboard polling inside intervention code.
- No Discord transport rewrite, webhook migration, generic retry/rate-limit framework, or new notification backend.
- No message-edit requirement.
- No global event bus/statechart/scheduler framework.
- No new `ActiveIntent` or navigation arbitration concept.
- No unrelated `BattleHandler` cleanup.
- No shared Python environment mutation.

## Acceptance criteria

1. `nemesis_action = "pause"` starts exactly one intervention session and pauses via the authoritative pause API.
2. Configured alarm count is used; default is `5`.
3. Only successful usable message IDs enter cleanup bookkeeping.
4. User Ctrl+Space before deadline can atomically resolve `ACKNOWLEDGED` and then resume as user-originated.
5. ACK win prevents timeout/flee and deletes all tracked messages best-effort.
6. Deadline win atomically resolves `TIMED_OUT` exactly once and marks serialized runtime recovery pending.
7. Deadline/background callback does not execute existing game-side flee IO.
8. Runtime-owned timeout recovery calls programmatic authoritative resume to release pause gates, then executes existing flee exactly once, then performs notification cleanup, all before normal `step()` continues.
9. Timeout retains exactly one usable tracked notification when one exists.
10. Late Ctrl+Space during timeout pending/in-progress cannot user-resume or alter the terminal outcome.
11. Near-simultaneous ACK/timeout has one deterministic winner; losing path has no terminal side effect.
12. Duplicate starts do not resend, re-arm, or reset the active intervention.
13. Notification send/delete failures do not block core lifecycle completion.
14. Zero usable notification IDs still permits correct timeout/ack recovery.
15. Timer factory/start failure converges through the same `TIMED_OUT` + pending runtime recovery path.
16. Existing direct `nemesis_action = "flee"` remains green.
17. Existing pause timer compensation and `resume_event` behavior remain green for both resume origins.
18. Production code does not make `BattleHandler` own Discord IO, raw keyboard polling, background timeout loops, duplicate pause state, or terminal arbitration.
19. Deterministic focused tests cover ACK, timeout, duplicate start, partial notification failure, delete failure, zero IDs, one-message retention, resume origin, real ACK/timeout race, late user resume, timer failures, and a real `resume_event`-gated action seam proving recovery releases the gate before flee.

## Expected minimal implementation surface

- small nemesis intervention lifecycle/coordinator module;
- minimal nemesis pause-dispatch changes in `states/handlers/battle.py`;
- minimal explicit resume-origin support in `states/state_machine.py`;
- narrow runtime-loop handoff for user resume decisions and serialized timeout recovery;
- existing `NotificationPort` unchanged;
- bounded nemesis intervention configuration in existing configuration ownership;
- dedicated deterministic focused tests plus minimal regression coverage.

## Completion gate

This SPEC is **Final**.

Production implementation must follow this document and existing architecture contracts. Gemini/Antigravity is the v1 production implementation writer. OpenCode Scout/reviewers remain read-only. After implementation is pushed and executable tests are available in the canonical shared environment, run `scripts/ai_gate.ps1 -Task nemesis-user-intervention-lifecycle`, then perform final semantic/architecture review from GitHub before merge.
