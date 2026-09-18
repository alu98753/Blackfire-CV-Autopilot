Now let me read the key files in the task scope:
Now let me search for all `--backend` references and check remaining key files:
Let me check the remaining key files:
Let me check a few more remaining files for completeness:
# Scout Context: cli-io-mode-contract-cleanup

**Status:** Maximum steps reached. Providing final scout report based on 8 files inspected.

## Relevant files and symbols

1. **`cli/arguments.py`** - The single CLI resolution point. Line 20 defines `--backend` as deprecated compatibility flag. Line 76 computes `args.backend_mode = not args.foreground` - this is the canonical mode resolution.

2. **`run.bat`** - Launcher generates `--backend` in every menu path (lines 29-65 for main modes, lines 91-143 for subflows). All help text recommends `--backend` (line 43). Default fallback is `--backend --mode daily` (line 65).

3. **`runtime/bootstrap.py`** - Composition root. Line 153 reads `backend_mode = getattr(args, "backend_mode", True)`. Line 155 passes `foreground=not backend_mode` to `compose_io()`. Line 191 stores `state_machine.backend_mode = backend_mode` for downstream metadata use.

4. **`main.py`** - Line 77-79 creates launch-gate capturer via `compose_capture(foreground=not getattr(args, "backend_mode", True), ...)`.

5. **`runtime/supervisor.py`** - `prepare_resume_command()` (lines 90-106) preserves tokens but does NOT explicitly handle `--backend`. It only manages `--target`, `--profile`, `--resume`, `--restart-game`. The `--backend` token survives only because the original command string is preserved wholesale.

6. **`states/exceptions/subflows/game_relaunch.py`** - Lines 29-31 reuse `machine.capturer` (no backend_mode reconstruction). Does NOT touch I/O mode selection. Clean from the prior foreground-demo-mode-isolation task.

7. **`scripts/test_single_click.py`** - Dev diagnostic script. Line 25 defines its own `--backend` flag (separate parser, `default=True`). Line 32 computes `backend_mode = not args.foreground`. This is an independent CLI surface, not the same parser as `cli/arguments.py`.

8. **`tests/test_behavior_main_entrypoint.py`** - Lines 199-209 test `--backend` acceptance and `backend_mode` resolution. Line 24 in `make_args()` includes `"backend": True` as a default attribute.

## Current control flow

```
CLI parse (cli/arguments.py:76)
  args.backend_mode = not args.foreground
  ??main.py:78 ??compose_capture(foreground=not backend_mode)  [launch gate]
  ??bootstrap.py:153-155 ??compose_io(foreground=not backend_mode)  [runtime]
  ??bootstrap.py:191 ??state_machine.backend_mode = backend_mode  [metadata]
  ??state_machine.py:1812-1813 ??quest_cfg["backend_mode"] = self.backend_mode  [propagation]
```

The `--backend` flag on `args` is never read again after line 76 computes `backend_mode`. The computed boolean `backend_mode` flows into composition and metadata. The raw `args.backend` field has zero runtime consumers.

## Classification of every `--backend` reference

| Location | Type | Notes |
|----------|------|-------|
| `cli/arguments.py:20` | Parser acceptance (dead token) | Stored in `args.backend` but never read; `args.backend_mode` derived solely from `--foreground` |
| `run.bat` (all menus) | Launcher-generated redundant token | Generates `--backend` in every command; removing it changes zero runtime behavior |
| `utils/quest_mapper.py:69,73,74` | Generated command strings | Subprocess commands include `--backend`; removing it is inert |
| `utils/quest_scheduler.py:158` | Generated command string | Same as quest_mapper |
| `scripts/test_single_click.py:25` | Independent dev script | Separate argparse, not the main CLI; has its own `--backend`/`--foreground` |
| `README.md:102` | Stale documentation | Documents `--backend` as compatibility |
| `README.zh-TW.md:102,259,291` | Stale documentation (zh-TW) | Instructs users to add `--backend` for normal use |
| `docs/architecture/runtime_config_hot_reload_architecture.md:16,45` | Stale documentation | References `--backend` in I/O path diagrams |
| `docs/storys/...jewelry_workshop_multi_sell_story.md:46` | Stale documentation | Example command uses `--backend` |
| `meta_data/outputs/PLAYER_DATA_SECURITY_REPORT.md:87` | Stale documentation | Example command uses `--backend` |
| `tests/test_behavior_main_entrypoint.py:204,25` | Test acceptance assertion | Tests that `--backend` is accepted and `backend_mode=True` |
| `.agents/skills/...core_design_patterns.md:89` | Skill reference text | Documents `--backend` as a composition entry |

