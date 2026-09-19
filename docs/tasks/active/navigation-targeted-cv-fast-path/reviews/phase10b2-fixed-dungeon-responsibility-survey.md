# Phase 10B-2 - Fixed-Target Dungeon Duplicate Responsibility Survey

## Scope

This is a bounded survey only. It makes no production or test change. The
survey covers the fixed-target Dungeon path after Phase 7 and the verified
card-navigation/session work through Phase 10B-1.

The question is whether the remaining Dungeon block is dead duplicate search,
or whether it still owns status, downstream, greedy, recovery, or compatibility
responsibilities.

## Current fixed-target flow

```text
NavigationHandler.handle()
  -> confirmed Dungeon tab
  -> should_scan_dungeons
  -> _handle_fixed_dungeon_navigation()
       -> resolve one fixed target through DungeonCatalog-backed metadata
       -> SharedCardNavigator target-first localization / directional tracking
       -> FOUND: release shared session and return FOUND
       -> HANDLED: swipe, relocalize, or bounded reset/recovery; stop this frame
  -> fixed_dungeon_search = (result == FOUND)
  -> Dungeon scan/status/downstream block
       -> fixed FOUND: scan only the committed entry for status and click data
       -> greedy/no fixed target: scan the broader entry set and select by policy
       -> cooldown / locked / unavailable handling
       -> click, fight/start, or recovery
```

The shared path owns normal fixed-target physical localization. A `FOUND`
handoff does not own cooldown, locked/unavailable evaluation, card status OCR,
click, fight/start, or Dungeon exploration. Those remain in the existing
handler block.

## Reachability matrix

| Scenario | Shared fixed navigator | Legacy Dungeon block | Broad entry scan | Swipe owner | Status/downstream owner |
|---|---|---|---|---|---|
| canonical fixed target, target visible | Yes; returns `FOUND` | Yes, same frame | Committed entry only | **No**; status scan clicks only | Existing handler block |
| canonical fixed target, target absent | Yes; returns `HANDLED` and `handle()` returns immediately | **No** for that frame | None | **No** | Shared navigator |
| fixed-target tracking miss | Yes | **No** | None | **No**; same-direction request is shared | None until `FOUND` |
| fixed-target miss bound / relocalize | Yes | **No** | None | **No** blind legacy swipe | None until re-localized |
| fixed-target `NEED_RESET_LEFT` | Yes | **No** | None | **No**; bounded alignment recovery only | None until recovery |
| fixed `FOUND` + committed target rescan succeeds | Yes then released | Yes | Target entry only | **No** | Existing status/click/fight path |
| fixed `FOUND` + target rescan missing + locked evidence | Yes then released | Yes | Empty target-only scan; bounded reset/recovery returns | **No** | Existing recovery path |
| fixed `FOUND` + target rescan missing + no page evidence | Yes then released | Legacy block is not entered after `is_dungeon_page=False` | None | **No** | None |
| fixed target cooldown/locked/unavailable | Shared handoff may occur first; status gate remains | Yes | Target entry/status evidence | **No** in canonical fixed flow | Existing status policy |
| greedy Dungeon | No fixed shared session until a unique target exists | Yes | Broad scan | **Yes**, existing greedy search primitive | Existing greedy/status policy |
| legacy/compatibility target accepted only by later legacy resolver | Shared resolver may return no target | Yes | Broad scan | **Yes** if target is not visible | Existing compatibility/status path |
| non-`ndarray` frame | Shared fixed path is guarded out | Fixed CV scan is guarded out; generic path may remain | None in this block | **No** for this call site | Existing generic path |
| runtime config refresh / target change | Session identity validation clears stale session | Handler re-evaluates current config | Depends on current config | Shared path after reacquire | Existing status/downstream path |
| runtime config refresh / target change | Session identity validation clears stale session | Handler re-evaluates current config | Depends on current config | Shared path after reacquire | Existing status/downstream path |

## Responsibility matrix

