# foreground-demo-mode-isolation

Status: Draft

## Goal

Isolate visible foreground physical I/O as an explicit demo/compatibility adapter path while making production runtime composition depend on backend Win32 capture/input adapters without spreading `backend_mode` conditionals through production I/O components.

This is Phase 2 after `backend-default-runtime-mode`. Phase 1 already changed public semantics to backend-by-default, added explicit `--foreground`, preserved temporary legacy `--backend` compatibility, and made backend capture/input fail closed. This task is structural isolation, not another semantic inversion.

## Lightweight survey evidence

Latest `main` base:

`145522e4a7fbb773c45f10fb358ce310c0b095d6` — merge of `backend-default-runtime-mode`.

Current production composition resolves the I/O mode at startup and passes a boolean into shared mixed-mode implementations:

- `cli/arguments.py` sets `args.backend_mode = not args.foreground`.
- `runtime/bootstrap.py` constructs `ScreenCapturer(... backend_mode=...)` and `MouseController(... backend_mode=...)`.
- `main.py` / `SteamGameLauncher` also propagate the resolved mode.
- `actions/mouse.py::MouseController` contains backend/foreground branches for click, scroll, drag, and safe-area movement.
- `capture/screen.py::ScreenCapturer.capture` contains backend/foreground branches; Phase 1 already made the backend branch fail closed.
- `utils/steam_launcher.py::SteamGameLauncher` can construct both capturer and mouse from `backend_mode`.
- `states/exceptions/subflows/game_relaunch.py` still propagates the mode into `SteamGameLauncher`.

The Greenfield-lite architecture already defines the desired dependency direction:

```text
main / composition root
  → agent loop
    → perception / intent / navigation / recovery
      → ports
        → capture / matcher / input / process adapters
```

and explicitly states that input adapters are business-blind.

## Intended responsibility boundary

Target architecture, subject to Scout confirmation against the full nearby implementation:

```text
Production Runtime
  └─ Backend I/O adapters
      ├─ Win32 capture
      └─ Win32 mouse/input

Demo / Compatibility Runtime
  └─ Foreground I/O adapters
      ├─ visible MSS/PIL capture
      └─ pyautogui physical input
```

The composition root may still resolve `--foreground`, but production consumers should receive an already-selected capture/input dependency rather than repeatedly deciding backend vs foreground at action time.

## Scope

- Identify the smallest architecture-consistent seam for separate backend and foreground capture/input adapters.
- Move runtime mode selection toward the composition root / factory boundary.
- Remove broad `if self.backend_mode ... else ...` duplication from production input/capture execution paths where the adapter split owns that decision.
- Preserve the existing public CLI contract from Phase 1:
  - no mode flag → backend production path;
  - `--foreground` → explicit visible demo path;
  - legacy `--backend` remains accepted until separately deprecated/removed.
- Preserve current HWND/target ownership and multi-instance semantics.
- Preserve backend fail-closed behavior: backend failure must never silently invoke foreground physical input or foreground capture.
- Preserve foreground demo behavior: visible capture plus pyautogui physical interaction.
- Keep state machine, navigation, gameplay policy, timing, coordinates, and CV semantics behavior-preserving.
- Update deterministic tests around composition and adapter boundaries.
- Make only directly required launcher/relaunch compatibility changes.

## Known invariants

- Production runtime uses backend Win32 I/O by default.
- Production backend failure never silently falls back to foreground capture or physical mouse input.
- `--foreground` remains explicit opt-in demo/compatibility behavior.
- Target HWND / window selection remains a separate responsibility from selecting the I/O adapter.
- Input/capture adapters remain business-blind and do not own gameplay intent/state.
- Gameplay handlers and state-machine code should not gain new mode-selection responsibilities.
- One tick / one-frame and existing capture semantics must remain intact.
- Behavior-preserving refactor: backend click/scroll/drag coordinates, delays, post-message behavior, capture result contract, and foreground demo behavior must not change unless the Final SPEC explicitly says so.
- No shared Python environment mutation.

## Provisional design direction

Preferred direction to validate during Scout:

