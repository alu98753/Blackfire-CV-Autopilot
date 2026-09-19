# navigation-targeted-cv-fast-path

Status: Final

## Current implementation checkpoint (authoritative handoff)

This section is the progress SSOT for context reconstruction. The historical phase sections below retain the original Final contract and rationale; they are not evidence that completed phases are still pending.

Last reviewed production anchor before this checkpoint: `87ff4eb8d588ccacab1368301d576a5d6919a7c6`.

### Completed

- **Phases 0–9: complete.** Declarative five-tab routing, ordered catalogs, `SharedCardNavigator`, Stage/Domain/Demon Lord/fixed-Dungeon/Lord migrations, and verified-session target-only CV are implemented and reviewed.
- **Phase 10A: complete.** Dead-responsibility survey established that cleanup units are responsibilities, not whole functions. See `reviews/phase10a-dead-responsibility-survey.md`.
- **Phase 10B-1: complete.** Generic `navigation_path` no longer owns canonical normal Stage/Dungeon/Domain lobby-tab clicks; declarative routing is the normal owner.
- **Phase 10B-2: complete survey/correction.** Canonical fixed-target Dungeon horizontal search is already fully deduplicated; remaining `swipe_towards_target()` ownership is greedy/compatibility, not canonical fixed search. See `reviews/phase10b2-fixed-dungeon-responsibility-survey.md`.
- **Phase 10B-3: complete.** Dungeon shared fixed-target resolution and legacy compatibility resolution are explicit separate owners with their historical precedence/validation semantics preserved.
- **Phase 10B-4: complete.** After canonical fixed Dungeon `FOUND`, the shared committed target index flows directly into target-only rescan/status/click; the canonical path no longer re-enters the legacy compatibility resolver.

### Remaining Phase 10 work

Recommended order for a fresh conversation:

1. **Lord legacy reset/search/swipe cleanup.** Survey current `has_reset_to_left`, first-card alignment, candidate scan, and direct swipe reachability. Remove only physical-navigation responsibilities proven replaced by shared navigation; preserve availability selection, cooldown OCR, bookkeeping, click/start/fight.
2. **Stage/Domain legacy main-card fallback audit.** Re-check whether any canonical normal-path reset-first alignment or horizontal search remains reachable. Preserve Stage sub-stage flow and Domain entry/start/explore. Compatibility/recovery paths are not automatically dead.
3. **Cooldown/mix fallback tab-routing cleanup.** In `_switch_to_stage_or_back()` and nearby mix/daily fallback code, separate direct tab-click responsibilities already owned by declarative routing from live cooldown, scheduler, collect-only, stamina-retreat, and fallback policy. Do not delete the function as a unit.
4. **Demon Lord incomplete-catalog fallback decision.** The legacy fallback remains KEEP until a repository-level contract proves supported configs always provide a complete canonical Demon Lord catalog, or characterization proves a narrower removable slice.
5. **Final Phase 10 acceptance review.** Re-run focused tests and verify: no supported normal-path lobby switch bypasses declarative routing; no scoped mode owns a second independent horizontal card-search algorithm; no supported normal-path card search resets left before target-first localization; only proven-dead responsibilities were removed.

### Explicit KEEP boundaries while finishing Phase 10

- Greedy Dungeon broad scan/priority/eligibility/cooldown/locked-unavailable selection.
- Dungeon post-FOUND cooldown/status/OCR/click/fight/start/explore behavior.
- Bounded reset-left recovery when localization cannot establish useful evidence.
- Stage sub-stage behavior.
- Domain downstream start/explore behavior.
- Lord availability/cooldown business policy and downstream combat behavior.
- Demon Lord stone/prepare/start behavior and incomplete-catalog compatibility until proven removable.
- Legacy/non-canonical compatibility behavior unless characterization proves it dead.

### Known verification context

The recent Dungeon-focused Phase 10B-4 run reported **94 tests, 90 passed, 4 known pre-existing branch failures**. This is a local focused baseline, not a substitute for the final task-wide gate.

### Out-of-scope future work

External/manual Scene drift during verified TRACK and concurrent Scene validation / generation-aware guarded physical-action commit are **not Phase 10 work**. They are tracked separately at:

`docs/tasks/todos/concurrent-scene-validation-action-commit.md`

Do not reopen Phase 9 or pull that future architecture into this cleanup task.

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

### Historical survey gap — resolved in Phase 1

The original survey found that `navigation_table.py` lacked target-aware cross-mode routing. That gap is resolved.

Current implementation provides:

- semantic Scene-derived clickable elements for all five scoped lobby tabs;
- target-aware declarative lobby-tab edges through `NavigationIntentPolicy` / `NavigationTable`;
- `SWITCH_LOBBY_TAB` with `expected_tab`;
- `NavigationProgress` postcondition handling that waits for later current-frame evidence that the expected tab is active;
- normal supported lobby-tab switching ownership in the declarative route rather than the generic `navigation_path` loop.

