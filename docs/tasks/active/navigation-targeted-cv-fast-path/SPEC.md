# navigation-targeted-cv-fast-path

Status: Final

## Goal

Unify lobby card navigation for these five modes:

- `stage`
- `domain`
- `dungeon`
- `lord`
- `demon_lord`

The task changes only the process used to:

1. reach the correct lobby mode;
2. localize the currently visible card position;
3. scroll toward the committed card target;
4. find the target card with CV.

Once the target card has been found and control is handed back to the existing mode-specific entry logic, this task stops.

## Explicit non-regression boundary

Do not change logic after the target card is selected/opened.

Examples that are explicitly out of scope:

- Stage: sub-stage scrolling/search after opening a main Stage card.
- Dungeon: existing target status/cooldown/locked checks, fight/start flow, dungeon entry, exploration, combat.
- Domain: start/explore behavior after selecting the Domain entry.
- Lord: cooldown OCR, start/fight behavior after selecting the Lord card.
- Demon Lord: stone insertion/selection, prepare modal, start/fight behavior after selecting the Demon Lord card.

The shared navigator may return a target match/position to the existing owner, but it must not take ownership of these downstream behaviors.

## Core behavioral model

All five modes must use the same card-navigation lifecycle.

```text
desired mode + desired card target
        |
        v
Is current Scene already the desired mode?
        |
   +----+----+
   | no      | yes
   v         v
navigation_table
switch mode
   |
   v
Scene proves target-mode postcondition
             |
             v
INITIAL LOCALIZATION
  1. match target card first
  2. if target found -> hand off immediately
  3. otherwise inspect this mode's ordered card catalog
     and establish visible index evidence
  4. if no usable card evidence -> reset-to-left fallback
             |
             v
derive direction from verified index relation
             |
             v
TARGET TRACKING
  match target card only
  -> found: hand off to existing mode-specific entry logic
  -> missed: common directional swipe, then target-only match again
             |
             v
bounded miss exhaustion
             |
             v
invalidate route knowledge and re-localize
             |
             v
if localization still cannot establish usable card evidence
-> reset-to-left fallback
```

## Scene/postcondition contract

Scene/current-frame visual evidence remains the sole authority for proving a lobby mode transition.

Examples:

```text
click Dungeon tab != Dungeon postcondition satisfied
navigation state == Dungeon target != Dungeon postcondition satisfied
previous Stage index == 7 != Dungeon current index == 7
```

Cross-mode transitions invalidate all retained card/index knowledge.

However, once:

1. the desired mode has been visually verified;
2. no mode-changing action has occurred;
3. the card-search session has not been invalidated;

steady-state card tracking must not re-run Stage/Domain/Dungeon/Lord/Demon-Lord active/inactive tab CV on every search frame.

During the target-tracking phase, the CV budget is exactly the committed target card template for that search observation.

Broader Scene/tab/card CV is re-enabled only when the tracking session is invalidated or bounded tracking misses are exhausted.

## Initial localization contract

The current behavior of immediately dragging to the leftmost/first card before checking the current viewport is not the desired default.

The required order is:

1. target mode is already Scene-confirmed;
2. match the committed target template first;
3. if the target is already visible, return FOUND immediately with no reset drag;
4. if the target is absent, perform one localization pass over the mode's ordered card catalog;
5. derive visible card index evidence from actual CV matches;
6. use the observed index relation to choose swipe direction;
7. only when localization cannot establish usable card evidence may the existing reset-to-left behavior be used as fallback.

This specifically prevents:

```text
target is already visible
-> blindly reset list to first card
-> scroll back toward target
```

## Ordered card index contract

All five modes need one normalized 1-based ordered card catalog:

```text
[(1, card_key, template), (2, card_key, template), ...]
```

The normalized catalog is navigation metadata only. It does not own cooldown, availability, combat, or downstream business semantics.

### Stage

Index authority must come from `BASE_STAGE_LEVELS` / `base_stage_levels` numeric level identity and each level's `entry` template.

Do not derive Stage semantic indices from raw `catalog.stage_templates` list positions because that list contains compatibility/alias templates such as multiple Level 2 templates.

Existing Stage config helpers may be extended/reused to expose this ordered navigation catalog.

### Dungeon

`DungeonCatalog` is already the 1-based index authority.

Reuse it rather than creating a second Dungeon index implementation.

### Domain

`config/defaults.toml` is already the canonical Domain existence authority.

`get_canonical_domain_mode_configs()` / `get_domain_mode_configs()` already enumerate canonical declared Domain configs and expose each `domain_entry_btn`.

