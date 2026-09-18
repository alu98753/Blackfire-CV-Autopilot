# Regression Review

Gate-accepted verdict: PASS
Blocking findings: 0

# Regression Review

## Behavior-preservation assessment

I compared each new adapter in `runtime/io_adapters.py` against the base-class implementation it replaces, and traced every production construction site. The diff is a faithful, intentionally fail-closed refactor:

- `BackendScreenCapturer.capture()` (io_adapters.py:21-29) replicates the base backend branch of `ScreenCapturer.capture()` (capture/screen.py:299-319): resume-event gate, `full_screen -> None`, `get_hwnd()` int/`>0` validation, `_capture_backend(hwnd)` with identical fail-closed returns. Only dropped statements are error logs; return values are identical.
- `ForegroundScreenCapturer.capture()` (io_adapters.py:37-61) replicates the base foreground path verbatim, including `get_window_rect()` fill, `monitors[1]` full-screen grab, `last_monitor` update, MSS grab, MSS->PIL `ImageGrab` fallback with BGRA2BGR/RGB2BGR conversion.
- `BackendMouseController` (io_adapters.py:64-131) preserves the exact PostMessage/SendMessage sequences, jitter, `_draw_debug_click`, timings (.01/.04/.04 click; .05 scroll; .03/.05/step-sleep/.15-or-.02 drag), and `_finalize_action` args. One intended deviation: the base class, in backend mode with a falsy `get_hwnd()`, fell through to the pyautogui branch (actions/mouse.py:141, 222, 277); the adapters now `return False` (fail-closed). This is exactly the SPEC critical invariant / acceptance criterion 4, not a regression.
- `ForegroundMouseController` (io_adapters.py:134-184) replicates base foreground click/scroll/drag/safe-area exactly, including `FailSafeException` re-raise and `_finalize_action` semantics.
- Composition is single-policy: `main.py:76-81` selects the launch-gate capture once via `compose_capture` (same `foreground=not backend_mode` derivation as the old `backend_mode=getattr(args, "backend_mode", True)`); `runtime/bootstrap.py:153-157` selects the runtime pair once via `compose_io`. Pause/resume wiring is preserved ??bootstrap still assigns `mouse._on_action_success`/`_is_paused_fn`/`_resume_event` and `capturer._resume_event` from `state_machine.resume_event` after composition (bootstrap.py:198-203).
- `SteamGameLauncher` no longer owns mouse/`backend_mode`; all production callers (main.py, game_relaunch.py) and tests were updated; grep found no remaining `SteamGameLauncher(` caller using removed params, and launcher methods only use `self.capturer` (get_hwnd/get_window_rect/ensure_window_on_monitor).
- Relaunch reuses `machine.capturer` and no longer re-reads `machine.backend_mode`; `state_machine.backend_mode` remains metadata only (state_machine.py:191, 1813), consistent with SPEC.

## Blocking findings

None found in the diff snapshot as currently provided.

## Advisory findings

1. `tests/test_runtime_io_composition.py::test_missing_templates_precede_io_composition` patches `runtime.bootstrap.compose_io`, but `init_state_machine_system` binds `compose_io` via a local `from runtime.io_adapters import compose_io` import (bootstrap.py:154), so the `compose.assert_not_called()` assertion is vacuous. Patch `runtime.io_adapters.compose_io` instead.
2. Relaunch monitor nuance: `SteamGameLauncher` constructed in `game_relaunch.py:48-52` no longer passes `monitor_index`; `ensure_window_on_monitor()` now runs on the machine's composed capturer, which carries the bootstrap `active_monitor`, whereas the pre-diff relaunch constructed a fresh capturer defaulting to monitor 1. This is a behavior refinement toward the configured monitor; confirm it is intended.
3. `SteamGameLauncher.__init__` hard-raises `ValueError` when no capturer is injected (steam_launcher.py:41-43), while `game_relaunch.py` passes `capturer=getattr(machine, 'capturer', None)`. All current relaunch callers (watchdog, handler, explore, login_flow, ports) operate on live bootstrap-injected machines whose `GameStateMachine.__init__` stores capturer (state_machine.py:137), so no live path is known to hit the raise; a machine restored without live dependencies is the only theoretical exposure. Consider asserting this invariant with a unit test documenting the intended failure contract.
4. Base `ScreenCapturer`/`MouseController` remain publicly mutable `backend_mode` facades; production no longer constructs them, but dev script `scripts/test_single_click.py:38` and several non-focused tests (e.g., `tests/test_mouse_refactor.py:63/76/86`, `tests/test_behavior_pause_resume.py:473/485`) still do ??acceptable under SPEC but worth aligning later.
5. Verification was static only (read-only constraint); the focused modules (`tests.test_runtime_io_composition`, `tests.test_foreground_demo_mode_isolation`, `tests.test_screen_capturer_architecture`, `tests.test_mouse_coordinates`, `tests.test_mouse_refactor`) were not executed. Dynamic runs through the shared `.venv` are still required.
6. IMPORTANT environment note: a prior review artifact (`docs/tasks/foreground-demo-mode-isolation/reviews/regression-review.md`) records a BLOCK (B1) claiming out-of-scope reverts of `config/defaults.toml` and `docs/tasks/generic-domain-catalog-expansion`. The diff snapshot supplied in this session (`.runtime/ai_gate/foreground-demo-mode-isolation/diff.patch`, fully read, 1125 lines) contains NO such changes ??only task docs, io_adapters, main/bootstrap, steam_launcher, game_relaunch, and tests. Either the snapshot was regenerated since that review or the artifact is stale. Before merge, regenerate the diff against `origin/main` and confirm the working tree contains the domain-catalog content (e.g., `abyssbeast_lair`/`coldoath_citadel` in `config/defaults.toml`).

<!-- blackfire-gate-fingerprint: {"schema":1,"role":"regression-reviewer","hash":"3f6c6ef68829cbd4d8643302a48105a28d2303caf3d183ada0f6798084b7e0e3"} -->
