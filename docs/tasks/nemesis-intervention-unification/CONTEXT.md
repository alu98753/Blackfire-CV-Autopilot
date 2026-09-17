# Nemesis Intervention Unification — Context

## Provenance

The canonical OpenCode Scout failed infrastructurally before producing `CONTEXT.md`:

```text
repository-default -> NON_ZERO_EXIT
Unexpected server error
canonical CONTEXT.md left untouched
```

The user explicitly authorized a one-time Gemini/Antigravity read-only Scout fallback. The fallback did not modify repository files or production code. ChatGPT then cross-checked the high-risk findings against the task branch before finalizing the SPEC.

## Key Evidence

### Existing intervention ownership

- `states/nemesis_intervention.py` already owns the bounded operator-intervention session, notification message tracking, timeout arbitration, and timeout recovery handoff.
- `states/state_machine.py` owns the actual pause/resume gate.
- `runtime/loop.py` is the runtime pause gate: while `state_machine.is_paused`, it keeps heartbeat fresh and skips `state_machine.step()`.
- Current `Ctrl+Space` flow conflates intervention acknowledgement with normal Resume. The new contract must split those meanings.

### Known nemesis flow

`states/handlers/battle.py` detects configured nemesis templates near battle start. `nemesis_action = "pause"` starts `NemesisIntervention`; timeout recovery later resumes internally and executes the existing flee subflow.

### Defeat-limit flow

`states/handlers/result.py` currently checks the consecutive-defeat threshold before the final retry increment. Once the configured maximum is reached it enters the give-up subflow. This threshold branch is the narrow integration seam for the new indefinite intervention and must be intercepted before any give-up click/state mutation.

### Hotkey ownership

`utils/keyboard_listener.py` / `PauseController` is the authoritative hotkey owner.

Existing relevant bindings:

- `Ctrl+Space`: pause/resume
- `Ctrl+Q`: deliberate manual fast restart
- `Ctrl+Shift+Q`: deliberate manual exit
- `Shift+C`: currently unused

The task therefore may add `Shift+C` without an existing direct binding collision.

### Permanent-pause escape-path audit

Automatic paths that must be verified or guarded include:

- Nemesis timeout recovery
- result-handler give-up continuation
- battle max-duration relaunch
- HP-stall restart/relaunch
- watchdog popup recovery/relaunch
- window-loss/capture-failure relaunch
- generic `request_relaunch()`
- handler/state transitions if execution bypasses the normal runtime pause gate
- scheduler/daily state reset
- supervisor daily maintenance restart
- supervisor crash/child-exit recovery

The in-process runtime loop already skips `state_machine.step()` while paused, and the exception watchdog already has a pause guard, but those are not sufficient evidence by themselves. Direct/recovery boundaries require deterministic coverage.

### Supervisor finding

`runtime/supervisor.py` performs daily maintenance restart independently of child pause/intervention state and automatically relaunches after child exit/recovery paths. `runtime/heartbeat.py` currently exports `is_paused` but no Nemesis-intervention ownership/policy state.

Final architecture decision:

- automatic scheduled maintenance must be deferred while an intervention-owned manual hold is active;
- if the child exits/crashes while an intervention-owned permanent/manual hold was active, supervisor recovery must fail closed rather than silently replacing the child and losing the hold;
- deliberate `Ctrl+Q` / `Ctrl+Shift+Q` remain explicit user actions and are not prohibited by the automatic-escape invariant.

The smallest implementation may extend heartbeat metadata so the supervisor can distinguish an intervention-owned hold from ordinary liveness state. Exact field names are implementation detail.

### Notification/i18n

`runtime/notification_i18n.py` is the existing reusable message dictionary/formatter boundary, but Nemesis messages are not yet defined there. Current Nemesis CLI/Discord wording is assembled closer to `BattleHandler` / `NemesisIntervention` and does not mention `Shift+C`.

Two distinct Chinese messages are required:

1. known/configured nemesis — bounded grace period, then existing flee fallback;
2. defeat-limit / possible unregistered nemesis — indefinite hold, no automatic flee/give-up.

Both CLI and Discord must explicitly tell the operator to press `Shift+C`.

### Configuration

Current defaults still place:

```toml
[notification]
nemesis_intervention_grace_period_seconds = 60.0
nemesis_intervention_notification_count = 5
```

and Golden Empire duplicates those settings at mode level.

Final canonical configuration is:

```toml
[nemesis_intervention]
grace_period_seconds = 180.0
notification_count = 5
```

Old keys and redundant mode-level copies cease to be authoritative. `battle_max_defeat` remains separate.

### Template inventory

Move existing images to:

```text
templates/nemesis/domain/golden_empire/
  elf_mythril_hag.png
  golden_king.png
  golden_wall_guard_tulan.png
  human_golden_tulakh.png
  undead_altalim.png

templates/nemesis/dungeon/
  dragon_karsos.png
  dragonkin_sakroth.png
  ice_boss_calvia_body.png
```

This is a path/reference migration, not a matcher redesign. Existing domain/dungeon applicability remains intact.

## Final Decisions Derived from User Contract

1. `NemesisIntervention` name/responsibility remains unchanged.
2. Policies are bounded/timed and indefinite/no-timeout; indefinite is never represented by a huge timeout value.
3. `Shift+C` means user-arrival acknowledgement only and always leaves automation paused.
4. Before `Shift+C`, active intervention blocks `Ctrl+Space` from resuming automation.
5. After `Shift+C`, intervention enters a manual-hold state; a later explicit `Ctrl+Space` may finish the intervention hold and resume normal automation.
6. `Ctrl+Q` / `Ctrl+Shift+Q` are explicit user actions and remain permitted.
7. Automatic supervisor daily restart is deferred during intervention-owned manual/permanent hold.
8. Unexpected child exit/crash while such a hold is active must not automatically relaunch into normal automation; fail closed and require operator action.
9. At defeat threshold, the logical defeat count must reflect that the configured limit was reached and must not be reset merely because the intervention started.
10. Shift+C acknowledgement performs best-effort cleanup of tracked repeated Discord alarms, preserving existing cleanup ownership. Known-nemesis timeout keeps the existing one-message history behavior.
11. Untracked profile configs are not silently rewritten by this task. Legacy tracked keys are removed as authoritative inputs; the canonical new section is the supported contract.