This task must add/establish one explicit ordered Domain card helper for navigation.

The canonical order declared in repository defaults is the left-to-right Domain card order contract. Profile overrides may alter effective values but may not inject/reorder Domain identities.

If real UI order differs, canonical defaults order must be corrected; runtime heuristics must not invent a different order.

### Lord

The ordered `config["bosses"]` declaration is already implicitly treated as card order because the current Lord alignment uses the first declared boss as the first/leftmost card.

The shared catalog helper must formalize that existing ordering into 1-based navigation indices.

Availability/cooldown filtering must not change the catalog's physical indices.

### Demon Lord

The ordered `config["bosses"]` declaration is likewise the navigation card order.

The current implementation already uses the first declared boss as the first-card alignment anchor.

The shared catalog helper must expose all declared Demon Lord cards by stable 1-based index so future additional bosses automatically use the same scrolling algorithm.

## Localization result

Localization may observe more than one card in the same viewport.

A valid localization result should retain factual observed indices, for example:

```text
visible_indices = {2, 3, 4}
target_idx = 7
=> direction = RIGHT
```

or:

```text
visible_indices = {6, 7, 8}
target_idx = 2
=> direction = LEFT
```

Target matching must be attempted first so an already-visible target short-circuits before scanning unrelated card templates.

If the target is absent:

- `target_idx > max(visible_indices)` -> move toward higher indices;
- `target_idx < min(visible_indices)` -> move toward lower indices;
- target index lying inside the observed range while its own template did not match is contradictory localization evidence and must not trigger blind directional movement.

Contradictory evidence invalidates localization and enters bounded relocalization/fallback.

## Shared directional swipe contract

Stage, Domain, Dungeon, Lord and Demon Lord must use the same shared horizontal page-swipe primitives.

The default directional mechanics should come from `CardListNavigator`:

- target at higher index -> `swipe_left_page()`;
- target at lower index -> `swipe_right_page()`.

Do not retain separate Stage-only/Lord-only/Dungeon-only horizontal search algorithms when they represent the same card-list operation.

A swipe does not prove the new exact card index.

Therefore this is allowed:

```text
verified anchor 2
target 7
=> direction higher
=> swipe
=> only match target 7
```

This is forbidden:

```text
verified anchor 2
one swipe
=> assume current index is 3 or 4
```

The implementation may tune one common page-swipe amplitude if tests/UI evidence support it, but all five modes must consume the same primitive.

## Target-only tracking contract

After localization has established a direction:

```text
mode_verified = true
target_idx known
direction known
```

each steady-state search observation must:

1. match only the committed target card template;
2. if found, return the match to the existing mode owner;
3. if not found, perform the shared directional page swipe;
4. increment the shared target-miss/search-attempt state;
5. on the next eligible observation, match only the same target again.

No unrelated card templates, active/inactive mode tab templates, first-card anchors, door templates, start buttons, or other Scene templates may be matched inside this steady target-tracking branch.

The existing owner may resume its normal CV after target FOUND because card navigation ownership has ended.

## Bounded target-search definition

"Target not found for too long" is not defined by elapsed seconds in this task.

It is defined by completed target-only search observations after directional card-search progress.

A target miss means:

- the mode had already been verified;
- localization had established a search direction;
- the committed target template was matched on the stable search frame;
- the target was absent.

Use one shared deterministic miss/search bound for the common navigator.

The default bound is derived from the ordered catalog size:

```text
max_target_tracking_misses = number_of_cards_in_current_mode
```

On exhaustion:

1. do not declare the target impossible;
2. invalidate the current localization/direction;
3. re-run Scene verification and initial localization;
4. only use reset-to-left if useful card localization still cannot be established.

This is separate from existing reset-to-left retry counters.

## Reset-to-left contract

The existing `CardListNavigator.reset_to_left()` behavior must remain.

It changes role:

### Old common pattern

```text
enter card mode
-> reset to first card
-> then search target
```

### Required role

```text
enter/verify mode
-> target-first localization
-> use observed card indices if available
-> target tracking
-> relocalize if tracking exhausted
-> reset-to-left only when reliable localization cannot otherwise be established
```

Reset-to-left remains a bounded recovery primitive, never a successful localization by itself.

Its postcondition still requires visual evidence of the first card.

## Lobby mode routing through NavigationTable

The shared card algorithm starts only after the desired lobby mode is Scene-confirmed.

If current Scene is not the desired mode, switching among Stage/Domain/Dungeon/Lord/Demon-Lord must be owned by declarative navigation routing rather than each handler's legacy custom path.

### Survey-confirmed infrastructure gap

