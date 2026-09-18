Now let me look at the tests and state machine helpers referenced by the decision path.
The tests grep hit the whole tests directory. Let me target the navigation test file directly, plus read the state machine helpers.
Maximum steps for this agent have been reached, so I'm stopping exploration and delivering the scout report from the evidence already gathered. No tools were used to produce this final report.

# Scout Context

Task: `daily-domain-dungeon-cooldown-fallback` ??prevent managed Daily + Tier-4 Domain from entering `COLLECT_ONLY` when all eligible dungeons are on cooldown; route through the existing Tier-4 Domain fallback instead. Spec status: Draft (implementation blocked until Final).

## Relevant files and symbols
Files inspected (4 of 8 budget used):
- `docs/tasks/active/daily-domain-dungeon-cooldown-fallback/task.json` ??scope, non-goals, focused test target (`tests.test_behavior_navigation`).
- `docs/tasks/active/daily-domain-dungeon-cooldown-fallback/SPEC.md` ??bug claim and acceptance criteria.
- `states/handlers/navigation.py` ??the decision path: `_enter_collect_only_after_dungeon_cooldown` (:448), `_is_stage_farming_allowed` (:477), `_switch_to_stage_or_back` (:493), and the buggy `target_idx is None` branch (:1003-1025). The lobby/mix sibling branch (:1083-1093).
- `states/state_machine.py` ??`apply_tier4_fallback_config` (:1721-1746): restores the user Tier-4 baseline and arms preemption; only self-transitions to `COLLECT_ONLY` when `tier4_mode == none` or type `collect_only`. Confirms `tier4_mode=domain` keeps navigating after the fallback. Also located `is_daily_pipeline_active` (:2281) and `evaluate_and_schedule_daily_pipeline` (:2513).

## Current control flow
Inside the greedy dungeon branch, when no eligible dungeon yields `target_idx`:
- `target_idx is None` (:1003) computes `is_in_retreat`/`is_temp_resume`, then guards: `is_in_retreat or is_temp_resume or not self._is_stage_farming_allowed()` (:1006) ??`_enter_collect_only_after_dungeon_cooldown` (:1012).
- Only survivors of that guard reach `type == "dungeon"` ??collect_only (:1014) or `type == "mix" or is_daily_pipeline_active()` ??`_switch_to_stage_or_back` (:1019).
- For a managed Daily quest with `tier4_mode=domain`, `enable_stage_farming=False` is expected, so `not self._is_stage_farming_allowed()` is True and the branch exits to `COLLECT_ONLY` before :1019 can run. This is exactly the SPEC's "intercepting guard."
- By contrast, `_switch_to_stage_or_back` internally orders the managed-Daily Tier-4 Domain route (:520-534 ??`apply_tier4_fallback_config()` + re-enter `STATE_NAVIGATING`) *before* its own `_is_stage_farming_allowed()` gate (:544). The sibling specific-target cooldown paths (:971-973, :992-994) already route active-Daily via `_switch_to_stage_or_back`, so only the `target_idx is None` branch is out of alignment ??matching the SPEC's "single fallback authority" premise.
- The :1083-1093 sibling gate sits inside `allow_mix_tab_switching = (not is_managed_daily) or is_tier4_fallback` (:1057) and `type == "mix"` only; for a managed Daily (non-mix runtime key) it is not reachable ??consistent with SPEC's out-of-scope note.

## Existing safety mechanisms
- `_switch_to_stage_or_back()` already owns the Daily Tier-4 Domain authority with correct precedence; it also handles managed-Daily dynamic rescheduling (:515) and Tier-4 `none` ??collect_only (:537).
- Stamina-retreat, temp-resume, pure `dungeon`, ordinary `mix`?tage, and Tier-4 `none` invariants are structurally preserved as long as the fix only relaxes the `enable_stage_farming=False` leg for managed-Daily, not the retreat/temp legs.
- `apply_tier4_fallback_config()` is idempotent (no-op when fallback already active) and armed with preemption ??safe to re-enter repeatedly.

## Existing tests
- `tests/test_behavior_navigation.py` is the declared focused surface but its cooldown-fallback fixtures could not be verified within budget (broad grep results only). Must be inspected during implementation.
- `_is_stage_farming_allowed()` already hard-prohibits stage farming during stamina retreat (:482) and temporary dungeon resume (:484) ??reusable guard boundary.

- `tests/test_behavior_daily_preemption.py` covers `apply_tier4_fallback_config()` lifecycle: preemption arming, idempotent re-apply, and all-quests-cooling ??fallback switch ??directly relevant regression guards for the fix.
## Regression and architecture risks
- Ordering risk: naive reorder (route managed Daily to `_switch_to_stage_or_back` unconditionally before :1006) would send stamina-retreat/temp-resume Daily flows into Tier-4 fallback, violating the retreat/temp invariants. The safe shape is to keep the retreat/temp legs of :1006 and relax only the `not self._is_stage_farming_allowed()` leg for `is_daily_pipeline_active()`, letting existing :1019 handle routing.
- `_switch_to_stage_or_back` may consume the frame via `evaluate_and_schedule_daily_pipeline` reschedule before reaching the Tier-4 branch ??intended existing behavior, not to be disturbed.
- Architecture drift: SPEC correctly scopes out the :1083 lobby/mix sibling; evidence confirms it is unreachable for managed Daily, so leaving it untouched is safe.
- No shared-state/concurrency concerns identified on this single-threaded navigation path (only the watchdog-shared timers, untouched by this fix).

## Uncertainty
- The precise content of `tests/test_behavior_navigation.py` cooldown-fallback fixtures is unverified within budget; acceptance criterion 3 needs the exact reproduction fixture confirmed there.
- Whether stamina retreat + Daily + Tier-4 Domain should also reach Tier-4 fallback (vs. collect-only) is a policy detail not stated in the SPEC; currently the retreat leg wins. Confirm intended semantics before Final.
- The `enable_stage_farming` default for `daily` inside `_is_stage_farming_allowed` (default_farm True for `daily`) interacts with the fix: a Daily config with no explicit `enable_stage_farming` already passes the guard. Only explicit `False` reproduces the bug.

## Minimal proposed change surface
- `states/handlers/navigation.py`, `target_idx is None` branch near lines 1003-1013 only: refine the guard so `not self._is_stage_farming_allowed()` no longer intercepts an active managed Daily pipeline, while retreat/temp legs and the :1019 `_switch_to_stage_or_back` routing remain untouched.
- `tests/test_behavior_navigation.py`: one focused regression test reproducing Daily Tier-4 Domain + all-dungeons-cooldown ??asserts no `COLLECT_ONLY` and re-entry into `STATE_NAVIGATING` with fallback config applied.
- No changes to `state_machine.py`, `_switch_to_stage_or_back`, or the :1083 lobby/mix branch.

## Recommendation
GO WITH SPEC CHANGES ??the intercepting guard is precisely located (:1006) and the existing `_switch_to_stage_or_back` Tier-4 ordering is verified, so the defect and minimal surface are confirmed. SPEC changes recommended: (a) pin down retreat/temp-resume semantics for the managed-Daily Tier-4 case, and (b) note the explicit-`False` `enable_stage_farming` precondition so the regression fixture is unambiguous.
