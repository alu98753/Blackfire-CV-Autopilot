Now let me read the key implementation files.
Now let me check the navigation handler for the second DOMAIN_EXPLORE adoption site and the test files.
Let me check the navigation handler around line 714 for the second adoption site.
I have enough evidence. Let me check one more thing - the battle handler adoption at line 56 to verify it already guards with domain identity.
Maximum steps reached. Here is the completed scout localization report based on the 7 files inspected.

# Scout Context

## Relevant files and symbols

- `states/handlers/lobby.py` ??`LobbyHandler._handle_preconditions()` (`:118-133`) is Bug A: `if not stage_farming_enabled and not is_in_dungeon` fires for ALL non-dungeon, stage-farming-disabled configs including `type="domain"`, diverting Domain lobbies to `COLLECT_ONLY` before `START_PRIMARY` can execute. `_handle_start_button()` (`:137-200`) is the committed start retry/timeout owner; no domain awareness needed there.
- `states/state_machine.py` ??`detect_current_state()` (`:1198-1215`) is Bug B: `if pos and (d_btn.endswith("explore_btn.png") or is_domain_mode)` allows `explore_btn.png` match to adopt `DOMAIN_EXPLORE` unconditionally even when `is_domain_mode` is False and `self.config` lacks `domain`. The `is_domain_mode` check at `:1203-1207` already consults `self.config` AND `primary_config` but is only used to gate `exit_to_lobby.png`, not `explore_btn.png`.
- `states/handlers/domain_explore.py` ??`DomainExploreHandler.handle()` (`:33-42`) and `__init__` (`:15-17`): fail-fast `ValueError` when `config.get("domain")` is absent. This is the crash site for Bug B. The handler's fail-fast is an invariant that must be preserved.
- `states/handlers/battle.py` ??`:54-66` already guards DOMAIN_EXPLORE adoption with `is_domain` (checks `config.get("type") == "domain"` or `config.get("domain")`), so this path is already safe.
- `states/handlers/navigation.py` ??`NavigationHandler.handle()` (`:714-720`) is a second unguarded DOMAIN_EXPLORE adoption path: `explore_btn.png` match with only `not need_bag_cleaning` as guard, no domain-identity check. This is a third adoption site alongside `detect_current_state()` and `battle.py:54-66`.
- `tests/test_behavior_lobby_state_machine.py` ??Entirely stage-centric (`config = {"type": "stage", "enable_stage_farming": True}`), zero domain coverage. No test prevents regression of the Lobby bug.
- `tests/test_domain_common_behavior.py` ??Comprehensive domain config/strategy/Tier-4 tests but no `LobbyHandler` integration test and no `UNKNOWN -> DOMAIN_EXPLORE` config-identity test.

## Current control flow

**Bug A (Lobby start blocked):** `NAVIGATING -> LOBBY` -> `LobbyHandler.handle()` -> committed start check -> `_handle_preconditions()` -> `enable_stage_farming == False` (always true for domain configs, confirmed at `config.py:636-637`) -> `is_in_dungeon == False` -> unconditional `COLLECT_ONLY` transition + config swap. The correct `START_PRIMARY` path via `resolve_navigation_context()` at `:71` is never reached.

**Bug B (scene without identity):** `UNKNOWN` -> `detect_current_state()` -> `explore_btn.png` matched at high confidence -> condition `d_btn.endswith("explore_btn.png")` is True -> `DOMAIN_EXPLORE` adopted -> `DomainExploreHandler.handle()` -> `config.get("domain")` is None -> `ValueError` -> supervisor restart loop.

**NavigationHandler path:** `NAVIGATING` -> `NavigationHandler.handle()` -> `explore_btn.png` matched -> `DOMAIN_EXPLORE` adopted without domain identity check (`:714-720`). Third adoption site.

## Existing safety mechanisms

- `is_in_dungeon` guard in `_handle_preconditions()` prevents false COLLECT_ONLY during active dungeon sessions.
- Committed-start non-preemption (`start_first_click_time` + `NavigationProgress.begin/clear`).
- `primary_config.get("domain")` already checked in `is_domain_mode` for `exit_to_lobby.png` gating ??precedent for Bug B fix.
- `battle.py:54-55` already demonstrates the correct `is_domain` guard pattern.
- `DomainExploreHandler` fail-fast `ValueError` is an intentional invariant ??preserve it.
- `config.py:636-637`: `enable_stage_farming` defaults True only for `["stage", "mix", "daily"]`, confirming domain configs always have it False.