Current `navigation_table.py` does not yet provide target-aware cross-mode routing among the five lobby select scenes.

Current limitations:

- `NavigationTable.next_edge(scene, intent_id)` does not receive the desired target tab/mode;
- `SceneSnapshot` exposes `active_tabs` but no semantic click element for each target lobby tab;
- inactive target-tab matches found by Scene detection are not currently exposed as a navigation-table click element;
- `NavigationProgress.InFlightAction` already has `expected_tab`, but current postcondition handling does not use it to prove a generic expected-tab-active transition.

### Required routing result

The implementation must extend the existing navigation policy/table contract so that:

```text
current Scene = Stage
desired Tab = Dungeon
-> NavigationTable/NavigationIntentPolicy returns declarative switch-to-Dungeon action
-> executor clicks Scene-derived Dungeon tab evidence
-> in-flight action records expected_tab = Dungeon
-> later Scene evidence reports Dungeon active
-> postcondition succeeds
-> card localization begins
```

The same mechanism must support all pairwise transitions needed among the five scoped lobby modes and generic `LOBBY` where target-tab evidence exists.

The exact table representation may be a target-aware edge type or an extension of the existing edge resolver, but routing ownership must remain in `NavigationIntentPolicy` / `NavigationTable`.

Do not reintroduce tab-switch policy inside card navigation.

## Shared component boundary

There must be one shared implementation of the card-search algorithm consumed by all five modes.

The shared component owns only:

- ordered navigation card metadata;
- initial target-first localization;
- observed index set/anchor relation;
- direction selection;
- common page swipe;
- target-only tracking miss count;
- localization invalidation;
- reset-to-left fallback orchestration.

It must not own:

- which task/mode should run;
- cooldown eligibility;
- boss availability policy;
- battle/start behavior;
- sub-stage behavior;
- Domain exploration behavior;
- Demon Lord stones.

The implementation may extend `CardListNavigator` and add a narrowly scoped catalog/session helper, or add one dedicated shared lobby-card navigator. Do not duplicate the same lifecycle independently in five handlers.

## Mode-specific handoff

When the shared navigator returns FOUND, each existing owner resumes from its existing target-card action boundary.

### Stage

FOUND main Stage card -> existing Stage card click/entry path -> existing sub-stage logic unchanged.

### Domain

FOUND Domain entry -> existing Domain entry click -> existing start/explore logic unchanged.

### Dungeon

FOUND target Dungeon card -> existing target-specific cooldown/locked/unavailable checks -> existing click/fight/start path unchanged.

For greedy Dungeon, broader target selection may occur before a single target is committed. Once a concrete Dungeon target index is committed, shared card navigation applies.

### Lord

Existing availability/cooldown policy may decide which Lord is the committed target.

After a unique target boss is chosen, the shared navigator locates that boss.

FOUND -> existing cooldown OCR/click/start/battle logic unchanged.

Do not scan multiple available Lord templates on every scroll frame after one target has been committed.

### Demon Lord

Existing policy chooses the committed Demon Lord target.

The shared navigator localizes/scrolls to that target.

FOUND -> existing card click -> stone/prepare/start logic unchanged.

## Invalidation conditions

The shared card-search session is invalidated by:

- desired mode changes;
- committed card target changes;
- any cross-mode action;
- Scene/postcondition revalidation failure;
- bounded target-tracking miss exhaustion;
- contradictory localization evidence;
- handler/subflow reset;
- recovery/relaunch;
- target card FOUND and ownership handed off;
- leaving the card-selection surface for detail/preparation/battle/loading.

## Survey findings that constrain implementation

1. Dungeon already has `DungeonCatalog`; reuse it.
2. Stage has numeric `base_stage_levels`; use those as semantic indices, not raw `stage_templates` list positions.
3. Domain has canonical discovery helpers but lacks an explicit ordered navigation index helper.
4. Lord and Demon Lord already rely on declaration order to identify their first card, so that order can be formalized as navigation order.
5. Stage/Dungeon/Domain currently call `_handle_primary_card_alignment()` before normal target search; this is the reset-first behavior that must be removed from the normal path.
6. Lord likewise aligns to first card before its candidate scan.
7. Demon Lord already checks its selected target before reset-to-left, but does not yet share the common index/directional-search lifecycle.
8. Existing `NavigationTable` does not currently own target lobby-tab switching and must be extended before legacy mode-switch paths can be removed from this scope.
9. `NavigationProgress` already carries `expected_tab`, providing an existing place to bind visual tab-transition postconditions.

## Production scope

Expected production/reference surfaces include:

