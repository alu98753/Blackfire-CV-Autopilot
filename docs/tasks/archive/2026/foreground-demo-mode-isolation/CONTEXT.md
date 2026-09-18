Now let me check the main entry point and a few key test files to understand test coverage and constructor patterns.
**MAXIMUM STEPS REACHED** ??I've completed 10 tool calls (8 reads + 1 grep + 1 grep). Here is the scout report based on the evidence gathered.

---

# Scout Context

## Relevant files and symbols

| File | Why it matters |
|---|---|
| `cli/arguments.py` | Sets `args.backend_mode = not args.foreground` (line 76) ??the single CLI-level mode resolution point. |
| `runtime/bootstrap.py` | Composition root: constructs `ScreenCapturer(... backend_mode=...)` (line 156), `MouseController(... backend_mode=...)` (line 158), propagates `backend_mode` onto `state_machine` (line 192). |
| `actions/mouse.py` | `MouseController` ??every method (`click`, `scroll`, `drag`, `move_to_safe_area`) contains `if self.backend_mode:` branches with interleaved Win32 vs pyautogui logic. This is the primary duplication target. |
| `capture/screen.py` | `ScreenCapturer` ??`capture()` (line 292) branches on `self.backend_mode`; backend already fails closed (lines 308??19). Backend black-image returns `None` without foreground fallback (line 282??83). |
| `utils/steam_launcher.py` | `SteamGameLauncher.__init__` creates fallback `ScreenCapturer` and `MouseController` when not injected (lines 45??6), using its own `backend_mode`. This is the key re-construction site that could violate isolation. |
| `states/exceptions/subflows/game_relaunch.py` | Passes `machine.backend_mode` into `SteamGameLauncher` constructor (line 53); also assigns `machine.last_state_change = time.time()` (line 70). |
| `main.py` | Creates a separate `SteamGameLauncher` at line 76 for the initial launch gate (before `init_state_machine_system`), propagating `args.backend_mode`. |
| `states/state_machine.py` | Stores `backend_mode` on the machine (line 192 of bootstrap) and propagates it to quest configs (lines 1812??813). Also serializes `backend_mode` through `__setstate__` guards (lines 1708, 1715). |

## Current control flow

```
cli/arguments.py::parse_arguments()
  ?? args.backend_mode = not args.foreground        ??single resolution point

main.py::main()
  ?? SteamGameLauncher(... backend_mode=args.backend_mode)   ??initial launch gate
  ??    ?? may create its OWN ScreenCapturer/MouseController if none injected
  ?? init_state_machine_system(args, config, target_hwnd)
        ?? ScreenCapturer(... backend_mode=backend_mode)     ??runtime capturer
        ?? MouseController(... backend_mode=backend_mode)    ??runtime mouse
        ?? state_machine.backend_mode = backend_mode         ??stored on SM for relaunch/quest propagation

states/exceptions/subflows/game_relaunch.py::execute()
  ?? SteamGameLauncher(... backend_mode=machine.backend_mode)  ??constructs AGAIN
        ?? capturer/mouse passed from machine if present
```

