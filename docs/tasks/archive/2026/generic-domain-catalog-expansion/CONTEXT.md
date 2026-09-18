# Scout Context: generic-domain-catalog-expansion

**Status:** Maximum steps reached. Producing report from gathered evidence.

---

## Relevant files and symbols

| File | Why it matters |
|------|----------------|
| `docs/tasks/generic-domain-catalog-expansion/SPEC.md` | Canonical spec defining goal, invariants, acceptance criteria |
| `docs/tasks/generic-domain-catalog-expansion/task.json` | Task descriptor with scope and focused tests |
| `config/defaults.toml` | Canonical domain catalog authority; currently declares `golden_empire` only (lines 125-138) |
| `states/domains/generic_domain.py` | `GenericDomainStrategy` ??the strategy new unregistered domains dispatch through (13 lines, fully understood) |
| `tests/test_domain_common_behavior.py` | Existing domain catalog/Tier4 dispatch tests using placeholder `"abyss_nest"` / `"frost_citadel"` ??needs update to real identities |
| `cli/tier4_setup.py` | Interactive/non-interactive Tier4 domain route assembly; consumes `get_tier4_domain_options()` dynamically |
| `tests/test_behavior_main_entrypoint.py` | Contains the two stale regression tests (greedy dungeon + runtime loop refresh-order) to be repaired |
| `runtime/loop.py` | `run_main_loop()` ??contains the nemesis_intervention guard at line 63 that the runtime-loop stale test must model |

## Current control flow

2. **Strategy dispatch:** `states/domains/__init__.py:get_domain_strategy(domain_id, handler)` checks if a specialized strategy class exists; if not, returns `GenericDomainStrategy(handler, domain_name=domain_id)`.
1. **Domain discovery:** `config.py:get_canonical_domain_mode_configs()` scans `PRIMARY_MODES` for all entries with `type == "domain"`. Any matching key is automatically a supported domain. No Python registry needed.
3. **Daily Tier4:** `cli/tier4_setup.py:setup_daily_tier4_config()` calls `get_tier4_domain_options()` which builds options from `get_canonical_domain_mode_configs()`. `build_tier4_fallback_config()` assembles the execution route preserving domain SSOT fields.
4. **Runtime loop:** `runtime/loop.py:run_main_loop()` at line 63 checks `intervention.has_pending_timeout_recovery()` before `refresh_config_at_safe_point()` and `step()`. A bare `MagicMock()` for `nemesis_intervention` is truthy, causing the existing test to take the recovery branch instead of the intended no-intervention path.

## Existing safety mechanisms

- `validate_domain_execution_config()` enforces all 8 structural fields per SPEC invariant 5.
- `validate_profile_mode_overrides()` prevents profile injection of undeclared domains (canonical/effective separation).
- `normalize_domain_execution_config()` auto-fills canonical common defaults (`bread_cost=3`, `domain_reset_max_attempts=7`, etc.).
- `GenericDomainStrategy` explicitly refuses Golden Empire fallback (line 9 docstring; confirmed by test `test_generic_domain_strategy_for_declared_unregistered_domain`).
- Fail-fast on undeclared domain via `get_domain_strategy` raising `ValueError`.

## Existing tests

- **`test_behavior_main_entrypoint.py`**: 16 tests for startup/CLI/loop contracts. Two stale tests identified:
- **`test_domain_common_behavior.py`**: ~30 tests covering domain discovery, Tier4 dispatch, strategy stability, SSOT ownership, lord boss preemption, hot reload. Uses placeholder identities `"abyss_nest"` and `"frost_citadel"` ??needs update to `"abyssbeast_lair"` and `"coldoath_citadel"`.
  1. **Greedy dungeon test** (`test_greedy_dungeon_deduplicates_targets_and_persists_only_changed_policy`, line 108): Hardcodes `"8"` as greedy selection; current catalog has 8 dungeons so greedy = 9, meaning `"8"` selects dungeon #8 (not greedy). Test needs to derive dynamic greedy choice.

## Regression and architecture risks

