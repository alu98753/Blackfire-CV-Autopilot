# Spec Review

Gate-accepted verdict: PASS
Blocking findings: 0

# Spec Review

## Clause coverage

- **Scope & status**: Task `domain-common-template-decoupling` status Final; base `origin/main`; diff snapshot contains config.py, config/defaults.toml, cli/, states/domains/*, states/handlers/*, states/state_machine.py, utils/tier4_config.py, utils/scene_snapshot.py, tests/, template asset renames, and the SPEC/task docs.
- **2.1 Catalog authority (existence = unmerged defaults snapshot)**: `get_canonical_defaults()`/`get_canonical_domain_mode_configs()`/`is_supported_domain()` read `_DEFAULTS_MANAGER.snapshot()` (unmerged); `get_domain_mode_configs()` merges profile-effective values only for canonical keys. `validate_profile_mode_overrides()` rejects undeclared mode keys, structural `type` tampering, and `domain` identity tampering, wired into `get_defaults_config()` before merge.
- **2.1.3 / 2.2 / AC 11-13 (strategy registry, no golden fallback)**: `states/domains/__init__.py` verified in tree ??`get_domain_strategy()` raises `ValueError` for undeclared/typo domains, dispatches `GoldenEmpireStrategy` only for golden_empire, otherwise `GenericDomainStrategy(handler, domain_name=...)`. `DOMAIN_STRATEGIES` reduced to a pure override registry. `DomainExploreHandler` (verified in tree) raises `ValueError` when `machine.config["domain"]` is missing; no `domain_name` identity compatibility fallback, no `"golden_empire"` default.
- **2.3 / 2.4 (common paths, treasure semantics, SSOT)**: All four assets exist under `templates/domains/common/` (explore_btn.png, open.png, find_treasure.png, treasure.png) and are absent from `templates/domains/golden_empire/` (only entry.png remains, a legitimate per-domain asset). `utils/scene_snapshot.py` maps `domains/common/explore_btn.png ??DOMAIN_EXPLORE_BTN`. `config/defaults.toml` `explore_priorities = ["domains/common/explore_btn.png"]`; `[defaults.activities]` and `[primary_modes.daily]` declare `enable_domain`; golden_empire mode does not carry `enable_domain`; `enable_golden_empire` removed. `DomainTreasureSubflow` (open = actionable; find_treasure/treasure = scene evidence with no click/guess) is exercised by new scenario A/B/C tests.
- **3.2/3.3/3.4 (policy ownership, seam assembly, required contract)**: `validate_daily_domain_policy()` fail-fasts on `enable_domain == false` and missing/blank `tier4_domain`; `build_tier4_fallback_config()` no longer falls back to `DEFAULT_TIER4_DOMAIN` and validates the selected key against canonical domain modes; `build_domain_execution_route()` roots the route in deepcopy of the selected domain config (Daily execution-like fields cannot override domain SSOT) and strips `enable_domain`. `normalize_domain_execution_config()` is the single provider of canonical common defaults; `normalize_config()` applies it for domain-type configs. `enable_lord_boss` dual ownership implemented via `has_pending_daily_activity(include_lord_boss=False)` + direct read `config["enable_lord_boss"]` (KeyError on unnormalized config is the intended fail-fast, covered by tests). `_build_tier4_fallback_config()`/`apply_tier4_fallback_config()` raise `RuntimeError` without a valid `primary_config`.
- **AC-8/AC-10 / obsolete references**: Grep across the tree shows `enable_golden_empire`, `DEFAULT_TIER4_DOMAIN`, `TIER4_DOMAIN_OPTIONS`, and the four old `domains/golden_empire/{explore_btn,open,find_treasure,treasure}.png` paths occur only in (a) negative assertions inside tests and (b) historical/SPEC doc prose ??zero production (`states/`, `utils/`, `config/`, `cli/`) dependencies remain.
- **Focused tests**: task-declared files exist, including new `tests/test_domain_common_behavior.py` covering strategy dispatch, fail-fast, treasure semantics, catalog discovery, tier4 route assembly, and SSOT invariants; existing golden_empire/daily_tier4/dungeon_relaunch tests were updated to the common paths.

## Blocking findings

None.

## Advisory findings

- `states/domains/base_domain.py` imports `os` at module top while `handle_explore_click` still gates on `os.path.exists` before matching; this is a soft maintainability note (path-existence short-circuiting), not a contract violation.
- `cli/arguments.py` help text composed from `PRIMARY_MODES` labels plus generic suffix: acceptable per AC-5 but the fallback `cfg.get('name', k)` means any mode missing `name` silently degrades to its key; advisory only, since domain modes are structurally required to declare `name`.
- Docs outside the task (`docs/storys/daily_tier4_player_route_story.md` still mentions `TIER4_DOMAIN_OPTIONS` and `docs/tasks/BACKLOG.md` churn) are historical/context-only text; SPEC classifies such prose separately from live contracts, so it is not blocking.

## Test evidence gaps

- No evidence from actually running the focused suite was collected in this review (read-only); the subset relevant to the changed runtime policy is `tests/test_domain_common_behavior.py`, `tests/test_behavior_daily_tier4.py`, `tests/test_behavior_golden_empire.py`, `tests/test_dungeon_relaunch_recovery.py`, plus `tests/test_behavior_navigation.py`/`tests/test_profile_config_overlay.py` for the navigation/overlay seams. Node bootstrap items in BACKLOG.md are unrelated to this task's contract.
- The unmerged `_DEFAULTS_MANAGER.snapshot()` path and the profile-overlay rejection path are covered by unit tests but not by an end-to-end runtime check in this review; treat as residual integration confidence, not a defect signal.

<!-- blackfire-gate-fingerprint: {"schema":1,"role":"spec-reviewer","hash":"6ff89eca4108a8a670858af91c91e5c72150f992860cbcd34c5911b76e212f2e"} -->
