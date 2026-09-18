# Spec Review

Gate-accepted verdict: PASS
Blocking findings: 0

# Spec Review

## Clause coverage

- **Composition contract (AC1/AC2/AC14, SPEC 75-87, 168):** `cli/arguments.py:76` remains the single CLI mode resolution point. `main.py:76-81` selects the launch-gate capture once via `compose_capture(foreground=not backend_mode, ...)`; `runtime/bootstrap.py:153-157` selects the runtime pair once via `compose_io(...)`. `runtime/io_adapters.py:183-197` is the only I/O selection seam. No downstream re-selection exists.
- **Action-time branching removed (AC3-5, SPEC 178-179):** base `MouseController`/`ScreenCapturer` no longer carry `backend_mode` (`actions/mouse.py:24-25`, `capture/screen.py:17`); `click/scroll/drag/move_to_safe_area/capture` raise `NotImplementedError` in the base. Backend adapters contain Win32-only paths with no MSS/PIL/pyautogui fallback; foreground adapters contain MSS->PIL/pyautogui-only paths with no backend branches.
- **Fail-closed invariants (AC6, invariants 3-4):** `BackendScreenCapturer.capture` returns `None` on full-screen/invalid HWND/backend failure without touching MSS/PIL. `BackendMouseController` returns `False` on errors; missing-hwnd now returns `False` instead of origin's latent foreground fall-through ??the exact hardening SPEC AC3/4 require.
- **Behavior preservation (AC8-9, invariants 6-7):** adapter bodies reproduce origin Win32 message ordering and sleeps (0.01/0.04/0.04 click; 0.05 scroll; 0.03/0.05/0.15 or 0.02 drag), `_finalize_action` args, foreground pyautogui sequences, and `click` default `move_duration=(0.03, 0.07)` matching the base.
- **Launcher contract (AC10/AC18, SPEC 152-168):** `utils/steam_launcher.py` dropped `mouse`/`backend_mode`; requires injected capturer (`ValueError` otherwise, line 41-42); uses capturer only for `get_hwnd`/`get_window_rect`/`ensure_window_on_monitor`. No production caller passes removed params.
- **Relaunch invariant (AC11/AC21-23, appendix scope 3):** `game_relaunch.py:29-31,45,51-55` reuses `machine.capturer`, raises `RuntimeError` when missing, never reconstructs I/O from `backend_mode`. Bootstrap composes a non-null capturer into `GameStateMachine(capturer=..., mouse=...)` (bootstrap.py:182-189).
- **Metadata allowance (AC12, SPEC 144-150):** remaining `backend_mode` is metadata only (`bootstrap.py:191`, `cli/mode_setup.py`, `state_machine.py:1708/1715/1812-1813`, `cli/arguments.py:76`); grep confirms no production I/O construction re-reads it.
- **Test migration (AC13/AC16/AC19):** no test mutates `.backend_mode` anymore; `test_mouse_refactor`, `test_mouse_coordinates`, `test_behavior_pause_resume`, `test_behavior_screen_capturer`, `test_screen_capturer_architecture`, `test_behavior_main_entrypoint`, `test_behavior_safety_and_battle_scenarios` use explicit adapters. New deterministic modules `tests/test_runtime_io_composition.py` (CLI modes, main/bootstrap composition, missing-template ordering) and `tests/test_foreground_demo_mode_isolation.py` (fail-closed, timing/ordering, launcher/relaunch reuse, missing-capturer failure) cover AC14/AC15/AC22/AC23.
- The prior regression-review BLOCKs (unmigrated `test_behavior_safety_and_battle_scenarios`; broken `scripts/crop_tool.py`, `scripts/diagnose_merchant_gold_ocr.py`, `tests/test_capture.py`) are resolved in the current diff, which migrates all four.
- **Unmigrated base-class test usages** (`test_mouse_refactor:37,51`, `test_debug_visualizer:97`, `test_long_run_resilience:36,54`) exercise only shared mechanics (`_finalize_action`, `_draw_debug_click`, `_release_backend_resources`, `close`) that do not raise ??no test regression.

## Blocking findings

None.

## Advisory findings

- `capture/screen.py:20` retains a stale `backend_mode` docstring line (cosmetic drift).
- `BackendScreenCapturer.capture` drops origin's failure log lines (`[ScreenCapturer] Backend capture failed; refusing foreground fallback.`); the externally observable `None` result contract is preserved.
- `ForegroundMouseController.click` no longer logs before re-raising `pyautogui.FailSafeException`; re-raise behavior itself is preserved.
- `ScreenCapturer.__init__` still constructs `mss.MSS()` even for backend adapters (matches origin construction-time side effect; released by `close()`).
- The `test_runtime_io_composition`/`test_foreground_demo_mode_isolation` modules were not executed in this read-only review; static inspection found no structural defect.

## Test evidence gaps

Focused modules were not run (read-only review). Static review of the new modules and migrated tests found matching assertion/parameter alignments (`compose_capture`/`compose_io` kwargs, `ForegroundScreenCapturer`/`BackendScreenCapturer` patches, PostMessage/SendMessage ordering assertions). Running the five focused modules through the shared `.venv` remains for the user/implementer to confirm green.

<!-- blackfire-gate-fingerprint: {"schema":1,"role":"spec-reviewer","hash":"775683104a20ed99083761353f52426153c7f47bb05df25c38553141fcadb8a0"} -->