### Routing contract (implemented)

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

## Original survey findings and current resolution

1. Dungeon index authority remains `DungeonCatalog`.
2. Stage navigation indices are derived from numeric `base_stage_levels`, not alias-bearing raw `stage_templates` positions.
3. An explicit ordered Domain navigation catalog now exists and uses canonical repository declaration order.
4. Lord and Demon Lord declared boss order is formalized as physical navigation order; availability filtering does not renumber it.
5. Canonical Stage, Domain, fixed Dungeon, Lord, and Demon Lord navigation consume the shared card-navigation lifecycle.
6. Canonical fixed-target Dungeon horizontal search is already deduplicated. Do not remove greedy/compatibility `swipe_towards_target()` merely to force cleanup.
7. Dungeon shared target resolution and legacy compatibility resolution intentionally remain distinct; Phase 10B-3 made this ownership explicit without normalizing historical semantics.
8. Canonical fixed Dungeon `FOUND` now carries shared target identity into status/click handoff without re-entering the legacy resolver.
9. Remaining cleanup evidence is concentrated in Lord legacy physical-navigation slices, Stage/Domain compatibility/fallback leftovers, cooldown/mix direct tab-click slices, and Demon Lord incomplete-catalog compatibility.
10. The original NavigationTable target-tab routing gap is resolved; `expected_tab` is part of the implemented visual postcondition contract.

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


## Required phased migration order

> **Progress note:** Phases 0–9 are complete. The phase descriptions below are retained as the original Final migration contract and regression boundary. Phase 10 is partially complete as recorded in the authoritative checkpoint at the top of this SPEC.


Implementation MUST proceed in the following order. A later phase must not begin until the previous phase has focused test evidence for its exit criteria. Do not collapse several phases into one rewrite merely because the final architecture is already known.

### Phase 0 — Baseline and regression lock

Purpose:
- Freeze current verified behavior before routing/card-navigation changes.
- Make downstream ownership boundaries observable in tests.

Required work:
- Run current focused navigation/card-selection tests.
- Add characterization tests only where an upcoming phase otherwise has no regression boundary.
- Record the current owner boundary for lobby-mode routing, main-card selection, and post-card behavior.

Must not change:
- production navigation behavior;
- CV scope;
- swipe geometry;
- reset-to-left behavior;
- downstream Stage/Dungeon/Domain/Lord/Demon-Lord logic.

Exit criteria:
- focused tests are green or pre-existing failures are explicitly documented;
- tests can detect accidental changes to Stage sub-stage navigation, Dungeon status/fight/start handoff, Domain start/explore handoff, Lord cooldown/start/fight handoff, and Demon Lord stone/prepare/start handoff.

### Phase 1 — Declarative lobby mode switching

Purpose:
- Move only the responsibility for switching among Stage, Domain, Dungeon, Lord, and Demon Lord into the declarative routing layer.
- Do not change card localization or scrolling yet.

Required work:
- Expose semantic clickable elements for all five lobby tabs.
- Make NavigationIntentPolicy / NavigationTable target-aware.
- Add an explicit switch-tab action/postcondition contract.
- Bind the in-flight action to expected_tab.
- Require later current-frame Scene evidence showing expected_tab active before the switch succeeds.

Compatibility rule:
- Keep legacy tab-switch mechanisms physically present as bounded fallback during this phase.
- Do not delete generic navigation_path tab clicking, mix-specific Stage/Dungeon switching, or _switch_to_stage_or_back() yet.
- Tests must nevertheless prove that supported normal-path transitions use the new declarative route first.

Must not change:
- main-card search;
- reset-first behavior;
- card catalogs;
- card swipe logic;
- Scene CV suppression;
- post-card behavior.

Exit criteria:
- representative transitions Stage↔Dungeon, Stage↔Domain, Stage↔Lord, Stage↔Demon Lord, plus generic Lobby→target tab are resolved declaratively;
- clicking the target tab alone does not satisfy the postcondition;
- transition succeeds only after Scene reports expected_tab active.

### Phase 2 — Unified ordered card catalogs

Purpose:
- Establish one factual indexing contract before changing any scrolling.

Required output:
- Every scoped mode exposes stable 1-based navigation metadata equivalent to [(index, card_key, template), ...].
- This metadata represents physical card order only.

Authority by mode:
- Stage: derive from base_stage_levels numeric level identity and canonical entry. Do not use raw stage_templates positions because aliases can shift positions.
- Dungeon: reuse DungeonCatalog.
- Domain: derive from canonical repository Domain declarations and each domain_entry_btn. Canonical declaration order becomes left-to-right navigation order.
- Lord: formalize existing bosses declaration order as physical card order.
- Demon Lord: formalize existing bosses declaration order as physical card order.

