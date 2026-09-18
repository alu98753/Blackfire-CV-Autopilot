# daily-domain-dungeon-cooldown-fallback

Status: Final

## Goal

Fix the verified navigation bug where a managed Daily pipeline with Tier 4 configured as Domain enters `COLLECT_ONLY` after all eligible dungeons are detected on cooldown.

The correct behavior is to preserve the existing Daily scheduling/fallback ownership and allow the existing `_switch_to_stage_or_back()` path to decide the next residency. For Tier-4 Domain, that existing path must restore the Tier-4 Domain fallback and continue navigation toward Domain.

## Verified reproduction

The reproduced failure requires all of the following:

- Daily pipeline is active.
- The user configured Tier 4 residency as Domain.
- The current Daily/Dungeon route has `enable_stage_farming=False`.
- Dungeon selection has completed enough scanning to conclude that no eligible dungeon target is available, so `target_idx is None`.
- The runtime is not in stamina retreat.
- The runtime is not in temporary dungeon-resume mode.

On current code, the `target_idx is None` branch evaluates:

```python
if is_in_retreat or is_temp_resume or not self._is_stage_farming_allowed():
    ...
    self._enter_collect_only_after_dungeon_cooldown(...)
    return
```

Because Tier-4 Domain legitimately uses `enable_stage_farming=False`, the Stage-oriented predicate becomes true and performs an early return to `COLLECT_ONLY` before the managed Daily fallback logic can run.

This is the bug.

## Existing authority to preserve

The task must reuse the existing fallback authority in `NavigationHandler._switch_to_stage_or_back()`.

That function already owns the relevant Daily fallback semantics:

- active Daily + Tier-4 Domain -> use the existing Tier-4 Domain fallback path via `apply_tier4_fallback_config()`, then continue in `STATE_NAVIGATING`;
- active Daily + Tier-4 none -> `COLLECT_ONLY`;
- otherwise, where stage farming is permitted -> Stage fallback;
- existing Daily dynamic rescheduling remains authoritative where currently applicable.

Do not duplicate this policy in the `target_idx is None` branch.

## Required control-flow correction

Only the legacy `enable_stage_farming=False` interception in the `target_idx is None` dungeon-selection path should be relaxed for an active Daily pipeline.

The implementation must preserve this precedence:

```text
1. stamina retreat / temporary dungeon resume
   -> existing COLLECT_ONLY behavior remains authoritative

2. pure dungeon mode cooldown fallback
   -> existing COLLECT_ONLY behavior remains authoritative

3. managed Daily / existing mix fallback delegation
   -> delegate to _switch_to_stage_or_back()

4. ordinary non-Daily stage-farming permission behavior
   -> unchanged
```

An implementation may use any small, equivalent guard reshaping, but it must not broadly reorder unrelated navigation decisions.

A safe semantic shape is:

```python
if is_in_retreat or is_temp_resume:
    # preserve existing COLLECT_ONLY behavior
    ...

if not self.machine.is_daily_pipeline_active() and not self._is_stage_farming_allowed():
    # preserve ordinary non-Daily behavior
    ...

# existing pure-dungeon handling remains

if self.machine.config.get("type") == "mix" or self.machine.is_daily_pipeline_active():
    self._switch_to_stage_or_back(...)
    return
```

This is illustrative, not a requirement to copy the exact syntax.

## Scope

Production scope:

- `states/handlers/navigation.py`
  - only the `target_idx is None` dungeon-selection fallback decision needed to correct this reproduced bug.

Test scope:

- `tests/test_behavior_navigation.py`
  - add focused regression coverage for the reproduced Daily + Tier-4 Domain failure;
  - add or preserve narrowly targeted boundary coverage necessary to prove the nearby behaviors below remain unchanged.

Task artifacts may be updated as normal under:

- `docs/tasks/active/daily-domain-dungeon-cooldown-fallback/`

## Required invariants

### Daily Tier-4 Domain

Given:

- Daily pipeline active;
- primary policy `tier4_mode=domain`;
- explicit `enable_stage_farming=False`;
- all eligible dungeons unavailable / `target_idx is None`;
- not stamina retreat;
- not temporary dungeon resume;

Then:

