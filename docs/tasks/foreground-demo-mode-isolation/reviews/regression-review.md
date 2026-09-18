# Regression Review

Gate-accepted verdict: PASS
Blocking findings: 0

# Regression Review

## Behavior-preservation assessment

The diff retires the mutable `backend_mode` switch from `MouseController`/`ScreenCapturer`, moves the concrete backend/foreground mechanics into explicit adapters (`runtime/io_adapters.py`), and composes I/O once at the root (`main.py:76-81`, `runtime/bootstrap.py:153-157`). The adapter bodies are faithful line-for-line ports of the old mode branches:

- Backend click/scroll/drag message sequences, sleeps (0.01/0.04/0.04; 0.05; 0.03/0.05/step/0.15/0.02), cooldowns (0.3), `_finalize_action(cooldown=..., move_safe=...)` calls, and `_draw_debug_click` ordering are preserved; `tests/test_foreground_demo_mode_isolation.py:test_backend_drag_preserves_timing_and_release_sequence` pins them.
- Foreground pyautogui click/scroll/drag, failsafe re-raise, human-like tween, safe-area ClientToScreen semantics are preserved.
- Public action signatures/defaults are unchanged ??the diff never touches the `def click/scroll/drag` lines, so defaults like `move_duration=(0.03, 0.07)` and `click_relative`'s `(0.05, 0.12)` positional pass-through are identical. No foreground timing regression.
- Fail-closed is now strict: a backend click/scroll/drag with no HWND returns `False` instead of the old code silently falling through to pyautogui. This is the SPEC's critical invariant, not a regression.
- `SteamGameLauncher` no longer references `self.mouse` anywhere; all production callers inject a composed capturer (`main.py`, `game_relaunch.py`); `test_behavior_supervisor_lifecycle.py` and the skipped `test_game_process_lifecycle.py` were updated to the constructor.
- `GameRelaunchSubflow` reuses `machine.capturer`, raises `RuntimeError` when capturer is missing, and constructs the launcher without `backend_mode` (tests: `test_relaunch_reuses_machine_capture`, `test_relaunch_missing_capture_fails_before_launcher`).
- Remaining `backend_mode` references are metadata only (CLI resolution, `cli/mode_setup.py` config, `state_machine.py` serialization/quest-cfg propagation, `quest_mapper.py`); no production code constructs I/O from it.
- Existing tests that still construct base `ScreenCapturer`/`MouseController` (`test_long_run_resilience.py`, `test_mouse_refactor.py`, `test_debug_visualizer.py`) only exercise inherited mechanics (`_release_backend_resources`, `close`, `_finalize_action`), so the base-class `NotImplementedError` stubs do not break them.

## Blocking findings

None.

## Advisory findings

1. **Dev-script capture semantics changed** ??`scripts/diagnose_merchant_gold_ocr.py` previously constructed `ScreenCapturer(window_title=..., hwnd=...)` with the old default (`backend_mode=False`, foreground MSS) and now uses `BackendScreenCapturer` (HWND PrintWindow/BitBlt, black-image ??None). For an OCR diagnosis tool this can change the captured image or fail where foreground previously succeeded; the minimum-wiring migration would have been `ForegroundScreenCapturer` (as `crop_tool.py`/`test_capture.py` did). Dev-only, so non-blocking.
2. **Stale docstring** ??`capture/screen.py:20` still documents the removed `backend_mode` constructor parameter; cosmetic.
3. **Logging loss in fail-closed paths** ??old backend branches logged "refusing foreground fallback" / error reasons before returning `None`/`False`; the adapters return silently. Result contract is unchanged; only diagnostic logging is thinner.
4. **Dual capturer instances at startup** ??`main.py` composes one capturer for the launcher gate and `bootstrap.py` composes a second for the machine; relaunch reuses the machine's. Same family, one selection policy per SPEC, but the first capturer's MSS handle stays open for the process lifetime. Acceptable per contract.

Confidence in PASS: grounded in the diff snapshot plus direct reads of `actions/mouse.py`, `runtime/io_adapters.py`, `capture/screen.py`, `utils/steam_launcher.py`, `main.py`, `runtime/bootstrap.py`, `game_relaunch.py`, and the migrated/new tests; repo-wide `backend_mode`/constructor greps found no production re-selection path.

<!-- blackfire-gate-fingerprint: {"schema":1,"role":"regression-reviewer","hash":"2abc6f5dceaffb51f17faa904444f8c08e73b0f8b17737307525d714a652eda3"} -->
