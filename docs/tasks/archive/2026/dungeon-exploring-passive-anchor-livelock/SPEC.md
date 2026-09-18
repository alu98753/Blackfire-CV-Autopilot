# dungeon-exploring-passive-anchor-livelock

Status: Final

## Goal

Eliminate the dungeon `EXPLORING` livelock in which the runtime correctly recognizes `SceneId.DUNGEON_EXPLORING` / `dungeons/leave.png`, transitions into `EXPLORING`, but makes no gameplay progress and eventually reaches the global watchdog timeout.

The fix must preserve the distinction between:

- passive dungeon-presence evidence (`dungeons/leave.png`);
- actionable exploration work (Treasure / Fight / Skill / Bless / GoDown / Complete / battle handoff);
- bounded local waiting/recovery while the runtime is still verifiably inside the dungeon.

The task is behavior-preserving for all already-verified dungeon actions except for the incorrect passive-anchor / actionless-stall semantics described below.

## Confirmed evidence

Real runtime evidence shows:

- login/relaunch recovery recognizes `SceneId.DUNGEON_EXPLORING`;
- global state detection matches `dungeons/leave.png` and performs `UNKNOWN -> EXPLORING`;
- subsequent `EXPLORING` ticks repeatedly match `dungeons/leave.png` and log dungeon-anchor maintenance;
- no actionable dungeon progress occurs;
- after roughly 200 seconds, the global watchdog escalates through popup recovery to game relaunch;
- relaunch/login returns to the same dungeon scene and the pattern repeats.

Current `ExploreHandler` treats `dungeons/leave.png` as a passive anchor in the branch body, but the branch still falls through to the common matched-item tail:

```python
self.no_explore_match_count = 0
return
```

Therefore passive scene-presence evidence is incorrectly granted the same control-flow semantics as successfully handled actionable work.

The existing regression `tests/test_dungeon_relaunch_recovery.py::test_3_explore_handler_handles_leave_anchor` explicitly locks in this behavior by requiring the anchor match to reset `no_explore_match_count` while also asserting that the anchor is not clicked.

## Final root-cause model

### Layer 1 — passive-anchor starvation

`dungeons/leave.png` is persistent dungeon-presence / floor-anchor evidence, not normal gameplay progress. It must not consume the entire exploration tick as if an action was completed.

Current loop:

```text
leave.png visible
  -> confirm dungeon presence
  -> common matched-item tail treats tick as handled
  -> reset no_explore_match_count
  -> return
  -> next tick sees the same passive anchor
```

This can occur after login/relaunch recovery and also during ordinary exploration whenever higher-priority actionable events are temporarily absent.

### Layer 2 — missing in-dungeon bounded local stall semantics

Removing the `leave.png` reset/return alone is insufficient.

The current post-loop `no_explore_match_count` path is a suspected-scene-exit check: after repeated no-event passes it searches for lobby/stage/town anchors and returns to navigation only if one is found. If the runtime is still genuinely inside the dungeon, it resets the counter and continues waiting without any local recovery decision.

Therefore `EXPLORING + valid dungeon presence + no actionable event` currently has no bounded local owner; it can still idle until the outer 200-second watchdog.

## Architecture ownership

`ExploreHandler` is the authoritative owner for dungeon-local action selection and dungeon-local stall classification while `current_state == EXPLORING`.

The solution must preserve these boundaries:

- scene detection / login recovery may identify `DUNGEON_EXPLORING`, but they do not own dungeon actions;
- `NavigationHandler` owns navigation into the dungeon, not internal dungeon event progression;
- `ExceptionWatchdog` remains a global disaster-recovery safety net, not the normal owner of dungeon-local progress semantics;
- `GameStateMachine` remains the owner of state transitions / relocalization primitives, but must not become a second dungeon action selector;
- `ExploreHandler` must not create a parallel watchdog thread or duplicate global recovery system.

## Required behavior

### 1. Passive anchor semantics

`dungeons/leave.png` remains valid evidence that the runtime is inside dungeon exploration.

When observed during normal exploration it may:

- maintain `is_in_dungeon = True`;
- participate in floor-transition bookkeeping that is already contractually required.

It must not, by itself:

- be clicked as normal exploration progress;
- be counted as an actionable event;
- reset actionless/progress accounting;
- cause an unconditional early `return` that starves the rest of the exploration-control path;
- call `notify_ui_progress()` merely because the anchor remains visible.