- `states/handlers/navigation.py`
- `states/handlers/lord_boss.py`
- `states/handlers/demon_lords.py`
- `states/navigation_intent.py`
- `states/navigation_progress.py`
- `states/navigation_routing.py`
- `states/navigation_table.py`
- `utils/scene_snapshot.py`
- `utils/scene_detector.py`
- `utils/card_navigator.py`
- `utils/dungeon_catalog.py`
- `utils/config_helper.py`
- `config.py`
- `config/defaults.toml`
- one narrowly scoped new shared catalog/navigation helper if needed

## Acceptance criteria

1. All five modes consume one shared card-navigation lifecycle.
2. Entering a verified mode no longer resets to the first card before checking whether the target is already visible.
3. Initial localization always matches the target first.
4. If target is visible initially, no horizontal drag occurs before mode-specific handoff.
5. If target is absent, localization derives real visible index evidence from the mode's ordered catalog.
6. Direction is based only on verified observed index relation to target index.
7. During steady tracking, exactly the committed target card template is matched per card-search observation.
8. Steady tracking does not re-run lobby active/inactive tab matching.
9. Cross-mode transitions invalidate card/index knowledge.
10. Cross-mode target-tab switching is resolved through `NavigationIntentPolicy` / `NavigationTable` using Scene-derived click evidence and a visual expected-tab postcondition.
11. Stage indices come from `base_stage_levels`, not raw alias-bearing `stage_templates` positions.
12. Dungeon index handling continues to use `DungeonCatalog`.
13. Domain has a tested ordered navigation catalog derived from canonical Domain declarations.
14. Lord and Demon Lord have tested ordered catalogs derived from declared boss order.
15. A target miss bound is shared and deterministic; default is current catalog size.
16. Exhausting target tracking triggers relocalization, not immediate blind reset or target failure.
17. Reset-to-left remains available and bounded only as localization fallback.
18. A reset is considered successful only after first-card visual evidence.
19. Stage post-main-card sub-stage logic is behaviorally unchanged.
20. Dungeon target status/fight/start/explore logic after FOUND is behaviorally unchanged.
21. Domain start/explore logic after FOUND is behaviorally unchanged.
22. Lord cooldown/start/fight logic after FOUND is behaviorally unchanged.
23. Demon Lord stone/prepare/start logic after FOUND is behaviorally unchanged.
24. Existing scheduler/task-priority/cooldown business semantics remain unchanged.
25. No `time.sleep()`, debounce, polling interval, or animation-wait optimization is part of this task.

## Deterministic tests required

Add focused tests for:

- target visible on initial localization -> zero reset drag;
- target visible on initial localization -> zero unrelated card scans after target hit;
- target absent + observed lower index -> common higher-index swipe;
- target absent + observed higher index -> common lower-index swipe;
- steady tracking matcher calls contain only target template;
- target-tracking miss bound -> relocalization;
- relocalization failure -> reset-to-left fallback;
- cross-mode switch clears card-search session;
- Stage/Dungeon/Domain/Lord/Demon-Lord catalog target-index resolution;
- Stage alias template does not shift semantic level indices;
- target-aware NavigationTable transitions among lobby modes;
- tab switch postcondition succeeds only after Scene reports expected tab active;
- mode-specific handoff preserves existing downstream logic.

Run existing nearby tests at minimum:

- `tests/test_behavior_navigation.py`
- `tests/test_behavior_navigation_intent.py`
- `tests/test_behavior_navigation_progress.py`
- `tests/test_behavior_navigation_scenarios.py`
- `tests/test_behavior_navigation_table.py`
- `tests/test_dungeon_swipe_unit.py`
- `tests/test_dungeon_catalog.py`
- `tests/test_domain_common_behavior.py`
- `tests/test_lord_boss_subflow.py`
- `tests/test_lord_boss_swipe.py`
- `tests/test_demon_lords_subflow.py`

## Non-goals

- Any post-card Stage sub-stage algorithm change.
- Dungeon exploration/combat algorithm changes.
- Dungeon cooldown/locked/unavailable business-rule changes.
- Domain exploration/start algorithm changes.
- Lord cooldown/OCR/start/battle changes.
- Demon Lord stone/preparation/start changes.
- Scheduler/task-priority changes.
- Greedy Dungeon target-selection policy redesign.
- General OpenCV/TemplateMatcher optimization.
- General SceneDetector redesign outside target-mode routing/postcondition support.
- Blind coordinate-based card selection.
- Swipe-history position inference.
- Cross-mode position priors.
- Timing/sleep/debounce/polling optimization.
