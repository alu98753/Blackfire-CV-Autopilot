# Spec Review

Gate-accepted verdict: PASS
Blocking findings: 0

# Spec Review

## Clause coverage

Review of Final SPEC `foreground-demo-mode-isolation` against `.runtime/ai_gate/foreground-demo-mode-isolation/diff.patch` and the current working tree (grounded by reading `runtime/io_adapters.py`, `runtime/bootstrap.py`, `main.py`, `utils/steam_launcher.py`, `states/exceptions/subflows/game_relaunch.py`, `capture/screen.py`, `actions/mouse.py`, `cli/arguments.py`, and affected tests; grepping every `backend_mode`, `ScreenCapturer(`, `MouseController(`, `SteamGameLauncher(` usage).

- Architecture contract / AC1-2 / AC5: new `runtime/io_adapters.py` selects one fixed I/O family (`compose_io`/`compose_capture`) from the single CLI resolution point `cli/arguments.py:76` (`args.backend_mode = not args.foreground`). `main.py` and `bootstrap.py` both derive `foreground=not backend_mode` from the same policy; two capturer instances of the same family (launcher + state machine) are permitted by SPEC line 168 ("exactly one mode-selection policy"). Default flow composes backend family; `--foreground` composes foreground family. AC16 preserved: `--foreground`/`--backend` flags intact and `test_behavior_main_entrypoint.py:204-206` still proves default/foreground/legacy resolution.
- AC3-4 / AC6 / critical invariant: `BackendScreenCapturer.capture` returns `None` on full-screen, invalid HWND, backend failure, and black image with no MSS/PIL path; `BackendMouseController` click/scroll/drag/move_to_safe_area are message-for-message and sleep-for-sleep identical to the base backend branches (`actions/mouse.py`), never touching pyautogui, and now fail closed on missing HWND instead of the old base-class fallthrough to pyautogui (deliberate tightening consistent with the critical invariant).
- AC7 / foreground semantics: `ForegroundScreenCapturer` preserves MSS -> PIL fallback, bbox semantics, `last_monitor`; `ForegroundMouseController` preserves pyautogui coordinate conversion, human-like tween/duration, failsafe re-raise, cooldowns, and `_finalize_action` flags.
- AC10-11 / launcher + relaunch: `SteamGameLauncher` owns no mouse and no `backend_mode`; it raises `ValueError` without an injected composed capturer. Only production construction sites are `main.py:80` and `game_relaunch.py:48`, both injecting the composed/selected capturer; relaunch reuses `machine.capturer` with no `backend_mode` reconstruction.
- AC12 / state machine: `states/state_machine.py` keeps `backend_mode` only at serialization guards (1708, 1715) and quest-config metadata propagation (1812-1813); no new I/O-selection branches. `cli/mode_setup.py` writes metadata only. Base classes retain constructor-resolved mode for dev scripts (`scripts/test_single_click.py`) and tests, consistent with the SPEC's "resolved once during construction" allowance ??no production post-construction mutation path remains.
- AC13-15 / tests: `test_mouse_coordinates.py` and `test_screen_capturer_architecture.py` migrated from `.backend_mode =` mutation to explicit `Backend/ForegroundScreenCapturer`/`MouseController` construction; `test_behavior_supervisor_lifecycle.py:105` and `test_game_process_lifecycle.py:35` updated for the new launcher signature (earlier Block findings B1/BFC-F1/BFC-F2 are resolved in the current tree). New non-skipped `tests/test_foreground_demo_mode_isolation.py` deterministically proves both families, launcher injection/no-mode-owner, backend-no-pyautogui, MSS->PIL, drag timing/release order, and relaunch capture reuse (AC14/15).
- AC17 / scope: diff touches only in-scope production files plus `tests/`; no gameplay/CV/scheduler changes found.

## Blocking findings

None.

## Advisory findings

- `tests/test_behavior_pause_resume.py:473,485` still mutate `capturer.backend_mode = True` on a base `ScreenCapturer`. This is outside the SPEC's required focused-isolation list (AC13 applies to the focused modules, which are clean), the mutations are behaviorally inert against the new adapters, and the pause/resume wiring itself is unchanged. Recommend migrating when the module is next touched; otherwise low risk.
- `tests/test_mouse_refactor.py` (focused module) is unchanged and exercises the legacy base `MouseController(backend_mode=...)` constructor path rather than the adapters; accepted as testing the shared implementation, but adapter-level coverage for safe-area semantics lives only in the new isolation module.
- `BackendScreenCapturer.capture` drops the base's three "refusing foreground fallback" error log lines; the None result contract is preserved but the SPEC's "backend capture failure logging" ownership is thinner.
- The fail-closed no-HWND backend-input behavior (old base fell through to pyautogui) is intentional per the critical invariant but is not directly pinned by a test ??the new adapter tests always inject a valid HWND.
- `compose_io` forwards `resume_event` only to the mouse; `bootstrap.py` compensates by setting `capturer._resume_event` afterward ??a future-caller misuse seam worth documenting.

## Test evidence gaps

No suite execution was performed (read-only review). Focused modules were verified by inspection and are consistent with the new composition paths. Remaining evidence gap: an actual run of the four focused modules plus `tests.test_foreground_demo_mode_isolation` to confirm no behavioral drift, and a decision on the pause_resume mutation cleanup.

<!-- blackfire-gate-fingerprint: {"schema":1,"role":"spec-reviewer","hash":"8227eb18b54c3eda4fec4e8594130c1d595275f42ff29393b84da1fe9ac07e4b"} -->
