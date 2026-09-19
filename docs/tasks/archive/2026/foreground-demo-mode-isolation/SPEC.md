# foreground-demo-mode-isolation

Status: Final

## Goal

Isolate visible foreground physical I/O as an explicit demo/compatibility path, while production runtime uses backend Win32 capture/input implementations selected once at composition time.

This is Phase 2 after `backend-default-runtime-mode`. Phase 1 established:

- no flag -> backend production semantics;
- `--foreground` -> explicit visible foreground mode;
- legacy `--backend` remains accepted for compatibility;
- backend capture/input failures fail closed rather than silently invoking foreground I/O.

This task is a behavior-preserving architecture refactor. It does not re-decide those semantics.

## Evidence base

Base:

`145522e4a7fbb773c45f10fb358ce310c0b095d6`

Scout evidence:

`docs/tasks/foreground-demo-mode-isolation/CONTEXT.md`

Scout confirmed that `backend_mode` is currently threaded through multiple construction sites and re-checked inside ordinary I/O operations:

- `cli/arguments.py` resolves `args.backend_mode = not args.foreground`;
- `main.py` passes the mode into `SteamGameLauncher`;
- `runtime/bootstrap.py` constructs `ScreenCapturer` and `MouseController` with the mode and stores it on `GameStateMachine`;
- `actions/mouse.py` branches inside click/scroll/drag/safe-area movement;
- `capture/screen.py` branches inside capture;
- `utils/steam_launcher.py` can construct its own capture/input objects from the mode;
- `states/exceptions/subflows/game_relaunch.py` passes `machine.backend_mode` back into the launcher.

Additional Final-SPEC review established:

- `SteamGameLauncher` does not require mouse ownership for its current launch/readiness flow; it uses capture/window responsibilities for HWND/window rect/monitor placement.
- `tests/test_game_process_lifecycle.py` is class-level skipped and therefore is not sufficient focused verification by itself.
- Existing tests directly mutate `.backend_mode`; these are test-shape artifacts and must not force preservation of a mutable production mode switch.
- `state_machine.config["backend_mode"]` propagation is compatibility/runtime metadata, not permission for gameplay code to choose I/O implementations.

## Architecture contract

Target:

```text
CLI / composition root
  |
  +-- Production (default)
  |     +-- Backend capture adapter
  |     |     \-- Win32 HWND capture only
  |     \-- Backend input adapter
  |           \-- Win32 message input only
  |
  \-- Demo (--foreground)
        +-- Foreground capture adapter
        |     \-- MSS -> PIL fallback
        \-- Foreground input adapter
              \-- pyautogui physical mouse
```

Downstream consumers receive already-selected dependencies.

The ordinary capture/input execution path must not decide backend vs foreground at action time.

The repository already relies on constructor injection and duck-typed concrete APIs. This task therefore does **not** introduce a framework-scale ABC/Protocol hierarchy. Prefer explicit concrete backend/foreground implementations plus a small composition/factory seam. A thin compatibility facade is allowed only where it prevents unnecessary unrelated churn; such a facade must not retain mutable runtime mode switching.

Exact class/module names are implementation details, but responsibility must follow this contract.

## Responsibility boundaries

### CLI / composition

Owns:

- interpreting `--foreground`;
- retaining legacy `--backend` parser compatibility;
- choosing production vs demo I/O family once.

Does not own:

- capture mechanics;
- click/drag/scroll mechanics;
- gameplay logic.

### Backend capture

Owns:

- HWND-backed Win32 capture;
- current backend capture resource cleanup;
- backend capture failure logging/result contract;
- window lookup/geometry behavior needed by existing runtime.

Must never:

- call MSS;
- call PIL ImageGrab;
- silently switch to visible capture.

### Foreground capture

Owns:

- visible MSS capture;
- existing PIL fallback when MSS fails;
- visible/full-screen behavior currently belonging to foreground mode.

Must never be entered because backend capture failed.

### Backend input

Owns:

- Win32 message click;
- Win32 scroll;
- Win32 drag;
- Win32 safe-area cursor message;
- existing backend coordinate conversion, jitter, delays, callback/finalization semantics.

Must never:

- invoke pyautogui after a backend failure.

