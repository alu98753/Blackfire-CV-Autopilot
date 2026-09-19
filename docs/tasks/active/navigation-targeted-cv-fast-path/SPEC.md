# navigation-targeted-cv-fast-path

Status: Final

## Goal

Reduce unnecessary CV/template matching during lobby navigation after the destination mode and target are known, without weakening visual postcondition verification.

The scoped lobby modes are:

- `stage`
- `domain`
- `dungeon`
- `lord`
- `demon_lord`

The task covers only:

1. cross-mode switching among these lobby modes; and
2. same-mode card/list navigation after the target mode has been visually confirmed.

This is a navigation-perception optimization, not a general CV optimization.

## Core contract

Broad CV is permitted for scene/postcondition verification and initial in-mode localization.

Once all of the following are true:

1. the target mode is confirmed by current-frame visual Scene evidence;
2. a same-mode anchor/current card has been positively observed where the mode actually requires card localization;
3. the navigation target is committed;

navigation may enter a target-tracking fast path and should not keep reclassifying unrelated card identities on every swipe.

Cross-mode transitions invalidate all retained card-position knowledge.

Action history, requested mode, navigation state, previous mode, or previous card position must never satisfy a Scene postcondition.

### Scene is the only postcondition authority

Example:

```text
Stage active
-> click Dungeon tab
-> Dungeon postcondition is NOT satisfied yet
-> only current-frame Scene evidence may confirm Dungeon active
```

Therefore:

```text
action issued != postcondition satisfied
navigation state != scene truth
requested mode != observed mode
previous card index != current-mode localization
```

## Architecture boundary

`NavigationIntentPolicy` remains the owner of intent/routing semantics.

Scene/perception remains evidence-producing.

This task must not create another routing policy inside CV code.

The fast path may retain only evidence-derived navigation facts such as:

```text
verified_mode = dungeon
last_verified_anchor = dungeon_2
committed_target = dungeon_7
search_direction = right
target_miss_count = 1
```

It must not manufacture an exact current position from swipe history:

```text
after one swipe -> current_position = dungeon_4
```

unless that card was actually observed.

## Actual mode ownership

The five modes do not share one implementation shape.

| Mode | Navigation/card owner | Observed structure |
|---|---|---|
| Stage | `NavigationHandler` | target template search plus bounded horizontal scroll; no full stage-card iteration in the target-search block |
| Domain | `NavigationHandler` | one configured domain entry target; no domain card-index list / horizontal target-index loop found |
| Dungeon | `NavigationHandler` | full configured dungeon-entry scan builds `visible_dungeons` before target selection/progress |
| Lord | `LordBossHandler` | first-card alignment, then scans available selected boss templates; swipes and repeats that candidate loop |
| Demon Lord | `DemonLordsHandler` | selected target template is already matched directly; first-card alignment is fallback/acquisition |

Implementation must respect these differences. Do not force a shared broad-scan/fast-path mechanism onto modes that do not have the same problem.

## In-scope case A — cross-mode switching

Representative transitions include:

```text
domain -> stage
domain -> dungeon
stage -> dungeon
dungeon -> stage
stage -> lord
stage -> demon_lord
lord -> stage
demon_lord -> stage
```

Required behavior:

1. Clicking a target tab/mode is only an action.
2. The target mode postcondition must be proven by current-frame visual evidence.
3. Position/card state from the previous mode must be invalidated before establishing target-mode route knowledge.
4. Expected-tab perception may remain narrow when the existing Scene contract allows it.
5. If expected-tab evidence is ambiguous or contradictory, existing broader relocalization behavior remains available.

Example:

```text
Stage 7 visible
-> click Dungeon
-> screen happens to show Dungeon 6/7/8
```

No Stage->Dungeon positional relationship may be inferred.

## In-scope case B — same-mode navigation

### Stage

Current code already matches the committed stage target directly rather than iterating every stage card in the main target-search block.

Required behavior:

- preserve Scene-confirmed Stage postcondition;
- preserve target-specific matching;
- do not add a broad Stage-card scan merely to implement this task;
- if same-mode anchor information is introduced or reused, it may guide direction but must remain evidence-derived;
- do not treat `horizontal_scroll_count` as proof of an exact Stage index;
- existing sub-stage candidate scanning is outside the primary top-level Stage-card optimization unless directly required to preserve behavior.