| Responsibility | Evidence | Classification | Replacement / owner |
|---|---|---|---|
| Fixed-target localization, direction, tracking, miss bound, relocalization | `_handle_fixed_dungeon_navigation()` and `SharedCardNavigator`; shared integration tests | **KEEP** | `SharedCardNavigator` owns normal physical navigation; no canonical duplicate horizontal owner remains |
| Fixed-target status/cooldown memory and OCR | `_check_dungeon_status()` and cooldown tests | **KEEP** | Existing Dungeon handler/status policy |
| Locked/unavailable/light-skull evaluation | `_check_dungeon_status()` and Dungeon card tests | **KEEP** | Existing status owner |
| Fixed-target card click and fight/start handoff | `target_idx in visible_dungeons` branch and scenario tests | **KEEP** | Existing Dungeon downstream owner |
| Greedy broad scan and candidate priority | `is_greedy` branch, allowed indices, cooldown filtering | **KEEP** | Existing greedy policy |
| No-visible-card reset and bounded recovery | `reset_to_left`, alignment attempts, town/collect-only fallback | **KEEP** | Existing recovery policy |
| `CardListNavigator.swipe_towards_target()` at `navigation.py:1614` | Reachable from greedy broad scan and from a later legacy target resolver when the shared resolver rejects a malformed/legacy target; not reachable from canonical fixed-target `FOUND` flow | **KEEP** | Greedy and compatibility owners; not a canonical fixed-target duplicate |
| `visible_dungeons` container | Used by status, greedy selection, fixed click, and bounded recovery | **KEEP** | Do not delete; it is not a second canonical fixed-target horizontal owner |
| Fixed target resolution | `_resolve_fixed_dungeon_target_idx()` uses explicit index validation, then `DungeonCatalog.resolve_index_from_nav_path()` | **SPLIT** | Narrow future candidate: separate canonical resolution from legacy compatibility parsing; `DungeonCatalog` remains index authority |
| Non-`ndarray` frame behavior | Type guard bypasses shared fixed navigation and CV scan | **UNKNOWN** | No repository-wide contract proves this path replaceable |
| Legacy configuration behavior | `navigation_path` compatibility parsing and generic handler path | **UNKNOWN** | No repository-wide contract proves all legacy configurations canonical |

## Fixed-target duplicate candidates

The previous survey incorrectly treated the post-`FOUND` status scan as a
route to the legacy swipe. Control flow disproves that: a fixed target that is
not `FOUND` returns `HANDLED` and `NavigationHandler.handle()` returns
immediately. After `FOUND`, `fixed_dungeon_search` restricts `scan_entries` to
the committed target. If that scan succeeds, status/click handling runs. If
it fails but locked-entry evidence keeps `is_dungeon_page` true, the
`not visible_dungeons` branch performs bounded reset/recovery and returns. If
there is no page evidence, the later block is not entered. None of these
canonical fixed-target outcomes reaches `swipe_towards_target()`.

The remaining `CardListNavigator.swipe_towards_target()` ownership is the
greedy broad scan and a compatibility/malformed configuration case where
`_resolve_fixed_dungeon_target_idx()` returns `None` but the later legacy
resolver can still derive a target. This is not a canonical fixed-target
duplicate execution path.

The `scan_entries` selection is also not itself a delete candidate: after
`fixed_dungeon_search` it is target-only, but its result supplies the location
and status input used by existing cooldown/locked/unavailable/click behavior.

### Resolver asymmetry

The shared resolver requires both `dungeon_names` and `dungeon_entries`. For an
explicit raw index it requires `DungeonCatalog.is_valid_index(parsed_idx,
custom_names=names)` and `parsed_idx <= len(entries)`. The later legacy resolver
first tries `DungeonCatalog.resolve_index_from_nav_path(nav_path, entries)` and,
if that fails, accepts any parsed raw index in `1..len(entries)` without
checking the length of `dungeon_names`.

Therefore a malformed configuration with more entry templates than names can
be rejected by the shared explicit-index resolver but accepted by the later
legacy resolver. A legacy `navigation_path` entry that matches
`dungeon_entries` is also a compatibility input to the later broad scan. These
are compatibility responsibilities and were not changed; they are not
evidence that canonical fixed-target search is duplicated.

## Greedy responsibilities to keep

