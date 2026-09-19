# Phase 10A — Dead Responsibility Survey

## Scope and methodology

This survey covers the production code at `445545ee5fc6850b04241beb1ef1928cd5226d3b`, after Phases 1–9. It treats a function as a container of responsibilities rather than as a deletion unit. Reachability was checked from `NavigationHandler.handle()`, `LordBossHandler.handle()`, and `DemonLordsHandler.handle()` through their conditions and early returns. Existing tests were reused as evidence; this survey adds no tests and makes no production change.

The conclusions below distinguish normal shared-navigation ownership from compatibility, fallback, recovery, scheduler, cooldown, and post-FOUND behavior. A legacy block is not considered removable merely because a shared navigator exists.

## Ownership graph

```text
Lobby mode switching
  → NavigationIntentPolicy / NavigationTable / execute_lobby_tab_route
  → legacy tab clicks remain in fallback and business-recovery branches

Card target selection
  → existing mode business policy
  → Lord availability/candidate order, Demon Lord availability, Dungeon greedy policy

Card physical localization/navigation
  → SharedCardNavigator + mode navigation catalogs
  → legacy mode-specific search remains as compatibility or unsupported-config fallback

Reset recovery
  → CardListNavigator.align_first_card/reset_to_left after failed localization

Dungeon greedy selection
  → NavigationHandler's broader visible_dungeons scan and status policy

Cooldown / availability
  → NavigationHandler, LordBossHandler, DemonLordsHandler, and existing managers

FOUND downstream
  → existing mode owners: Stage sub-stage flow, Domain start/explore,
    Dungeon status/fight, Lord OCR/start/fight, Demon Lord stone/prepare flow
```

No second normal-path owner was proven for shared physical card tracking. Several legacy blocks still contain valid fallback or downstream responsibilities and therefore require a split before cleanup.

## Candidate responsibility matrix

