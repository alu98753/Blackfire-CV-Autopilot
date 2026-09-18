# Spec Review

Gate-accepted verdict: PASS
Blocking findings: 0

# Spec Review

## Clause coverage

Reviewed task `foreground-demo-mode-isolation` (Final SPEC incl. bounded cleanup appendix) against the candidate diff (`.runtime/ai_gate/foreground-demo-mode-isolation/diff.patch`) and current repository files.

- **Composition contract (AC1/AC2, SPEC 75-87, 168):** `cli/arguments.py:76` remains the single resolution point; `main.py:76-81` selects the launch-gate capture once via `compose_capture(foreground=not backend_mode, ...)`, `runtime/bootstrap.py:153-157` selects the runtime pair once via `compose_io(...)`. No downstream re-selection. Satisfied.
- **Backend capture fail-closed (AC3/AC6):** `BackendScreenCapturer.capture` (runtime/io_adapters.py:20-28) uses only `_capture_backend`; returns `None` for full-screen/invalid HWND/backend failure; no MSS/PIL call. Isolated tests (`test_backend_capture_is_fail_closed_without_foreground_calls`, `test_3_backend_*`) assert no fallback. Satisfied.
- **Backend input no-pyautogui (AC4):** `BackendMouseController.click/scroll/drag/move_to_safe_area` (io_adapters.py:62-128) use Win32 only; `test_backend_input_never_calls_pyautogui` asserts moveTo/mouseDown/scroll/dragTo never called. Satisfied.
- **Foreground capture/input (AC5/AC7/AC9):** `ForegroundScreenCapturer` keeps MSS?IL fallback; `ForegroundMouseController` keeps pyautogui semantics incl. `FailSafeException` re-raise; `test_foreground_capture_uses_pil_after_mss_failure`, `test_foreground_input_uses_pyautogui` cover. Satisfied.
- **Behavior preservation (AC8, SPEC 344, AC20):** Backend click (MOUSEMOVE??01?BUTTONDOWN??04?BUTTONUP??04), scroll (MOUSEMOVE??05?M_MOUSEWHEEL, cooldown .3), drag (MOUSEMOVE??03?BUTTONDOWN??05?teps??15/.02?OUSEMOVE??02?BUTTONUP, cooldown .3, move_safe) replicate the pre-diff Win32 sequences; `test_backend_drag_preserves_timing_and_release_sequence` asserts message order, sleeps (.03/.05/.15/.02) and finalize args. Satisfied.
- **Launcher contract (AC10/AC18):** `utils/steam_launcher.py` no longer owns `mouse`/`backend_mode`; requires injected capturer (`ValueError` otherwise); `ensure_game_ready`/`is_game_open`/`run_launch_subflow` use capturer only (`get_hwnd`/`get_window_rect`/`ensure_window_on_monitor`). No remaining `SteamGameLauncher(` production caller uses removed params. Satisfied.
- **Relaunch contract (AC11/AC21-23):** `states/exceptions/subflows/game_relaunch.py:29-31` fails explicitly (`RuntimeError`) when `machine.capturer` is None; passes `capturer=capturer` to launcher; no `backend_mode`/`mouse` reconstruction. Tests `test_relaunch_reuses_machine_capture`, `test_relaunch_missing_capture_fails_before_launcher` cover both paths. Satisfied.
- **Metadata allowance (SPEC 144-150, AC12):** `state_machine.backend_mode` remains only for serialization guards (`__setstate__`), quest-config propagation (state_machine.py:1812-1813), CLI/mode_setup config metadata; grep shows no production constructor kwarg `backend_mode=` and no `.backend_mode =` mutation in production besides bootstrap metadata. Satisfied.
- **Test migration (AC13/AC19):** No remaining test constructs `MouseController(backend_mode=...)`/`ScreenCapturer(backend_mode=...)`; previously mutating tests (test_mouse_coordinates, test_screen_capturer_architecture, test_behavior_pause_resume, test_mouse_refactor) now use explicit adapters; new deterministic modules `tests/test_runtime_io_composition.py` (CLI modes, main/bootstrap composition, missing-template ordering) and `tests/test_foreground_demo_mode_isolation.py` (fail-closed, timing, launcher/relaunch) added. Satisfied.
- **Phase-1 CLI (AC16):** `tests/test_runtime_io_composition.test_cli_modes` and updated `test_behavior_main_entrypoint` still prove default backend, `--foreground`, legacy `--backend`. Satisfied.

## Blocking findings

None.

## Advisory findings

1. Non-focused tests still construct the raw base classes whose capture/click/scroll/drag now raise `NotImplementedError`: `tests/test_behavior_safety_and_battle_scenarios.py:49,73,307`, `tests/test_nemesis_intervention.py:260`, `tests/test_debug_visualizer.py:97`, `tests/test_long_run_resilience.py:36,54`, `tests/test_capture.py:21`. If any of these invoke `capture()`/`click()` they will fail post-change; they are outside the focused list but inside the `tests/` scope ??worth verifying when the focused set is run.
2. Dev scripts `scripts/crop_tool.py:46` and `scripts/diagnose_merchant_gold_ocr.py:56` construct base `ScreenCapturer` and would raise `NotImplementedError` if they call `capture()`. SPEC appendix allows dev-only scripts to remain out of scope unless broken; `scripts/test_single_click.py` was migrated but these two were not.
3. `capture/screen.py:20` retains a stale `backend_mode` docstring line (cosmetic drift only).
4. Full-suite/run evidence not executed during this read-only review; verdict rests on code/diff inspection and the deterministic test assertions present in the snapshot.

## Test evidence gaps

- Not executed here: the focused modules (`tests.test_runtime_io_composition`, `tests.test_screen_capturer_architecture`, `tests.test_mouse_refactor`, `tests.test_mouse_coordinates`, `tests.test_foreground_demo_mode_isolation`) and the pause/resume deterministics. Evidence of behavior-preservation is code-level (message/timing parity) plus in-diff test assertions.
- No evidence yet that the unmigrated non-focused tests/scripts listed in Advisory 1-2 pass or fail; required only as a follow-up check, not a focused criterion.

<!-- blackfire-gate-fingerprint: {"schema":1,"role":"spec-reviewer","hash":"e6017775c8cbd9f03559acfd7f679715196e52ddbbd7b7384fa666571ad551a7"} -->
