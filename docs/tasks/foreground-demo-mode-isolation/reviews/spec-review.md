# Spec Review

Gate-accepted verdict: PASS
Blocking findings: 0

# Spec Review

## Clause coverage

Reviewed `docs/tasks/foreground-demo-mode-isolation/SPEC.md` (Final) against the candidate diff and current working tree (snapshots match on-disk state).

- **Composition contract (AC1/AC2, "exactly one mode-selection policy"):** `cli/arguments.py` remains the single resolution point (`backend_mode = not foreground`); `main.py` and `runtime/bootstrap.py` both derive `foreground=not backend_mode` from the same resolved arg and route through the new `runtime.io_adapters.compose_io` / `compose_capture` seam. Satisfied.
- **No action-time mode branch (AC3/AC4/AC5):** `BackendScreenCapturer.capture` is HWND/`_capture_backend` only (no MSS/PIL); `BackendMouseController` click/scroll/drag/safe-area are Win32 message-only (no pyautogui). `ForegroundScreenCapturer` retains MSS -> PIL fallback; `ForegroundMouseController` uses pyautogui only. Base classes retain legacy mixed branches but production no longer constructs them (verified all production construction sites: `main.py`, `runtime/bootstrap.py`, `game_relaunch.py`).
- **Fail-closed (invariant 3/4, AC6):** Backend capture returns `None` on invalid HWND/full-screen/backend failure; backend input returns `False` on missing HWND instead of falling through to pyautogui (difference from old base-class fall-through is a compliance improvement, not a regression).
- **Launcher contract (AC10):** `SteamGameLauncher` no longer owns `mouse` or `backend_mode`; requires an injected capturer (ValueError otherwise); no remaining `self.mouse` references.
- **Relaunch contract (AC11):** `GameRelaunchSubflow` passes `capturer=getattr(machine, 'capturer', None)`, no `backend_mode`/`mouse` reconstruction.
- **Metadata allowance (SPEC 144-150, AC12):** `state_machine.backend_mode` retained only for serialization guards (`__setstate__`) and quest-config propagation; no new gameplay I/O-selection branches.
- **Tests (AC13-16, focused verification):** New non-skipped `test_runtime_io_composition.py` and `test_foreground_demo_mode_isolation.py` prove both composition families, launcher injected-capture requirement, relaunch capture reuse, and backend no-fallback; `test_mouse_coordinates.py` / `test_screen_capturer_architecture.py` migrated to adapters; Phase-1 CLI semantics covered in `test_runtime_io_composition.test_cli_modes`. `test_game_process_lifecycle.py` remains skipped but the SPEC's requirement for non-skipped deterministic launcher/relaunch coverage is met by the new modules.
- **Behavior preservation (AC8/AC9):** Adapter timings, finalize cooldown/move_safe, jitter, and message sequences (e.g., backend drag `WM_MOUSEMOVE -> LBUTTONDOWN -> interpolated moves -> LBUTTONUP` with `.03/.05/.15/.02` sleeps) match base backend paths; foreground human-like/failsafe/target_pos semantics match base foreground paths.

## Blocking findings

None

## Advisory findings

- `runtime/io_adapters.py` is a new module under `runtime/` while task.json scope lists `runtime/bootstrap.py` as a file entry (no `runtime/` directory). Scope-list governance nuance; no contract impact.
- `BackendScreenCapturer.capture` drops the base class's fail-closed diagnostic logging ("refusing foreground fallback"); result contract is identical but the SPEC's "failure logging" responsibility is thinner. Consider restoring logging.
- `tests/test_mouse_refactor.py` still constructs raw `MouseController(backend_mode=...)` (mode resolved once at construction, never mutated) and `scripts/test_single_click.py` (dev-only) still exercises the legacy facade. Consistent with the SPEC compatibility policy but not migrated to adapters.

## Test evidence gaps

Focused evidence present for composition, launcher injection, relaunch reuse, and backend fail-closed behavior (new deterministic modules). Remaining gaps: no executed test run was performed in this read-only review; `test_mouse_refactor.py` migration to adapter classes is not demonstrated (constructor-arg facade usage only); paused/resume adapter wiring tests were untouched (SPEC only requires them if pause/resume wiring changed). A focused run of the five required modules via the shared `.venv` is still needed as final verification.

<!-- blackfire-gate-fingerprint: {"schema":1,"role":"spec-reviewer","hash":"eef50d2f0ab095dbac66cbeacd34e33d3ca33da0db69edfbdd82e84898980092"} -->