| Candidate / location | Responsibility and current callers | Reachability | Replacement owner / evidence | Downstream coupling | Decision | Reason |
|---|---|---|---|---|---|---|
| `states/handlers/navigation.py:41` `filter_navigation_path()` and `:1842–1920` reversed `filtered_nav_path` loop | Filters and clicks `navigation_path` entries. `NavigationHandler.handle()` reaches the loop after scene handling, routing execution, shared-card handling, and dungeon status logic do not return. | Normal for remaining path work; active lobby-tab entries are filtered when the corresponding tab is already active. | Declarative lobby switching is owned by `NavigationDecisionExecutor` / `execute_lobby_tab_route()`; `tests/test_behavior_navigation_table.py`, `tests/test_behavior_navigation_progress.py`, and `tests/test_behavior_routing_observability.py` cover that owner. | The same loop still handles door/town entry, detail-screen navigation, sub-stage scrolling/clicking, cooldown guards, non-lobby entries, and compatibility aliases. | **SPLIT** | Only the lobby-tab-switching responsibility is a cleanup candidate. The whole `navigation_path` mechanism is not dead. |
| `states/handlers/navigation.py:1005` `_switch_to_stage_or_back()` | Handles dungeon cooldown reporting, `all_dungeons_on_cooldown_until`, daily rescheduling, Tier-4 Domain fallback, collect-only fallback, stage-farming policy, and direct `common/select_stage.png` / `goback_town.png` actions. Callers are cooldown and fallback branches in `NavigationHandler.handle()`. | Fallback/business policy path; not the normal declarative tab route. | `NavigationIntentPolicy` / `NavigationTable` owns normal tab switching. Existing cooldown and stamina-retreat tests cover the remaining policy behavior, including `tests/test_behavior_dungeon_cards.py`, `tests/test_behavior_dungeon_scenarios.py`, and `tests/test_stamina_retreat_routing.py`. | The function combines direct tab clicking with scheduler, cooldown, collect-only, and fallback state transitions. | **SPLIT** | The direct normal tab-switch portion may be isolated later; the function cannot be deleted as a unit. |
| Mix Stage/Dungeon switching in `navigation.py:1331–1681` | Scans fixed or greedy Dungeon cards, applies cooldown/locked/unavailable policy, clicks `select_stage` during cooldown fallback, and uses stage fallback navigation. | Normal for Dungeon status handling and greedy selection; direct tab clicks are fallback branches. | Declarative routing handles ordinary cross-mode switching; `tests/test_behavior_navigation_table.py` and `tests/test_behavior_navigation_progress.py` cover it. `tests/test_behavior_dungeon_cards.py` and `tests/test_behavior_dungeon_scenarios.py` cover fallback semantics. | The same block owns cooldown, locked/unavailable detection, OCR/status checks, click/start transitions, and greedy priority. | **SPLIT** | Only ordinary lobby tab switching is replaceable; cooldown and recovery branches remain live. |
| Stage main-card legacy alignment/search: `navigation.py:748` `_handle_primary_card_alignment()`, generic path at `:1842–1920` | Aligns a primary card list to its first card and later uses `navigation_path` entries. `handle()` invokes it when shared Stage navigation is not the active path or when the shared path hands off. | Normal for unsupported/incomplete configurations and generic downstream path; shared Stage path runs first for canonical targets. | `stage_navigation_catalog()` + `SharedCardNavigator` in `_handle_stage_shared_navigation()` at `:399`; evidence in `tests/test_behavior_stage_shared_navigation.py`, including target-first and target-only tracking tests. | Stage sub-stage scroll/search/click after main-card handoff is still in the generic path and is explicitly protected by `tests/test_behavior_navigation.py`, `tests/test_stage_quest_sub_stage_routing.py`, and `tests/test_sub_stage_navigator.py`. | **SPLIT** | Reset-first/main-card search can be removed only after fallback coverage is characterized. Sub-stage behavior must stay. |
| Domain main-card legacy alignment/search: `navigation.py:748`, `:1842–1920` | Uses first-card alignment and generic `navigation_path` Domain entry handling after scene/routing decisions. | Normal fallback/unsupported-config path; canonical Domain targets enter `_handle_domain_shared_navigation()` at `:523`. | `domain_navigation_catalog()` + `SharedCardNavigator`; evidence in `tests/test_behavior_domain_shared_navigation.py` and `tests/test_domain_common_behavior.py`. | Domain entry click, start, explore, strategy, and scheduler behavior remain downstream owners. | **SPLIT** | Main-card localization is a cleanup candidate; entry/start/explore behavior is not. |
| Fixed Dungeon path: `navigation.py:664` `_handle_fixed_dungeon_navigation()` and old scan at `:1349–1604` | Shared path resolves a concrete target and owns target localization. The later block still performs status checks and downstream click/fight handling; when the shared result is not used, it can scan entries through the compatibility path. | Shared fixed-target path is normal when the frame is a supported ndarray and Scene is confirmed. Old scan remains reachable for fallback/non-shared conditions; greedy branch is separate. | `dungeon_navigation_catalog()` + `SharedCardNavigator`; evidence in `tests/test_behavior_dungeon_shared_navigation.py`, `tests/test_behavior_dungeon_cards.py`, `tests/test_dungeon_catalog.py`, and `tests/test_dungeon_swipe_unit.py`. | Cooldown, locked/unavailable status, card crop/OCR, click/start/fight, and recovery remain in the same handler. | **SPLIT** | Repeated fixed-target localization/search is a cleanup candidate only after separating it from status and downstream logic. |
| Greedy Dungeon branch in `navigation.py:1400–1604` | Broader `visible_dungeons` scan, allowed-index priority, cooldown filtering, locked/unavailable checks, and selection of a candidate before a unique target is committed. | Normal when `greedy_dungeon=True`; `_resolve_fixed_dungeon_target_idx()` deliberately returns no fixed target, so it does not enter the fixed shared session. | No replacement is intended. `tests/test_behavior_dungeon_shared_navigation.py` and Dungeon scenario/state-machine tests cover the boundary and existing semantics. | Candidate priority, eligibility, cooldown, and status policy are coupled. | **KEEP** | Fixed-target migration does not make broader greedy evidence dead. |
| Lord navigation state and legacy search: `lord_boss.py:27`, `:419–541` | `has_reset_to_left`, first-card alignment, candidate loop over `avail_bosses`, cooldown OCR, click/start, and final `swipe_left_page()`. Called by `LordBossHandler.handle()`. | Shared Lord navigation is normal for a committed canonical target. The reset/search blocks remain reachable for compatibility/incomplete configurations and for downstream candidate handling. | Target selection remains in the existing availability policy; physical navigation is `_handle_lord_shared_navigation()` / `SharedCardNavigator`; evidence in `tests/test_behavior_lord_shared_navigation.py`, `tests/test_lord_boss_subflow.py`, and `tests/test_lord_boss_swipe.py`. | Candidate selection, cooldown OCR, confidence protection, bookkeeping, click/start/fight remain live. `shared_lord_handoff` is a same-frame handoff guard; `lord_card_session.owns_tracking` is the tracking owner. | **SPLIT** | Old physical reset/swipe may be removed only as an isolated fallback responsibility. The function and candidate/OCR logic must remain. |
| Demon Lord compatibility path: `demon_lords.py:348` `_step_select_boss_card_legacy()` | Target-first direct card match, first-card alignment, bounded reset, and relaunch behavior when the target is absent from the canonical catalog. Called when `_step_select_boss_card()` cannot resolve the target key in the catalog. | Compatibility-only for incomplete/legacy catalog configurations; the current code does not establish that every supported external configuration always supplies a complete canonical catalog. | Canonical path is `demon_lord_navigation_catalog()` + `SharedCardNavigator`; evidence in `tests/test_behavior_demon_lord_shared_navigation.py` and `tests/test_demon_lords_subflow.py`. | Stone queue, prepare modal, start/fight, availability, and reset/relaunch remain coupled. | **KEEP** | The repository contains an explicit incomplete-catalog fallback and no stronger configuration contract was found. |
| Reset-first/alignment calls: `navigation.py:456,578,717,812`; Lord `:133,434`; Demon `:294,381`; Dungeon old scan `:1443` | Aligns a card list or resets left after no useful localization evidence, or supports legacy/unsupported paths. | Shared navigator uses these only after localization cannot establish useful evidence; old callers remain in fallback and greedy/status flows. | `SharedCardNavigator` owns target-first localization and returns `NEED_RESET_LEFT`; existing alignment tests include `tests/test_card_alignment.py`, mode shared-navigation tests, and Dungeon/Gol​den Empire recovery tests. | First-card evidence, bounded attempts, relaunch, cooldown fallback, and recovery are coupled. | **SPLIT** | Valid recovery must stay. Only an immediately-before-search normal reset, if proven reachable only in replaced canonical paths, is a Phase 10B candidate. |
| Horizontal card search: `PageSwipeRequest` / `CardListNavigator` plus direct calls at `navigation.py:1604`, `lord_boss.py:541`, and legacy alignment helpers | Performs actual page drags. `PageSwipeRequest` delegates to the common `CardListNavigator` primitive; direct calls remain in fallback, greedy selection, or legacy branches. | Common primitive is normal and shared. Direct calls are mixed normal downstream/fallback/compatibility reachability. | `SharedCardNavigator` owns scoped fixed-target tracking; `tests/test_behavior_*_shared_navigation.py` and `tests/test_dungeon_swipe_unit.py` cover geometry and direction. | Greedy selection, recovery, and legacy unsupported-config behavior still depend on direct calls. | **SPLIT** | Keep the common primitive and greedy/recovery callers; remove only duplicate scoped card-search algorithms after reachability tests. |

