# Regression Review

Gate-accepted verdict: PASS
Blocking findings: 0

# Regression Review

## Behavior-preservation assessment

The diff implements the Final SPEC contract for domain-common template decoupling, with intentionally changed behaviors that align with the SPEC's strict invariants rather than accidental regressions:

- **Template path move** (`domains/golden_empire/{explore_btn,open,find_treasure,treasure}.png` ??`domains/common/`): all production references were updated in lockstep (`states/handlers/battle.py`, `result.py`, `navigation.py`, `state_machine.py`, `utils/scene_snapshot.py`, `config/defaults.toml`, `BaseDomainStrategy`/`DomainTreasureSubflow`, `golden_empire.py` stays as a thin subclass). Grep confirms no residual production reference to old paths, `enable_golden_empire`, `DEFAULT_TIER4_DOMAIN`, or `TIER4_DOMAIN_OPTIONS` outside docs/tests.
- **Treasure semantics**: old GoldenEmpire `handle_custom_events` fell through to confirm-template clicks when only scene evidence (`find_treasure.png`/`treasure.png`) was present; the new `DomainTreasureSubflow.handle` claims the frame without clicking (SPEC 禮2.3 "Unknown never guesses"). Intentional contract change, covered by tests (scenarios A/B/C).
- **GoldenEmpire fallback removal**: `get_domain_strategy` now fail-fasts on undeclared domains and dispatches `GenericDomainStrategy` for declared-but-unregistered domains; `DomainExploreHandler` raises `ValueError` when `domain` identity is missing. Spec-mandated (AC 11-13, 禮2.2.3).
- **Tier 4 ownership**: `build_tier4_fallback_config`/`build_domain_execution_route` root the route in the selected domain config, strip `enable_domain`, and `apply_tier4_fallback_config`/`_build_tier4_fallback_config` raise `RuntimeError` without `primary_config`. Call sites reviewed: `refresh_config_at_safe_point` sets `primary_config` before rebuilding; `evaluate_next_activity`/`navigation._switch_to_stage_or_back` use it only within Daily pipeline flows. `has_pending_daily_activity(include_lord_boss=False)` + direct `config["enable_lord_boss"]` implement the dual-ownership contract.
- **Preserved**: domain scene detection gating in state machine 禮4.5, dungeon exit/relaunch recovery paths, direct golden_empire mode execution, `GAME_CONFIGS` normalization at import (`config.py:669`, `bootstrap.py:195`), CLI mode choices, Daily Tier 4 selection flow (interactive/non-interactive).

## Blocking findings

None

## Advisory findings

1. **Visual DOMAIN_EXPLORE in non-domain configs now raises**: state_machine 禮4.5 transitions to `STATE_DOMAIN_EXPLORE` on `explore_btn.png` regardless of config type (pre-existing condition `or is_domain_mode`). Previously `DomainExploreHandler` degraded to golden_empire fallback; now `handle()` raises `ValueError` if `config["domain"]` is absent. Spec intent, but the run-loop exception boundary was not fully verified in this review ??worth confirming the loop catches/recovers instead of dying on a stray visual detection in `mix`/`stage`/`collect_only` modes.
2. **`_check_lord_boss_preemption` KeyError on unnormalized config**: `config["enable_lord_boss"]` relies on domain normalization at import/startup; any future path constructing a domain config without `normalize_config`/`build_tier4_fallback_config` crashes mid-loop. Covered by tests as intended fail-fast, but this is a runtime (not startup) failure mode.
3. **`cli/mode_setup.py` bread_cost direct index**: `bread_cost = config["bread_cost"]` is safe only when the domain config passed to setup flow is normalized; `bootstrap.py:195` normalizes the startup config, but direct-mode CLI paths outside bootstrap were not exhaustively traced.
4. **Documentation drift**: old 90-second/30-second watchdog prose and `docs/storys/daily_tier4_player_route_story.md` still reference removed symbols/text; docs remain historical/classification work.

Suggested validation: run the focused test list from task.json (`test_domain_common_behavior`, `test_behavior_golden_empire`, `test_behavior_navigation`, `test_behavior_daily_tier4`, `test_dungeon_relaunch_recovery`, `test_profile_config_overlay`) plus `test_main_config.py` (normalize_config seam).

<!-- blackfire-gate-fingerprint: {"schema":1,"role":"regression-reviewer","hash":"57c30bcc78bfdd911cad9a6868a1a978ea05304fe8ba3bf4696f3d111c4051db"} -->