## Existing tests

- `test_behavior_lobby_state_machine.py`: covers first-click, retry, disappearance->loading, bread-collection non-preemption, battle-feature transition, timeout reset. All with `{"type": "stage", "enable_stage_farming": True}`. **Zero domain-lobby coverage.**
- `test_domain_common_behavior.py`: covers domain strategy instantiation, Tier-4 fallback, config normalization, profile validation, lord-boss preemption. No `LobbyHandler` integration test; no `detect_current_state()` test with non-domain config + `explore_btn.png`.
## Regression and architecture risks


- Bug A fix must not break `enable_stage_farming=False` COLLECT_ONLY for `stage`/`collect_only` types (SPEC acceptance 4). The `auto_resume_dungeon_on_cd` deepcopy side-effect at `:127-129` is part
Maximum steps for this agent have been reached. Here is the completed scout localization report based on the 7 files inspected within budget.

---

# Scout Context

## Relevant files and symbols

- `states/handlers/lobby.py` ??`LobbyHandler._handle_preconditions()` (`:118-133`) is Bug A: `if not stage_farming_enabled and not is_in_dungeon` fires for ALL non-dungeon, stage-farming-disabled configs including `type="domain"`, diverting Domain lobbies to `COLLECT_ONLY` before `START_PRIMARY` can execute. `_handle_start_button()` (`:137-200`) is the committed start retry/timeout owner; no domain awareness needed there.
- `states/state_machine.py` ??`detect_current_state()` (`:1198-1215`) is Bug B: `if pos and (d_btn.endswith("explore_btn.png") or is_domain_mode)` allows `explore_btn.png` match to adopt `DOMAIN_EXPLORE` unconditionally even when `is_domain_mode` is False and `self.config` lacks `domain`. The `is_domain_mode` check at `:1203-1207` already consults `self.config` AND `primary_config` but is only used to gate `exit_to_lobby.png`, not `explore_btn.png`.
- `states/handlers/domain_explore.py` ??`DomainExploreHandler.handle()` (`:33-42`) and `__init__` (`:15-17`): fail-fast `ValueError` when `config.get("domain")` is absent. This is the crash site for Bug B. The handler's fail-fast is an invariant that must be preserved.
- `states/handlers/navigation.py` ??`NavigationHandler.handle()` (`:714-720`) is a second unguarded DOMAIN_EXPLORE adoption path: `explore_btn.png` match with only `not need_bag_cleaning` as guard, no domain-identity check. Third adoption site.
- `states/handlers/battle.py` ??`:54-66` already guards DOMAIN_EXPLORE adoption with `is_domain` (checks `config.get("type") == "domain"` or `config.get("domain")`), so this path is already safe.
- `tests/test_behavior_lobby_state_machine.py` ??Entirely stage-centric (`config = {"type": "stage", "enable_stage_farming": True}`), zero domain coverage.
- `tests/test_domain_common_behavior.py` ??Comprehensive domain config/strategy/Tier-4 tests but no `LobbyHandler` integration test and no `UNKNOWN -> DOMAIN_EXPLORE` config-identity test.

## Current control flow

**Bug A (Lobby start blocked):** `NAVIGATING -> LOBBY` ??`LobbyHandler.handle()` ??committed start check ??`_handle_preconditions()` ??`enable_stage_farming == False` (always true for domain configs, confirmed at `config.py:636-637`) ??`is_in_dungeon == False` ??unconditional `COLLECT_ONLY` transition + config swap. The correct `START_PRIMARY` path via `resolve_navigation_context()` at `:71` is never reached.

**Bug B (scene without identity):** `UNKNOWN` ??`detect_current_state()` ??`explore_btn.png` matched ??condition `d_btn.endswith("explore_btn.png")` is True ??`DOMAIN_EXPLORE` adopted ??`DomainExploreHandler.handle()` ??`config.get("domain")` is None ??`ValueError` ??supervisor restart loop.

**NavigationHandler path:** `NAVIGATING` ??`NavigationHandler.handle()` ??`explore_btn.png` matched ??`DOMAIN_EXPLORE` adopted without domain identity check (`:714-720`). Third adoption site.

## Existing safety mechanisms