### Foreground input

Owns:

- pyautogui click;
- pyautogui scroll;
- pyautogui drag;
- physical safe-area movement;
- existing foreground coordinate conversion, human-like motion, failsafe, delays, callback/finalization semantics.

### GameStateMachine / gameplay

Consumes selected capture/input dependencies.

Must not select an I/O implementation.

A legacy/runtime `backend_mode` fact may temporarily remain on state/config only where required by unrelated compatibility/serialization paths, but:

- it is metadata, not an I/O selector;
- new gameplay branches on it are forbidden;
- capture/input/launcher construction must not depend on re-reading it downstream.

Removing all legacy metadata propagation is not required for this task unless it is proven dead and removal is local/risk-free.

### SteamGameLauncher

Owns process/window readiness only.

It may use an injected capture/window-capable dependency for:

- `get_hwnd`;
- `get_window_rect`;
- `ensure_window_on_monitor`.

It must not:

- own or construct a mouse/input adapter solely because an old constructor parameter existed;
- create mixed-mode capture/input fallbacks from `backend_mode`;
- become a second runtime I/O mode owner.

For initial startup, composition may create the appropriate capture/window dependency before state-machine construction, or use a small shared factory. There must still be exactly one mode-selection policy.

### GameRelaunchSubflow

Must reuse the machine's already-selected capture/window dependency when invoking launcher behavior.

It must not use `machine.backend_mode` to reconstruct a fresh competing I/O family.

## Scope

- Split or strategy-isolate backend and foreground capture behavior so ordinary capture execution has no mutable `backend_mode` branch.
- Split or strategy-isolate backend and foreground input behavior so click/scroll/drag/safe-area execution has no mutable `backend_mode` branch.
- Add the smallest composition/factory seam necessary to select production vs demo dependencies once.
- Update `runtime/bootstrap.py` and `main.py` to use that seam.
- Remove `SteamGameLauncher` mouse ownership/construction if no current behavior requires it.
- Remove launch/relaunch reconstruction based on downstream `backend_mode`.
- Preserve window targeting/HWND ownership and multi-instance behavior.
- Migrate deterministic tests from mutating `.backend_mode` toward constructing/selecting the intended adapter.
- Add non-skipped deterministic launcher/relaunch composition coverage sufficient to verify isolation.
- Preserve Phase-1 CLI semantics and backend fail-closed behavior.

## Known invariants

1. Production runtime is backend by default.
2. `--foreground` is explicit demo/compatibility opt-in.
3. Backend capture failure never invokes foreground MSS/PIL.
4. Backend input failure never invokes pyautogui.
5. Foreground capture retains MSS -> PIL fallback.
6. Backend and foreground coordinate semantics remain behavior-preserving.
7. Existing click/scroll/drag timings, jitter, callbacks, pause gate, action-success notification, and safe-area semantics remain behavior-preserving.
8. HWND/target selection and multi-instance behavior remain unchanged.
9. One tick / one frame semantics remain unchanged.
10. Capture/input adapters remain business-blind.
11. State machine/navigation/handlers do not gain new I/O-selection responsibilities.
12. No shared Python environment mutation.
13. Behavior-preserving refactor: no gameplay, CV, scheduler, navigation, or recovery-policy semantic change.

## Compatibility policy

### CLI

Preserve:

```text
no flag       -> backend production
--foreground  -> foreground demo
--backend     -> accepted legacy compatibility flag
```

This task does not remove `--backend`.

### Python constructors / tests

Compatibility with mutable runtime toggling such as:

```python
capturer.backend_mode = True
mouse.backend_mode = False
```

is **not** an invariant.

Tests that use this pattern must migrate to explicit adapter construction/selection.

A legacy constructor/facade may remain temporarily only if required by meaningful external/dev call sites and only if its mode is resolved once during construction. It must not permit switching the implementation by mutating a boolean after construction.

## Non-goals

- Removing `--foreground`.
- Removing legacy `--backend`.
- Video recording functionality.
- Rewriting HWND/window management.
- Reworking TemplateMatcher or detector architecture.
- Gameplay/state-machine behavior changes.
- Navigation/scheduler/recovery/timing changes.
- Broad quest-config cleanup.
- Serialization redesign.
- DI frameworks, service containers, generalized plugin systems, or unnecessary ABC hierarchies.
- Broad dev-tool migration unrelated to runtime I/O isolation.
- Shared environment/dependency mutation.