The `backend_mode` boolean is threaded through 4 independent construction sites (`main.py` launcher, `bootstrap.py` capturer+mouse, `game_relaunch.py` launcher, and `SteamGameLauncher`'s own fallback constructors). Every `MouseController` method and `ScreenCapturer.capture()` re-checks the boolean at action time.

## Existing safety mechanisms

- **Backend fail-closed (capture):** `ScreenCapturer.capture()` (lines 308??19) refuses foreground fallback on missing HWND, backend failure, and unsupported full-screen. Black-image also returns `None` without MSS fallback.
- **Backend fail-closed (mouse):** `MouseController.click/scroll/drag` return `False` on backend exception; they do NOT fall through to pyautogui. The pyautogui path is only reached when `self.backend_mode` is `False`.
- **Constructor injection in bootstrap:** `ScreenCapturer` and `MouseController` are passed into `GameStateMachine` via constructor injection (lines 183??89).
- **WindowHandle abstraction:** Both `ScreenCapturer` and `MouseController` delegate HWND lookup to `utils.window.WindowHandle` ??a shared, mode-agnostic dependency.
- **Callback inversion:** Mouse ??SM communication uses injected callbacks (`_on_action_success`, `_is_paused_fn`, `_resume_event`), not direct SM references.

## Existing tests

| Test file | What it covers for this task |
|---|---|
| `test_behavior_main_entrypoint.py` | `test_argument_parser_defaults_to_backend_and_supports_foreground_opt_in` ??asserts `backend_mode` resolves correctly from `--foreground`/`--backend`/default. `test_main_binds_selected_window_profile_before_loading_mode_and_starts_loop` ??asserts `SteamGameLauncher` receives `backend_mode=True` and `ScreenCapturer` receives `backend_mode=True`. `test_initializer_wires_profile_runtime_refresh_and_daily_pipeline` ??asserts `capturer_class` called with `backend_mode=True`. |
| `test_screen_capturer_architecture.py` | Tests backend capture fail-closed: backend=True returns `None` on invalid HWND, on full-screen, on PrintWindow failure, on black image. Foreground path tested separately. |
| `test_mouse_refactor.py` | `test_move_to_safe_area_backend_mode` ??asserts Win32 PostMessage path. Foreground tests for `click`, `scroll`, `drag` use `backend_mode=False`. |
| `test_mouse_coordinates.py` | `test_click_backend_mode_client_coords` ??asserts PostMessage call args with backend_mode=True. `backend_mode=False` test asserts pyautogui calls. |
| `test_game_process_lifecycle.py` | Not yet read ??likely covers process termination/relaunch but `backend_mode` involvement is uncertain. |

**Gap:** No test covers `SteamGameLauncher`'s fallback constructor behavior (creating its own `ScreenCapturer`/`MouseController` when none injected). No test covers `game_relaunch.py`'s propagation of `machine.backend_mode` into the launcher. No test asserts that `state_machine.backend_mode` is set during bootstrap.

## Regression and architecture risks

1. **Triple construction site:** `SteamGameLauncher.__init__` constructs capturer+mouse as fallback (lines 45??6) AND `main.py` creates a launcher before `bootstrap.py` creates the runtime capturer+mouse AND `game_relaunch.py` creates yet another launcher. Any adapter split must handle all three sites or the fallback constructors will silently create mixed-mode components.

2. **Mutable `backend_mode` on state_machine:** The attribute is set after construction (`state_machine.backend_mode = backend_mode` in bootstrap line 192) and also mutated in tests (e.g., `test_behavior_pause_resume.py:473` sets `capturer.backend_mode = True` directly). Any migration to frozen/injected adapters must preserve or replace these mutable patterns.

3. **Quest config propagation:** `state_machine.py:1812??813` copies `backend_mode` into quest configs. This is a secondary consumer of the mode boolean that is unrelated to I/O adapter selection ??it may represent legitimate per-quest behavior gating rather than I/O mode branching. Needs classification.

4. **`state_machine.__setstate__` guards:** Lines 1708/1715 of `state_machine.py` explicitly preserve `backend_mode` through serialization. Deserialization paths in supervisor restart depend on this.

5. **Test mutation patterns:** Multiple tests directly set `.backend_mode` on constructed objects (e.g., `self.capturer.backend_mode = True` in `test_screen_capturer_architecture.py:84`). If the adapter pattern replaces the boolean with injected concrete classes, these test patterns break.

## Uncertainty

- **`test_game_process_lifecycle.py`:** Not read within budget. May contain `backend_mode`-relevant assertions for the relaunch/termination path.
- **Port/protocol seam:** The SPEC asks whether `ScreenCapturer`/`MouseController` APIs are already consumed polymorphically (via a protocol) or whether consumers reference concrete classes. From the code read, `TemplateMatcher`, `GameStateMachine`, and handlers all receive the concrete `ScreenCapturer` and `MouseController` via constructor injection ??no abstract base class or Protocol is visible. This needs verification.
- **`state_machine.py` quest propagation semantics:** Whether `backend_mode` in quest configs controls I/O adapter selection vs. game-logic behavior gating is unclear without reading the quest consumer code.
- **`utils/steam_launcher.py` fallback constructors:** Whether any production path actually hits the `or ScreenCapturer(...)` / `or MouseController(...)` fallback (vs. always receiving injected instances) cannot be proven without tracing all call sites.

## Minimal proposed change surface

1. **New adapter classes or protocol** in `capture/` and `actions/` (or a new `adapters/` package) ??one backend concrete, one foreground concrete, sharing a common interface.
2. **`runtime/bootstrap.py`** ??select concrete adapters once based on `backend_mode`, inject them downstream.
3. **`actions/mouse.py`** ??split into `BackendMouseAdapter` and `ForegroundMouseAdapter` (or a single class with adapter-strategy injection), removing the `if self.backend_mode` branches.
4. **`capture/screen.py`** ??same split for the capture path.
5. **`utils/steam_launcher.py`** ??accept injected adapters; remove fallback construction of mixed-mode components.
6. **`states/exceptions/subflows/game_relaunch.py`** ??propagate injected adapters instead of re-constructing from `machine.backend_mode`.
7. **`main.py`** ??pass selected adapters through the launcher and bootstrap.
8. **Test updates** for the 5 focused test files plus `game_relaunch` and launcher coverage.

## Recommendation

**GO WITH SPEC CHANGES** ??The repository evidence confirms the SPEC's diagnosis: `backend_mode` is threaded as a mutable boolean through 4+ construction sites and re-checked at every I/O action. The intended adapter isolation is architecturally sound and the smallest change surface is identifiable. However, the SPEC should be updated to explicitly address:

1. The `SteamGameLauncher` fallback-constructor hazard (must be resolved, not just noted).
2. The `state_machine.backend_mode` quest-config propagation ??is it in-scope for removal or explicitly preserved as unrelated to I/O adapter selection?
3. The mutable `.backend_mode` test patterns ??the SPEC should state whether tests should migrate to injected adapters or retain a compatibility boolean for test convenience.
4. The absence of an existing port/protocol seam ??the SPEC's "provisional design direction" mentions protocols but the codebase uses concrete class injection throughout; the Final SPEC should commit to a concrete pattern (ABC, Protocol, or wrapper).
