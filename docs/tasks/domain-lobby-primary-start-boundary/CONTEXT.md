Key Bug A and Bug B locations confirmed. Now inspecting the state machine's `detect_current_state` adoption logic, intent routing, and config normalization.
Bug A and B locations confirmed. Now reading config normalization, START_PRIMARY executor, defaults.toml domain entries, and the two focused test files.
Maximum steps for this agent have been reached; tools are disabled and only a text response is permitted below.

I completed the core localization reads (8 files: task.json, SPEC.md, `states/handlers/lobby.py`, `states/handlers/domain_explore.py`, `states/state_machine.py`, `states/navigation_routing.py`, `config.py`, `config/defaults.toml`) plus targeted greps across `states/`, `tests/`, `config/`, `cli/`, and `utils/`. One planned read (`tests/test_domain_common_behavior.py`) was not completed. The scout report follows.

# Scout Context

## Relevant files and symbols

- `states/handlers/lobby.py` ??`LobbyHandler._handle_preconditions()` (`:118-133`) is the confirmed Bug A site: `if not enable_stage_farming and not is_in_dungeon` ??clicks `goback_town`, swaps config to `collect_only`, transitions `COLLECT_ONLY`. No route-type guard exists. `_handle_start_button()` (`:137-200`) executes the committed domain start (clicks configured `lobby_start_btn`, retries, timeout at 5s).
- `states/state_machine.py` ??`detect_current_state()` (`:1198-1215`): `explore_btn.png` match alone (unconditional `if pos and (d_btn.endswith("explore_btn.png") or is_domain_mode)`) drives `UNKNOWN -> DOMAIN_EXPLORE`. Note `is_domain_mode` already consults `self.config` type/domain **and** `self.primary_config.get("domain")` (`:1203-1207`) ??it gates only `exit_to_lobby.png`, giving a ready recovery hook for Bug B.
- `states/handlers/domain_explore.py` ??`DomainExploreHandler.handle()` (`:33-42`) and `_init_strategy()` raise `ValueError` when `config.get("domain")` is absent. `__init__` (`:15-17`) tolerates absence (strategy=None), so the crash lands on the first handler tick ??deterministic contract mismatch confirmed.
- `states/navigation_routing.py` ??`NavigationDecisionExecutor.execute()` (`:311-342`): `START_PRIMARY` invokes `start_callback` (lobby's `_handle_start_button`) or transitions to `STATE_LOBBY`. Intent routing already owns `START_PRIMARY`; no change needed here.
- `config.py` ??`normalize_config()` (`:621-657`): `enable_stage_farming` defaults True only for `stage/mix/daily`; domain modes default False. `"domain" in cfg` routes to `normalize_domain_execution_config()` ??the canonical domain-identity normalization point.
- `config/defaults.toml` ??Golden Empire, Abyssbeast Lair, Coldoath Citadel all `type="domain"`, each with `domain` key and `lobby_start_btn = "domains/common/start_btn.png"` (`:125-154`). Fix is generic across all three; no Golden-Empire branch needed.
- `tests/test_behavior_lobby_state_machine.py` ??entirely stage-centric (config always `{"type": "stage", "enable_stage_farming": True}`, `stages/start.png`); good committed-start semantics coverage, zero domain coverage.
- `tests/test_domain_common_behavior.py` ??exists (glob-confirmed) but content not yet inspected.

## Current control flow

Bug A: `NAVIGATING -> LOBBY` ??`LobbyHandler.handle()`: battle-feature popup checks ??committed-start short-circuit ??`_handle_preconditions()` ??the unguarded stage-farming fallback fires for domain configs (since domain ??`enable_stage_farming == False`), blocking scene detection / START_PRIMARY. The intended path (`resolve_navigation_context` ??`NavigationDecisionExecutor` ??START_PRIMARY ??`_handle_start_button`) is reachable only if preconditions return False.

Bug B: `detect_current_state()` matches `explore_btn.png` with any config ??`STATE_DOMAIN_EXPLORE` ??`DomainExploreHandler.handle()` raises `ValueError` on missing `domain`, restart-loop risk. Sibling adoption paths exist: `states/handlers/navigation.py:714-720` (explore_btn at threshold 0.80, guarded only by `not need_bag_cleaning`, not by config domain identity) and `battle.py:56-66`/`result.py` (domain-identity-guarded, thus already safe).

## Existing safety mechanisms

- `is_in_dungeon` guard in the same `lobby.py` fallback condition.
- Committed-start non-preemption (`start_first_click_time` + `NavigationProgress.begin/clear` of `PRIMARY_NAVIGATION`) ??preserved invariants.
- `primary_config.get("domain")` precedent in `is_domain_mode`: an existing candidate owner for Bug B recovery.
- `config.py normalize_domain_execution_config()` ??canonical domain-config normalization seam.
- Higher-priority preconditions (bag clean, lord-boss town-subflow) execute before the stage-farming check.

## Existing tests

- `test_behavior_lobby_state_machine.py`: first-click/retry/disappearance/timeout semantics, bread-collection non-preemption, battle-feature transition, bag-click helpers. No `type="domain"` fixture.
- `test_domain_common_behavior.py`: exists; coverage unknown (unread).

## Regression and architecture risks

- Removing or broadening the `lobby.py` fallback must not change stage/mix/daily `enable_stage_farming=False` ??COLLECT_ONLY behavior (acceptance 4), including the `auto_resume_dungeon_on_cd` deepcopy side-effect.
- Bug B gating must not break cold/restart relocalization into a domain when the config **is** a valid domain (acceptance 12). Whether `primary_config` is reliably the active Domain owner across Tier-4 fallback, Daily preemption, and temporary dungeon-resume routes is unverified (SPEC question 9).
- `navigation.py:714-720` is a sibling unguarded adoption ??if the fix only covers `detect_current_state()`, a non-domain config navigating could still adopt DOMAIN_EXPLORE.
- Secondary Y-coordinate anomaly: no inspected evidence ties it causally to Bug A/B; consistent with the SPEC's non-goal framing.

## Uncertainty

- `test_domain_common_behavior.py` content unread (step budget); may already constrain implementation with domain Lobby/explore fixtures.
- Whether tests exist asserting `explore_btn` alone ??DOMAIN_EXPLORE regardless of config (SPEC question 11).
- Whether the Bug B gate belongs in `detect_current_state()` or in a shared domain-execution-context resolver; spec permits either.

## Minimal proposed change surface

1. `states/handlers/lobby.py` `_handle_preconditions()` (`:118-133`): gate the stage-farming fallback on non-domain routes only (e.g., `config.get("type") != "domain"`).
2. `states/state_machine.py` `detect_current_state()` (`:1212-1214`): require unambiguous Domain execution identity (config `domain` or verified `primary_config`) before adopting `DOMAIN_EXPLORE`; fail closed without entering the handler.
3. Tests: add a domain fixture to `test_behavior_lobby_state_machine.py`; add a deterministic `UNKNOWN + explore_btn + config without domain` regression test.


GO ??both bugs are confirmed at the exact sites the spec identifies, the generic three-domain path is verified (`defaults.toml`/`normalize_config`), and the minimal surface is two conditions plus tests. Implementer should first read `tests/test_domain_common_behavior.py` and confirm `primary_config` ownership semantics before finalizing the Bug B gate; no spec changes required unless those findings contradict acceptance criteria 10-12.
## Recommendation
