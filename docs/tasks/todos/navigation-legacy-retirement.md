# Navigation Legacy Retirement

Status: Future Work

Origin: `navigation-targeted-cv-fast-path` Phase 10 checkpoint closeout.

## Goal

After Activity execution config ownership and Activity orchestration semantics are consolidated, remove navigation compatibility paths whose supported callers have become unreachable.

This future work is intentionally a **retirement task**, not a second navigation redesign. The shared navigation architecture already exists. Its job is to prove old compatibility owners dead under the stronger upstream contracts, then delete them while preserving verified behavior.

## Prerequisites

Complete these first:

1. [Activity Execution Config SSOT](activity-execution-config-ssot.md)
2. [Activity Plan + Mode Consolidation](activity-plan-mode-consolidation.md)

The intended dependency is:

```text
Activity Execution Config SSOT
        ↓
Activity Plan + Mode Consolidation
        ↓
Navigation Legacy Retirement
```

Do not begin broad deletion before those prerequisites define which config/orchestration shapes remain supported.

## Candidate retirement inventory

### Stage

Reassess and remove compatibility responsibilities made unreachable by explicit Stage Activity identity:

- legacy main-card manual horizontal search;
- `horizontal_scroll_count` ownership used only by that search;
- reset-first primary-card compatibility for Stage;
- ordinary historical `mix -> Stage` compatibility routing/search;
- legacy exhaustion recovery that exists only to support the old main-card search, unless its recovery semantic is still required and must be re-expressed independently.

Preserve Stage main-card click handoff and all sub-stage behavior.

### Domain

Reassess and remove:

- noncanonical Domain identity fallback;
- primary-card alignment ownership retained only because a runtime config can omit canonical Domain identity.

Preserve Domain start/explore and strategy behavior.

### Fixed-target Dungeon

Reassess and remove:

- `_resolve_legacy_compat_dungeon_target_idx()` when supported config producers make canonical fixed-target identity complete;
- any compatibility-only fixed-target search residue that becomes unreachable.

Preserve Dungeon cooldown/status/locked/fight/start/explore behavior.

### Lord

Reassess and remove compatibility navigation based on:

- `has_reset_to_left`;
- `reset_swipe_count`;
- reset-first / broad candidate scanning / direct page-swipe ownership when it exists only for noncanonical navigation.

Preserve target-selection policy, cooldown/OCR, DailyManager updates, click/start/fight behavior.

### Demon Lord

Reassess and remove:

- `_step_select_boss_card_legacy()`;
- incomplete-catalog navigation compatibility once supported Demon Lord configuration is guaranteed to expose canonical catalog identity.

Preserve stone planning/insertion, prepare/start/fight/completion behavior.

### Cross-mode routing

Reassess and remove direct tab-click responsibility from:

- `_switch_to_stage_or_back()` where declarative routing owns the transition;
- remaining historical `mix` Stage/Dungeon direct switching;
- cooldown/fallback branches that still combine Activity selection policy with physical tab clicking.

Business decisions may remain, but physical routing must have one owner.

## Explicit non-targets

Do not classify these as duplicate navigation legacy merely because they predate the shared navigator:

- Greedy Dungeon broad scan, priority, eligibility, cooldown, and locked/unavailable target selection while no unique target is committed;
- Stage sub-stage scrolling/search and boss-skull validation;
- Dungeon post-FOUND status/cooldown/locked/fight/start/explore logic;
- Domain start/explore behavior;
- Lord target selection, availability, cooldown OCR, DailyManager updates, start/fight behavior;
- Demon Lord stone/prepare/start/fight behavior;
- bounded reset-left as a recovery primitive when localization truly has no useful evidence.

## Required deletion rule

A compatibility branch may be deleted only when all of the following are true:

1. supported config producers can no longer generate its triggering shape;
2. supported orchestration can no longer select its historical ownership path;
3. canonical shared navigation covers the same physical navigation responsibility;
4. downstream business/recovery semantics have either been proven obsolete or preserved independently;
5. focused regression tests characterize the replacement boundary.

The goal is **semantic deletion**, not simply moving the same legacy algorithm behind a new helper.

## Expected end state

For each fixed-target Stage/Domain/Dungeon/Lord/Demon-Lord card-navigation path:

```text
selected Activity + canonical target
        ↓
declarative lobby routing
        ↓
Scene-confirmed target tab
        ↓
SharedCardNavigator
        ↓
FOUND
        ↓
mode-specific downstream behavior
```

No supported canonical path should retain a second independent horizontal card-search algorithm.