Whether the template remains physically listed in config `explore_priorities` is an implementation detail. If retained for compatibility, `ExploreHandler` must give it non-consuming passive semantics. If removed from the actionable list, dungeon-presence detection must remain explicit and deterministic. Do not expand this into a config architecture redesign.

### 2. Preserve legal transition windows

Temporary lack of actionable events is legal while an already-started dungeon transition is settling.

Existing bounded windows must remain authoritative where present, including:

- go-down / floor transition: `dungeon_floor_transitioning` + `last_godown_click_time`, with the existing approximately 4-second transition contract;
- dungeon-complete exit: `dungeon_completing` + `last_dungeon_complete_click_time`, using the existing completion retry/timeout contract;
- post-bless settle: `bless_received_this_floor` + `last_bless_claim_time`, using the existing 3.5-second postcondition check;
- battle-entry handoff: existing `dungeon_fight` -> `auto.png` / `STATE_BATTLE` behavior must remain unchanged.

Do not invent new wait durations when an existing timer/flag already owns the transition.

### 3. Distinguish suspected scene exit from in-dungeon actionless stall

`no_explore_match_count` currently serves the "maybe we are no longer in the dungeon" fallback check. Do not silently redefine it into a global progress watchdog if doing so would mix responsibilities further.

The implementation must make these two conditions semantically distinct:

```text
A. no dungeon event because runtime may have left the dungeon
B. dungeon presence is still positively confirmed, but there is no actionable dungeon event
```

For condition A, preserve the existing bounded lobby/stage/town fallback detection behavior.

For condition B, persistent passive-anchor evidence must no longer reset the system into an endless healthy-looking wait loop.

A minimal new local counter/timestamp is allowed only if needed to represent condition B cleanly. Prefer reusing an existing field if one already has exactly this ownership; do not overload an unrelated timer.

### 4. Bounded local stall handling

After all currently valid transition windows have expired, if dungeon presence remains positively confirmed and no actionable dungeon event is available for a bounded period, `ExploreHandler` must stop treating this as ordinary healthy exploration waiting.

The bounded local handling must:

1. be owned by `ExploreHandler` as the dungeon-local classifier;
2. use existing state-machine/recovery primitives for relocalization or escalation rather than inventing a second global watchdog;
3. not manufacture fake progress by calling `notify_ui_progress()` without a real action/postcondition;
4. not click `dungeons/leave.png` as the default recovery action;
5. not silently cycle a local counter back to zero and continue forever while the same passive-only condition persists;
6. terminate the local wait in a deterministic, testable handoff to an existing recovery/relocalization path.

The implementation may use an existing `STATE_UNKNOWN` / recovery transition or another already-existing state-machine recovery primitive if that is the narrowest compatible mechanism. If one bounded relocalization immediately returns to the identical passive-only condition, the local stall budget must not be accidentally forgotten in a way that recreates an unbounded `UNKNOWN -> EXPLORING -> UNKNOWN` loop.

Do not introduce destructive dungeon abandonment (clicking Leave / intentionally forfeiting the run) without a separate explicit product decision; it is outside this task.

### 5. Real progress semantics

Meaningful dungeon progress is an actual action / state handoff / completed postcondition, not template presence.

Existing actionable behavior must remain intact:

- dungeon complete / continue handling;
- Treasure subflow;
- skill-event subflow;
- Bless subflow;
- GoDown / GoDownConfirm;
- Fight-room entry;
- transition to battle when `auto.png` appears.

If `notify_ui_progress()` is used, it must correspond to genuine UI/workflow progress, not passive observation.

## Scope

Expected implementation surface:

- `states/handlers/explore.py`
- `tests/test_dungeon_relaunch_recovery.py`
- `tests/test_behavior_dungeon_state_machine.py`
- `config/defaults.toml` only if the implementation cleanly separates `leave.png` from the actionable priority list
- `states/state_machine.py` only if a narrow existing transition/recovery primitive must be reused or minimally exposed
- this task's tracked artifacts

Read-only verification surface that should normally remain unchanged:

- `states/login_flow.py`
- scene detector/catalog implementation
- `states/handlers/navigation.py`
- `states/exceptions/watchdog.py`
- Daily scheduler / tier logic

## Known invariants