Stage should receive no architectural rewrite if the existing target-only behavior already satisfies the contract.

### Domain

Current Domain navigation has one configured `domain_entry_btn` per primary mode and no verified domain horizontal card-index loop.

Required behavior:

- preserve Scene-confirmed Domain postcondition;
- preserve direct target matching;
- do not invent a multi-card localization/tracking abstraction for Domain;
- only remove duplicate CV if the same semantic evidence is demonstrably matched more than once in the scoped navigation flow.

### Dungeon

Dungeon is the primary optimization target.

Current fixed-target flow can know the configured target index before progress, but currently scans all configured `dungeon_entries` to construct `visible_dungeons` on each eligible frame.

Required two-phase behavior for a committed fixed target:

#### Acquisition / relocalization

After Dungeon Scene/tab is visually confirmed:

- broad Dungeon-card matching is allowed to establish one same-mode anchor/current visible card;
- the target card may be detected during this acquisition;
- locked/unavailable/safety evidence required for correct target handling must remain available;
- no card-position state may be inherited from another mode.

#### Target tracking

Once a same-mode Dungeon anchor and committed target are known:

- derive only the search direction from the verified anchor-to-target relation;
- after each directional swipe, steady-state CV should match the committed target rather than all unrelated dungeon entry templates;
- do not estimate intermediate exact dungeon indices from swipe count/history;
- target found -> run the existing target-specific availability/status checks before click;
- target miss -> continue bounded directional search;
- bounded miss exhaustion, contradictory Scene evidence, loss of Dungeon postcondition, target change, or other invalidation -> return to acquisition/relocalization.

Greedy Dungeon behavior may retain broader perception while target selection itself still depends on comparing multiple eligible dungeons. Do not change greedy selection semantics. Target-only tracking is required only after a concrete target is committed and doing so preserves cooldown/locked semantics.

### Lord

Lord card navigation is owned by `LordBossHandler`.

Current behavior:

- visually confirms Lord tab;
- aligns to the first configured boss;
- obtains `avail_bosses`;
- scans available selected boss templates in order;
- if none matches, swipes left and repeats the candidate loop.

Required behavior:

- preserve Lord Scene/tab postcondition verification;
- preserve availability/cooldown semantics;
- once a specific boss target is committed, subsequent card-search frames should not scan unrelated available boss templates solely to rediscover the target;
- if the business rule still allows several bosses to be chosen interchangeably because no single target is committed, the candidate scan remains valid and is not to be removed;
- target-only tracking may begin only after one target is committed;
- cross-mode/tab loss or target change invalidates target-specific tracking;
- no exact intermediate boss position may be inferred from swipe history.

### Demon Lord

Demon Lord already matches one selected target template directly in `_step_select_boss_card()`.

Required behavior:

- preserve this target-only behavior;
- preserve visual subscene/tab confirmation;
- preserve first-card alignment as acquisition/fallback;
- do not introduce a broader candidate scan;
- only change this path if necessary to share invalidation/postcondition behavior required by this SPEC.

## Directional swipe contract

A larger swipe amplitude is allowed only if implementation evidence shows it reduces search steps without breaking the existing bounded recovery contract.

The implementation must not assume that one swipe equals one card/index.

Any enlarged swipe must remain:

- directional, derived from verified same-mode anchor vs committed target;
- bounded by an explicit retry/miss limit;
- followed by current-frame target verification;
- followed by relocalization/fallback when the bound is exhausted or evidence becomes contradictory.

The exact pixel/percentage amplitude and retry limit are implementation details and must be justified by existing UI geometry/tests rather than guessed in the SPEC.

## Invalidation conditions

Target-tracking state must be invalidated when any of the following occurs:

- target mode/tab Scene postcondition is lost;
- active mode changes;
- committed target changes;
- handler/subflow resets;
- bounded target misses are exhausted;
- contradictory visual evidence appears;
- recovery/relaunch path begins;
- battle/detail/preparation transition leaves the card-selection surface.

Mode-specific existing reset semantics must continue to apply.

## Scope

Primary production surfaces:

- `states/handlers/navigation.py`
- `states/handlers/lord_boss.py`
- `states/handlers/demon_lords.py`
- `utils/scene_detector.py`
- `utils/scene_types.py`
- `states/navigation_routing.py`
- `utils/card_navigator.py`
- `vision/matcher.py`