## Acceptance criteria

1. Default startup selects backend capture and backend input exactly once at composition time.
2. `--foreground` selects foreground capture and foreground input exactly once at composition time.
3. Ordinary backend capture execution contains no foreground fallback path.
4. Ordinary backend click/scroll/drag/safe-area execution contains no pyautogui fallback path.
5. Ordinary foreground capture/input execution does not contain backend-selection branches.
6. Backend failure remains fail-closed with the existing externally observable result contract.
7. Foreground capture preserves MSS -> PIL fallback.
8. Existing backend click/scroll/drag coordinate and timing semantics remain unchanged.
9. Existing foreground pyautogui coordinate, failsafe, human-like, timing, and safe-area semantics remain unchanged.
10. `SteamGameLauncher` no longer constructs/owns an unused mouse adapter and does not independently select a runtime I/O mode.
11. Relaunch reuses the machine's selected capture/window dependency and does not reconstruct I/O from `machine.backend_mode`.
12. Gameplay/state-machine code does not acquire new `backend_mode` branches for I/O selection.
13. Direct test mutation of `.backend_mode` is removed from focused isolation tests in favor of explicit adapter construction.
14. Deterministic non-skipped tests prove both production and demo composition.
15. Deterministic non-skipped tests prove launcher/relaunch cannot silently create a contradictory I/O family.
16. Phase-1 CLI tests still prove default backend, explicit `--foreground`, and legacy `--backend` acceptance.
17. No unrelated gameplay/CV/scheduling/environment behavior changes are introduced.

## Focused verification

Required focused modules:

```text
tests.test_runtime_io_composition
tests.test_screen_capturer_architecture
tests.test_mouse_refactor
tests.test_mouse_coordinates
tests.test_foreground_demo_mode_isolation
```

`tests.test_runtime_io_composition` is the dedicated deterministic module for
this task's CLI/main/bootstrap composition contract, avoiding unrelated
dungeon/runtime-loop behavior contained in `tests.test_behavior_main_entrypoint`.

Add or update a non-skipped deterministic test module for launcher/relaunch composition. The existing class-level skipped `tests.test_game_process_lifecycle` does not satisfy this acceptance criterion unless the relevant tests are safely refactored into non-side-effecting, non-skipped deterministic coverage.

If implementation touches pause/resume adapter wiring, also run the relevant deterministic `tests.test_behavior_pause_resume` target(s).

Focused verification must run through the repository's shared `.venv`; no dependency mutation.

## Implementation guidance

Preferred minimal shape:

```text
resolve CLI mode
  -> small I/O composition factory
      -> backend concrete capture + input
      OR
      -> foreground concrete capture + input
  -> inject selected dependencies
      -> launcher window/process readiness
      -> GameStateMachine
      -> relaunch reuses same capture/window dependency
```

Reuse shared mode-agnostic mechanics such as `WindowHandle`, callbacks, pause gate, and action finalization rather than duplicating them.

Do not preserve a mixed-mode production class merely to keep old tests unchanged.

## Scout uncertainties resolved

- **Consumer seam:** current code uses constructor-injected concrete/duck-typed APIs; no new broad Protocol/ABC framework is required.
- **Pattern:** explicit backend/foreground concrete implementations selected by a small composition/factory seam.
- **Launcher mouse ownership:** not required by current launcher behavior; remove it from launcher responsibility.
- **Mutable test mode:** migrate tests; do not preserve mutable production mode switching for test convenience.
- **State-machine backend_mode:** may remain temporarily as compatibility metadata where unrelated consumers/serialization require it, but cannot own I/O selection.
- **Relaunch:** must reuse selected dependencies rather than reconstructing by mode.
- **Full-screen capture:** foreground/demo concern; backend remains unsupported/fail-closed.
- **Launcher/relaunch verification:** must gain non-skipped deterministic coverage.

## Lifecycle

Scout evidence has been reviewed and incorporated.

`Status: Final`

