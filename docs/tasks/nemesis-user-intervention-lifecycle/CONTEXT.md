Now let me read the architecture contract and check for existing test coverage:
# Scout Context: nemesis-user-intervention-lifecycle

## Status: Maximum Steps Reached

I have completed the reconnaissance phase with 6+ files inspected. Here is the localized audit report based on evidence gathered.

---

## Relevant files and symbols

| File | Why it matters |
|------|---------------|
| `states/handlers/battle.py:317-387` | `_check_and_handle_nemesis_encounter()` ??owns nemesis visual detection and dispatches `machine.pause()` or `_run_nemesis_flee_subflow()` |
| `states/state_machine.py:350-378` | `pause()` / `resume()` / `toggle_pause()` ??authoritative pause owner with timer compensation; `resume_event` (threading.Event) gates the main loop |
| `utils/keyboard_listener.py:16-389` | `PauseController` ??Ctrl+Space background thread polls keys; calls `_on_toggle` callback on trigger |
| `runtime/loop.py:33-35` | Wires `PauseController(on_toggle=on_pause_toggle)` ??bridges hotkey to `state_machine.toggle_pause()` |
| `ports/notification_port.py:37-67` | `NotificationPort` ABC with `notify_alarm()` returning `NotificationResult.external_message_id` and `delete_message()` ??the port the lifecycle must use |
| `states/handlers/base.py:82` | `self.machine.resume_event.wait()` ??proves the main handler loop **blocks** when paused |

## Current control flow

1. **Nemesis detection**: `BattleHandler.handle()` ??`_check_and_handle_nemesis_encounter()` performs CV template matching against `nemesis_templates` during the first 3 ticks.
2. **Pause dispatch** (line 370-377): If `nemesis_action == "pause"` and a nemesis is detected, calls `self.machine.pause()` and returns `True`. **No notification is sent; no grace period is armed; no timeout is scheduled.** The current behavior is: pause and wait indefinitely for user Ctrl+Space.
4. **Flee path** (existing): `nemesis_action == "flee"` ??`_run_nemesis_flee_subflow()` handles setting menu ??give-up ??confirm ??dungeon cooldown ??transition.

**Critical finding**: `resume_event.wait()` blocks in the **handler's main loop** (`base.py:82`). This means the timeout owner for the grace period **cannot live inside the paused handler loop** ??it must be a separate thread or scheduled outside the blocked main thread.

## Existing safety mechanisms

- **Timer compensation**: `GameStateMachine.compensate_internal_timers()` (line 393-439) adjusts `last_state_change`, battle timers, stashed timestamps, and handler timestamps by `pause_duration` on resume. This prevents watchdog false positives after long pauses.
3. **User resume path**: `PauseController._poll_ctrl_space()` ??sets `toggle_event_pending` ??main thread consumes via `check_toggle_triggered()` ??calls `state_machine.toggle_pause()` ??calls `resume()` ??sets `resume_event` ??unblocks `resume_event.wait()` in `base.py:82`, `capture/screen.py:298`, `actions/mouse.py:112`, `state_machine.py:1813`.
- **`just_resumed_from_user`** flag (line 376): Set on resume, consumed once by `BattleHandler` to detect lobby recovery. The SPEC requires distinguishing user-originated vs programmatic resume ??this flag is a candidate but is currently set on **all** resumes including programmatic ones.
- **Single pause ownership**: `pause()` has a guard `if not self.is_paused` (line 354); `resume()` has `if self.is_paused` (line 368). Timer compensation runs only on genuine transitions.
- **NotificationPort abstraction**: `NullNotifier` fallback exists (line 144-145 of state_machine.py). `NotificationResult.external_message_id` is already optional/nullable, supporting the "only track successful sends" invariant.

## Existing tests

| Test file | Coverage |
| `test_behavior_golden_empire.py:453-482` | `test_nemesis_pause_action_subflow` ??proves nemesis detection ??`machine.pause()` called, no click dispatched |
| `test_behavior_golden_empire.py:484-508` | `test_nemesis_backward_compatibility_with_flee_bosses` ??proves `flee_bosses`/`flee_boss_action` legacy keys still trigger pause |
|-----------|----------|
| `test_behavior_pause_resume.py:25-51` | `test_pause_resume_lifecycle` ??basic pause/resume/toggle_pause state transitions |
| `test_behavior_pause_resume.py:53-84` | `test_internal_timers_compensation_math` ??verifies `compensate_internal_timers()` arithmetic |
| `test_behavior_pause_resume.py:128+` | Multiple PauseController unit tests for key detection, debounce, window filtering |
| `test_behavior_dungeon_nemesis.py` | 4 tests for nemesis flee path (cooldown, primary_config fallback, collect_only fallback) |