Configuration may be read to resolve target/template ordering but should not be redesigned.

## Acceptance criteria

1. Scene/current-frame visual evidence remains the only authority for Stage/Domain/Dungeon/Lord/Demon-Lord mode postconditions.
2. Cross-mode switching invalidates retained same-mode card/route knowledge.
3. No implementation infers exact card/index position from action/swipe history alone.
4. Fixed-target Dungeon:
   - initial localization may inspect multiple Dungeon cards;
   - after one same-mode anchor and target are known, post-swipe steady-state matching does not scan every unrelated `dungeon_entries` template;
   - target-specific cooldown/locked/unavailable checks remain correct;
   - bounded target misses return to relocalization/fallback.
5. Stage preserves its existing target-specific top-level stage search and does not gain an unnecessary full Stage-card scan.
6. Domain remains direct-target navigation unless concrete duplicate matching is removed; no synthetic multi-card abstraction is added.
7. Lord:
   - candidate scanning remains when no unique boss target is committed;
   - once a unique target is committed, subsequent search frames do not scan unrelated boss templates merely to find that target;
   - existing availability/cooldown semantics remain unchanged.
8. Demon Lord preserves its existing selected-target-only card match and acquisition fallback.
9. Any changed horizontal swipe behavior is directional, bounded, followed by target verification, and does not assume fixed index displacement.
10. Matcher/template scope is tested deterministically using fake/mock matcher call assertions or equivalent; wall-clock timing is not an acceptance criterion.
11. Existing recovery, relaunch, cooldown, locked-entry, battle-entry, and task-priority semantics remain behaviorally unchanged.
12. No production behavior outside the scoped lobby navigation/card-selection flows is changed.

## Focused tests

At minimum run:

- `tests/test_dungeon_swipe_unit.py`
- `tests/test_behavior_navigation.py`
- `tests/test_behavior_navigation_intent.py`
- `tests/test_behavior_navigation_scenarios.py`
- `tests/test_behavior_navigation_progress.py`
- `tests/test_lord_boss_subflow.py`
- `tests/test_lord_boss_swipe.py`
- `tests/test_demon_lords_subflow.py`

Add focused tests proving:

- fixed-target Dungeon target-only post-swipe matcher scope;
- Dungeon relocalization after bounded miss/invalidation;
- cross-mode position-state invalidation;
- Lord candidate-scan vs committed-target distinction;
- Demon Lord remains single-target rather than broadened;
- Stage does not regress from target-only matching into full-card scans.

## Non-goals

- Dungeon exploration/combat after entering the dungeon.
- Domain exploration after entering the domain.
- Demon Lord stone-selection logic.
- Lord/Demon Lord battle execution after card selection.
- Battle/result/collection/backpack/town-building/login flows.
- Scheduler/task-priority redesign.
- Dungeon greedy selection semantics redesign.
- Cooldown policy redesign.
- General SceneDetector optimization outside the scoped lobby-mode postcondition needs.
- General OpenCV/TemplateMatcher performance work.
- `time.sleep()`, debounce, animation-wait, polling-frequency, or timeout tuning.
- Blind fixed-coordinate navigation.
- Cross-mode position priors.
- Using navigation state or action history as Scene evidence.

## Evidence notes

Scout evidence established the Dungeon full-entry scan and existing expected-tab Scene fast path.

A bounded follow-up survey plus code spot-check established:

- Stage already uses target-specific top-level stage matching after alignment and does not iterate all Stage cards in that block.
- Domain has one configured domain entry target and no verified horizontal card-index loop.
- Lord card selection is owned by `LordBossHandler`, which scans the currently available selected boss set until a match.
- Demon Lord card selection is owned by `DemonLordsHandler`, which already matches the selected target template directly.
- Lord and Demon Lord therefore must not be modeled as copies of the Dungeon implementation.

## Remaining implementation uncertainty

- The smallest ownership surface for shared target-tracking metadata is intentionally not prescribed. Implementation may keep state local to each existing owner or introduce a narrowly scoped shared value object, but must not create a second routing policy.
- Exact Dungeon/Lord swipe amplitude and miss bounds are not prescribed; tests and existing UI contracts must justify them.
- Greedy Dungeon may legitimately require broader perception before a concrete target is committed.
