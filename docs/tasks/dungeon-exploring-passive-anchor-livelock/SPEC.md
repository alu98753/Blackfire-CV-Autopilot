# dungeon-exploring-passive-anchor-livelock

Status: Draft

## Goal

Eliminate the dungeon `EXPLORING` livelock in which the runtime correctly recognizes `SceneId.DUNGEON_EXPLORING` / `dungeons/leave.png`, transitions into `EXPLORING`, but makes no gameplay progress and eventually reaches the global watchdog timeout.

The task must preserve the distinction between passive scene evidence ("we are in a dungeon") and actionable exploration progress (an input/state transition/postcondition that advances the dungeon workflow).

## Observed evidence

A real runtime trace shows:

- login/relaunch recovery recognizes `SceneId.DUNGEON_EXPLORING`;
- global state detection matches `dungeons/leave.png` and performs `UNKNOWN -> EXPLORING`;
- subsequent `EXPLORING` ticks repeatedly match `dungeons/leave.png` and log `維護地下城探索狀態`;
- no actionable dungeon progress is visible in the trace;
- after ~200 seconds, the watchdog treats `EXPLORING` as stalled and escalates through popup recovery to game relaunch;
- relaunch/login returns to the same dungeon scene and the loop repeats.

Current `ExploreHandler` treats `dungeons/leave.png` as a special anchor: it sets `is_in_dungeon = True`, then the common matched-item tail resets `no_explore_match_count` and returns from the handler for that tick.

## Scope

Primary investigation / likely implementation surface:

- `states/handlers/explore.py`
- `states/state_machine.py` only if transition/re-entry ownership is part of the defect
- `states/login_flow.py` / scene detection only if needed to verify recovery handoff semantics; do not change correct dungeon recognition merely to hide the livelock
- dungeon behavior tests, especially `tests/test_behavior_dungeon_state_machine.py`
- any directly related detector/scene contract needed to prove passive-vs-actionable semantics
- this task's tracked artifacts

## Known invariants

- `dungeons/leave.png` is valid evidence that the current scene is dungeon exploration; the observed scene recognition itself is not the primary failure.
- Scene/anchor recognition must not be equated with successful gameplay progress.
- Detector/perception responsibilities must remain separate from input/action ownership.
- A state may remain `EXPLORING` across many ticks, but persistent passive evidence alone must not indefinitely starve an actionable progress path or falsely reset progress/stall accounting.
- Existing Treasure / Fight / Bless / GoDown / battle-result behavior must remain behavior-preserving unless new evidence proves a contract conflict.
- Recovery from login/relaunch into an already-active dungeon must converge onto the same valid exploration-progress semantics as normal dungeon entry.
- Do not weaken or disable the watchdog to conceal the defect.
- Do not change CV thresholds/templates unless evidence shows a separate perception defect.

## Non-goals

- No broad dungeon rewrite.
- No general scene-detection redesign.
- No generic watchdog redesign.
- No changes to Daily scheduler priority/tier semantics.
- No unrelated navigation, battle, bag, town, or domain behavior changes.
- No speculative new CV model/template work without evidence.
- No production implementation while this SPEC is Draft.

## Provisional acceptance criteria

1. A deterministic regression reproduces the observed condition: runtime enters/has `EXPLORING`, `dungeons/leave.png` remains visible across repeated ticks, and no higher-priority actionable dungeon event is visible.
2. Persistent `leave.png` alone can no longer create an infinite "matched -> reset counters -> return" loop that survives until the outer watchdog timeout without an exploration-progress attempt, bounded local recovery, or a semantically correct handoff.
3. `leave.png` continues to serve as valid dungeon-presence / scene evidence and must not itself cause an erroneous exit from dungeon state.
4. The final implementation identifies one authoritative owner for the next exploration-progress action when only passive dungeon anchor evidence is present; no duplicate click owners or parallel progress loops are introduced.
5. Existing actionable dungeon events retain their priority and behavior: completion, confirm/continue, fight, treasure, skill, bless, go-down, and battle handoff continue to work.
6. Login/relaunch recovery into an already-active dungeon reaches the same progress-capable `EXPLORING` behavior as ordinary entry.
7. Progress/stall accounting distinguishes passive anchor observation from meaningful action/progress so repeated anchor matches cannot indefinitely mask a stall.
8. Focused dungeon regression tests pass, including a new test for the passive-anchor-only condition.
9. `git diff --check` passes.

## Uncertainty to resolve before Final

- What is the existing authoritative mechanism that actually starts/continues dungeon exploration when the screen shows only the dungeon anchor? Determine whether it is an existing button/action, a state transition/handoff, a delayed event model, or another handler path.
- Is `dungeons/leave.png` intended to remain inside `explore_priorities`, or should passive anchors be represented separately from actionable priority items?
- Which progress counter/timestamp is architecturally correct for distinguishing passive observation from real progress? Avoid inventing a second watchdog/state owner if an existing mechanism already owns this.
- Does the defect occur only after login/relaunch recovery, or also after normal dungeon entry whenever `leave.png` is the only matched item?
- Are there existing tests/legacy behavior that intentionally rely on `leave.png` resetting `no_explore_match_count`?

## Architecture review focus

Before Final SPEC, verify against `docs/architecture/project_arch_greenfield_lite_v1.md` that the solution preserves:

- perception vs action separation;
- one authoritative action owner;
- postcondition/progress semantics rather than "match == success";
- bounded recovery;
- behavior-preserving refactor constraints for already-verified dungeon flows.
