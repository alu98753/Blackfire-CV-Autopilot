# Regression Review

Gate-accepted verdict: PASS
Blocking findings: 0

# Regression Review

## Behavior-preservation assessment
The diff (SPEC.md + task.json artifacts, `states/handlers/navigation.py` guard reshape, `tests/test_behavior_navigation.py` additions) implements the Final SPEC's required minimal control-flow correction.

Production change verified in `states/handlers/navigation.py:1003-1027` (`target_idx is None` branch): the legacy compound guard `is_in_retreat or is_temp_resume or not self._is_stage_farming_allowed()` was split into (1) retreat/temp-resume ??`_enter_collect_only_after_dungeon_cooldown()` and (2) `not is_daily_pipeline_active() and not _is_stage_farming_allowed()` ??collect_only, with the pure-dungeon and mix/daily delegation legs untouched. Behavior preservation table vs old code:

- Stamina retreat / temporary dungeon resume: both old and new ??collect_only (first guard), tier4 fallback never applied. Preserved.
- Pure dungeon (`type=="dungeon"`), daily or not, stage farming allowed or not: new code still reaches the `type=="dungeon"` branch ??collect_only in every case, identical to old outcome. Preserved.
- Non-daily mix + `enable_stage_farming=True`: guard skipped ??`_switch_to_stage_or_back`. Preserved.
- Non-daily mix + `enable_stage_farming=False`: guard 2 ??collect_only. Preserved.
- Daily active + `tier4_mode=domain` + stage farming disabled (the reproduced bug): now reaches `_switch_to_stage_or_back` ??`apply_tier4_fallback_config()` + `transition_to(STATE_NAVIGATING)` (nav lines 520-534, unchanged). Intended fix; matches AC 1-2.
- Daily active + `tier4_mode=none`: delegates to `_switch_to_stage_or_back`, which collect_only's at line 537-541. Net outcome preserved (SPEC invariant "Tier-4 none remains COLLECT_ONLY"); with `quest_scheduler` present the pre-existing dynamic-reschedule leg (line 515-518) may run first, but that behavior is old, untouched, and already reachable from sibling cooldown paths (lines 971-973, 992-994) ??this branch is now aligned with them, as SPEC requires.
- No change to `_switch_to_stage_or_back`, `apply_tier4_fallback_config`, `state_machine.py`, or cooldown detection (non-goals respected). No shared mutable state, watchdog timers, or notify_ui_progress semantics touched. The mojibake visible in `diff.patch` is a patch-encoding rendering artifact; the actual repo file contains valid UTF-8 Chinese strings.

## Blocking findings
None.

## Advisory findings
1. **Test-harness fragility (test fidelity)**: the six new tests do not stub `handler.scene_detector` (unlike existing suite members at lines 170-172, 205-207, 931-932); they rely on the real `SceneDetector` auto-constructed at nav line 664-668 against a MagicMock machine. Whether `"dungeon" in scene.active_tabs` and the greedy scan settle as the fixture intends should be confirmed by running `tests.test_behavior_navigation` (AC 8). Failures would fail loudly (fallback/transition assertions), except `test_ordinary_mix_mode_stage_farming_enabled_switches_to_stage`, whose `mouse.click(648,715)` assertion could pass via the later lobby/mix sibling click as well, weakening branch isolation.
2. **Daily route with `type=="dungeon"`**: the fix does not change this shape (collect_only before and after, due to the `type=="dungeon"` branch preceding the daily delegation). Behavior is unchanged vs baseline, consistent with the SPEC reproduction which presupposes a non-`dungeon` runtime type; worth confirming production managed-Daily quest routes are `type` mix/daily so AC-1 fixtures match production configuration shape.
3. **Assertion rigor**: `transition_to.assert_called_with(...)` verifies only the last recorded call under MagicMock semantics; in the collect-only tests an earlier spurious transition would not be caught. Minor testing nit, not a behavior risk.

Suggested validation: run `tests.test_behavior_navigation` (focused target) to confirm the six new regressions exercise the intended branch and pass; optionally stub `handler.scene_detector` with an explicit `SceneInfo` (dungeon tab active) to harden isolation.

<!-- blackfire-gate-fingerprint: {"schema":1,"role":"regression-reviewer","hash":"2eecd005fe2b52428dcb10a97425fac258491bd2074d157ea83d870283c42ffd"} -->
