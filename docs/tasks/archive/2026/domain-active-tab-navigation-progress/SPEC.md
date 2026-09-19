# domain-active-tab-navigation-progress

Status: Final

## Goal

Fix Domain primary navigation so that once the Domain tab is already active, navigation acknowledges that progress, stops re-clicking `domains/Domains_entry.png`, and proceeds to the existing Domain card-alignment / target-search flow (including the leftward reset/search behavior used to find the configured domain such as Golden Empire).

## Problem

Runtime evidence shows the scene layer correctly recognizes `domain_select` after `domains/Domains_entry_after.png` wins over the inactive template, but primary navigation repeatedly clicks `domains/Domains_entry.png` anyway.

Observed loop:

```text
DOMAIN_SELECT observed
-> IntentRouting continue_primary
-> Domains_entry.png remains in navigation_path
-> click Domain tab again
-> DOMAIN_SELECT observed
-> repeat
```

The shared `filter_navigation_path()` currently skips already-active Stage and Dungeon tab buttons, but not Domain. This leaves Domain asymmetric with the other lobby tabs and prevents route progress from reaching the existing Domain card-alignment flow.

## Scope

Primary implementation scope:
- `states/handlers/navigation.py`
- nearby navigation behavior tests covering active-tab filtering / domain card alignment

Read/verify as needed:
- `utils/scene_detector.py`
- `utils/scene_snapshot.py`
- `states/navigation_routing.py`
- `states/navigation_progress.py`
- existing tests for primary navigation, scene active tabs, and card alignment

## Required behavior

1. When Domain is not active, `domains/Domains_entry.png` remains a valid primary-navigation step.
2. When `scene.active_tabs` contains `domain`, the Domain tab button is considered completed navigation progress and is filtered/skipped like Stage and Dungeon.
3. After Domain becomes active, navigation must proceed into the existing Domain target alignment/search flow rather than stall.
4. Existing Domain card alignment should own the reset/scroll/search behavior for the configured domain target; do not duplicate that responsibility in routing or scene detection.
5. `domains/Domains_entry_after.png` / scene detection remains the source of truth for whether the Domain tab is active. Do not infer active state merely because a click was attempted.
6. Preserve Stage and Dungeon behavior.
7. Do not move task selection into Navigation.
8. Do not alter scheduler priority or Daily activity selection.

## Architecture invariants

- Scene/perception determines observed UI state.
- Navigation progress consumes observed state and suppresses already-completed parent navigation steps.
- Domain, Dungeon, and Stage active-tab semantics should be symmetric at the shared navigation-progress boundary unless the UI genuinely differs.
- Card alignment/search owns horizontal list positioning after the correct tab is active.
- A click attempt is not progress; observed postcondition is progress.

## Acceptance criteria

- Given primary Domain navigation with Domain inactive, the Domain tab button is still eligible to click.
- Given primary Domain navigation with `active_tabs={"domain"}`, `domains/Domains_entry.png` is removed/skipped from the effective navigation path.
- Given active Domain tab and a target Domain card not initially visible, control reaches the existing Domain card alignment/reset/search path rather than re-clicking the tab.
- Regression test proves repeated `DOMAIN_SELECT` frames do not repeatedly dispatch the Domain tab click.
- Existing Stage/Dungeon active-tab skip tests continue to pass.
- Existing scene detection behavior for `Domains_entry.png` vs `Domains_entry_after.png` remains unchanged.

## Non-goals

- No scheduler/Daily priority changes.
- No new scene-classification framework.
- No rewrite of `CardListNavigator` unless a directly demonstrated Domain-specific bug is found after the active-tab progress fix.
- No generic navigation planner rewrite.
- No changes to Domain combat/exploration behavior.
- No threshold tuning unless tests/runtime evidence prove the active-tab classifier itself is wrong.

## Implementation guidance

Prefer the smallest coherent fix. The likely correction is to make Domain participate in the same shared active-tab skip contract as Stage and Dungeon. Before finalizing, verify that the active-tab key is exactly `domain` and that the existing Domain branch in `_handle_primary_card_alignment()` is reached after filtering. If that second handoff is broken, fix only the missing progress handoff required by this SPEC rather than adding a second navigation owner.
