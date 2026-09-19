# backend-default-runtime-mode

Status: Final

## Goal

Make backend Win32 I/O the production/default runtime mode. Foreground physical-input/capture behavior becomes explicit opt-in through `--foreground`, while remaining behavior-preserving for demo/visible-operation use. This task is Phase 1 of the foreground-click deprecation roadmap; it changes the public mode contract, propagation, and backend fail-safe behavior without performing the later architectural isolation/removal of foreground implementation.

## Current architecture / responsibility boundary

The resolved runtime I/O mode originates at `cli/arguments.py::parse_arguments` and is consumed through the production startup/runtime boundaries:

- `cli/mode_setup.py::setup_mode_config`
- `main.py::main`
- `runtime/bootstrap.py::init_state_machine_system`
- `actions/mouse.py::MouseController`
- `capture/screen.py::ScreenCapturer`
- `utils/steam_launcher.py::SteamGameLauncher`
- `states/state_machine.py` mode propagation
- `states/exceptions/subflows/game_relaunch.py::GameRelaunchSubflow.execute`
- `runtime/supervisor.py::prepare_resume_command` restart/resume preservation

Target-window/HWND selection and ownership remain separate responsibilities and must not be redesigned by this task.

## Final CLI contract

- No I/O-mode flag: backend Win32 non-grabbing mode.
- `--foreground`: explicit foreground physical-input/capture mode.
- Legacy `--backend`: temporarily accepted as a deprecated compatibility flag during Phase 1. It is no longer required to obtain backend behavior and must not remain the internal source of truth for the resolved mode.
- `--foreground` is the only explicit selector for foreground behavior.
- Do not introduce a `--demo` alias in Phase 1; repository vocabulary already uses `foreground` and `scripts/test_single_click.py` provides precedent.

Implementation may represent the resolved mode as a boolean or a clearer internal value, but production code must propagate the resolved semantic mode rather than relying on the old meaning `args.backend == explicit opt-in`.

## Scope

- Change CLI semantics so ordinary startup resolves to backend without `--backend`.
- Add/standardize explicit `--foreground` opt-in.
- Preserve temporary compatibility for legacy `--backend`; deprecation messaging may be argparse/help/log based, but must not alter the resolved backend behavior.
- Propagate the resolved mode consistently through startup/bootstrap, launcher, mouse, capture, state-machine, and relaunch boundaries.
- Ensure restart/resume preserves an original `--foreground` token, does not synthesize `--backend`, and mode-free restarts resolve backend under the new default.
- Narrowly harden production/runtime implicit defaults or call sites where omission could silently select foreground behavior. Broad test/dev utility migration is not required.
- Make `ScreenCapturer.capture()` mode-aware so backend capture failure does not fall through to MSS/PIL foreground capture.
- Add/update deterministic focused tests for CLI semantics, propagation, restart preservation, mouse selection, launcher propagation, and backend capture fail-safe behavior.
- Update only directly affected documentation/scripts that encode the old production contract (`foreground` default / `--backend` required).
- Classify direct dev/diagnostic utilities that intentionally use foreground capture without forcing a broad Phase-1 rewrite.

## Known invariants

- Production/default execution uses backend non-grabbing I/O.
- Production backend failure must never silently become foreground physical input or foreground capture.
- In backend mode, `_capture_backend()` failure must surface as capture failure (`None` or the existing explicit failure contract); it must not invoke MSS/PIL fallback.
- Foreground mode retains its existing MSS/PIL and `pyautogui` behavior in this phase.
- Mouse backend failure must not fall through to `pyautogui`.
- Existing backend Win32 input/capture semantics remain behavior-preserving except for removal of the unsafe backend-to-foreground capture fallback.
- Target-window/HWND ownership remains explicit and continues to support multi-instance/native/sandbox selection.
- Supervisor/restart remains an argument-preservation responsibility, not the owner of runtime mode policy.
- Phase 1 must not conflate default migration/fail-safe hardening with Phase-2 foreground implementation isolation.

## Restart / resume contract

`runtime/supervisor.py::prepare_resume_command` currently preserves the original command and only manages restart/profile/target/resume tokens. Preserve that responsibility boundary:

- original `--foreground` survives restart/resume;
- no restart path adds `--backend` merely to recover the production default;
- a mode-free original command remains mode-free and resolves backend when reparsed;
- legacy `--backend`, if present in an existing command, may remain preserved during the compatibility phase.

`states/exceptions/subflows/game_relaunch.py` must receive/use the already resolved runtime mode; its current `getattr(machine, "backend_mode", False)` foreground-biased fallback must not silently select foreground in production.

## Constructor/default safety boundary

Production/runtime construction sites must not silently select foreground because a mode argument was omitted. Implementation may either remove/alter unsafe defaults or make production call sites explicit, whichever is the smallest architecture-consistent change.

This requirement is limited to production/runtime boundaries. Unit tests and dev-only utilities that intentionally instantiate foreground components without an explicit mode do not all need mechanical migration.

Known defaults requiring review:

