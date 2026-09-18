# Task Specification: Generic Domain Catalog Expansion

Status: Final

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

## Final Domain configuration contract

Repository game metadata confirms the display identities:

- `abyssbeast_lair` -> `深淵獸巢`
- `coldoath_citadel` -> `寒誓古堡`

The broader analysis document also uses `冷誓要塞 / 寒誓古堡` for `coldoath_citadel`; this task uses `寒誓古堡` because the dedicated domain guide uses that as its primary display name.

Both are canonical Generic Domains. They MUST NOT be added to `DOMAIN_STRATEGIES`.

### Structural config

Each new Domain must explicitly declare:

- `name`
- `type = "domain"`
- `domain`
- non-empty `navigation_path`
- `domain_tab_btn = "domains/Domains_entry.png"`
- `domain_tab_after_btn = "domains/Domains_entry_after.png"`
- its own `domain_entry_btn`
- `lobby_start_btn = "domains/common/start_btn.png"`

Expected navigation shape:

`common/door.png -> domains/Domains_entry.png -> <domain entry template> -> domains/common/start_btn.png`

This is a configuration contract for the existing generic Domain flow. This task does not add new navigation logic.

### Entry templates

- `abyssbeast_lair`: `domains/abyssbeast_lair/abyssbeast_lair.png`
- `coldoath_citadel`: `domains/coldoath_citadel/coldoath_citadel.png`

### Common defaults and ticket semantics

Do not duplicate canonical common defaults into the new TOML sections unless an existing structural requirement needs them. Let `normalize_domain_execution_config()` provide:

- `bread_cost = 3`
- common explore priorities
- common result buttons
- `domain_reset_max_attempts = 7`
- `enable_lord_boss = true`

Repository game docs show these Domains use domain-specific entry tickets (`nest_fragment_map x1`, `frostbound_sigil x1`). That is separate game-domain metadata. This task MUST NOT reinterpret `bread_cost` as ticket cost or add ticket-consumption automation; no current runtime contract for that behavior was found.

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

## Final implementation constraints

1. Expected production change surface is `config/defaults.toml` only for Domain registration. Python production modules should remain unchanged unless implementation evidence proves the finalized contract cannot be satisfied.
2. `states/domains/__init__.py`, `GenericDomainStrategy`, CLI discovery code, and `utils/tier4_config.py` are verification surfaces, not expected implementation targets.
3. Do not create static Domain options, special-case branch logic, or identity aliases.
4. Test-only fixes for the two stale entrypoint regressions must not change production code.

## Acceptance criteria

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

## Resolved uncertainty / bounded residual risk

- Display names are resolved from repository game docs: `深淵獸巢` and `寒誓古堡`.
- No evidence requires specialized Python behavior for either Domain; GenericDomainStrategy is the intended implementation.
- Domain-specific tickets are documented game metadata but are outside this task's automation contract.
- The shared navigation shape cannot be visually proven from static repository evidence alone. The task therefore validates declarative path wiring, template existence/preflight, CLI/Tier4 discovery, and Generic strategy dispatch. Real-game visual validation remains a post-implementation runtime check, not a reason to add speculative special cases.
- Minimal focused tests are `tests.test_domain_common_behavior` and `tests.test_behavior_main_entrypoint`; add a nearby focused module only if implementation actually touches another runtime seam.
