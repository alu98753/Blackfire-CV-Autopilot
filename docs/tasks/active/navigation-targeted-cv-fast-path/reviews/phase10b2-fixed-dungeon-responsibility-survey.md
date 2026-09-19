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
| canonical fixed target, target visible | Yes; returns `FOUND` | Yes, same frame | No; committed entry only | Shared navigator before handoff | Existing handler block |
| canonical fixed target, target absent | Yes; returns `HANDLED` | No for that frame | No | Shared navigator | Next frame after handoff |
| fixed-target tracking miss | Yes | No | No | Shared navigator, same committed direction | None until `FOUND` |
| fixed-target miss bound / relocalize | Yes | No | No | No blind legacy swipe | None until re-localized |
| fixed-target `NEED_RESET_LEFT` | Yes | No | No | Existing bounded alignment recovery | None until recovery |
| fixed target `FOUND` with target status evidence | Yes then released | Yes | Target entry only | No duplicate search in the normal evidence case | Existing status/click/fight path |
| fixed `FOUND` plus target/status evidence mismatch | Yes then released | Yes | Target entry may be absent; locked-page evidence can keep the block active | A legacy `swipe_towards_target` fallback remains reachable | Existing block |
| fixed target cooldown | Shared target handoff may occur first; status gate remains | Yes | Target entry only when available for status | No normal search ownership | Existing cooldown policy |
| fixed target locked/unavailable | Shared handoff does not replace status evaluation | Yes | Target entry/status evidence | Recovery/status paths remain | Existing `_check_dungeon_status` and callers |
| greedy Dungeon | No fixed shared session until a unique target exists | Yes | Broad scan | Existing greedy/recovery primitive | Existing greedy/status policy |
| non-`ndarray` frame | Shared fixed path is guarded out | Generic/compatibility path may remain | CV scan is guarded out | No shared fixed guarantee | Existing generic path |
| legacy `navigation_path` config | Used as a compatibility target resolver when no explicit index is present | Existing compatibility/downstream path remains | Depends on runtime frame/evidence | Not proven dead in all configurations | Existing handler policy |
| runtime config refresh / target change | Session identity validation clears stale session | Handler re-evaluates current config | Depends on current config | Shared path after reacquire | Existing status/downstream path |

## Responsibility matrix

| Responsibility | Evidence | Classification | Replacement / owner |
|---|---|---|---|
| Fixed-target localization, direction, tracking, miss bound, relocalization | `_handle_fixed_dungeon_navigation()` and `SharedCardNavigator`; shared integration tests | **SPLIT** only where old fallback overlaps | `SharedCardNavigator` owns normal physical navigation |
| Fixed-target status/cooldown memory and OCR | `_check_dungeon_status()` and cooldown tests | **KEEP** | Existing Dungeon handler/status policy |
| Locked/unavailable/light-skull evaluation | `_check_dungeon_status()` and Dungeon card tests | **KEEP** | Existing status owner |
| Fixed-target card click and fight/start handoff | `target_idx in visible_dungeons` branch and scenario tests | **KEEP** | Existing Dungeon downstream owner |
| Greedy broad scan and candidate priority | `is_greedy` branch, allowed indices, cooldown filtering | **KEEP** | Existing greedy policy |
| No-visible-card reset and bounded recovery | `reset_to_left`, alignment attempts, town/collect-only fallback | **KEEP** | Existing recovery policy |
| Fixed-target legacy `swipe_towards_target()` fallback | `navigation.py:1601-1614`; reached from the legacy block after fixed handoff when evidence keeps the page active but target location is absent | **SPLIT** | Candidate for a later narrow cleanup after a reachability characterization test |
| `visible_dungeons` container | Used by status, greedy selection, fixed click, and recovery | **KEEP / SPLIT** | Do not delete as a whole; only isolate any proven duplicate search slice |
| Fixed target resolution | `_resolve_fixed_dungeon_target_idx()` uses explicit index first, then `DungeonCatalog.resolve_index_from_nav_path()` | **KEEP** | Compatibility parsing plus `DungeonCatalog` index authority |
| Non-`ndarray` frame behavior | Type guard bypasses shared fixed navigation and CV scan | **UNKNOWN** | No repository-wide contract proves this path replaceable |
| Legacy configuration behavior | `navigation_path` compatibility parsing and generic handler path | **UNKNOWN** | No repository-wide contract proves all legacy configurations canonical |

## Fixed-target duplicate candidates

The strongest candidate is not the whole legacy Dungeon block. It is the
specific fallback call to `CardListNavigator.swipe_towards_target()` at
`states/handlers/navigation.py:1614`. The normal fixed-target path has already
committed direction and performs target-only tracking through
`SharedCardNavigator`; the legacy swipe therefore duplicates physical search
when it is reached for a canonical fixed target.

However, the call is not proven unreachable. After shared `FOUND`, the same
frame performs a target-entry/status scan. If that scan does not produce the
target location but locked-entry evidence keeps `is_dungeon_page` true, the
legacy branch can still reach the fallback. This is an evidence-mismatch or
recovery-like path, not proof that the whole block is dead.

The `scan_entries` selection is also not itself a delete candidate: after
`fixed_dungeon_search` it is target-only, but its result supplies the location
and status input used by existing cooldown/locked/unavailable/click behavior.

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

Missing characterization evidence before deleting the fixed-target legacy
swipe slice:

1. `fixed_result == "FOUND"` followed by target-only status scan with target
   location absent and locked-entry evidence present.
2. The same branch with cooldown/unavailable status, proving status handling
   remains without a replacement swipe.
3. Non-`ndarray`, legacy `navigation_path`, and runtime config-refresh reachability
   boundaries.

## Recommended Phase 10B-2 implementation slice

1. Add the smallest characterization test for the post-`FOUND` status handoff
   and the legacy fallback reachability boundary.
2. Remove only the canonical fixed-target fallback call to
   `CardListNavigator.swipe_towards_target()` if the test proves the branch is
   not required by a compatibility or recovery contract.
3. Keep `visible_dungeons`, status evaluation, greedy selection, click/fight,
   cooldown fallback, reset recovery, and compatibility parsing unchanged.

## Classification counts

- DELETE_CANDIDATE: **0**
- SPLIT: **3**
- KEEP: **6**
- UNKNOWN: **2**

No production cleanup is performed by this survey.
