# Regression Review

Gate-accepted verdict: PASS
Blocking findings: 0

# Regression Review

## Behavior-preservation assessment

Reviewed the diff against `origin/main` (base `145522e4`) with line-by-line comparison of `runtime/io_adapters.py` adapters versus the original per-mode paths in `capture/screen.py` and `actions/mouse.py`.

- **Backend capture**: `BackendScreenCapturer.capture()` reproduces the base backend branch exactly ??`None` for `full_screen`, non-int/invalid HWND, and backend failure; otherwise `_capture_backend(hwnd)`. MSS/PIL are unreachable (invariant 3). Only diagnostic `logging.error` calls were dropped; the externally observable result contract is identical.
- **Foreground capture**: `ForegroundScreenCapturer.capture()` matches the base foreground path (MSS region/monitor selection, `last_monitor` update, BGRA2BGR, PIL bbox fallback) including `full_screen` ??`monitors[1]`.
- **Backend input**: message sequences, sleeps (`.01/.04/.04` click, `.05` scroll, `.03/.05/step/.15-or-.02/.02` drag), jitter, `_draw_debug_click`, and `_finalize_action` flags (`move_safe=True`; `cooldown=.3, move_safe=False`; `cooldown=.3, move_safe=True`) are byte-for-byte equivalent. `test_backend_drag_preserves_timing_and_release_sequence` pins the drag contract.
- **Foreground input**: pyautogui coordinate conversion, `human_like` tween, `mouseDown/mouseUp` timing, `FailSafeException` re-raise, and cooldowns match the base foreground branch.
- **Composition**: `main.py` and `runtime/bootstrap.py` select one fixed adapter family once; `compose_capture`/`compose_io` are patched consistently in `test_behavior_main_entrypoint.py`. `state_machine.backend_mode` remains metadata-only (serialization guards at `state_machine.py:1708,1715` and quest propagation at `1812-1813` unchanged; `state_machine.py` itself is untouched by the diff).
- **Launcher/relaunch**: `SteamGameLauncher` lost `mouse`/`backend_mode`; no launcher method used them after construction. All production callers inject capturer (`main.py:80`, `game_relaunch.py:48`); `machine.capturer` is always set (`bootstrap.py:182-189`, `GameStateMachine.__init__` stores it). Relaunch no longer reconstructs I/O from `machine.backend_mode`.
- **Phase-1 CLI semantics** (`cli/arguments.py`) are untouched; `--foreground`/`--backend`/default resolution is preserved.

## Blocking findings

None.

## Advisory findings

1. **Intentional fail-open removal (backend input, missing hwnd).** The base `MouseController.click/scroll/drag` fell through to pyautogui physical movement when `backend_mode=True` but `get_hwnd()` returned falsy; the adapters return `False` instead. This strengthens the critical invariant (no silent foreground fallback) and is covered by `test_backend_input_never_calls_pyautogui`, but it is a genuine semantic tightening versus origin/main worth recording in regression documentation.
2. **Thinned diagnostics.** Adapter capture refusals (`full_screen`, invalid hwnd, closed MSS handle) and PIL-fallback exceptions no longer emit the base class's error/warning logs. Result contract unchanged; only observability is reduced.
3. **Legacy mixed-mode base classes remain.** `ScreenCapturer`/`MouseController` still expose the mutable `backend_mode` branch for dev scripts (`scripts/*.py`) and non-focused tests (`test_mouse_refactor.py`, `test_behavior_pause_resume.py`). Permitted by SPEC compatibility policy, but the "no action-time mode selection" property now relies on composition discipline; a future cleanup could delete the mixed branch.
4. **`SteamGameLauncher` now raises `ValueError` when capturer is absent.** Fail-fast by design; all known call sites (production and tests, including the previously skipped `test_game_process_lifecycle.py` and the non-skipped `test_behavior_supervisor_lifecycle.py`) inject a capturer. Any future constructor call without capturer will break loudly rather than silently create a default-mode capturer ??intended, but a hard API change outside the old constructor's implicit contract.

## Testability

The diff adds non-skipped deterministic coverage for composition families, launcher no-mode-owner, backend fail-closed capture/input, foreground pyautogui/PIL paths, drag timing/release sequence, and relaunch capturer reuse (`test_foreground_demo_mode_isolation.py`), satisfying acceptance criteria 13-15.

<!-- blackfire-gate-fingerprint: {"schema":1,"role":"regression-reviewer","hash":"3855550e0d041ca0f5c41806931ee3b65468afed9ed9178931fb4296cf95db46"} -->
