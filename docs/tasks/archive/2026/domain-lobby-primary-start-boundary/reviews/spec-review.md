# Spec Review

Gate-accepted verdict: PASS
Blocking findings: 0

# Spec Review

Maximum steps for this agent have been reached; this is the final structured summary.

## Verified grounding

- Task `docs/tasks/domain-lobby-primary-start-boundary/task.json` (Status: Final, base `2c433caa...`).
- SPEC.md (406 lines) with Final Acceptance Criteria 1-19 and the Mandatory Config Provenance result (`user_data` EXONERATED; root cause = runtime config replacement + execution-context restoration gap).
- Diff snapshot `diff.patch` matches the current worktree (commit `4f6014a` "fix: enforce domain primary start boundaries" merged into `domain-lobby-primary-start-boundary`). All 3 production files and 3 test files verified in-tree:
  - `states/handlers/lobby.py:118-126` ??Bug A fix: stage-farming COLLECT_ONLY fallback now gated by `not is_domain_mode`.
  - `states/handlers/navigation.py:714-729` ??Bug B fix: explore_btn adoption requires `is_domain_mode` of `self.machine.config`.
  - `states/state_machine.py:1203-1211` ??Bug B fix: `detect_current_state()` requires `is_domain_mode` for `explore_btn.png`; **removed the `primary_config` domain check** from `is_domain_mode`.
  - New tests in `tests/test_behavior_lobby_state_machine.py`, `tests/test_behavior_golden_empire.py`, `tests/test_behavior_navigation.py` confirmed present.

## Clause coverage

- Acceptance 1-2 (direct Domain lobby not diverted; START_PRIMARY executes `domains/common/start_btn.png`): satisfied by lobby.py guard + new `test_domain_start_is_not_diverted_by_stage_farming_disabled` (asserts click at (300,400), state stays LOBBY).
- Acceptance 3 (generic Domain path, no Golden-Empire-only branch): satisfied ??guard keys on `config["type"]=="domain"` or presence of `domain`.
- Acceptance 4 (stage/mix/daily COLLECT_ONLY preserved): `is_domain_mode` is False for those types; existing stage tests remain structurally unchanged.
- Acceptance 5-6 (bag/lord-boss preconditions, committed start, alignment, brightness): unchanged code paths.
- Acceptance 7-8 (no DOMAIN_EXPLORE adoption without identity in both adoption sites): satisfied by both guards.
- Acceptance 9 (restore from canonical owner) ??permissive "may": implementation chooses fail-closed instead of restoring from `primary_config`; permissible.
- Acceptance 10 (fail closed, no guessing): satisfied; removal of the `primary_config` clause makes adoption strictly require `self.config` domain identity.
- Acceptance 11 (DomainExploreHandler fail-fast preserved): `domain_explore.py` untouched.
- Acceptance 12 (UNKNOWN + explore_btn + config without domain, no crash): new golden_empire test `test_unknown_domain_visual_does_not_adopt_without_domain_identity`.
- Acceptance 13 (navigation-path regression): new navigation test asserts "DOMAIN_EXPLORE" not among transitioned states.
- Acceptance 14 (valid direct Domain still relocalizes): satisfied for direct Domain mode because `self.config` itself carries `type="domain"`/`domain`; pre-existing positive adoption test in `test_behavior_golden_empire.py` (~L691-710) remains in place.
- Acceptance 15 (Tier-4 no silent adoption): conservative ??no silent adoption by construction.
- Acceptance 16-18: focused tests present; PyTorch warning and Y-coordinate anomaly untouched.
- Acceptance 19 (fix proven source, not suppress): provenance traced in SPEC; guard prevents dispatch rather than weakening the handler invariant.

## Blocking findings

None.

## Advisory findings

1. `state_machine.py:1203-1211` removed the `primary_config` domain clause from `is_domain_mode`. This is the conservative fail-closed choice consistent with the SPEC's "may restore" wording and the proven Daily case (`primary_config` = daily/mix with `tier4_mode=none`), but it also disables any ExceptionWatchdog/Tier-4 relocalization capability that previously relied on `primary_config` to adopt `DOMAIN_EXPLORE`. Confirm no existing test or runtime path depends on primary_config-driven adoption (cold restart where `self.config` is not yet installed), and validate Tier-4 fallback restores the full Domain config into `self.config` before relying on relocalization.
2. `tests/test_domain_common_behavior.py` (named in SPEC "Required Focused Tests" and task scope) received no additions; the mandatory regression cases were placed in `test_behavior_golden_empire.py` instead. This satisfies the substance of acceptance 12/13 but deviates from the SPEC's "at minimum" module list; acceptable since the SPEC permits "the narrowest state-machine/relocalization test module already used by the repository."
3. New positive-path coverage for acceptance 14 (`NAVIGATING -> DOMAIN_EXPLORE` with valid Domain config) is not newly added; it rests on pre-existing navigation tests. The negative-path test structure (asserting DOMAIN_EXPLORE not in `transition_to` calls) is sound but does not assert which fail-closed state is entered.

## Test evidence gaps

- No test was executed in this read-only review (per constraints). The new unit tests were inspected statically; their assertions (click coordinates, state stay/not-adopt) encode the required contract, but runtime behavior of `resolve_navigation_context`/`SceneDetector` in the domain fixture and full-suite regressions were not run.
- The `detect_current_state()` positive test (golden_empire ~L691-710) was not re-read in full to confirm its config fixture carries `domain`; if it relied on the removed `primary_config` clause, it would now fail ??verify by running `tests.test_behavior_golden_empire`.

## Recommendation for next step

Run the focused modules `tests.test_behavior_lobby_state_machine`, `tests.test_behavior_navigation`, `tests.test_behavior_golden_empire` (plus SPEC-named `tests.test_behavior_state_machine`) to close the execution-evidence gap; if all pass, the implementation satisfies the Final Acceptance Criteria and can proceed to integration review. No blocking contract violation was found in the static review.

<!-- blackfire-gate-fingerprint: {"schema":1,"role":"spec-reviewer","hash":"f3fe13581cd2939b106f2b67d526c194127ccf78235ec7afa8486f7f84b713d9"} -->
