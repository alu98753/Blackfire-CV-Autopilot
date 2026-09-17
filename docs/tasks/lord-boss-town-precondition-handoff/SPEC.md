# Lord Boss Town Precondition Handoff

Status: Final

## Goal

Prevent `lord_boss` from bypassing the canonical Town destination/precondition contract. If lord-boss eligibility appears while dungeon exploration owns the current workflow, the boss intent may remain pending, but `LORD_BOSS` must not receive control until the dungeon flow finishes, returns to Lobby, the existing route returns the character to Town, and Town is physically verified/readiness-established.

## Scope

- Register/integrate `lord_boss` with the canonical Town subflow precondition contract instead of the legacy immediate-dispatch path.
- Preserve a selected/pending lord-boss intent while an already-committed dungeon workflow owns `DUNGEON_EXPLORING`, `BATTLE`, `RESULT`, `LOADING`, or its completion/return path.
- After dungeon completion naturally returns to Lobby, allow the existing navigation/normalization path to return from Lobby to Town.
- Dispatch `LORD_BOSS` only after canonical Town physical verification and interaction readiness succeed.
- Preserve lord-boss target/config context across this wait/handoff.
- Correct affected logging so it never claims the Town precondition is established before it has actually been verified.
- Add focused deterministic regression tests for dungeon ownership, Lobby-to-Town handoff, already-at-Town dispatch, and boss-context preservation.

## Known invariants

- Lord-boss scheduler eligibility, priority, timing, tier selection, and boss-selection semantics remain unchanged.
- A newly eligible `lord_boss` is a pending business intent; it does not preempt an already committed dungeon flow.
- `DUNGEON_EXPLORING` remains owned by the dungeon workflow until that workflow completes naturally. This task must not force an early dungeon exit merely because a lord boss becomes available.
- Dungeon completion is expected to return to Lobby. Existing navigation/REACH_TOWN behavior owns the subsequent Lobby -> Town normalization.
- `DemonLordsHandler` / lord-boss business handlers remain responsible for boss UI/combat behavior, not dungeon completion, generic dungeon exit, or generic navigation recovery.
- `ReachTownNormalizationController` remains destination-scoped and must not consume, complete, defer, or replace the lord-boss business intent.
- `TownSubflowPreconditionController` already treats `BATTLE`, `RESULT`, `LOADING`, `DUNGEON_EXPLORING`, and committed target states as workflow-owned frames; this ownership boundary is preserved.
- `LORD_BOSS` must not be entered merely because `lord_boss` was selected. Town physical verification/readiness is a dispatch precondition.
- Already-at-Town lord-boss behavior remains prompt and behavior-compatible apart from using the canonical precondition plumbing.
- No new CV templates, dungeon heuristics, or forced-exit behavior are introduced.
- Behavior-preserving changes are preferred outside the identified bug.

## Non-goals

- Change lord-boss priority or scheduler eligibility.
- Preempt, cancel, shorten, or redesign dungeon exploration.
- Add a special `lord_boss -> leave dungeon` escape path.
- Make the lord-boss handler own Lobby/Town navigation.
- Redesign `ReachTownNormalizationController` or the navigation graph unless a minimal compatibility correction is strictly required by tests.
- Change boss combat, rewards, cooldowns, stamina semantics, or availability bookkeeping.
- Migrate unrelated legacy Town subflows as part of this task.
- Add new CV assets/templates.

## Required behavior

### A. Boss becomes eligible during dungeon ownership

1. Scheduler may select/retain `lord_boss` as pending work.
2. Current dungeon workflow continues to own the frame and state lifecycle.
3. FSM MUST NOT transition from dungeon-owned state/scene directly to `LORD_BOSS`.
4. No lord-boss handler is invoked against the dungeon scene.
5. Dungeon exploration/battle/result/completion proceeds using existing behavior.

### B. Dungeon completes

1. Existing dungeon flow completes naturally and returns to Lobby.
2. Pending `lord_boss` remains intact.
3. Existing canonical navigation/REACH_TOWN path handles Lobby -> Town.
4. `lord_boss` business dispatch remains blocked while Town is not physically verified and interaction-ready.