- `actions/mouse.py::MouseController(... backend_mode=False ...)`
- `capture/screen.py::ScreenCapturer(... backend_mode=False ...)`
- `utils/steam_launcher.py::SteamGameLauncher(... backend_mode=False ...)`
- `states/exceptions/subflows/game_relaunch.py` fallback to `False`

## Capture fail-safe contract

Current `ScreenCapturer.capture()` attempts backend capture and then can continue to MSS/PIL. Phase 1 must change this behavior:

- backend mode + backend capture success -> return backend image;
- backend mode + backend capture failure -> return/surface capture failure; do not invoke MSS/PIL;
- foreground mode -> preserve current foreground capture fallback behavior.

`full_screen=True` is not to be silently reclassified as production backend capture. If an active production path requires full-screen capture, implementation must stop and report the call site for SPEC reconsideration rather than inventing a mixed-mode fallback. Dev/demo full-screen behavior may remain foreground.

## Utility/dev-only boundary

Known utilities such as `scripts/test_single_click.py`, `scripts/crop_tool.py`, and `scripts/diagnose_merchant_gold_ocr.py` are not production bootstrap ownership surfaces. `scripts/test_single_click.py` already uses `--foreground` with backend default and is useful terminology precedent.

Do not broadly migrate utility scripts merely because constructor defaults change. If a utility requires an explicit mode to remain functional after a narrowly necessary constructor change, make only the minimum compatibility update and keep it classified as dev/demo behavior.

## Non-goals

- Deleting `pyautogui` or foreground capture code.
- Creating a new foreground/backend interface hierarchy or package solely for architectural aesthetics.
- Broad isolation of all foreground code.
- Adding video recording functionality.
- Changing CV detection, scheduler/state-machine behavior, gameplay policy, coordinates, timing, or click semantics unrelated to I/O mode selection/fail-safe behavior.
- Broad utility-script cleanup.
- Shared Python environment mutation.
- Phase-2 `foreground-demo-mode-isolation` work.

## Acceptance criteria

1. Normal application startup without an I/O-mode flag resolves backend mode.
2. `--foreground` explicitly resolves foreground physical-input/capture mode.
3. Legacy `--backend` remains accepted during Phase 1 but is not required for backend behavior; its compatibility/deprecation semantics are covered by deterministic tests.
4. The resolved mode reaches production `SteamGameLauncher`, `ScreenCapturer`, `MouseController`, state-machine, and game-relaunch boundaries without relying on foreground-biased omission defaults.
5. Supervisor/restart preserves `--foreground`, does not synthesize `--backend`, and a mode-free restart remains backend by default.
6. Backend `ScreenCapturer` failure does not invoke MSS or PIL/ImageGrab and surfaces capture failure through the existing capture failure contract.
7. Foreground capture retains the existing foreground fallback behavior.
8. Backend mouse behavior never silently falls through to `pyautogui`.
9. Existing backend/foreground coordinate/click semantics remain behavior-preserving.
10. Directly affected docs no longer tell production users that `--backend` is required; foreground is documented as explicit opt-in/demo-compatible behavior.
11. No Phase-2 foreground deletion/isolation or video-recording functionality is introduced.
12. Focused tests pass using the repository/shared environment without dependency mutation.

## Focused verification

At minimum, implementation should run the affected deterministic test modules covering these boundaries:

- `tests/test_behavior_main_entrypoint.py`
- `tests/test_screen_capturer_architecture.py`
- `tests/test_mouse_coordinates.py`
- `tests/test_mouse_refactor.py`
- `tests/test_behavior_supervisor_lifecycle.py`
- `tests/test_game_process_lifecycle.py`

Add `tests/test_long_run_resilience.py` when restart argument-preservation assertions are placed there or existing affected coverage requires it.

Required behavioral assertions include:

- no mode flag -> backend;
- `--foreground` -> foreground;
- legacy `--backend` accepted;
- resolved mode propagation into bootstrap/launcher components;
- `--foreground` survives `prepare_resume_command`;
- restart path does not inject `--backend`;
- backend capture failure does not call MSS/PIL;
- foreground capture fallback remains available;
- existing backend/foreground mouse coordinate tests remain passing.

## Documentation impact boundary

Update only documents/scripts with executable or user-facing instructions that encode the old mode contract, including relevant occurrences identified by Scout in README, feature guides, sandbox dual-instance guidance, and runtime configuration documentation. Do not perform unrelated documentation cleanup.

## Deferred Phase 2

`foreground-demo-mode-isolation` owns later structural cleanup such as:

- deleting/deeper deprecating foreground production implementation;
- isolating foreground/demo implementation behind dedicated interfaces/modules;
- removing broad `if backend_mode ... else ...` duplication;
- broad utility migration;
- video/demo recording integration if desired later.

## Scout evidence

The user explicitly authorized Gemini/Antigravity as a temporary read-only Scout instead of `scripts/ai_scout.ps1`. The Scout identified the complete mode propagation, restart semantics, constructor defaults, existing tests, repository terminology precedent for `--foreground`, and the current backend-to-MSS/PIL capture fallback. Gemini was evidence provider only; ChatGPT + user own this Final SPEC.
