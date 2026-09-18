# Spec Review

Gate-accepted verdict: PASS
Blocking findings: 0

# Spec Review

## Clause coverage

Reviewed Final SPEC (`docs/tasks/active/daily-domain-dungeon-cooldown-fallback/SPEC.md`), `task.json`, the empty gate `status.txt`, `diff.patch` (baseline `origin/main`), and the current working tree.

**Production change (navigation.py:1003-1027)** ??the `target_idx is None` fallback was reshaped from the combined guard `is_in_retreat or is_temp_resume or not self._is_stage_farming_allowed()` into the SPEC's normative precedence:
1. retreat / temp-resume ??`_enter_collect_only_after_dungeon_cooldown` (lines 1006-1010)
2. `not is_daily_pipeline_active() and not _is_stage_farming_allowed()` ??COLLECT_ONLY (lines 1011-1015) ??the only relaxed leg, active Daily no longer intercepted
3. pure `type == "dungeon"` ??COLLECT_ONLY (1016-1020, unchanged)
4. `type == "mix" or is_daily_pipeline_active()` ??`_switch_to_stage_or_back()` (1021-1023, unchanged)

This matches the SPEC's sanctioned guard reshaping without duplicating Daily policy and with no edits to `_switch_to_stage_or_back`, `apply_tier4_fallback_config`, state_machine, or the lobby/mix sibling branch (non-goals all respected).

**Decision-surface delta** ??Enumerating the branch conditions (retreat R, temp T, daily D, allowed A, type TY) shows the only behavioral difference versus baseline is the intended fix: `竅R?岑曷?伶?岑括?劫Y?ungeon` now delegates to `_switch_to_stage_or_back` instead of entering COLLECT_ONLY. All other combinations (including D?劫Y=="dungeon", and both mix/dungeon non-Daily cases) are byte-for-byte equivalent to baseline, satisfying "no production behavior outside this decision boundary changes".

**Invariants** ??Daily Tier-4 Domain (AC1/2): reaches `_switch_to_stage_or_back` ??daily+tier4_domain branch (navigation.py:520-534) ??`apply_tier4_fallback_config()` + `transition_to(STATE_NAVIGATING)`. Stamina retreat / temp resume / pure dungeon / Tier-4 none invariants: structurally preserved (verified via code trace; `_switch_to_stage_or_back:536-541` keeps Tier-4 none ??COLLECT_ONLY).

**Tests** ??Six new tests in `tests/test_behavior_navigation.py` (lines 1293-1540) map 1:1 to AC1+2, AC3, AC4, AC5, AC6, AC7. Fixture `_setup_dungeon_cooldown_screen` drives the greedy loop with `greedy_allowed_indices=[1]` + `dungeon_cooldowns={1: future}` so `target_idx is None` is reached; matcher side-effects and mock `is_daily_pipeline_active`/`apply_tier4_fallback_config` assertions are consistent with the real machine API (`state_machine.py:1721, 2281`).

**Scope** ??Diff touches only the four in-scope paths (SPEC.md, task.json, navigation.py, test file); no out-of-scope production file modified (AC10).

## Blocking findings

None

## Advisory findings

1. **AC8 unverified in this review** ??this gate review is read-only; "existing focused navigation suite passes" (`tests.test_behavior_navigation`) must be confirmed by the declared test run. The six new tests depend on the pre-existing SceneDetector/routing mock infra (neutral scene + `"dungeon"` active tab) to reach the greedy fallback branch; they follow the established suite pattern but were not executed here.
2. **Ordering nuance** ??for a managed-Daily route whose config `type` is `"dungeon"`, the pure-dungeon branch (1016-1020) still precedes Daily delegation and yields COLLECT_ONLY. This is identical to baseline and matches the SPEC's own safe shape (pure-dungeon handling before the daily check), so it is not a deviation; the SPEC's reproduction is a `mix`-typed runtime route, consistent with the sibling guards at navigation.py:971-973/992-994.
3. **Log-only wording** ??the split guard now logs the retreat reason from the first branch and the stage-farming reason from the second; semantically identical to baseline's conditional reason string. No behavioral impact.
4. `status.txt` is empty, so this review is the first recorded gate evaluation; no prior failing evidence exists.

## Test evidence gaps

- Focused test execution of `tests.test_behavior_navigation` (AC8) is pending the implementation gate run; all assertions in the added tests were statically cross-checked against traced control flow and the real machine API but not executed.
- No regression test asserts the non-Daily `mix` + `enable_stage_farming=False` ??COLLECT_ONLY case; the invariant is preserved by trace, and AC6-required coverage (mix + enabled) is present, so this is advisory only.

<!-- blackfire-gate-fingerprint: {"schema":1,"role":"spec-reviewer","hash":"b67e1d5d2fadcfe71ea29f19a3cad874b3a980fb2e90fd224b5520fb25d3afed"} -->