Must not change:
- tab routing behavior;
- card CV;
- scrolling;
- reset-to-left;
- target eligibility;
- post-card behavior.

Exit criteria:
- all five modes resolve stable target index/template pairs;
- Stage aliases do not alter semantic stage indices;
- Domain additions automatically receive indices from canonical order;
- Lord/Demon Lord availability filtering never renumbers physical positions;
- Dungeon remains owned by DungeonCatalog.

### Phase 3 — Shared card navigator in isolation

Purpose:
- Implement and test the shared card-search state machine before attaching it to production handlers.

Shared responsibilities:
- target-first localization;
- one ordered-catalog localization pass;
- visible index evidence;
- direction derivation;
- common page swipe request;
- target-only tracking state;
- miss counting;
- relocalization;
- reset-to-left fallback orchestration.

Required semantics:
- FOUND;
- localized target is to higher indices;
- localized target is to lower indices;
- TRACKING;
- RELOCALIZE;
- NEED_RESET_LEFT;
- CONTRADICTORY.

Required localization order:
1. Match committed target first.
2. If target visible, return FOUND.
3. Otherwise scan the ordered catalog once.
4. Build visible_indices from actual CV observations.
5. Derive direction from target_idx relative to observed indices.
6. If no usable evidence exists, request reset-left fallback.

Tracking rule:
- Once direction exists, each search observation matches only the committed target.
- Miss → common directional swipe → increment miss counter.
- No exact post-swipe index may be inferred.

Miss bound:
- Default maximum target-tracking misses equals current catalog size.
- Exhaustion invalidates localization and requests relocalization.
- It must not immediately declare the target impossible or jump directly to reset-left.

Must not change:
- no production handler is migrated in this phase.

Exit criteria:
- initially visible target produces FOUND with zero reset/swipe;
- lower visible indices produce higher-index direction;
- higher visible indices produce lower-index direction;
- contradictory observed range causes no blind swipe;
- tracking matches target only;
- miss exhaustion causes relocalization;
- failed localization may request reset-left;
- swipe history never creates a synthetic exact index.

### Phase 4 — Migrate Stage main-card navigation

Purpose:
- Use Stage as the first production consumer because its sub-stage logic gives a clean handoff boundary.

Required work:
- Replace only Stage main-card localization/scroll/search with the shared navigator.
- Flow becomes: Stage Scene confirmed → target Stage known → target-first localization → common directional navigation → FOUND → existing Stage card click/entry path.
- Existing sub-stage behavior remains untouched.
- Remove reset-first behavior from the Stage normal path.

Temporary safety rule:
- Do not suppress recurring Stage Scene/tab verification yet. Keep it as a safety net during integration.

Must not change:
- sub-stage scrolling;
- sub-stage candidate scanning;
- Stage post-card start/fight/result behavior;
- general Scene CV policy.

Exit criteria:
- visible target causes no reset drag;
- both navigation directions use the shared swipe primitive;
- shared navigator releases ownership at FOUND;
- all Stage sub-stage tests remain unchanged.

### Phase 5 — Migrate Domain main-card navigation

Purpose:
- Prove the common algorithm works for a catalog expected to grow.

Required work:
- Use the ordered Domain catalog from Phase 2.
- Apply target-first localization, real-index direction, shared swipe, and target tracking.
- Do not special-case Domain because the current catalog is small.

Temporary safety rule:
- Keep recurring Domain Scene/tab verification enabled.

Must not change:
- Domain start behavior;
- Domain explore transition;
- Domain strategy selection;
- treasure/explore logic;
- Domain scheduler policy.

Exit criteria:
- visible Domain target short-circuits with no reset;
- unseen Domain target uses catalog-derived direction;
- adding another canonical Domain requires no new navigation branch;
- existing Domain start/explore tests remain unchanged.

### Phase 6 — Migrate Demon Lord card navigation

Purpose:
- Convert Demon Lord from target-first + reset fallback to target-first + localization + directional tracking.

Required work:
- Keep current target-first lookup.
- On miss, localize visible Demon Lord cards, derive direction, use common swipe, then target-only tracking.
- Reset-left becomes localization fallback only.

Temporary safety rule:
- Keep existing Demon Lord subscene classification active.

Must not change:
- target eligibility;
- card click behavior after FOUND;
- stone selection/insertion;
- prepare modal;
- start/fight/result behavior.

Exit criteria:
- visible target causes no reset;
- absent target uses index-directed common swipe;
- post-FOUND stone/preparation tests remain unchanged.

### Phase 7 — Migrate fixed-target Dungeon navigation

