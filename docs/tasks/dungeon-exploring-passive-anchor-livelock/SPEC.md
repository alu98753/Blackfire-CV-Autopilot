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

Read-only Gemini survey plus GitHub cross-check confirmed the exact control flow in `states/handlers/explore.py`: `dungeons/leave.png` performs no click, but still falls through to the common matched-item tail:

```python
self.no_explore_match_count = 0
return
```

This means passive scene-presence evidence is currently treated as handled work for the tick.

The existing relaunch regression test `tests/test_dungeon_relaunch_recovery.py::test_3_explore_handler_handles_leave_anchor` explicitly locks in the same behavior: it expects `leave.png` to remain non-clicking while also resetting `no_explore_match_count` to zero. This test therefore protects the current livelock-enabling semantics rather than detecting repeated-anchor starvation.

## Confirmed root cause

The root defect is **passive-anchor / actionable-progress semantic conflation** inside `ExploreHandler`:

```text
leave.png visible
  -> confirm dungeon presence
  -> common matched-item tail treats the tick as successfully handled
  -> reset no_explore_match_count
  -> return
  -> next tick sees the same passive anchor
```

Because `leave.png` is persistent scene evidence rather than gameplay progress, the loop can continue without input, state transition, postcondition completion, or other meaningful progress until the outer watchdog expires.

This defect is not inherently recovery-only. Any normal dungeon state in which higher-priority actionable events are temporarily absent while `leave.png` remains visible can enter the same starvation pattern.

## Important constraint discovered during survey

Simply changing `leave.png` to "do not reset and do not return" is **not yet a complete fix**.

The existing post-loop `no_explore_match_count` path only performs bounded checks for lobby/stage/town fallback anchors. After six unmatched/actionless passes it resets the counter and, if no external scene anchor is found, continues waiting. Therefore merely allowing `leave.png` to fall through can still leave the runtime waiting indefinitely until the outer watchdog.

Before Final SPEC, the task must identify which existing owner should perform the bounded local progress/recovery decision when:

```text
state == EXPLORING
and dungeon-presence evidence remains valid
and no actionable dungeon event is currently available
```

The implementation must not invent a parallel watchdog or duplicate action owner if an existing progress/recovery mechanism already owns this condition.

## Scope

Primary investigation / likely implementation surface:

- `states/handlers/explore.py`
- `states/state_machine.py` only if progress/recovery ownership or transition/re-entry semantics are part of the defect
- `states/login_flow.py` / scene detection only to verify recovery handoff semantics; do not change correct dungeon recognition merely to hide the livelock
- `tests/test_behavior_dungeon_state_machine.py`
- `tests/test_dungeon_relaunch_recovery.py`
- any directly related progress/recovery contract needed to prove passive-vs-actionable semantics
- this task's tracked artifacts

## Known invariants

- `dungeons/leave.png` is valid evidence that the current scene is dungeon exploration; the observed scene recognition itself is not the primary failure.
- `dungeons/leave.png` must not be clicked as part of normal dungeon exploration recovery.
- Scene/anchor recognition must not be equated with successful gameplay progress.
- Detector/perception responsibilities must remain separate from input/action ownership.
- A state may remain `EXPLORING` across many ticks, but persistent passive evidence alone must not indefinitely starve an actionable progress path or falsely reset progress/stall accounting.
- Existing Treasure / Fight / Bless / GoDown / battle-result behavior must remain behavior-preserving unless new evidence proves a contract conflict.
- Recovery from login/relaunch into an already-active dungeon must converge onto the same valid exploration-progress semantics as normal dungeon entry.
- Do not weaken or disable the watchdog to conceal the defect.
- Do not change CV thresholds/templates unless evidence shows a separate perception defect.
- Do not add a second global watchdog/progress owner inside `ExploreHandler`.

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
3. `leave.png` continues to serve as valid dungeon-presence / scene evidence and must not itself cause an erroneous exit from dungeon state or be clicked as normal progress.
4. The final implementation identifies one authoritative owner for the next exploration-progress/recovery decision when only passive dungeon anchor evidence is present; no duplicate click owners or parallel progress loops are introduced.
5. Existing actionable dungeon events retain their priority and behavior: completion, confirm/continue, fight, treasure, skill, bless, go-down, and battle handoff continue to work.
6. Login/relaunch recovery into an already-active dungeon reaches the same progress-capable `EXPLORING` behavior as ordinary entry.
7. Progress/stall accounting distinguishes passive anchor observation from meaningful action/progress so repeated anchor matches cannot indefinitely mask a stall.
8. Existing `test_3_explore_handler_handles_leave_anchor` is updated so it no longer requires passive-anchor observation to reset progress/no-action accounting, while preserving the no-click invariant.
9. A new multi-tick regression covers `EXPLORING + persistent leave.png + no actionable event` and proves the system reaches the intended bounded progress/recovery behavior rather than an infinite passive loop.
10. Focused dungeon regression tests pass.
11. `git diff --check` passes.

## Resolved uncertainty

- `leave.png` is acting as passive dungeon-presence / floor anchor evidence in the current exploration path; the handler intentionally does not click it.
- The current common matched-item tail wrongly grants passive-anchor observation the same control-flow treatment as actionable dungeon work.
- The defect can occur outside login/relaunch recovery whenever `leave.png` is the only persistent match.
- Existing test coverage explicitly expects `leave.png` to reset `no_explore_match_count`, so one existing regression must be corrected rather than merely supplemented.
- `no_explore_match_count` currently mixes at least two semantics: "no matched exploration template" and "no actionable gameplay progress". Passive anchor presence demonstrates that these are not equivalent.

## Uncertainty to resolve before Final

- When valid dungeon-presence evidence persists but there is no actionable dungeon event, what existing component/mechanism is the authoritative owner of bounded local progress/recovery?
- Is the intended behavior to wait for a delayed dungeon event under an existing bounded timer, actively re-check/repair floor-transition state, perform a documented local recovery action, or hand off to an existing recovery owner?
- Which existing timestamp/counter/postcondition should represent this condition without creating a second watchdog or independent progress loop?
- Should `dungeons/leave.png` remain physically present in `explore_priorities` with special non-consuming semantics, or should passive anchors be represented outside the actionable priority list? The choice must preserve existing configuration/runtime contracts and avoid unnecessary scope expansion.

## Architecture review focus

Before Final SPEC, verify against `docs/architecture/project_arch_greenfield_lite_v1.md` that the solution preserves:

- perception vs action separation;
- one authoritative action owner;
- postcondition/progress semantics rather than "match == success";
- bounded recovery;
- behavior-preserving refactor constraints for already-verified dungeon flows.