1. Keep CLI/runtime mode resolution at startup.
2. Introduce or expose explicit backend and foreground concrete adapters (or equivalent factories) behind the existing capture/input consumer contracts.
3. Select the concrete adapters once in the composition root.
4. Pass selected dependencies downstream.
5. Retain only narrowly justified compatibility facades where existing tests/dev utilities materially benefit; do not preserve mixed-mode branching solely for convenience.

The exact class/module names are intentionally not Final yet.

## Non-goals

- Changing the Phase-1 CLI semantics.
- Removing `--foreground`.
- Removing legacy `--backend` in this task unless Scout proves it is required for the isolation and the Final SPEC explicitly approves it.
- Video recording functionality.
- Gameplay/state-machine refactors unrelated to I/O dependency selection.
- CV detector/matcher changes.
- Navigation, scheduler, recovery-policy, or timing changes.
- HWND/window ownership redesign.
- Broad cleanup of unrelated dev scripts.
- Shared environment or dependency mutation.
- Replacing the repository architecture with a new framework/DI container.

## Provisional acceptance criteria

1. Normal production startup composes backend capture/input implementations without downstream production code needing to branch on foreground/backend for ordinary capture/click/scroll/drag execution.
2. `--foreground` composes the foreground demo/compatibility implementations and preserves visible capture + pyautogui behavior.
3. Backend capture failure remains fail-closed and never invokes MSS/PIL as an implicit fallback.
4. Backend input failure remains fail-closed and never invokes pyautogui as an implicit fallback.
5. Foreground capture retains its existing MSS → PIL fallback behavior.
6. Existing backend and foreground coordinate/click/drag/scroll semantics remain behavior-preserving.
7. HWND target selection and multi-instance targeting remain unchanged.
8. Launcher/relaunch paths reuse the already selected runtime I/O responsibility instead of creating a contradictory mode owner.
9. State-machine/gameplay code does not acquire new I/O mode-selection conditionals.
10. Focused deterministic tests prove production and demo composition plus fail-closed behavior.
11. No unrelated gameplay, CV, scheduling, or environment changes are introduced.

## Initial focused verification candidates

At minimum inspect/retain/update coverage around:

- `tests/test_behavior_main_entrypoint.py`
- `tests/test_screen_capturer_architecture.py`
- `tests/test_mouse_refactor.py`
- `tests/test_mouse_coordinates.py`
- `tests/test_game_process_lifecycle.py`

Scout should determine whether launcher/relaunch-specific tests need to be added to the focused set.

## Uncertainty for Scout

Scout must answer before this Draft becomes Final:

- What is the smallest stable consumer contract already relied on by `TemplateMatcher`, `GameStateMachine`, handlers, and tests: concrete `ScreenCapturer/MouseController` APIs or an existing port/protocol seam?
- Should Phase 2 use separate concrete classes, factories returning common protocols, composition wrappers, or a narrowly compatible facade?
- Which `backend_mode` usages are true architectural mode selection versus legitimate demo-specific/window-management behavior?
- Does `SteamGameLauncher` actually need mouse ownership, or can it reuse injected runtime dependencies without constructing mixed-mode components?
- Which dev utilities intentionally rely on direct foreground constructors and therefore need explicit demo adapter construction?
- Are any tests asserting constructor defaults/mutable `backend_mode` toggling that should be migrated rather than preserved?
- Can runtime/state-machine `backend_mode` propagation be removed completely in this task, or is some compatibility field still required at relaunch/supervisor boundaries?
- Are there any full-screen capture consumers that are demo-only and should move explicitly to the foreground adapter?
- What is the correct module/package location consistent with existing repository architecture and naming?

## Lifecycle note

This SPEC remains Draft until `scripts/task_start.ps1 -Task foreground-demo-mode-isolation` returns `TASK_READY`, `scripts/ai_scout.ps1 -Task foreground-demo-mode-isolation` produces `CONTEXT.md`, and ChatGPT + user re-read the evidence and finalize the responsibility boundary. Production implementation must not begin while Status is Draft.
