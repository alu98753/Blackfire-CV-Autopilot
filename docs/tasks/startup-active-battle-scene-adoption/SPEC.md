# startup-active-battle-scene-adoption

Status: Final

## Goal

When the process starts while the game is already inside a visually verifiable active battle session, global scene acquisition must recognize that battle and bootstrap/adopt the existing battle session without requiring bot-owned navigation history.

## Problem Statement

Current cold-start behavior can enter a recovery loop where navigation/full relocalization reports no candidates and IntentRouting repeatedly receives `scene=unknown` with `reason=scene_evidence_insufficient`, even though the game is already inside an active battle. The responsibility gap is upstream of IntentRouting: scene/session acquisition must be able to recover an already-existing battle independently of how the bot arrived there.

A secondary signal observed in the same failure is that a current intent such as `collect_diamond` may coexist with stale navigation context such as `expected_tab=dungeon`. This task must determine whether that stale navigation progress is causally blocking global relocalization. It is only in scope if required to restore correct active-battle acquisition.

## Scope

- Cold-start/global scene acquisition when the game is already in an active battle.
- Full relocalization participation of existing active-battle visual/session evidence.
- Bootstrap/adoption of an already-running battle session into the state expected by downstream battle logic.
- Handoff from recovered battle scene/session into the existing intent-routing and battle lifecycle.
- Causal investigation of stale `expected_tab` / navigation progress only where it prevents correct global relocalization or battle adoption.
- Focused deterministic regression tests for the new recovery path and fail-closed boundaries.

## Known Invariants

- Scene truth is derived from visual/session evidence. It must never be inferred from scheduler priority, current intent, requested destination, or `expected_tab`.
- `IntentRouting` is allowed to fail closed when scene evidence is insufficient. This task must supply valid upstream evidence rather than weaken `scene_evidence_insufficient` behavior.
- Full/global relocalization remains conservative when evidence is absent, ambiguous, or conflicting.
- A battle entered through the existing normal bot-owned navigation path must continue to behave as before.
- Existing scheduler and priority policy, including daily-dungeon priority relative to indefinitely runnable domain/stage work, is unchanged.
- Session/state ownership must remain explicit: recognition of a battle scene and ownership/adoption of a battle session may cooperate, but neither may depend on fabricated navigation history.
- Behavior outside the directly required cold-start recovery path is preserved.

## Non-goals

- Redesigning scheduler or intent-selection policy.
- Changing dungeon/domain/stage priority semantics.
- Making IntentRouting guess a scene from intent.
- Treating `UNKNOWN + dungeon intent` (or any equivalent intent heuristic) as proof of battle.
- Broad navigation-progress cleanup if stale progress is unrelated to this failure.
- Broad CV threshold/template tuning unrelated to already-available active-battle evidence.
- Broad battle lifecycle/state-machine refactoring.
- Replacing or weakening conservative ambiguity/conflict handling.

## Required Responsibility Boundary

The intended flow is:

`startup / global acquisition -> visual/session scene evidence -> active-battle recognition -> existing-session bootstrap/adoption -> existing intent routing / battle lifecycle`

Intent may consume the resulting scene, but intent must not manufacture it.

If an existing battle detector/evidence provider already exists, prefer wiring/reusing it in the global acquisition path rather than adding a parallel intent-specific detector.

If the existing battle lifecycle already exposes a suitable bootstrap/adoption operation, reuse it. If not, add the narrowest explicit adoption boundary necessary instead of simulating the normal navigation path.

## Acceptance Criteria

1. Starting the process while the game is already inside a visually recognizable active battle no longer loops indefinitely at `scene=unknown` solely because the bot did not navigate into that battle itself.
2. Active-battle recognition during cold start/global relocalization is based on visual/session evidence and works independently of current intent and `expected_tab`.
3. Once active battle is recognized, the pre-existing battle session is bootstrap/adopted into the state owned by the existing downstream battle lifecycle; production code must not fabricate prior navigation actions to achieve this.
4. Existing IntentRouting consumes the recovered battle scene/session through its normal interface. Its fail-closed `scene_evidence_insufficient` semantics remain intact for genuinely insufficient evidence.
5. Cold start in a recognizable lobby/non-battle scene continues to resolve normally and is not falsely adopted as battle.
6. Ambiguous or insufficient visual evidence remains `unknown`/fail-closed rather than being inferred from intent.
7. A dungeon-related intent, stale `expected_tab=dungeon`, or equivalent scheduler/navigation state without battle visual evidence must not cause battle adoption.
8. Existing bot-navigated battle behavior is preserved.
9. Focused tests cover at minimum: cold-start active battle recognition; active-session adoption/handoff; cold-start lobby/non-battle behavior; ambiguous/unknown evidence; and intent/navigation-state presence without battle evidence.
10. If stale `expected_tab` / navigation progress is proven causal, fix only the ownership/invalidation behavior required by this failure and cover it with a regression test. If it is unrelated, leave production behavior unchanged and report it as a separate follow-up candidate.

## Implementation Guidance

- First trace the current source of battle-scene evidence and the current FullRelocalize/global acquisition candidate set.
- Trace which component currently creates/owns battle-session state after a normal navigation-driven battle entry.
- Reuse those contracts where possible; avoid parallel scene truth or duplicate battle ownership.
- Prefer an explicit cold-start/session-adoption transition over pretending that navigation just succeeded.
- Preserve observability sufficient to distinguish: recognized/adopted active battle, insufficient evidence, and rejected/ambiguous evidence.

## Uncertainty To Resolve During Implementation

- Which existing detector/evidence provider is the canonical source for active-battle recognition and whether FullRelocalize currently omits it.
- Whether the battle lifecycle already has an explicit session bootstrap/adoption API or currently assumes all battle sessions were initiated by bot-owned navigation.
- Whether stale `expected_tab` / navigation progress is a cause of the failure or only a coincident diagnostic signal.

These uncertainties may affect exact implementation shape, but they do not change the responsibility boundary or acceptance criteria above. If resolving them would require a materially broader architecture rewrite, stop and report the boundary instead of silently expanding this task.