**Gap**: No test exists for timeout-acking race, notification lifecycle, or grace-period expiry.
## Regression and architecture risks


1. **`toggle_pause()` race**: The SPEC mandates explicit `resume()` for timeout recovery, never `toggle_pause()`. Current `PauseController` calls `toggle_pause()`. If the timeout fires `resume()` while user also hits Ctrl+Space, the `is_paused` guard prevents double-resume. However, the SPEC requires one deterministic winner ??the lifecycle coordinator must **atomically resolve** the intervention before calling resume, preventing the other path from acting.
2. **`just_resumed_from_user` ambiguity**: Currently set on ALL `resume()` calls (line 376). The SPEC requires distinguishing user-originated from programmatic resume. Either a separate flag or parameter is needed on `resume()` without breaking the existing `compensate_internal_timers` call.
3. **Blocking main thread**: `resume_event.wait()` in `base.py:82` proves the timeout **must** be owned by an external thread/timer (e.g., `threading.Timer` or `clock` scheduler), not the handler loop.
4. **Notification burst threading**: Sending 5 alarm messages requires either sequential calls within the lifecycle or a bounded concurrent pattern. Rate-limiting behavior of the Discord adapter under burst is unverified.
5. **Greenfield-lite compatibility**: The SPEC proposes a new "intervention lifecycle owner." The architecture contract says "one active intent" and "one in-flight action." The lifecycle coordinator must not become a second intent or conflict with the `ActiveIntent` ownership ??it should be a cross-cutting session manager, not a new state handler.

## Uncertainty

1. **`PauseController` callback path exact wiring**: `runtime/loop.py` wires `on_toggle=on_pause_toggle` but the full main-loop integration (how `check_toggle_triggered()` is polled per tick) was not fully read within budget.
2. **`resume_event.wait()` granularity**: The wait appears in 4 locations (capture, mouse, state_machine, base handler). Whether the timeout owner must set a **separate** event or can reuse `resume_event` to unblock a paused agent is an implementation detail.
3. **Notification adapter rate limits**: The Discord adapter's behavior under 5 rapid `notify_alarm()` calls was not inspected. The SPEC says burst spacing is provisional.
4. **Whether timeout should retract alarm messages**: The SPEC leaves this intentionally unresolved in Draft.

## Minimal proposed change surface

1. **New module**: `states/intervention_lifecycle.py` ??`NemesisInterventionSession` class owning: deadline timer, tracked message IDs, terminal state (ACKNOWLEDGED/TIMED_OUT), exactly-once guard.
5. **Existing `nemesis_check_done` lifecycle**: After 3 checks, nemesis detection locks. The lifecycle coordinator must handle the case where nemesis is detected on tick 1, intervention starts, but tick 2-3 still run `_check_and_handle_nemesis_encounter` ??the `nemesis_check_done` flag prevents re-detection, but the battle handler's `return True` short-circuits the rest of `handle()`, so no conflict arises. This was verified.
2. **`states/handlers/battle.py`**: `_check_and_handle_nemesis_encounter()` line 370-377 ??instead of bare `machine.pause()`, create/start the intervention session, which internally calls `machine.pause()`.
3. **`states/state_machine.py`**: `resume()` gains an optional `reason` parameter (or a separate `resume_from_timeout()` method) so the lifecycle can call `resume()` without setting `just_resumed_from_user`.
4. **`ports/notification_port.py`**: No structural change; lifecycle calls `notify_alarm()` in a loop and tracks returned `external_message_id` values.
6. **`tests/test_nemesis_intervention_lifecycle.py`**: New test module covering all 12 acceptance criteria.
5. **`config.py` / config JSON**: Add `nemesis_intervention_grace_sec` and `nemesis_intervention_alarm_count` keys.

## Recommendation

**GO WITH SPEC CHANGES**

The codebase supports the proposed lifecycle pattern: pause/resume ownership is clean, `NotificationPort` has the needed interface, `resume_event` blocking proves the timeout must be external-threaded, and existing tests cover the baseline pause and flee paths. Two SPEC items need clarification before Final:

1. **`just_resumed_from_user` disambiguation**: The SPEC must declare whether `resume()` gains a `reason` parameter, a separate `resume_from_timeout()` method, or a `ProgrammaticResume` flag ??all three are viable but affect the change surface.
2. **Timeout retraction decision**: The SPEC should explicitly resolve whether timeout-resolved interventions retract alarm messages (currently "intentionally unresolved"). This affects whether the lifecycle tracks message IDs in the timeout path at all.