## Safe delete candidates

No whole candidate qualifies as `DELETE_CANDIDATE` in this survey. Each candidate still contains either a compatibility/fallback path, business policy, recovery, or FOUND downstream responsibility. The safest future deletions are responsibility slices inside the SPLIT rows, not whole functions.

## SPLIT candidates

The strongest Phase 10B candidates are:

1. Generic lobby-tab clicks inside the reversed `navigation_path` loop, after proving every supported normal lobby transition reaches `NavigationIntentPolicy` and expected-tab postcondition handling.
2. The direct `select_stage` / `dungeon` tab-switch slices in cooldown fallback code, only after preserving cooldown, scheduler, collect-only, and stamina-retreat transitions.
3. Canonical fixed-target Stage/Domain/Dungeon/Lord card-search loops that duplicate `SharedCardNavigator`, while retaining generic compatibility paths and all post-FOUND owners.

## KEEP responsibilities

- `navigation_path` entries for door/town navigation, detail-screen navigation, Stage sub-stage selection/scroll/click, cooldown guards, and compatibility aliases.
- `_switch_to_stage_or_back()` business policy: cooldown report/bookkeeping, daily rescheduling, Tier-4 fallback, collect-only fallback, and stage-farming policy.
- Greedy Dungeon broader candidate scan, priority, eligibility, locked/unavailable checks, and downstream status handling.
- Lord availability/candidate selection, cooldown OCR, confidence protection, bookkeeping, and start/fight flow.
- Demon Lord incomplete-catalog fallback until a repository-level completeness contract is established.
- Bounded reset-left recovery after localization fails to produce useful evidence, including first-card visual confirmation.
- All FOUND downstream behavior for Stage, Domain, Dungeon, Lord, and Demon Lord.
- `CardListNavigator` as the physical swipe primitive used by `PageSwipeRequest`.

