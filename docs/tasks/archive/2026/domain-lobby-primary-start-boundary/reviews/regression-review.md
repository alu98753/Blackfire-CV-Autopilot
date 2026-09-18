# Regression Review

Gate-accepted verdict: PASS
Blocking findings: 0

# Regression Review

## Behavior-preservation assessment

The diff changes exactly the two Domain runtime-handoff boundaries the Final SPEC owns, and preserves the surrounding contracts I verified in the worktree:

- **Bug A (lobby):** `states/handlers/lobby.py:_handle_preconditions()` now skips the `enable_stage_farming == false -> COLLECT_ONLY` fallback when the runtime config is Domain-owned (`type == "domain"` or a `domain` key). Canonical domains (`defaults.toml:127-154`) carry `type="domain"`, `domain=<id>`, and `lobby_start_btn="domains/common/start_btn.png"`, so the intended path is preserved: scene detection -> `resolve_navigation_context` -> `START_PRIMARY` decision -> `start_callback` -> `_handle_start_button()` (reads `config["lobby_start_btn"]`). Stage/mix/daily configs have no `domain` key and use `tier4_domain` (not `domain`), so the legacy fallback still applies to them (SPEC acceptance 4). `auto_resume_dungeon_on_cd` defaults are `false` for all canonical domains; the cooldown-return capture in the omitted branch was never an exercised Domain flow.
- **Bug B (adoption identity):** both `GameStateMachine.detect_current_state()` (`states/state_machine.py:1203-1214`) and `NavigationHandler.handle()` (`states/handlers/navigation.py:716-729`) now require `is_domain_mode` from `self.machine.config` before adopting `DOMAIN_EXPLORE` from `explore_btn.png`/`exit_to_lobby.png`. `DomainExploreHandler.handle()` reads only `self.machine.config["domain"]` and raises `ValueError` otherwise, so the removed `primary_config.get("domain")` term never backed a *working* adoption flow (it would have crashed downstream); the change converts a deterministic crash into SPEC-mandated fail-closed behavior. The Tier-4 Domain route (`utils/tier4_config.py:43-58`) installs `type="domain"` + `domain=<id>` into the runtime config, so Tier-4 domain adoption still works (SPEC criterion 15). `battle.py:54-66` already used the identical guard pattern and is unchanged.
- **Tests:** existing `test_behavior_golden_empire.py::test_unknown_state_detects_golden_empire_scene` uses a fixture config with `type="domain"`/`domain="golden_empire"`, so it still passes under the new gate. New regressions cover the exact SPEC crash contract (`UNKNOWN` + `explore_btn` + config without `domain`), the navigation sibling path, and the domain lobby start; the lobby test fixture `rect={"left":100,"top":100}` makes `click(300,400)` from match `(200,300)` consistent with `_handle_start_button()`.

## Blocking findings

None

## Advisory findings

- The `is_domain_mode` heuristic (`type == "domain" or bool(domain)`) is now duplicated in three production sites (`lobby.py`, `navigation.py`, `state_machine.py`). Current behavior is consistent (Tier-4 route carries both keys; daily uses `tier4_domain`, never `domain`), but a shared helper would prevent future drift. SPEC Notes explicitly permit either shape, so this is non-blocking.
- Fail-closed for a non-Domain runtime config physically inside a Domain scene routes through the pre-existing `UNKNOWN` -> `unknown_scene_count` -> relaunch mechanism (`state_machine.py:1233-1249`). This is the bounded recovery the SPEC authorizes (criterion 11) and replaces the prior unhandled-`ValueError` crash loop; worth confirming at runtime that the number of UNKNOWN frames before relaunch stays within the configured bound for this scenario.
- The Domain lobby test does not assert the `NavigationProgress.begin` intent bookkeeping on the domain start path; committed-start semantics are covered by existing stage tests, so the gap is minor and non-blocking.

Confidence in PASS: grounded in direct reads of all changed call sites, the handler invariant, defaults.toml, tier4_config.py, and the impacted tests.

<!-- blackfire-gate-fingerprint: {"schema":1,"role":"regression-reviewer","hash":"3addb50cc89f2dbf23c94b3adcc01a12301ea77e89113eace9e85bd02a59ff5d"} -->
