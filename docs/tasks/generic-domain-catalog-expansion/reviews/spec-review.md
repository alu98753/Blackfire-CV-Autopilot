# Spec Review

Gate-accepted verdict: PASS
Blocking findings: 0

# Spec Review

## Clause coverage

Spec: `docs/tasks/generic-domain-catalog-expansion/SPEC.md` (Final), scope per `task.json`, diff snapshot `.runtime/ai_gate/generic-domain-catalog-expansion/diff.patch`, baseline `origin/main`.

**Invariant 1 / Acceptance 1-3 (catalog authority + structural contract):** `config/defaults.toml:136-154` declares `[primary_modes.abyssbeast_lair]` (name 瘛望殿?詨楷) and `[primary_modes.coldoath_citadel]` (name 撖??文) with all 8 required structural fields (`name`, `type="domain"`, `domain`, non-empty `navigation_path`, `domain_tab_btn`, `domain_tab_after_btn`, `domain_entry_btn`, `lobby_start_btn`). Entry templates referenced (`domains/abyssbeast_lair/abyssbeast_lair.png`, `domains/coldoath_citadel/coldoath_citadel.png`) exist on disk. Display names match SPEC 禮Final Domain configuration contract and the confirmed task identities.

**Invariant 2 / Acceptance 4 (generic dispatch):** `states/domains/__init__.py:7-25` ??`DOMAIN_STRATEGIES` still registers only `golden_empire`; both new IDs flow through `get_domain_strategy` to `GenericDomainStrategy`; undeclared IDs fail fast with `ValueError`. No Python registry additions in the diff.

**Invariant 5-6, Acceptance 8-9, constraint 5-6 (common defaults + GE cleanup):** `golden_empire` raw TOML (defaults.toml:125-134) retains `bread_cost = 3` and no longer declares `explore_priorities`, `result_buttons`, `domain_reset_max_attempts`, `enable_lord_boss`. `config.py:432-438` `CANONICAL_DOMAIN_COMMON_DEFAULTS` + `normalize_domain_execution_config` (config.py:486-495) inject the canonical values; `validate_domain_execution_config` (config.py:441-483) enforces the 8-field structure. Acceptance 10 (`bread_cost` unchanged) holds.

**Acceptance 5-7 (CLI / Tier4 discovery):** Discovery is dictionary-driven via `get_canonical_domain_mode_configs()`; no Python static lists were edited. Updated tests exercise tier4 options, interactive=False tier4 assembly (`?妍 "瘥?貉?隞餃? (Tier 4: 瘛望殿?詨楷)"`), and CLI `--mode` acceptance for both new IDs.

**Stale test repairs (SPEC 禮Stale regression tests, acceptance 11, invariant 9 / constraint 4):**
- Greedy dungeon: `tests/test_behavior_main_entrypoint.py:114` derives `str(len(DUNGEON_NAMES) + 1)`, which exactly matches production `cli/dungeon_setup.py:21-22` (`num_dungeons = len(DUNGEON_NAMES)`, `greedy_choice_str = str(num_dungeons + 1)`). No production change to dungeon selection.
- Runtime loop refresh-order: `tests/test_behavior_main_entrypoint.py:348` sets `has_pending_timeout_recovery.return_value = False`, matching the guard in `runtime/loop.py:62-65`; pause-controller mocks mirror loop.py:54/57/66 (`check_manual_exit_triggered`, `check_manual_restart_triggered`, `check_toggle_triggered`). Assertions still verify `refresh_config_at_safe_point()` before `step()` (loop.py:72-74). Test-fixture maintenance only; no production runtime changes.

**New SSOT test:** `tests/test_domain_common_behavior.py:1344-1419` `test_canonical_defaults_contains_expanded_generic_domains` reads real `defaults.toml` and covers raw-Toml key absence, 8-field validation, normalization values, name/entry assertions, and strategy dispatch for all three domains.

## Blocking findings

None.

## Advisory findings

1. Diff snapshot encoding: `diff.patch` renders all CJK display names as mojibake (e.g., `name = "??畾?閰冽扑"`), while the on-disk files (`config/defaults.toml`, tests) contain correct UTF-8 values (`瘛望殿?詨楷`, `撖??文`). This is a snapshot-generation artifact, not a repository defect, but gate tooling should beware encoding when diffing CJK content.
2. A few legacy fixtures still use placeholder identity `abyss_nest` (`test_tier4_fallback_preserves_domain_route_fields`, `test_tier4_fallback_preserves_enable_lord_boss_ownership`). These construct their own mock mode dicts and do not touch the real catalog, so they do not violate the identity contract; renaming them is optional cleanup.
3. Acceptance 12 (focused tests pass) was assessed by static inspection only; tests were not executed in this read-only review.

## Test evidence gaps

Static grounding confirms the changed tests align with production logic and the finalized TOML contract. Execution of focused tests (`tests.test_domain_common_behavior`, `tests.test_behavior_main_entrypoint`) remains the outstanding dynamic evidence; no other focused module was added since the diff touches only the two in-scope test files plus `config/defaults.toml` and task docs.

<!-- blackfire-gate-fingerprint: {"schema":1,"role":"spec-reviewer","hash":"40d4871fca0efa3a030e2a7243884edd4e19a2d08e0f8292c102d9dd832e8dd7"} -->