- `is_in_dungeon` guard in `_handle_preconditions()` prevents false COLLECT_ONLY during active dungeon sessions.
- Committed-start non-preemption (`start_first_click_time` + `NavigationProgress.begin/clear`).
- `primary_config.get("domain")` already checked in `is_domain_mode` for `exit_to_lobby.png` gating ??precedent for Bug B fix.
- `battle.py:54-55` already demonstrates the correct `is_domain` guard pattern.
- `DomainExploreHandler` fail-fast `ValueError` is an intentional invariant ??preserve it.
- `config.py:636-637`: `enable_stage_farming` defaults True only for `["stage", "mix", "daily"]`, confirming domain configs always have it False.

## Existing tests

- `test_behavior_lobby_state_machine.py`: covers first-click, retry, disappearance?oading, bread-collection non-preemption, battle-feature transition, timeout reset. All with `{"type": "stage", "enable_stage_farming": True}`. **Zero domain-lobby coverage.**
- `test_domain_common_behavior.py`: covers domain strategy instantiation, Tier-4 fallback, config normalization, profile validation, lord-boss preemption. No `LobbyHandler` integration test; no `detect_current_state()` test with non-domain config + `explore_btn.png`.

## Regression and architecture risks

- Bug A fix must not break `enable_stage_farming=False` COLLECT_ONLY for `stage`/`collect_only` types (SPEC acceptance 4). The `auto_resume_dungeon_on_cd` deepcopy side-effect at `:127-129` is part of that path.
- Bug B fix at `detect_current_state()` must not block cold/restart relocalization into a valid Domain when config IS a valid domain (acceptance 14). The existing `is_domain_mode` variable at `:1203-1207` already handles this correctly ??it just needs to gate `explore_btn.png` too.
- `navigation.py:714-720` is a third unguarded adoption site ??if the fix only covers `detect_current_state()`, a non-domain config navigating could still adopt DOMAIN_EXPLORE.
- Tier-4 Domain fallback, Daily preemption, and temporary dungeon-resume routes may replace `self.config` at runtime while the game is physically inside a Domain scene. The Bug B gate must account for `primary_config` ownership semantics in these temporary routes (SPEC question 9).
- Removing or broadening the `lobby.py` fallback must not change stage/mix/daily `enable_stage_farming=False` ??COLLECT_ONLY behavior, including the deepcopy side-effect.

## Uncertainty

- `test_domain_common_behavior.py` full content was not fully inspected (reached budget); it may already constrain implementation with domain Lobby/explore fixtures.
- Whether `primary_config` is reliably the active Domain owner across Tier-4 fallback, Daily preemption, and temporary dungeon-resume routes (SPEC question 9) ??not fully traced.
- Whether the Bug B gate should live in `detect_current_state()` and `NavigationHandler.handle()` separately, or in a shared Domain execution-context resolver (SPEC question 10).
- The provenance of config identity loss (profile merge corruption vs runtime config replacement) per the Mandatory Config Provenance Verification section ??not investigated (not required for localization audit).

## Minimal proposed change surface

1. **`states/handlers/lobby.py` `:118-119`**: Add route-type guard to the stage-farming fallback, e.g. `and self.machine.config.get("type") != "domain"` (or equivalently check for domain identity). Smallest possible Bug A fix.
2. **`states/state_machine.py` `:1212`**: Require domain identity before adopting `DOMAIN_EXPLORE` from `explore_btn.png`, using the existing `is_domain_mode` variable or equivalent. `exit_to_lobby.png` is already correctly gated.
3. **`states/handlers/navigation.py` `:716-720`**: Add the same domain-identity guard as site 2. Alternatively, extract a shared helper if a third call site emerges.
4. **Tests**: Add `type="domain"` fixtures to `test_behavior_lobby_state_machine.py` for Bug A regression; add `UNKNOWN + explore_btn + config without domain` test for Bug B regression in `test_domain_common_behavior.py` or a focused state-machine test module.

## Recommendation

**GO** ??Both bugs are confirmed at the exact sites the SPEC identifies. The generic three-domain path is verified (`defaults.toml`/`normalize_config`). The minimal surface is 2-3 condition guards plus tests. The `is_domain_mode` variable at `state_machine.py:1203-1207` already demonstrates the correct domain-identity consultation pattern and can be reused for Bug B. The `battle.py:54-55` pattern confirms this guard approach is already precedent in the codebase. No spec changes required; implementer should trace `primary_config` ownership semantics for Tier-4/Daily temporary routes before finalizing the Bug B gate location.
