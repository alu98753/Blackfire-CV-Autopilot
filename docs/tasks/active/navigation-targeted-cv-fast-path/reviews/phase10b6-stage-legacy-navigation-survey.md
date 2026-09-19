# Phase 10B-6 — Stage legacy main-card navigation survey

Production anchor: current `navigation-targeted-cv-fast-path` branch after Phase 10B-5.

## Scope

Stage only. This survey does not change production code.

The goal is to determine whether Stage legacy main-card reset/search/swipe responsibilities can be removed incrementally while preserving supported behavior.

Protected downstream boundary:

- Stage tab routing policy;
- Stage main-card click after FOUND;
- `stages/stage_label.png` detail-screen detection;
- sub-stage target search/scroll/click;
- start/battle/result behavior;
- Dungeon cooldown / mix fallback policy.

## Current Stage owners

### Canonical shared owner

`_handle_stage_shared_navigation()` owns Stage main-card physical navigation when:

- current config `type == "stage"`;
- Stage tab is visually active;
- a canonical Stage target can be resolved.

It already provides:

- target-first match;
- ordered Stage catalog localization;
- directional shared swipe;
- target-only tracking;
- bounded miss/relocalization;
- reset-left fallback through `align_first_card()`;
- FOUND handoff to the existing generic click/downstream flow.

### Legacy owners

Two older Stage physical-navigation responsibilities remain in `NavigationHandler`:

1. `_handle_primary_card_alignment()` can reset the Stage card list to its first card before the target is localized.
2. The generic Stage main-card horizontal-search block manually:
   - finds `target_level_btn` from `nav_path`;
   - matches the target;
   - waits on missing timers;
   - tracks `horizontal_scroll_count`;
   - performs its own left/right drags;
   - eventually tries `goback_town.png` after search exhaustion.

The generic reverse `navigation_path` click loop is **not** itself legacy Stage search. It still owns the Stage main-card click after shared FOUND and the protected sub-stage flow.

## Reachability findings

### 1. Normal pure Stage runtime is already canonical

Official Stage construction through `cli.stage_setup.setup_stage_config()` produces:

- `tier4_stage_level`;
- `stage_entry`;
- `stage_target`;
- `stage_navigation_path`.

Bounty Stage construction through `QuestMapper.to_config_dict()` produces:

- `stage_level`;
- `stage_entry`;
- `stage_target`;
- `stage_navigation_path`.

The existing shared resolver can resolve normal CLI Stage through `tier4_stage_level` / `stage_entry` / `stage_navigation_path`.

Therefore supported pure `type="stage"` runtime is already normally shared-owned.

### 2. Ordinary mix Stage fallback is still a live legacy owner

`setup_mode_config()` runs `setup_stage_config()` when ordinary `mix` enables Stage farming, so the mix config also has canonical Stage target metadata.

However `_stage_shared_navigation_enabled()` currently requires:

```python
config["type"] == "stage"
```

Therefore, after mix policy decides that Dungeon is unavailable and Stage is the active tab, the Stage card target is still navigated by:

- generic first-card alignment;
- generic manual horizontal Stage search.

This is the strongest live supported caller keeping Stage legacy physical navigation alive.

### 3. Daily Tier-4 Stage is not the same problem

`build_tier4_fallback_config()` converts Tier-4 Stage execution to `type="stage"`, and `_apply_tier4_stage_selection()` reconstructs `stage_entry`, `stage_target`, and `stage_navigation_path`.

Therefore Daily Tier-4 Stage execution already fits the canonical shared Stage path.

### 4. Incomplete/synthetic Stage configs still fall back

Some tests and externally constructed dictionaries contain only a partial `navigation_path`, or omit canonical Stage identity fields.

The current shared resolver does not inspect:

- `stage_level`;
- canonical Stage entry templates found only in generic `navigation_path`.

Those shapes can still fall through to the legacy Stage alignment/search path.

Before deleting compatibility behavior, distinguish:

- supported repository config producers;
- explicit legacy compatibility;
- synthetic test fixtures that should be rewritten to use a real supported Stage config.

## Safe incremental cleanup plan

### Stage-A — Expand canonical target resolution

No physical behavior deletion yet.

Extend Stage target identity resolution using only authoritative evidence:

1. `tier4_stage_level`;
2. `stage_level`;
3. `stage_entry`;
4. `stage_navigation_path`;
5. canonical Stage entry template present in generic `navigation_path`.

Do **not** infer semantic indices from raw `stage_templates` list positions because aliases can shift positions.

Add producer characterization proving the supported Stage producers resolve to the same catalog target.

Expected effect: older but still structurally meaningful routes join the shared owner without changing target choice.

### Stage-B — Give mix Stage fallback to SharedCardNavigator

Allow shared Stage main-card navigation when:

- Stage tab is visually active;
- navigation routing has not already issued a cross-tab action;
- current execution policy is actually using a canonical Stage target;
- this includes ordinary `mix` with Stage farming after Dungeon fallback.

Do not move the policy decision "Dungeon vs Stage" into the shared navigator.

The shared navigator receives an already-decided Stage execution surface only.

Required regressions:

- mix + Dungeon unavailable + target visible -> zero reset/drag;
- mix + target absent + lower visible Stage -> shared higher-index swipe;
- mix tracking frame -> only committed target match;
- shared reset fallback remains bounded;
- cooldown policy and tab-switch tests remain unchanged.

### Stage-C — Delete Stage legacy physical-navigation responsibilities

Only after Stage-A/B tests prove all supported Stage execution paths are shared-owned:

Remove Stage ownership from `_handle_primary_card_alignment()`.

Delete the manual Stage main-card horizontal-search block:

- target-level missing timer used only for main-card search;
- `horizontal_scroll_count` main-card search behavior;
- manual alternating left/right drag;
- old "8 misses -> goback_town" main-card recovery.

Before deleting the last recovery slice, characterize whether the old exhaustion behavior is a supported contract or only legacy behavior. If supported mix behavior depends on `goback_town`, preserve that **recovery policy** outside the physical search algorithm instead of keeping a second search implementation.

## Responsibilities that must remain

Even after Stage legacy main-card search is removed:

- `SharedCardNavigator` Stage navigation;
- shared bounded first-card alignment fallback;
- declarative Stage tab routing;
- generic main-card click after FOUND;
- Stage detail-screen detection;
- `_handle_sub_stage_scroll()`;
- sub-stage candidate scanning;
- boss-skull validation;
- Stage start/battle/result flow;
- mix/Dungeon cooldown and scheduler policy.

## Important deletion boundary

Do **not** delete the whole generic reversed `navigation_path` loop.

After shared Stage FOUND, that loop still performs the physical click of the visible Stage card and later owns sub-stage behavior.

The cleanup target is specifically the duplicate **main-card localization/reset/horizontal-search** responsibility.

## Can Stage legacy code be fully removed?

For supported repository-generated Stage routes: **likely yes**.

Evidence is strong because all normal producers create canonical Stage identity, and the only clear supported ownership gap is ordinary mix Stage fallback.

For arbitrary malformed/external dictionaries: **not yet proven**.

To remove every final compatibility branch without semantic ambiguity, first establish one of:

1. a Stage execution-config validation contract; or
2. characterization proving every supported config producer supplies canonical Stage identity.

The preferred Phase 10 path is #2 plus narrowly improved resolver support, avoiding a larger config architecture change.

## Recommended next action

Implement **Stage-A only first**.

It is the smallest behavior-preserving step and makes the later deletion proof much stronger without changing swipe/recovery behavior yet.
