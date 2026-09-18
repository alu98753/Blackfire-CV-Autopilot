# Regression Review

Gate-accepted verdict: PASS
Blocking findings: 0

# Regression Review

## Behavior-preservation assessment

The diff adds two Generic Domain declarations to `config/defaults.toml` and removes four redundant Golden Empire common-default overrides, keeping `bread_cost = 3` untouched (SPEC constraints 5-6, acceptance criteria 8-10). Verified against production code:

- `config.py:357-367` `get_canonical_domain_mode_configs()` scans raw TOML for `type == "domain"` ??both new sections are discovered automatically; no Python registry change exists (`states/domains/__init__.py` still maps only `golden_empire`, and `get_domain_strategy()` returns `GenericDomainStrategy` for declared-but-unregistered ids, satisfying invariants 1-4 and 8).
- `config.py:441-495` `validate_domain_execution_config()` requires exactly the 8 structural keys (bread_cost optional), and `normalize_domain_execution_config()` supplies `CANONICAL_DOMAIN_COMMON_DEFAULTS` (bread_cost=3, explore_priorities, result_buttons, domain_reset_max_attempts=7, enable_lord_boss=True). Raw new-domain sections contain exactly the 8 structural fields, so validation passes and normalization restores Golden Empire-equivalent runtime values. Production normalization callers exist at `config.py:657` and `utils/tier4_config.py:142`.
- `cli/arguments.py:15` builds `--mode` choices from `PRIMARY_MODES.keys()` and `cli/tier4_setup.py:77-103` builds Daily Tier 4 options from `get_tier4_domain_options()` ??both pick up the new domains without code edits (acceptance criteria 5-7).
- `runtime/loop.py:54-75` matches the repaired refresh-order test exactly: `check_manual_exit_triggered` / `check_manual_restart_triggered` at loop top, `nemesis_intervention.has_pending_timeout_recovery()` guard before `refresh_config_at_safe_point() -> step()`. The test's new mocks (`has_pending_timeout_recovery.return_value = False` plus the three pause-controller checks) are fixture-only and reflect current production structure; no production runtime change was made (SPEC constraints 4, non-goals).
- Stale greedy-dungeon test derives `greedy_choice = str(len(DUNGEON_NAMES) + 1)`; production `cli/dungeon_setup.py:21-22` computes `num_dungeons + 1` identically, so the test now exercises the true greedy path instead of dungeon #8.
- Entry templates `templates/domains/abyssbeast_lair/abyssbeast_lair.png` and `templates/domains/coldoath_citadel/coldoath_citadel.png` exist; TOML `domain_entry_btn`/`navigation_path` values reference them exactly (acceptance criteria 2-3, 9 in `test_canonical_defaults_contains_expanded_generic_domains`).
- Display names in the actual worktree files are 瘛望殿?詨楷 / 撖??文 and match the finalized SPEC; test expectations use the identical literals.

## Blocking findings

None

## Advisory findings

1. `diff.patch` snapshot renders all CJK text as mojibake (e.g., `??畾?閰冽扑` vs actual file `瘛望殿?詨楷`). The worktree files are valid UTF-8, so this is a snapshot-pipeline display artifact, not a content defect ??but reviewers must not diff-string against the snapshot when verifying correctness.
2. `test_tier4_new_generic_domain_selection_has_no_keyerror` no longer patches `PRIMARY_MODES` and now exercises the real TOML catalog; this intentionally couples the test to live catalog content and is consistent with the SSOT intent, but it means catalog edits will be reflected in this test's expectations.
3. `golden_empire` retains an explicit raw `bread_cost = 3` while the two new domains omit it (relying on normalization). This asymmetry is mandated by SPEC constraint 6/acceptance criterion 10, but is a latent inconsistency to revisit if a future domain needs a documented bread-cost override.
4. `utils/tier4_config.py` was only spot-checked at the `normalize_domain_execution_config` seam (line 142); its route/fallback assembly is unchanged and already covered by pre-existing tests (`test_domain_common_behavior.py:384-397, 705-776`), so risk is low.

<!-- blackfire-gate-fingerprint: {"schema":1,"role":"regression-reviewer","hash":"e68d9b37c991d8edae937f4f85a746f0b52814463565fb1f94f7c8e3d8a6b77d"} -->