## UNKNOWN / evidence gaps

The repository does not provide evidence that all supported Demon Lord configurations are guaranteed to contain complete canonical catalog entries. The compatibility fallback therefore remains KEEP rather than DELETE_CANDIDATE.

The current tests prove shared navigation and many fallback behaviors, but they do not constitute a complete reachability proof for every combination of legacy `navigation_path`, runtime config refresh, unsupported catalog, and non-ndarray frame. Phase 10B should add only the smallest characterization test needed before deleting each responsibility slice.

For fixed Dungeon hot reload, the Phase 9 implementation compares the resolved target index/key and current template against the existing navigator target. No additional cleanup conclusion is drawn from that behavior.

## Required tests before Phase 10B deletion

- A normal supported Stage/Domain/Dungeon/Lord/Demon Lord route test proving the relevant legacy block is not entered before and after FOUND handoff.
- A compatibility test for incomplete Demon Lord catalogs and any legacy Lord configuration that cannot construct a canonical catalog.
- A cooldown/fallback test for each direct `select_stage` or `goback_town` branch before removing only its tab-click slice.
- Stage sub-stage regression coverage before touching the generic `navigation_path` loop.
- Greedy Dungeon tests proving candidate order, eligibility, cooldown, locked/unavailable handling, and downstream click/fight behavior remain independent of fixed-target cleanup.

## Recommended Phase 10B bounded cleanup batch

1. Remove only the canonical normal-path lobby-tab click responsibility from the generic reversed `navigation_path` loop, after adding a reachability characterization test for supported modes.
2. Remove only duplicate canonical fixed-target main-card search branches that are proven unreachable after `SharedCardNavigator`, leaving compatibility and downstream status blocks intact.
3. Isolate direct cooldown-fallback tab clicks from `_switch_to_stage_or_back()` and the mix fallback block without changing their business policy or recovery transitions.

## Phase 10A verdict

- DELETE_CANDIDATE count: **0**
- SPLIT count: **9**
- KEEP count: **2**
- UNKNOWN count: **0**
