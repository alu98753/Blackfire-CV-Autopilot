# Regression Review

Gate-accepted verdict: BLOCK
Blocking findings: 2

# Regression Review

NOTE: The agent reached its maximum step budget before it could emit the structured result; this output is the final grounded assessment produced from the completed evidence gathering.

## Behavior-preservation assessment

The diff is a behavior-preserving adapter split that is largely faithful to the Final SPEC:

- Production composition is now centralized in `runtime/io_adapters.py` (`compose_io`/`compose_capture`); `main.py:76-81`, `runtime/bootstrap.py:153-157` select backend vs foreground once. No production file outside `runtime/io_adapters.py` constructs legacy `MouseController(...)`/`ScreenCapturer(...)` (repo grep confirmed).
- Shared mechanics (`_finalize_action`, `_wait_if_paused`, `check_user_intervention`, `_screen_to_client`, `_draw_debug_click`, `get_window_rect`, `ensure_window_on_monitor`, `close`) remain in the base classes.
- Timing/ordering fidelity verified by comparing the removed origin/main bodies with the new adapter bodies: backend click/scroll/drag Win32 message sequence, sleeps (0.01/0.04/0.05/0.03/0.15/0.02), `_finalize_action` args, and foreground pyautogui sequences all match. The `click` `move_duration` default is `(0.03, 0.07)` in origin/main and in the adapters ??foreground human-like motion timing is unchanged (`click_relative` still defaults to `(0.05, 0.12)` and forwards explicitly).
- `SteamGameLauncher` no longer constructs/owns a mouse adapter and has no leftover `self.mouse` references; missing capturer now fails explicitly with `ValueError` (per SPEC appendix).
- `GameRelaunchSubflow` reuses `machine.capturer` and raises `RuntimeError` when it is missing ??per SPEC appendix AC22/23. Watchdog invokes the subflow with no try/except (`states/exceptions/watchdog.py:55,75,129`); the failure propagates as an explicit invariant violation, which the appendix mandates. The machine is always composed with a non-null capturer in the supported bootstrap path (`runtime/bootstrap.py:182-189`); no pickle/serialization path produces a capturer-less machine (the `backend_mode` guards at `state_machine.py:1708/1715` are config hot-reload flag preservation, not machine serialization).
- One deliberate behavior change: backend click/scroll/drag with a missing hwnd now returns `False` instead of falling through to the pyautogui path (origin/main had a latent foreground fall-through in `backend_mode=True`). This is exactly the fail-closed hardening mandated by SPEC acceptance criteria 3/4 and invariant 4.
- Legacy `backend_mode` remains only as metadata on the state machine (`bootstrap.py:191`, `cli/mode_setup.py`, `state_machine.py:1812-1813`) ??no I/O selection re-reads it downstream.

## Blocking findings

### F1
Severity: BLOCKING
Regression / invariant: Existing deterministic behavior tests break because legacy base-class action methods now raise `NotImplementedError`; SPEC Compatibility policy ("Tests that use this pattern must migrate to explicit adapter construction/selection") was not applied to these tests.
Location: `tests/test_behavior_safety_and_battle_scenarios.py:test_mouse_controller_prohibits_movement_on_user_operating` (line 40-65) and `test_stuck_count_reset_on_mouse_action` (line 298-331)
Claim: Two previously passing tests now error; the base `MouseController.click/scroll` raise `NotImplementedError` on the very calls the tests exercise (`controller.click(500, 500)`, `controller.scroll(-5, 500, 500)`, `real_mouse.click(100, 100)`, `real_mouse.scroll(-800, 100, 100)`).
Evidence: `actions/mouse.py:132,146` raise `NotImplementedError` after `backend_mode` removal; the tests construct `MouseController` from `actions.mouse` (unmigrated); these pause-gate and stuck-count contracts are preserved by `BackendMouseController`/`ForegroundMouseController` but the tests were never converted, so the suite now errors instead of passing. The diff migration covered `test_mouse_refactor`, `test_mouse_coordinates`, `test_behavior_pause_resume`, `test_behavior_screen_capturer`, `test_screen_capturer_architecture`, `test_behavior_main_entrypoint` but not this module.
Suggested validation: Migrate both tests to `ForegroundMouseController` (pausing semantics under test apply to the paused-gate contract) and run `tests.test_behavior_safety_and_battle_scenarios`; verify green.
Confidence: 0.95

### F2
Severity: BLOCKING
Regression / invariant: Dev/verification tooling that the Final SPEC appendix declared in scope ("dev-only scripts may remain out of scope unless they break... if touched, migrate only the minimum necessary wiring") was left broken by the retired constructor surface.
Location: `scripts/crop_tool.py:46,70`; `scripts/diagnose_merchant_gold_ocr.py:56,58`; `tests/test_capture.py:21,32,45`
Claim: These tools construct base `ScreenCapturer` and call `capture()`, which now raises `NotImplementedError` (`capture/screen.py:298`), so the tools crash at runtime instead of capturing.
Evidence: `capture/screen.py:291-298` ??base `capture()` body replaced with `raise NotImplementedError("Select BackendScreenCapturer or ForegroundScreenCapturer")`; none of the three files was updated in the diff (only `scripts/test_single_click.py` was migrated). `mss.MSS()` is still constructed by the base `__init__` but `capture()` cannot execute.
Suggested validation: Migrate each tool to an explicit adapter (`BackendScreenCapturer`/`ForegroundScreenCapturer` selected by the tool's intended mode or via `runtime.io_adapters.compose_capture`), or explicitly exclude them in the SPEC; then smoke-run each tool path.
Confidence: 0.9

## Advisory findings

- `tests/test_behavior_pause_resume.py:407` (approx.) retains an unused `from actions.mouse import MouseController` import after migration to `ForegroundMouseController` ??harmless stale import.
- `BackendScreenCapturer` drops the original backend failure logging (`[ScreenCapturer] Backend capture failed; refusing foreground fallback.`) ??externally observable result contract (`None`) preserved; only diagnostics changed.
- `ForegroundMouseController.click` no longer logs on `pyautogui.FailSafeException` (original logged then re-raised); re-raise still present.
- A `mss.MSS()` handle is still created inside the base `ScreenCapturer.__init__` for backend adapters that never use it (construction-time side effect kept, matching origin/main; `close()` still released by `GameStateMachine` shutdown).
- Unverified within budget: full run of the focused test modules (`tests.test_runtime_io_composition`, `tests.test_screen_capturer_architecture`, `tests.test_mouse_refactor`, `tests.test_mouse_coordinates`, `tests.test_foreground_demo_mode_isolation`) was not executed (read-only review; no test runner invocation permitted).

<!-- blackfire-gate-fingerprint: {"schema":1,"role":"regression-reviewer","hash":"0b3008595ee0b9836a50556a30342398411280186d7760e9436c38f6d8091a0d"} -->
