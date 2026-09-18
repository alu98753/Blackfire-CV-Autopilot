# Spec Review

Gate-accepted verdict: BLOCK
Blocking findings: 2

# Spec Review

## Clause coverage

Review of task `foreground-demo-mode-isolation` (SPEC status: Final) against the candidate diff and current working tree. Grounding performed: read SPEC/task.json/status.txt/diff.patch, and current `runtime/io_adapters.py`, `utils/steam_launcher.py`, `runtime/bootstrap.py`, `main.py`, `states/exceptions/subflows/game_relaunch.py`, `capture/screen.py`, `actions/mouse.py`, and affected tests; grep for all `backend_mode` and `ScreenCapturer(`/`MouseController(`/`SteamGameLauncher(` usages.

- Architecture contract: composition seam (`compose_io`/`compose_capture` in new `runtime/io_adapters.py`) selects one I/O family from the single CLI flag; `main.py` and `bootstrap.py` both derive `foreground` from `args.backend_mode` ??one mode-selection policy. Two capturer instances (launcher + state machine) of the same family are constructed, which SPEC line 168 explicitly permits.
- Backend fail-closed: `BackendScreenCapturer.capture` (None on full_screen/invalid HWND/backend failure, black-image via `_capture_backend` returns None), `BackendMouseController` click/scroll/drag/safe-area verified message-for-message and sleep-for-sleep identical to the base backend branches (`actions/mouse.py`); no pyautogui path. The adapters actually remove the base class's pre-existing missing-HWND fallthrough to foreground pyautogui, consistent with the critical invariant (no silent foreground fallback).
- Foreground semantics: MSS?IL fallback and pyautogui click/scroll/drag/safe-area sequences match base foreground branches exactly.
- Launcher contract: `SteamGameLauncher` no longer owns mouse/`backend_mode`; uses injected capturer only for `get_hwnd`/`get_window_rect`/`ensure_window_on_monitor`. Relaunch reuses `machine.capturer`, no `backend_mode` kwarg. State-machine `backend_mode` remains only as metadata (serialization guards + quest-config propagation), no new I/O-selection branches.
- Deterministic launcher/relaunch coverage: new `tests/test_foreground_demo_mode_isolation.py` covers adapter family selection, launcher injection/no-mode-owner, backend-no-pyautogui, MSS?IL, drag timing/release order, relaunch reuse (AC 14/15 largely satisfied).

## Blocking findings

### B1
Severity: BLOCKING
Contract / invariant: Deterministic non-skipped suite must not regress; task scope includes `tests/` (AC 17 behavior-preserving scope)
Location: `tests/test_behavior_supervisor_lifecycle.py:105` vs `utils/steam_launcher.py:41-42`
Claim: The launcher constructor change (`raise ValueError` when capturer is None) breaks non-skipped deterministic test `test_scenario_s3_hung_window_auto_escalates_to_restart_game`.
Evidence: The test constructs `SteamGameLauncher(game_title="Blackfire Crusade", hwnd=12345)` with no capturer (line 105) in a non-skipped `unittest.TestCase` (file head lines 1-22 shows no skip decorator; the diff does not touch this file). The new constructor unconditionally raises `ValueError("SteamGameLauncher requires the composed capture dependency")` when `capturer is None`. The test then cannot reach its patched assertions, producing a test error in the deterministic suite.
Suggested validation: Update the test to inject a `MagicMock()` capturer (or make the launcher degrade deterministically), then run `tests.test_behavior_supervisor_lifecycle`.
Confidence: 0.95

### B2
Severity: BLOCKING
Contract / invariant: SPEC Compatibility policy line 230 ("Tests that use this pattern must migrate to explicit adapter construction/selection") and Acceptance criterion 13 ("Direct test mutation of `.backend_mode` is removed from focused isolation tests")
Location: `tests/test_mouse_coordinates.py:43,61`; `tests/test_screen_capturer_architecture.py:84,99,112,124,139`
Claim: Two of the four REQUIRED focused modules still directly mutate `.backend_mode`; the mandated migration to explicit adapter construction was not performed.
Evidence: Both files are in the SPEC's required focused list and task scope, yet the diff leaves them unchanged. `test_mouse_coordinates.py` assigns `self.mouse.backend_mode = True/False`; `test_screen_capturer_architecture.py` assigns `self.capturer.backend_mode = True/False`. The base classes retain the mutable attribute, so the tests still pass ??but the explicit acceptance criterion and the compatibility-policy migration obligation are unmet, and the base classes' post-construction mutability remains as the very pattern the SPEC forbids to preserve.
Suggested validation: Migrate these tests to construct `BackendScreenCapturer`/`ForegroundScreenCapturer` (or fix-mode constructor args) instead of mutating; confirm no `\.backend_mode\s*=` remains in the four focused modules.
Confidence: 0.90

## Advisory findings

- `tests/test_game_process_lifecycle.py:35-41` still passes `mouse=self.mock_mouse` to `SteamGameLauncher`, which the new constructor no longer accepts (TypeError). The module is class-level skipped so it does not fail the suite, but it is stale and contradicts the new constructor signature; it should be updated when de-skipped.
- Base classes `ScreenCapturer`/`MouseController` retain the mutable `backend_mode` attribute and action-time branches, now reachable only from dev scripts (`scripts/test_single_click.py`) and tests. This is tolerated as the small shared implementation, but it technically exceeds the SPEC's "legacy facade resolved once at construction" allowance; consider documenting it as the sanctioned legacy path.
- The launcher's initial `run_launch_subflow` polls `capturer.get_window_rect(quiet=True)`; with the backend adapter this is fail-closed on missing HWND, unchanged from base behavior ??no issue found, flagged only as a behavior path worth a quick direct inspection during implementation review.

## Test evidence gaps

- No execution was performed (read-only review). Focused modules were verified by inspection: the two `test_behavior_main_entrypoint` patch targets (`runtime.io_adapters.compose_capture`, `runtime.io_adapters.compose_io`) are consistent with the new bootstrap/main code paths.
- Remaining evidence gap: whether the un-migrated `test_behavior_supervisor_lifecycle.S3` failure (B1) and AC-13 migration (B2) are the only suite regressions ??full focused-module run is still needed after fixes.

<!-- blackfire-gate-fingerprint: {"schema":1,"role":"spec-reviewer","hash":"c5dd6a167a9c440d100308e689299698d0af2d9a177c5c03be05c43003d28c1b"} -->
