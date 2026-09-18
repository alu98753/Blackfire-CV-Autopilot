# backend-default-runtime-mode

Status: Draft

## Goal

Make backend Win32 I/O the production/default runtime mode while retaining foreground physical-input behavior only through an explicit opt-in demo path. This task is Phase 1 of the foreground-click deprecation roadmap; it changes defaults and mode propagation without performing the later architectural removal/isolation of foreground implementation.

## Scope

- Define the CLI contract so ordinary production startup selects backend I/O without requiring `--backend`.
- Provide an explicit foreground/demo opt-in suitable for future visible demonstrations or video recording.
- Propagate the resolved runtime I/O mode consistently through startup/bootstrap, launcher, mouse control, and screen capture responsibilities.
- Remove unsafe implicit constructor defaults where they could silently select foreground physical input when a caller forgets to pass the resolved mode, where compatible with the surveyed architecture.
- Add deterministic tests covering CLI defaults, explicit demo/foreground opt-in, and propagation into action/capture/runtime construction boundaries.
- Update directly affected user/developer documentation for the Phase-1 CLI contract.

## Known invariants

- Production/default execution must use backend non-grabbing I/O.
- Production backend failure must not silently fall back to foreground `pyautogui` physical input.
- Explicit demo/foreground mode remains behavior-preserving in this phase; its implementation is not removed.
- Existing backend Win32 behavior remains behavior-preserving unless a narrowly required propagation fix is discovered.
- Target-window/HWND ownership remains explicit and must continue to support multi-instance/native/sandbox selection.
- Phase 1 must not conflate mode-default migration with the larger Phase-2 foreground implementation isolation/refactor.

## Non-goals

- Deleting `pyautogui` or foreground capture code.
- Rewriting mouse/capture implementations into new backend interfaces solely for architectural aesthetics.
- Changing CV detection, scheduler/state-machine behavior, gameplay policy, coordinates, timing, or click semantics unrelated to selecting the I/O mode.
- Adding video recording functionality.
- Shared Python environment mutation.
- Phase-2 `foreground-demo-mode-isolation` work.

## Provisional acceptance criteria

1. Starting the normal application without an I/O-mode flag resolves to backend mode.
2. A clearly named explicit demo/foreground CLI option resolves to foreground physical-input/capture mode.
3. The resolved mode is propagated consistently to every production construction site that selects backend vs foreground mouse/capture behavior.
4. No production backend error path silently switches to foreground physical mouse input.
5. Deterministic tests prove the default and explicit-demo CLI semantics and representative propagation boundaries.
6. Existing focused tests for affected CLI/bootstrap/mouse/capture behavior remain passing or are intentionally updated to the new contract.
7. Documentation no longer instructs normal production users to add `--backend`; foreground is described as explicit demo/compatibility behavior.
8. No Phase-2 deletion/isolation of foreground implementation is performed.

## Uncertainty / Gemini Scout questions

- Find every current construction site and restart/supervisor command builder that consumes or reconstructs `args.backend` / `backend_mode`.
- Determine whether any resume/restart path explicitly appends `--backend`, and how mode should be preserved after the default inversion.
- Identify existing tests encoding the old `--backend == opt-in` contract.
- Recommend whether the Phase-1 public foreground flag should be `--demo`, `--foreground`, or an alias pair, based on repository vocabulary and call sites.
- Determine whether legacy `--backend` should remain accepted as a deprecated/no-op compatibility flag for one phase or be removed immediately.
- Verify `capture/screen.py` is the only current capture implementation selecting foreground vs backend behavior.
- Identify documentation/backlog/scripts that would become stale after the default inversion.

## Scout mode

For this task, the user explicitly authorized a temporary Gemini/Antigravity read-only survey instead of the normal AI Scout workflow. Gemini is evidence provider only: it must not modify production code, own/finalize this SPEC, or begin implementation while Status is Draft.