The greedy branch scans the configured entry set, applies
`greedy_allowed_indices`, cooldown filtering, locked/unavailable checks, and
priority order before committing a candidate. `_handle_fixed_dungeon_navigation`
returns no fixed target when `greedy_dungeon` is enabled. The broader scan is
therefore still the target-selection owner and must not be removed or routed
through the fixed-target session.

## Status and downstream responsibilities to keep

The post-`FOUND` handler remains responsible for target cooldown memory and
OCR, locked/unavailable status, card crop/status checks, click coordinates,
fight/start transitions, and the Dungeon prepare/exploring handoff. The shared
navigator does not click cards and does not provide those business decisions.

## Recovery responsibilities to keep

`NEED_RESET_LEFT` is already a bounded recovery result from the shared path and
uses first-card visual alignment. The legacy block still contains valid
no-visible-card recovery, cooldown fallback, town return, collect-only entry,
and `_switch_to_stage_or_back()` policy. These are not fixed-target duplicate
search as a whole and remain KEEP for this survey.

## Compatibility and unknowns

`DungeonCatalog` remains the index authority. `_resolve_fixed_dungeon_target_idx()`
accepts explicit `tier4_dungeon_index` / `dungeon_index` values and falls back
to `DungeonCatalog.resolve_index_from_nav_path()` for compatibility. The survey
does not establish that every runtime configuration is canonical or that every
non-`ndarray` frame is covered by the shared navigator. Those paths remain
compatibility/unknown boundaries.

No additional repository contract was found that guarantees all runtime config
refreshes, legacy navigation paths, or non-`ndarray` handler calls are safe to
remove. Target identity hot reload is covered by session identity checks, but
that does not prove legacy fallback reachability is empty.

## Test evidence and gaps

Focused Dungeon survey run:

```text
python -m unittest \
  tests.test_behavior_dungeon_shared_navigation \
  tests.test_behavior_dungeon_cards \
  tests.test_behavior_dungeon_scenarios \
  tests.test_dungeon_catalog \
  tests.test_dungeon_swipe_unit \
  tests.test_behavior_navigation
```

Result: **86 tests, 82 passed, 4 pre-existing failures**.

The passing evidence covers fixed-target visible/absent navigation, direction,
target-only tracking, miss exhaustion, reset-left fallback, session
invalidation, DungeonCatalog authority, greedy boundary, cooldown/status
handling, and legacy swipe/recovery primitives.

The four observed failures are outside this survey change and occurred without
production or test modifications: one declarative tab expectation in
`test_behavior_dungeon_cards.py`, two defeat-flow timing expectations in
`test_behavior_dungeon_scenarios.py`, and one legacy scrolling-direction
expectation in `test_behavior_dungeon_scenarios.py`.

Missing characterization evidence before any resolver/legacy-block cleanup:

1. A direct regression proving all three post-`FOUND` rescan outcomes return
   before `swipe_towards_target()`.
2. Resolver asymmetry cases where names and entries have different lengths,
   and where a legacy `navigation_path` or raw index is accepted only by the
   later resolver.
3. Non-`ndarray`, legacy `navigation_path`, and runtime config-refresh
   reachability boundaries.

## Revised cleanup recommendation

The canonical fixed-target path has no reachable second horizontal-search
owner. **Phase 10 fixed-target horizontal-search ownership is already
deduplicated.** Do not delete `swipe_towards_target()` merely to force a Phase
10 cleanup; its remaining ownership is greedy and compatibility.

At most two narrower candidates remain:

1. Separate the shared fixed-target resolver from the later compatibility
   resolver, preserving the observed raw-index and `navigation_path`
   asymmetry.
2. Isolate fixed-only rescan/status handling from the mixed greedy/status block
   only if characterization proves that the separation does not alter cooldown,
   locked/unavailable, recovery, or downstream behavior.

If those boundaries cannot be proven, there is no safe cleanup candidate for
this slice.

## Classification counts

- DELETE_CANDIDATE: **0**
- SPLIT: **1**
- KEEP: **8**
- UNKNOWN: **2**

No production cleanup is performed by this survey.