- **Config catalog authority:** `config/defaults.toml` is SSOT (SPEC invariant 1). New domains MUST be declared there with complete structural fields. No Python static list edits.
- **Test identity drift:** Tests use `"abyss_nest"` and `"frost_citadel"` as placeholders. These must be replaced with confirmed canonical identities `"abyssbeast_lair"` and `"coldoath_citadel"` to match the actual TOML entries.
- **Template path correctness:** Entry templates exist at `templates/domains/abyssbeast_lair/abyssbeast_lair.png` and `templates/domains/coldoath_citadel/coldoath_citadel.png`. The TOML `domain_entry_btn` values must match these paths relative to the templates root.
  2. **Runtime loop refresh-order test** (`test_runtime_loop_refreshes_config_before_each_state_machine_step`, line 337): Uses bare `MagicMock()` for `nemesis_intervention`, which is truthy, so `has_pending_timeout_recovery()` returns truthy and the loop enters recovery branch, never reaching `refresh_config_at_safe_point()` ??`step()`. Test must explicitly mock `has_pending_timeout_recovery()` as `False`.
- **Stale test repairs must not change production:** SPEC non-goals explicitly forbid changing dungeon catalog size or nemesis runtime behavior to make tests pass.
- **Display names:** SPEC uncertainty #1 ??exact display names for the two domains not yet confirmed from game metadata. Default naming from task.json suggests Chinese names need confirmation.
- **Dependency on `domain-common-template-decoupling`:** task.json notes this dependency; the generic domain infrastructure already exists and appears stable.

## Uncertainty

1. **Display names** for `abyssbeast_lair` and `coldoath_citadel` not confirmed from repository game docs/metadata. Task.json uses pinyin IDs but no Chinese display names were found in scope files inspected.
3. **Exact navigation visual identity** for both new domains (SPEC uncertainty #3) ??cannot confirm without runtime visual evidence or game screenshots beyond the shared `domains/common/start_btn.png` pattern.
2. **`bread_cost` default of 3** ??whether it's operationally valid for both new domains or merely legacy naming (SPEC uncertainty #2). No evidence of domain-specific bread cost difference found.
5. **Scope file `utils/tier4_config.py`** was listed in task.json scope but not inspected within budget. It exports `build_domain_execution_route`, `build_tier4_fallback_config`, `validate_daily_domain_policy` ??all already exercised by existing tests, so risk is low.
4. **Neither domain needs specialized boss/event handling** (SPEC uncertainty #4) ??no evidence found suggesting they do, but cannot prove negative from code alone.


1. **`config/defaults.toml`** ??Add `[primary_modes.abyssbeast_lair]` and `[primary_modes.coldoath_citadel]` TOML sections with complete structural fields matching SPEC invariant 5, using common defaults.
## Minimal proposed change surface
2. **`tests/test_domain_common_behavior.py`** ??Update placeholder identities (`"abyss_nest"`, `"frost_citadel"`) to canonical `"abyssbeast_lair"` / `"coldoath_citadel"` where applicable; add a test asserting both new domains exist in real `defaults.toml` and pass `validate_domain_execution_config()`.
3. **`tests/test_behavior_main_entrypoint.py`** ??Repair the two stale tests:
   - Runtime loop refresh-order: explicitly set `state_machine.nemesis_intervention.has_pending_timeout_recovery.return_value = False`.
   - Greedy dungeon: derive greedy choice from dynamic catalog size (`num_dungeons + 1`) instead of hardcoded `"8"`.
4. No Python production code changes expected. No new strategy classes. No CLI changes.

## Recommendation

**GO WITH SPEC CHANGES** ??The implementation surface is clean and well-bounded. The existing infrastructure (`GenericDomainStrategy`, canonical discovery, Tier4 assembly, SSOT normalization) fully supports adding TOML-only domain entries. However, SPEC should resolve:
1. Display names for both domains (uncertainty #1) before implementation writes TOML `name` fields.
2. Whether `bread_cost = 3` is confirmed correct or needs domain-specific override (uncertainty #2).
3. Confirm `utils/tier4_config.py` is read-only scope (no changes expected) to narrow the change surface.