Purpose:
- Remove the highest-cost repeated all-entry scan only after the shared navigator is already proven in simpler modes.

Required work:
- For a concrete committed Dungeon target: Scene confirmed → target-first localization → at most one catalog localization scan if target absent → direction → target-only tracking → FOUND → existing target-specific status logic.
- Repeated all-dungeon_entries scans must disappear from target-tracking frames.

Greedy Dungeon boundary:
- Greedy target selection may still use broader evidence before a single target is committed.
- Do not redesign greedy priority/eligibility semantics.
- Once greedy logic commits one target index, shared navigation may take over.

Temporary safety rule:
- Keep recurring Dungeon Scene/tab verification until Phase 9.

Must not change:
- cooldown semantics;
- locked-entry handling;
- unavailable checks;
- fight/start behavior;
- exploration/combat;
- greedy target selection.

Exit criteria:
- visible fixed target causes no reset/full-scan after target hit;
- localization may scan the catalog once;
- tracking frames match only target within the card-search layer;
- FOUND hands back to existing Dungeon status/cooldown/locked logic;
- existing Dungeon downstream tests remain unchanged.

### Phase 8 — Migrate Lord after separating target selection from target navigation

Purpose:
- Prevent business target selection from being absorbed into the shared physical navigator.

Required conceptual split:
- Target Selection asks which Lord should be attempted.
- Target Navigation asks where the already committed Lord card is.
- Only Target Navigation belongs to the shared navigator.

Required work:
- Preserve existing availability/cooldown policy that chooses candidates.
- Establish one unique committed target before invoking shared navigation.
- Use full physical Lord catalog indices, not filtered available-list positions.
- After commitment, do not repeatedly scan unrelated Lord card templates while scrolling.
- On FOUND, return to existing cooldown OCR / click / start flow.

Temporary safety rule:
- Keep existing Lord tab verification until Phase 9.

Must not change:
- availability semantics;
- cooldown update semantics;
- cooldown OCR;
- start/fight/result behavior.

Exit criteria:
- target-selection semantics remain unchanged;
- availability filtering does not renumber physical indices;
- committed target uses shared direction/tracking;
- unrelated boss templates are not repeatedly matched after commitment;
- downstream Lord behavior remains unchanged.

### Phase 9 — Enable verified-session target-only CV

Purpose:
- Only after all five modes consume the shared session, suppress repeated Scene/tab CV during steady card tracking.

Entry requirement:
- Phases 4–8 must prove each shared session has explicit verified mode identity, committed target, target index, direction, miss count, and invalidation.

Required behavior:
- ACQUIRE / RELOCALIZE may run Scene/tab CV, target-first matching, and ordered-catalog localization.
- TRACK must match exactly the committed target card template inside the card-search path.
- TRACK must not re-match active tab, inactive tab, unrelated cards, first-card anchor, door, start, or other Scene templates inside that ownership window.

Invalidation returns to Scene verification/localization on:
- desired mode change;
- committed target change;
- cross-mode action;
- miss-bound exhaustion;
- contradictory localization;
- handler/subflow reset;
- recovery/relaunch;
- target FOUND;
- leaving card-selection surface.

Safety boundary:
- Do not remove global runtime safety mechanisms outside the card-search ownership window.
- This phase suppresses duplicate perception only while a verified card-navigation session owns the search frame.

Exit criteria:
- matcher-call tests for every scoped mode show target-only card-search frames;
- invalidation resumes Scene verification;
- cross-mode switching cannot inherit previous verified mode/index knowledge.

### Phase 10 — Remove proven-dead legacy responsibilities

Purpose:
- Remove only legacy responsibilities that earlier phases have replaced and tested.

Eligible cleanup:
- navigation_path responsibility for lobby tab switching;
- mix-specific direct Stage/Dungeon tab switching that duplicates declarative routing;
- _switch_to_stage_or_back() tab-routing responsibility where declarative routing owns it;
- reset-first normal-path card alignment;
- duplicated mode-specific horizontal card-search loops.

Important constraint:
- Do not delete an entire legacy function or navigation_path just because part of its responsibility moved.
- If a legacy path still owns valid downstream behavior, keep that portion.
- Cleanup unit is responsibility, not file size or code age.

Exit criteria:
- no normal-path lobby mode switch bypasses NavigationIntentPolicy / NavigationTable;
- no scoped mode owns a second independent horizontal card-search algorithm;
- no normal-path card navigation resets left before target-first localization;
- dead branches are removed only after replacement coverage is proven;
- all focused tests pass.

## Phase-gate invariant

Every phase must leave the branch runnable and testable.

A production change in phase N must not depend on unfinished behavior planned for phase N+1.

If implementation evidence invalidates a later-phase assumption, stop at the current safe phase, update the SPEC with that evidence, and do not widen implementation opportunistically.


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