- navigation must not enter `STATE_COLLECT_ONLY` because Stage farming is disabled;
- control must reach the existing Daily fallback authority;
- the existing Tier-4 Domain fallback must be applied;
- navigation must remain/return in `STATE_NAVIGATING` toward Domain.

### Stamina retreat

If stamina retreat is active and all relevant dungeons are unavailable:

- existing behavior remains unchanged;
- it must continue to use the existing cooldown/collect-only retreat behavior;
- it must not be redirected into Tier-4 Domain merely because Daily is active.

### Temporary dungeon resume

If `is_dungeon_temporary_resume=True` and all relevant dungeons are unavailable:

- existing behavior remains unchanged;
- it must continue to use the existing collect-only cooldown behavior;
- it must not be redirected into Tier-4 Domain merely because Daily is active.

### Pure dungeon mode

For `config.type == "dungeon"` with no eligible dungeon target:

- existing cooldown fallback remains unchanged;
- it may continue entering `COLLECT_ONLY` according to the existing contract.

### Ordinary mix mode

For ordinary non-managed-Daily `mix` behavior:

- `enable_stage_farming=True` must continue allowing fallback to Stage;
- `enable_stage_farming=False` semantics must remain unchanged.

### Daily Tier-4 none

For active Daily with primary `tier4_mode=none`:

- the existing path may continue entering `COLLECT_ONLY`;
- this task must not convert Tier-4 none into Stage or Domain.

## Explicit non-goals

Do not:

- refactor or decompose `navigation.py`;
- rename helpers solely for clarity;
- introduce a new scheduler, fallback-policy object, or arbitration abstraction;
- change `_switch_to_stage_or_back()`;
- change `apply_tier4_fallback_config()`;
- change `states/state_machine.py`;
- change Daily scheduler priority;
- change `has_available_dungeon()`;
- change cooldown persistence or cooldown timing;
- change OCR or cooldown-sign recognition;
- change dungeon card scrolling/alignment;
- change Domain navigation implementation;
- change the later lobby/mix sibling fallback branch near the existing `allow_mix_tab_switching` logic;
- clean up other similar-looking fallback branches unless a focused regression proves they are required for this exact bug.

The Scout confirmed that the later lobby/mix sibling branch is not part of the reproduced managed-Daily path and is therefore protected out-of-scope.

## Acceptance criteria

1. A focused regression test reproduces the original failure with:
   - Daily active;
   - Tier-4 Domain;
   - explicit `enable_stage_farming=False`;
   - all eligible dungeons unavailable / no target;
   - no retreat;
   - no temporary resume.

2. That regression proves:
   - `COLLECT_ONLY` is not selected by the legacy Stage-farming guard;
   - the existing fallback path is reached;
   - Tier-4 Domain fallback config is applied;
   - navigation returns/remains in `STATE_NAVIGATING`.

3. Focused regression coverage proves stamina-retreat behavior remains unchanged.

4. Focused regression coverage proves temporary dungeon-resume behavior remains unchanged.

5. Focused regression coverage proves pure dungeon cooldown fallback remains unchanged.

6. Focused regression coverage proves ordinary mix + Stage-enabled fallback remains unchanged.

7. Focused regression coverage proves Daily Tier-4 none still reaches `COLLECT_ONLY`.

8. The existing focused navigation suite declared by `task.json` passes.

9. No production behavior outside this decision boundary changes.

10. No production files outside the minimal navigation decision path are modified unless a test fixture requires a narrowly justified change; any such change must be surfaced before implementation is considered complete.

## Implementation guidance

Prefer the smallest behavioral patch possible.

The intended architecture is not:

```text
Dungeon decides Domain
```

It is:

```text
Dungeon determines "no eligible dungeon"
        |
        v
existing Daily fallback authority
        |
        +-- Tier4 Domain -> Domain
        +-- Tier4 none   -> Collect Only
        +-- Stage policy -> Stage where allowed
```

The implementation must therefore remove only the premature Stage-permission interception for managed Daily while preserving the higher-priority retreat/temporary-resume guards.

## Verification

Run the focused test target declared in `task.json`:

```text
tests.test_behavior_navigation
```

If Gate is used after implementation, it must review against this Final SPEC and the unchanged non-goals above.

## Remaining uncertainty

No material architecture uncertainty remains for implementation.

The only implementation freedom is the exact minimal boolean/control-flow expression used to preserve the required precedence. Behavioral outcomes above are normative.
