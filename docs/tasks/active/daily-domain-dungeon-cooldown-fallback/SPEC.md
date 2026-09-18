# daily-domain-dungeon-cooldown-fallback

Status: Draft

## Goal

Fix the verified navigation bug where a managed Daily pipeline with Tier 4 configured as Domain enters `COLLECT_ONLY` after all eligible dungeons are detected on cooldown, instead of handing control back to the existing Daily Tier-4 Domain fallback path.

## Scope

- Touch only the dungeon-cooldown fallback decision path required to fix the reproduced Daily + Tier-4 Domain case.
- Prefer a minimal control-flow correction in `states/handlers/navigation.py`.
- Add focused regression coverage in the existing navigation behavior tests.
- Preserve all existing unrelated navigation behavior.

## Known invariants

- Dungeon availability only determines whether Dungeon can continue/preempt; it must not erase the configured Daily Tier-4 residency.
- For an active Daily pipeline whose primary policy has `tier4_mode == domain`, all eligible dungeons being on cooldown must route through the existing Tier-4 Domain fallback behavior rather than directly selecting `COLLECT_ONLY`.
- Stamina-retreat behavior must remain unchanged.
- Temporary dungeon-resume behavior must remain unchanged.
- Pure `dungeon` mode cooldown fallback must remain unchanged.
- Normal `mix` mode with stage farming enabled must continue to fall back to Stage.
- Daily Tier-4 `none` must continue to be allowed to enter `COLLECT_ONLY`.
- Do not change cooldown detection/OCR/card navigation semantics.
- Do not change scheduler priority between Daily activities.

## Problem evidence

On current `main`, the `target_idx is None` dungeon-selection branch checks:

```python
if is_in_retreat or is_temp_resume or not self._is_stage_farming_allowed():
    ...
    self._enter_collect_only_after_dungeon_cooldown(...)
    return
```

before the later managed Daily branch can call `_switch_to_stage_or_back(...)`.

For Tier-4 Domain, `enable_stage_farming=False` is expected, so this legacy Stage-oriented guard intercepts the flow and enters `COLLECT_ONLY`.

The existing `_switch_to_stage_or_back()` path already contains explicit Daily Tier-4 Domain handling via `apply_tier4_fallback_config()`, so this task should reuse that behavior rather than add a second fallback authority.

## Non-goals

- No navigation.py refactor or decomposition.
- No new scheduler/fallback abstraction.
- No cleanup of similarly worded fallback branches unless a focused test proves they are part of this exact reproduced bug.
- No changes to Stage/Domain configuration schema.
- No changes to `has_available_dungeon()`, cooldown persistence, OCR, scrolling, or card alignment.
- No behavioral changes to stamina retreat, temporary resume, pure dungeon mode, or ordinary mix mode.

## Provisional acceptance criteria

1. Given an active Daily pipeline with primary `tier4_mode=domain`, `enable_stage_farming=False`, and no eligible dungeon target, navigation does not transition to `COLLECT_ONLY`.
2. The same case reaches the existing Daily Tier-4 Domain fallback path, applies the Tier-4 fallback config, and remains/returns to navigation toward Domain.
3. A focused regression test reproduces the old failure and passes after the fix.
4. Existing focused navigation tests remain green.
5. Focused regression coverage demonstrates no change to:
   - stamina-retreat cooldown fallback;
   - temporary dungeon-resume cooldown fallback;
   - pure dungeon cooldown fallback;
   - mix-mode all-dungeons-cooldown -> Stage behavior;
   - Daily Tier-4 none -> Collect Only behavior.
6. No production files outside the minimal navigation decision path are changed unless required by the focused test fixture.

## Uncertainty

- The same Stage-oriented predicate appears in another lobby/mix fallback branch. It is intentionally out of scope unless Scout/code evidence shows that branch is reachable for this exact managed Daily Tier-4 Domain reproduction.
- Final SPEC should confirm the smallest safe ordering/guard change after Scout reviews the current intent-routing and managed-Daily gating around these branches.