### C. Town established

1. Once `SceneId.TOWN` and canonical Town readiness are established, the pending `lord_boss` may dispatch.
2. The intended lord-boss target/tier/config remains the one selected by existing scheduler semantics.
3. FSM transitions into `LORD_BOSS` only at this point.

### D. Already in Town

If `lord_boss` is selected while Town is already physically verified/readiness-established, canonical precondition handling may dispatch it immediately without an unnecessary detour.

## Acceptance criteria

1. `lord_boss` no longer uses a legacy immediate-dispatch path that can bypass canonical Town verification.
2. When `lord_boss` becomes pending during `DUNGEON_EXPLORING`, the dungeon workflow continues and `current_state` does not become `LORD_BOSS` because of scheduler selection alone.
3. The task introduces no forced dungeon exit for lord-boss availability.
4. After natural dungeon completion returns to Lobby, the existing route can normalize Lobby -> Town while preserving pending lord-boss intent.
5. `LORD_BOSS` dispatch occurs only after canonical Town location/readiness verification succeeds.
6. Pending lord-boss target/config survives dungeon ownership and Town normalization without being overwritten by temporary navigation configuration.
7. Already-at-Town dispatch remains prompt.
8. Runtime logging distinguishes `lord_boss selected/pending`, `Town normalization`, and actual `Town precondition satisfied -> LORD_BOSS dispatch`; no false precondition-success log remains on an unverified path.
9. Focused deterministic tests cover at minimum:
   - `lord_boss` is covered by the canonical Town subflow registry/contract;
   - dungeon-owned frame does not dispatch `LORD_BOSS`;
   - pending boss intent survives dungeon completion/Lobby handoff;
   - Lobby is normalized toward Town before dispatch;
   - verified/readiness-ready Town dispatches `LORD_BOSS`;
   - already-at-Town fast path;
   - selected lord-boss target/config is preserved.
10. Existing focused Town-subflow/navigation and dungeon behavior tests remain passing.

## Implementation boundary

The expected smallest architectural fix is at the Town-subflow registration/dispatch boundary. Prefer making `lord_boss` a first-class consumer of the existing Town precondition mechanism (with Town dispatch semantics) over adding boss-specific navigation or dungeon logic. Changes to `states/state_machine.py` should be limited to eliminating/guarding the bypass and preserving context/log semantics required by the contract. `states/town_subflow_navigation.py` should not need new dungeon behavior because it already yields committed dungeon-owned frames.

## Survey evidence

- `TOWN_SUBFLOW_SPECS` currently registers chest, hero draw, blood altar/sacrifice, bulletin board, jewelry workshop, and bag tidy, but not `lord_boss`; `spec_for()` otherwise defaults unknown flows to `dispatch_on_town=True`.
- `TownSubflowPreconditionController` explicitly skips handling while a committed workflow owns `BATTLE`, `LOADING`, `RESULT`, `DUNGEON_EXPLORING`, `POPUP_RECOVERY`, or the target subflow state. Therefore the existing architecture already expresses the required non-preemption rule.
- The same controller runs `ReachTownNormalizationController` before business dispatch and only executes `DISPATCH_TOWN_SUBFLOW` after normalization returns `ARRIVED`.
- `ReachTownNormalizationController` is explicitly destination-scoped to REACH_TOWN and isolates physical normalization failure from business-intent mutation.
- `GameStateMachine.ensure_explore_config()` already documents the broader precondition invariant: when the body is physically in a dungeon while a non-dungeon target intent exists, the target intent is latched and ExploreHandler owns the prerequisite dungeon path instead of dispatching the target handler.
- `GameStateMachine.TOWN_SUBFLOW_CONFIG_MAP` already maps `STATE_LORD_BOSS` to `lord_boss`, so boss runtime configuration synchronization exists once dispatch legitimately occurs.

## Verification

This task intentionally skips the formal Scout/Gate workflow by user request. Implementation should still run focused deterministic tests declared in `task.json`, followed by ChatGPT semantic/architecture review from GitHub before merge.
