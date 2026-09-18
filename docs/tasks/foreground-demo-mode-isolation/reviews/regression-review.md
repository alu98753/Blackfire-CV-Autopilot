# Regression Review

Gate-accepted verdict: BLOCK
Blocking findings: 2

# Regression Review

## Behavior-preservation assessment

The core adapter split is a faithful behavior-preserving refactor. I compared each new adapter against the base-class implementation it replaces:

- `BackendScreenCapturer.capture()` (runtime/io_adapters.py:21-29) replicates the base backend path of `ScreenCapturer.capture()` (capture/screen.py:292-319): resume-event gate, `full_screen -> None`, `get_hwnd()` int/`>0` validation, `_capture_backend(hwnd)` with identical fail-closed returns. Only difference: the error-log statements are dropped; return values are identical.
- `ForegroundScreenCapturer.capture()` (io_adapters.py:37-61) replicates the base foreground path verbatim: `rect = get_window_rect()` when None, `monitors[1]` for full-screen, `last_monitor` update, MSS grab, MSS->PIL `ImageGrab` fallback with BGRA2BGR/RGB2BGR conversion.
- `BackendMouseController` (io_adapters.py:64-131) preserves the exact PostMessage/SendMessage sequences, jitter (`random.randint(*offset_range)`), `_draw_debug_click`, and timings (.01/.04/.04 click, .05 scroll, .03/.05/step-sleep/.15-or-.02 drag) and `_finalize_action` args (click `move_safe=True`; scroll/drag `cooldown=.3`). One intended deviation: when `get_hwnd()` is falsy the base class fell through to the pyautogui branch even in backend mode (actions/mouse.py:141, 222, 277); the backend adapters now `return False` (fail-closed). That aligns with the SPEC critical invariant ("backend I/O failure must never silently fall back to physical input") and consumes the phase-1 legacy fall-through.
- `ForegroundMouseController` (io_adapters.py:134-184) replicates base foreground click/scroll/drag/safe-area exactly, including `FailSafeException` re-raise and `_finalize_action` semantics.
- Composition: `main.py:76-81` selects the launch-gate capture once via `compose_capture`; `runtime/bootstrap.py:153-157` selects the runtime pair once via `compose_io`; `state_machine.backend_mode` remains metadata only (state_machine.py:1708/1715 serialization guards, 1812-1813 quest-config propagation; no downstream I/O re-selection found). Launcher owns process/window readiness only (utils/steam_launcher.py:103-104 uses `ensure_window_on_monitor` on injected capturer; no mouse).
- CLI semantics unchanged (cli/arguments.py:76), and `--backend`/`--foreground`/default mapping is re-proven in the new `tests/test_runtime_io_composition.py`.

## Blocking findings

### B1
Severity: BLOCKING
Regression / invariant: Merge integration ??the diff snapshot reverts previously merged origin/main content (generic-domain-catalog-expansion) outside task scope.
Location: `config/defaults.toml` (`[primary_modes.abyssbeast_lair]`, `[primary_modes.coldoath_citadel]` removed; golden_empire common-default overrides re-added), `docs/tasks/generic-domain-catalog-expansion/*` deleted, `tests/test_domain_common_behavior.py`, `tests/test_behavior_main_entrypoint.py`
Claim: Relative to the stated baseline `origin/main`, the worktree deletes two domain-mode sections from the canonical `config/defaults.toml`, deletes the merged generic-domain-catalog-expansion task docs and both prior PASS reviews, and reverts the domain tests to `abyss_nest`/`frost_citadel` placeholders and the entrypoint tests to the stale hardcoded `"8"` greedy choice ??none of which is in task.json scope (`config/defaults.toml` and `tests/test_domain_common_behavior.py` are not listed).
Evidence: The diff.patch shows these as deletions with full baseline content, including the previously gate-accepted generic-domain-catalog-expansion EVIDENCE.md (PASS/blocking=0) and both review fingerprint blocks. Worktree grounding: `docs/tasks/generic-domain-catalog-expansion/` does not exist and `config/**` contains no `abyssbeast_lair`/`coldoath_citadel`. Merging this branch as-is would regress origin/main's domain catalog and its acceptance-tested regression coverage.
Suggested validation: Rebase the branch onto `origin/main` (or reconcile with the gate baseline), then regenerate the diff; confirm the diff then contains only foreground-demo-mode-isolation changes.
Confidence: 0.95

### B2
Severity: BLOCKING
Regression / invariant: Game relaunch recovery path failure semantics ??`SteamGameLauncher` now hard-raises `ValueError` when no capturer is injected, while `GameRelaunchSubflow` (crash self-healing path) still passes an optional `machine.capturer`.
Location: `utils/steam_launcher.py:41-43` (raise ValueError) vs `states/exceptions/subflows/game_relaunch.py:48-52` (`capturer=getattr(machine, 'capturer', None)`)
Claim: Whenever `machine.capturer` is falsy during a relaunch, the subflow now crashes with an unlogged/uncaught `ValueError` from the launcher constructor instead of the origin/main behavior where the launcher self-constructed capture/input from `machine.backend_mode` and attempted recovery.
Evidence: The surrounding code treats `machine.capturer` as optional everywhere: the same file guards it (`game_relaunch.py:25-26, 41-42`, plus `states/handlers/base.py:12/84`, `states/handlers/battle.py:430`, watchdog.py:50), and `GameStateMachine` receives capturer via constructor injection. The diff removes both `mouse=` and `backend_mode=` from this call (per SPEC acceptance 11 the launcher must not reconstruct I/O from backend_mode), but removes the fallback without an explicit fail-safe for the capturer-absent case, converting a graceful recovery attempt into a hard crash inside the exception subflow. If `machine.capturer` can be None in any live relaunch path (e.g., a machine restored without live dependencies), the self-healing loop breaks.
Suggested validation: Assert `GameStateMachine.__init__` requires a non-None capturer in production and that every relaunch caller holds a live machine with capturer set (unit test: `GameRelaunchSubflow.execute` with `machine.capturer = None` ??verify the intended failure contract, e.g., a documented `RuntimeError` with `record_recovery`, rather than an uncaught `ValueError`).
Confidence: 0.6

## Advisory findings

1. `tests/test_runtime_io_composition.py::test_missing_templates_precede_io_composition` patches `runtime.bootstrap.compose_io` with `create=True`, but `init_state_machine_system` binds its local `compose_io` via `from runtime.io_adapters import compose_io` inside the function, so the assertion `compose.assert_not_called()` is vacuous (the real function is fetched from `runtime.io_adapters`, not blocked). The test passes regardless of whether composition is skipped. Patch `runtime.io_adapters.compose_io` instead.
2. `tests/test_behavior_pause_resume.py:473/485` still mutate `.backend_mode` on base-class instances; acceptable only because the SPEC limits migration to focused isolation tests and the base classes remain a construction-resolved compatibility facade ??but the mutable attribute remains reachable, so any future caller could reintroduce runtime mode switching.
3. Dev-only `scripts/test_single_click.py:38` still constructs `MouseController(backend_mode=...)`; it exercises the legacy facade and is out of production scope, but it is now unrepresentative of the composed production path.
4. Static review only: focused tests were not executed (read-only constraint). Dynamic verification of `tests.test_runtime_io_composition`, `tests.test_foreground_demo_mode_isolation`, `tests.test_screen_capturer_architecture`, `tests.test_mouse_coordinates` is still required.

<!-- blackfire-gate-fingerprint: {"schema":1,"role":"regression-reviewer","hash":"ad27c03b39d9d7605078539f4a82695de4344a69ceb926bc96b0d3913cda3a54"} -->