- `dungeons/leave.png` is valid dungeon-presence evidence.
- `dungeons/leave.png` must not be clicked as part of normal dungeon exploration or normal local recovery.
- Passive scene evidence is not gameplay progress.
- Detector/perception responsibilities remain separate from action ownership.
- `ExploreHandler` is the single dungeon-local action/stall owner while `EXPLORING`.
- Existing legal transition timers/flags retain their current semantics.
- Existing Treasure / Fight / Skill / Bless / GoDown / completion / battle-result behavior remains behavior-preserving.
- Login/relaunch recovery into an already-active dungeon must converge on the same `ExploreHandler` semantics as ordinary dungeon entry.
- Global watchdog timeout values and exception-subsystem behavior are not weakened to hide this bug.
- No CV threshold/template changes unless separate evidence proves a perception defect.
- No fake `notify_ui_progress()` heartbeat for passive anchor visibility.

## Non-goals

- No broad dungeon rewrite.
- No general scene-detection redesign.
- No navigation redesign.
- No generic/global watchdog redesign.
- No background recovery thread.
- No new general state-machine framework.
- No Daily scheduler priority/tier changes.
- No unrelated battle, bag, town, domain, or collection changes.
- No speculative new CV model/template work.
- No automatic click of `leave.png` / intentional dungeon forfeiture as a recovery policy.

## Required tests

### A. Passive-anchor regression

Create a deterministic multi-tick test with:

```text
state = EXPLORING
leave.png = persistently visible
Treasure/Fight/Skill/Bless/GoDown/Complete/auto = absent
```

Prove that repeated `leave.png` visibility does not repeatedly reset progress/actionless accounting and does not consume each tick as successful work.

### B. Existing leave-anchor regression correction

Update `tests/test_dungeon_relaunch_recovery.py::test_3_explore_handler_handles_leave_anchor` so it continues to assert:

- `is_in_dungeon == True`;
- no click on `leave.png`;
- required floor-transition bookkeeping remains correct;

but it must no longer require passive-anchor observation to reset actionless/progress accounting as if gameplay progressed.

### C. Legal wait-window regressions

Prove that the local stall logic does not fire prematurely during existing legal transition windows, especially floor transition and post-bless settle.

### D. Bounded in-dungeon stall regression

Prove that after legal wait windows expire, persistent:

```text
EXPLORING + dungeon presence + no actionable event
```

reaches the chosen bounded recovery/relocalization handoff and cannot simply reset its local budget forever.

If the handoff can re-enter `EXPLORING`, add a deterministic regression proving repeated re-entry cannot recreate an unbounded passive-only loop by resetting the stall budget incorrectly.

### E. Existing dungeon behavior preservation

Existing focused dungeon tests for Treasure / Fight / Skill / Bless / GoDown / completion / battle handoff must remain green.

## Acceptance criteria

1. `leave.png` remains a valid passive dungeon anchor and is never clicked as normal exploration/recovery behavior.
2. `leave.png` visibility alone cannot reset actionable-progress/actionless-stall accounting or cause an unconditional consuming early return.
3. Existing legal transition windows continue to wait according to their current timers/flags and are not classified as stalls prematurely.
4. Suspected scene exit and confirmed in-dungeon actionless stall have distinct semantics.
5. Confirmed in-dungeon actionless behavior is bounded locally and cannot cycle indefinitely until the 200-second global watchdog merely because passive anchor evidence remains visible.
6. The bounded local owner is `ExploreHandler`; any eventual relocalization/recovery uses existing state-machine/recovery primitives rather than a new global watchdog/thread.
7. The implementation does not generate fake `notify_ui_progress()` events.
8. Login/relaunch recovery into a dungeon and ordinary dungeon entry use the same corrected exploration semantics.
9. Existing actionable dungeon flows preserve behavior.
10. Existing `test_3_explore_handler_handles_leave_anchor` is corrected.
11. A deterministic multi-tick passive-anchor-only regression exists.
12. A deterministic bounded in-dungeon actionless recovery regression exists.
13. Focused dungeon regression tests pass.
14. `git diff --check` passes.

## Implementation guidance

Prefer the smallest change that gives passive anchors non-consuming semantics and gives the already-authoritative `ExploreHandler` a bounded classification/handoff for confirmed in-dungeon actionless stalls.

Do not over-engineer this into a generic progress framework. If implementation evidence shows that satisfying the bounded handoff would require modifying global exception architecture or introducing destructive dungeon-abandonment behavior, stop and return that evidence rather than silently expanding scope.
