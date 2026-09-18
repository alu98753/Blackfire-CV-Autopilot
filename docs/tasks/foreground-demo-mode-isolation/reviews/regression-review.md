# Regression Review

Gate-accepted verdict: BLOCK
Blocking findings: 2

# Regression Review

## Behavior-preservation assessment

The diff isolates backend/foreground I/O behind fixed adapter subclasses selected once by `runtime.io_adapters.compose_io/compose_capture`. Comparing each override against the base implementation (`actions/mouse.py`, `capture/screen.py`) at the composition sites (`main.py`, `runtime/bootstrap.py`, `utils/steam_launcher.py`, `game_relaunch.py`):

- **Backend click/scroll/drag/safe-area**: message sequence, jitter, inter-message sleeps (.01/.04/.04; .05; .03/.05/steps/.15-or-.02/.02), `_finalize_action` cooldown/move_safe flags, and callback/finalization semantics match the base backend branches exactly. `move_to_safe_area` dispatches through the override, so `_finalize_action(move_safe=True)` stays backend-only.
- **Foreground click/scroll/drag/safe-area**: coordinate conversion, human-like tween/duration, failsafe re-raise, `moveTo`-based scroll, and inertia drag behavior match the base foreground branches.
- **Backend capture**: `_resume_event` gate, `full_screen -> None`, valid-HWND gate, and `_capture_backend(hwnd)` (rect ignored, black-image -> None) match base backend semantics.
- **Foreground capture**: MSS -> PIL fallback, bbox semantics, `last_monitor`, `sct is None -> None` all match.
- **Mode selection**: exactly one policy (`args.backend_mode` -> `foreground=not backend_mode`) is resolved once; launcher and relaunch reuse the composed/adapter capture, and `SteamGameLauncher` no longer constructs mixed-mode I/O.

Two contract/regression problems block acceptance (below). Otherwise the composed paths are behavior-preserving.

## Blocking findings

### BFC-F1
Severity: BLOCKING
Regression / invariant: `SteamGameLauncher` constructor contract change breaks an existing non-skipped deterministic test.
Location: `utils/steam_launcher.py:41-42` (`SteamGameLauncher.__init__`); `tests/test_behavior_supervisor_lifecycle.py:105`
Claim: The new constructor raises `ValueError` when `capturer` is None, but `tests/test_behavior_supervisor_lifecycle.py::test_scenario_s3_hung_window_auto_escalates_to_restart_game` still constructs `SteamGameLauncher(game_title="Blackfire Crusade", hwnd=12345)` with no capturer and no constructor mocking, so the test now errors at construction.
Evidence: Diff removes the `capturer or ScreenCapturer(...)` fallback and adds an unconditional `raise ValueError` on None; grep shows this unpatched construction is the real class (the test only later patches `is_game_open`/`run_launch_subflow`); the diff does not migrate this file even though the launcher contract change is in scope (`tests/`).
Suggested validation: Run `tests.test_behavior_supervisor_lifecycle`; migrate the test to inject a composed/mock capturer and assert `launcher.capturer` reuse.
Confidence: 0.97

### BFC-F2
Severity: BLOCKING
Regression / invariant: SPEC acceptance criterion 13 / task `test_contract` unmet; mutable `.backend_mode` switching survives in focused tests and in the retained base classes.
Location: `tests/test_screen_capturer_architecture.py:84,99,112,124,139`; `tests/test_mouse_coordinates.py:43,61`; SPEC.md 禮Compatibility policy and AC13; task.json `test_contract`
Claim: The Final SPEC requires direct `.backend_mode` mutation to be removed from focused isolation tests in favor of explicit adapter construction, and any retained facade must not permit switching implementations by mutating the boolean after construction; the diff migrates only `test_behavior_main_entrypoint.py`, leaving the other required focused modules on the mutable pattern while `ScreenCapturer.capture()`/`MouseController.click()` still branch on `self.backend_mode` at action time.
Evidence: Repository grep shows `.backend_mode =` mutations in the two named focused modules; the base classes remain mutable and branchy; no migration or removal of these test patterns appears in the diff.
Suggested validation: Migrate the named focused tests to `BackendScreenCapturer`/`BackendMouseController` (or foreground variants), then grep to confirm zero `.backend_mode =` mutations in the focused modules.
Confidence: 0.85

## Advisory findings

- Backend input with a missing HWND is now fail-closed (`return False`) whereas the old base class fell through to physical pyautogui clicks/scrells/drags when `backend_mode=True` and `get_hwnd()` was falsy. This matches the task's critical invariant, but it is a deliberate semantic tightening; the new adapter tests always inject a valid HWND, so the no-HWND backend-input case is not directly pinned by a test.
- `tests/test_game_process_lifecycle.py:35-41` (class-skipped) still passes the removed `mouse=` kwarg and would raise TypeError if unskipped; update it alongside the migration.
- `BackendScreenCapturer.capture()` silently returns None, dropping the base's three "refusing foreground fallback" log lines; the result contract is preserved but the SPEC's "backend capture failure logging" ownership regressed.
- `runtime/bootstrap.py:8-9` retains now-unused `ScreenCapturer`/`MouseController` imports.
- `compose_io(resume_event=...)` forwards `resume_event` only to the mouse, not the capturer; bootstrap compensates by setting `capturer._resume_event` afterward, which is an easy misuse seam for future callers.

<!-- blackfire-gate-fingerprint: {"schema":1,"role":"regression-reviewer","hash":"a11b2bf8306e6e38429e07b0442b04965c4edad39418efd27afbffc5087731eb"} -->