Gemini/Antigravity may now perform production implementation under this contract. OpenCode Scout/reviewers remain read-only. Any material deviation from this contract must be surfaced before implementation proceeds.

## Final bounded cleanup appendix

This appendix extends the Final SPEC only for the remaining runtime-I/O cleanup discovered during final review. It does not reopen or weaken any previously completed architecture, behavior-preservation, CLI, fail-closed, timing, launcher, or composition acceptance criteria above.

### Goal

Complete the isolation boundary by removing the remaining legacy mixed-mode API surface from runtime-facing code/tests and by making the relaunch capture dependency an explicit invariant.

### Additional scope

1. **Retire the legacy mixed-mode I/O facade from supported runtime/test usage.**
   - Production/runtime-facing code must not construct `MouseController(backend_mode=...)` or `ScreenCapturer(backend_mode=...)` as an I/O-selection mechanism.
   - Backend/foreground selection must use the explicit concrete adapters already established by this task.
   - Remove legacy `backend_mode` constructor/runtime-switch behavior from the base I/O classes only where required to make the explicit adapters the supported path and where doing so does not alter the already-verified backend/foreground mechanics.
   - Do not modify the verified Win32/pyautogui capture/input mechanics, coordinate transforms, jitter, callback/finalization behavior, safe-area behavior, or timing sequences.

2. **Align remaining focused/nearby tests with the explicit adapter architecture.**
   - Migrate `tests.test_mouse_refactor` and any directly affected deterministic tests away from legacy `MouseController(backend_mode=...)` / `ScreenCapturer(backend_mode=...)` construction when those tests are intended to verify production I/O behavior.
   - Preserve meaningful coverage of shared mode-agnostic mechanics.
   - Dev-only scripts may remain out of scope unless they break because the retired constructor surface is removed; if touched, migrate only the minimum necessary wiring.

3. **Make `machine.capturer` an explicit relaunch invariant.**
   - A live runtime `GameStateMachine` created through the supported bootstrap/composition path must always own a non-null already-composed capturer.
   - `GameRelaunchSubflow` must reuse that capturer and must not reconstruct capture from `machine.backend_mode`.
   - If relaunch is invoked with no capturer, fail explicitly and deterministically as an invariant violation; do not silently construct a replacement and do not fall back to foreground I/O.
   - Add deterministic coverage for the supported relaunch path and the missing-capturer invariant/failure contract.

### Additional non-goals

- No changes to dungeon/domain/gameplay/scheduler/navigation behavior.
- No changes to the already-verified backend click/scroll/drag/safe-area message sequence or timing.
- No changes to foreground pyautogui behavior.
- No new I/O factory/composition layer beyond the existing explicit adapter seam.
- No recovery-policy redesign beyond making missing capturer fail explicitly.
- No removal of CLI `--foreground` or legacy CLI `--backend` compatibility.
- No shared-environment or dependency changes.

### Additional acceptance criteria

18. Supported production/runtime paths no longer select I/O by constructing the legacy mixed-mode base classes with `backend_mode`.
19. Focused production-I/O tests use explicit backend/foreground adapters rather than the legacy constructor-selection path.
20. Removing the legacy facade does not change the already-reviewed backend/foreground capture/input behavior, especially backend click/scroll/drag/safe-area timing and Win32 message ordering.
21. A live state machine produced by the supported bootstrap path always has a non-null composed capturer.
22. Relaunch reuses the machine capturer and never reconstructs capture from `backend_mode`.
23. Relaunch with a missing capturer fails explicitly/deterministically and never creates a fallback capturer or invokes foreground I/O.
24. No unrelated gameplay/domain/dungeon/scheduler/runtime-loop behavior changes are introduced.

### Additional verification

At minimum, run the task's existing focused set plus deterministic coverage for:
- legacy mixed-mode constructor retirement / explicit adapter usage;
- backend behavior-preservation tests;
- relaunch reuse of the existing capturer;
- relaunch missing-capturer invariant failure.

Because this appendix changes production/runtime code after the previous Gate PASS, the prior Gate evidence is historical only. After implementation and focused verification, the user must run `scripts/ai_gate.ps1 -Task foreground-demo-mode-isolation` again. Gemini/Antigravity must not run AI Gate.
