# Task Specification: Generic Domain Catalog Expansion

Status: Draft

## Goal

Add two repository-declared Generic Domains to the canonical Domain catalog:

- `abyssbeast_lair`
- `coldoath_citadel`

using the infrastructure established by `domain-common-template-decoupling`, without adding new Python strategy registrations unless evidence proves domain-specific behavior is required.

Also repair two stale regression tests in `tests/test_behavior_main_entrypoint.py` that no longer reflect current merged runtime contracts.

## Scope

- `config/defaults.toml`
- existing entry templates:
  - `templates/domains/abyssbeast_lair/abyssbeast_lair.png`
  - `templates/domains/coldoath_citadel/coldoath_citadel.png`
- Generic Domain discovery / dispatch verification
- Daily Tier 4 dynamic Domain discovery verification
- direct CLI mode discovery verification
- `tests/test_domain_common_behavior.py`
- `tests/test_behavior_main_entrypoint.py`
- nearby tests only when required by the finalized contract

## Known invariants

1. `config/defaults.toml` is the canonical Domain existence/catalog authority.
2. New canonical `type = "domain"` modes with no specialized registry entry dispatch through `GenericDomainStrategy`.
3. No Python static Domain catalog or Tier 4 option list should be edited merely to add these two Domains.
4. `domain` is the sole strategy identity; mode key and strategy identity remain distinct concepts.
5. Domain structural required fields must be explicit:
   - `name`
   - `type = "domain"`
   - `domain`
   - non-empty `navigation_path`
   - `domain_tab_btn`
   - `domain_tab_after_btn`
   - `domain_entry_btn`
   - `lobby_start_btn`
6. Canonical common defaults remain owned by Domain normalization:
   - `bread_cost`
   - `explore_priorities`
   - `result_buttons`
   - `domain_reset_max_attempts`
   - `enable_lord_boss`
7. Common exploration / treasure behavior remains under `templates/domains/common/` and `BaseDomainStrategy` / `DomainTreasureSubflow`.
8. No Golden Empire fallback or identity borrowing is permitted.
9. Behavior-preserving test maintenance must not alter production runtime merely to satisfy stale tests.

## Confirmed identities

The user explicitly confirmed the canonical first new Domain identity is:

`abyssbeast_lair`

The second identity is:

`coldoath_citadel`

## Provisional Domain configuration intent

Each new Domain is expected to use:

- `domains/Domains_entry.png` as Domain tab button
- `domains/Domains_entry_after.png` as selected-tab evidence
- its existing repository entry template as `domain_entry_btn`
- `domains/common/start_btn.png` as lobby start
- common normalized defaults for exploration/result/bread/reset/Boss policy unless Scout finds a real domain-specific difference

Expected entry templates:

- `domains/abyssbeast_lair/abyssbeast_lair.png`
- `domains/coldoath_citadel/coldoath_citadel.png`

## Stale regression tests included in scope

### Greedy dungeon test

Current catalog contains 8 dungeons, so the interactive greedy option is dynamically `num_dungeons + 1 = 9`.

The existing regression test still feeds `"8"` as the greedy selection, which now selects dungeon #8 and makes:

`config["greedy_dungeon"] == False`

The test should derive or use the current dynamic greedy choice rather than encode the old catalog size.

Production dungeon selection behavior should not be changed for this test.

### Runtime loop refresh-order test

`runtime.loop.run_main_loop()` now contains a `nemesis_intervention.has_pending_timeout_recovery()` guard before the safe-point refresh and state-machine step.

A bare `MagicMock()` creates a truthy synthetic `nemesis_intervention`, so the existing test fixture no longer represents the intended no-intervention path.

The test should explicitly model the no-intervention / no-pending-recovery state and continue verifying:

`refresh_config_at_safe_point() -> step()`

Production runtime behavior should not be changed for this test.

## Non-goals

- Do not add specialized `AbyssbeastLairStrategy` or `ColdoathCitadelStrategy` without Scout evidence of genuinely different behavior.
- Do not redesign Domain scheduling.
- Do not reopen `domain-common-template-decoupling` architecture.
- Do not implement treasure scene-only recovery.
- Do not change dungeon catalog/runtime behavior to make stale tests pass.
- Do not change Nemesis runtime behavior to make stale mocks pass.
- Do not modify shared Python environment.
- Do not add a new static Domain list in Python.

## Provisional acceptance criteria

1. Both new Domains are declared in canonical `config/defaults.toml` with complete structural Domain contracts.
2. `abyssbeast_lair` uses `domains/abyssbeast_lair/abyssbeast_lair.png`.
3. `coldoath_citadel` uses `domains/coldoath_citadel/coldoath_citadel.png`.
4. Both dispatch to `GenericDomainStrategy` without Python registry additions.
5. Both appear automatically in direct CLI mode choices through canonical mode discovery.
6. Both appear automatically in Daily Tier 4 Domain options.
7. Daily Tier 4 route assembly preserves each selected Domain's own identity and entry/navigation config.
8. Existing Golden Empire behavior remains unchanged.
9. The two reported stale `test_behavior_main_entrypoint` failures are corrected by test maintenance only.
10. Relevant focused tests pass.

## Uncertainty / Scout questions

1. Confirm exact display name for `abyssbeast_lair` from repository game docs / metadata.
2. Confirm whether either new Domain has a non-bread entry cost that should affect the current `bread_cost` abstraction or whether common default `3` is merely legacy naming that is still operationally valid.
3. Confirm the exact navigation path around Domain tab -> entry -> common start is visually identical for both new Domains.
4. Confirm neither Domain currently needs specialized random-event or boss handling beyond common Domain behavior.
5. Identify the minimal focused test set needed to prove dynamic catalog discovery plus the two stale test repairs.