## Existing safety mechanisms

- **Fail-closed composition:** `compose_io()` and `compose_capture()` in `runtime/io_adapters.py` are the sole I/O selection seam. Backend and foreground are distinct classes with no cross-fallback.
- **Metadata-only propagation:** `state_machine.backend_mode` is used only for quest config serialization (`state_machine.py:1812-1813`) and `mode_setup.py:17,25` config propagation. No production I/O code reads it to re-select adapters.
- **Supervisor resume:** `prepare_resume_command()` preserves the original command tokens wholesale, so `--backend` survives restart without special handling.

## Existing tests

- `test_behavior_main_entrypoint.py:test_argument_parser_defaults_to_backend_and_supports_foreground_opt_in` (line 199) - Asserts `--backend` acceptance and `backend_mode` resolution.
- `test_behavior_main_entrypoint.py:test_main_binds_selected_window_profile_before_loading_mode_and_starts_loop` (line 228) - Asserts `compose_capture` called with `foreground=False` (backend default).
- `test_behavior_main_entrypoint.py:test_initializer_wires_profile_runtime_refresh_and_daily_pipeline` (line 305) - Asserts `compose_io` called with `foreground=False`.

## Regression and architecture risks

1. **Supervisor restart token preservation:** `prepare_resume_command()` does not strip `--backend` - it preserves all tokens. If `--backend` is removed from the parser, an existing superviser command string containing `--backend` from a previous run would cause `argparse` to fail on restart. The supervisor must be updated to strip the deprecated token, or the parser must retain it as a silent no-op.

2. **Quest mapper/scheduler subprocess commands:** `quest_mapper.py` and `quest_scheduler.py` generate commands with `--backend`. These are subprocess launches. If `--backend` is removed from argparse, these must be updated or argparse will reject the command.

3. **`scripts/test_single_click.py` independent parser:** This script has its own argparse with `--backend`. It is a standalone diagnostic tool and is NOT part of the main CLI contract. Its `--backend` flag serves a real purpose (selecting adapter class). It should be left alone or migrated to use the same `--foreground` opt-in pattern independently.

4. **`backend_mode` metadata consumers:** `state_machine.backend_mode` is propagated to quest configs and serialized in `__setstate__` guards. This metadata is harmless to preserve but should not be confused with a public CLI flag.

## Uncertainty

- The exact set of documentation files that need updating vs. historical-only text was not fully enumerated within budget. The grep found ~100 matches; a full classification during implementation will be needed.
- Whether `args.backend` (the raw boolean from `store_true`) is preserved for any serialization or restart-pickling reason cannot be proven without reading the full supervisor restart command reconstruction in all edge cases. The supervisor code was read and appears safe, but the exact interaction with a supervisor that restarts a process using the old command string (containing `--backend`) needs validation.
## Minimal proposed change surface

1. **`cli/arguments.py`** - Remove `--backend` argument. Keep `args.backend_mode = not args.foreground` unchanged.
2. **`run.bat`** - Remove `--backend` from all menu echo text, command constructions, and help text. Default command becomes `--mode daily` (no `--backend`).
3. **`utils/quest_mapper.py`** and **`utils/quest_scheduler.py`** - Remove `--backend` from generated subprocess command strings.
4. **`tests/test_behavior_main_entrypoint.py`** - Update `test_argument_parser_defaults_to_backend_and_supports_foreground_opt_in` to remove `--backend` acceptance test; update `make_args()` to remove `"backend": True`.

5. **`scripts/test_single_click.py`** - Independent script; migrate to `--foreground` opt-in or leave as-is (it's a separate surface).
6. **Documentation** - `README.md`, `README.zh-TW.md`, architecture docs, story docs, and task references need `--backend` references removed or updated.
7. **Supervisor resilience consideration** - Either add `--backend` to the supervisor's `prepare_resume_command()` stripping list, or add a deprecation warning instead of hard removal, to handle in-flight restarts.

## Recommendation


**GO WITH SPEC CHANGES**
The evidence is conclusive: `--backend` has zero independent semantic responsibility. The parser stores it but no production code reads `args.backend`; all runtime behavior derives from `args.backend_mode = not args.foreground`. The SPEC's deletion rule should be followed, but the SPEC must be updated to address:

1. The supervisor restart resilience concern (old command strings in flight during upgrade).
2. The `scripts/test_single_click.py` independent parser (explicitly scoped out or separately migrated).
3. Whether `backend_mode` metadata propagation (`state_machine.backend_mode`, `mode_setup.py` config) is preserved as harmless metadata or also cleaned up (it is not I/O-selection code and can safely remain).
