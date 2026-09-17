# Lord Boss Town Precondition Handoff

Status: Draft

## Goal

Prevent `lord_boss` from bypassing the canonical Town destination/precondition normalization when it is scheduled while another activity—especially dungeon exploration—still owns the current scene. `LORD_BOSS` must receive control only after the repository's canonical Town handoff/precondition contract is satisfied.

## Scope

- Integrate `lord_boss` with the centralized Town destination/precondition contract rather than the legacy immediate-dispatch path.
- Ensure a scheduler-selected `lord_boss` does not directly dispatch `LORD_BOSS` from a dungeon-owned scene.
- Preserve pending lord-boss runtime/activity configuration and intended boss selection across any Town-normalization handoff.
- Add focused regression coverage for dungeon-owned frames and the already-at-Town fast path.
- Correct any logging on the affected path that claims the Town precondition is established when it was not actually evaluated.

## Known invariants

- Lord-boss scheduler eligibility, priority, timing, and tier selection semantics remain unchanged.
- `DemonLordsHandler` remains responsible for lord-boss UI/combat behavior, not generic dungeon exit or generic navigation recovery.
- Existing dungeon frame-ownership semantics remain canonical: a valid `DUNGEON_EXPLORING` frame must not be silently stolen by a Town-only handler.
- `LORD_BOSS` must not be entered merely because `lord_boss` was selected; the physical/destination precondition must be satisfied first.
- Already-at-Town lord-boss behavior should remain behavior-compatible apart from the required precondition plumbing.
- No new CV templates or scene heuristics are introduced unless Scout evidence proves they are required.
- This is a targeted bug fix; unrelated verified behavior should remain unchanged.

## Non-goals

- Redesign the activity scheduler or change lord-boss priority.
- Redesign dungeon exploration, dungeon recovery, or dungeon completion semantics.
- Make `DemonLordsHandler` own generic dungeon exit/navigation.
- Change boss selection, combat, reward, cooldown, or availability behavior.
- Migrate every remaining legacy Town subflow unless Scout proves a shared atomic contract requires a paired change.

## Provisional acceptance criteria

1. If `lord_boss` is selected while the current physical scene is dungeon exploration, the FSM does not directly transition to `LORD_BOSS`.
2. The selected `lord_boss` enters or remains behind the canonical Town-precondition/handoff path, and `LORD_BOSS` is dispatched only after the required Town evidence/precondition succeeds.
3. A dungeon frame is not handed to the lord-boss handler as an unowned `UNKNOWN` scene in a way that creates an actionless livelock.
4. Pending lord-boss activity configuration survives the precondition handoff so the intended boss/tier context remains available when `LORD_BOSS` is eventually dispatched.
5. When Town is already established, `lord_boss` dispatch remains prompt and behavior-compatible.
6. Focused deterministic tests lock the registration/precondition regression and any corrected log semantics.
7. If the canonical contract intentionally waits for dungeon ownership to yield rather than forcing an immediate exit, tests document and preserve that ownership behavior and the subsequent transfer to Town normalization.

## Uncertainty / Scout questions

- While dungeon exploration actively owns the frame, is the canonical safe behavior to wait for/yield from dungeon ownership, or is there already an explicit safe dungeon-exit handoff that Town normalization should invoke?
- What is the minimum `TownSubflowSpec`/registry configuration required for `lord_boss`, including any activity-config snapshot or destination-state metadata?
- Are any other legacy Town subflows omitted from the same destination-contract rollout in a way that must be changed atomically with `lord_boss`, or can this remain strictly targeted?
- Which existing focused tests best express the Town-precondition contract and dungeon frame-ownership invariant without broad regression expansion?

## Initial debug evidence

- Runtime scheduling succeeds: `lord_boss` is selected and the FSM transitions from `UNKNOWN` to `LORD_BOSS`.
- `lord_boss` is absent from the centralized `TOWN_SUBFLOW_SPECS` registry, so the state machine preserves its legacy immediate-dispatch behavior instead of running canonical `REACH_TOWN` normalization.
- The immediate-dispatch helper logs that the Town precondition is established even on this legacy path, making the runtime trace misleading.
- The lord-boss handler does not own dungeon navigation; a dungeon screen falls outside its recognized scenes and cannot make progress there.
- Existing Town normalization explicitly respects dungeon exploration ownership, so the fix belongs at the precondition/handoff boundary rather than by teaching the lord-boss handler to escape dungeons ad hoc.
