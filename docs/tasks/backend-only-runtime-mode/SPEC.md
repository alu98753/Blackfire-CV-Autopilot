# Backend-Only Runtime Mode

Status: Draft

## Goal

Make the Win32 backend interaction path the single supported normal runtime mode.

Normal launches must use backend capture/input behavior without requiring the caller to pass `--backend`, and backend-vs-foreground selection must not be delegated to profile/configuration state.

This task intentionally changes the public launch contract: backend operation becomes implicit. The existing foreground physical-mouse path is to be retired from the supported runtime path, with the exact cleanup/deletion boundary finalized after Scout evidence.

## Problem statement

The current CLI exposes `--backend` as an opt-in `store_true` flag. `runtime/bootstrap.py` then propagates `args.backend` into `ScreenCapturer`, `MouseController`, and `GameStateMachine`. This leaves foreground and backend execution as a runtime mode choice even though long-running, multi-instance, and sandbox use has converged on non-stealing backend operation.

Simply changing the argparse default to `True` would preserve unnecessary mode state and keep responsibility for a choice the application no longer intends to expose. The target architecture is instead to remove backend-vs-foreground selection from normal runtime configuration and make backend behavior the canonical composition.

## Scope

Primary expected change surface:

- `cli/arguments.py`
- `runtime/bootstrap.py`
- `capture/` backend/foreground composition points directly controlled by this mode
- `actions/mouse.py` and directly related input composition points
- `states/state_machine.py` only where `backend_mode` is legacy propagated state rather than genuine domain/state-machine responsibility
- directly relevant CLI/bootstrap/input/capture tests
- user-facing launch/help documentation that still instructs callers to pass `--backend`
- `docs/todos/future_work.md` during final closeout, after implementation and verification are accepted

Scout should localize all remaining reads/writes of the backend/foreground selector and distinguish supported runtime behavior from dead/legacy compatibility code before the Final SPEC decides the deletion boundary.

## Known invariants

1. The existing backend interaction behavior is the behavioral baseline for production execution; this task must not silently alter backend click coordinates, Win32 message semantics, capture semantics, timing, or target-window selection.
2. Normal runtime must remain non-mouse-stealing and suitable for existing multi-instance/sandbox usage.
3. Gameplay policy, navigation/state-machine behavior, quest scheduling, recovery semantics, and CV matching behavior are outside this task except for removal of backend-mode plumbing that has no legitimate ownership there.
4. Backend-vs-foreground mode must not be reintroduced through profile TOML or another config switch merely to replace the CLI flag.
5. Target HWND/window-title/profile/monitor selection remain independent runtime concerns and must continue to work.
6. Existing dependency-injection/runtime-port boundaries should be preserved; making backend canonical must not create new direct Win32 dependencies inside domain/state-machine policy code.
7. Production implementation must not begin while this SPEC is `Status: Draft`.
8. `docs/todos/future_work.md` is updated only after this task has passed implementation verification and final semantic/architecture review, not during Scout/spec drafting.

## Target behavior

A normal invocation such as:

```text
python main.py ...
```

uses the existing backend capture/input path automatically. The caller does not need `--backend` and does not select foreground mode through config.

The supported runtime should have one clear composition decision: construct the backend-capable capture/input adapters required by the application, rather than propagate a boolean mode selector through unrelated layers.

## Provisional acceptance criteria

1. Normal application launch uses the backend Win32 input/capture behavior without requiring `--backend`.
2. No profile/config field is required or introduced to choose backend mode.
3. The supported CLI/runtime path no longer offers foreground physical-mouse execution as a normal mode choice.
4. `runtime/bootstrap.py` no longer propagates an application-level backend/foreground boolean merely to select between the two execution modes where that choice has become invariant.
5. `GameStateMachine` does not own backend-vs-foreground selection unless Scout finds a concrete state-machine behavior that genuinely requires this information; any retained dependency must be explicitly justified in the Final SPEC.
6. Existing backend behavior for target window, coordinates, capture, click delivery, pause/resume gating, and multi-instance operation remains behavior-preserving.
7. Focused automated tests cover the new default/no-flag launch contract and the runtime composition boundary; existing directly relevant backend/input/capture tests remain green.
8. Help text and active launch documentation no longer instruct normal users to opt into backend mode.
9. The Final SPEC explicitly decides whether the old `--backend` spelling is removed immediately or retained temporarily only as a compatibility no-op/deprecation surface.
10. The Final SPEC explicitly decides whether unreachable foreground implementation is deleted in this task or left as isolated deprecated code for a later cleanup; no dual-mode supported path may remain accidentally.
11. After implementation, `scripts/ai_gate.ps1 -Task backend-only-runtime-mode` passes and ChatGPT/human semantic review confirms responsibility boundaries and behavior preservation.
12. Only after criterion 11 is accepted, update the corresponding item in `docs/todos/future_work.md` to reflect completion of the backend-default/foreground-deprecation work rather than leaving the legacy item unchecked.

## Non-goals

- Do not redesign the CV pipeline or template-matching architecture.
- Do not change game automation policy or state transitions.
- Do not redesign target-window discovery, profiles, monitor selection, or sandbox naming.
- Do not add a new config toggle for foreground/backend selection.
- Do not broadly rewrite Win32 capture/input implementations merely because they are touched by the mode cleanup.
- Do not delete foreground code speculatively before Scout establishes its remaining callers/tests and the Final SPEC approves the deletion boundary.
- Do not update `future_work.md` early just because the task has been opened.

## Uncertainty to resolve with Scout

1. What are all current producers/consumers of `args.backend` / `backend_mode`, including tests, launchers, scripts, and documentation?
2. Does any production behavior genuinely depend on `GameStateMachine.backend_mode`, or is it leaked composition state that can be removed?
3. Are capture and input currently coupled to the same mode boolean for valid architectural reasons, or can canonical backend adapters eliminate that selector cleanly?
4. Is any supported developer/test workflow still intentionally exercising foreground physical-mouse mode?
5. Should `--backend` be removed immediately or accepted temporarily as a compatibility no-op to avoid breaking existing launch commands?
6. How much foreground-only implementation can be safely deleted in this task without turning a focused mode-convergence change into an unrelated input/capture rewrite?
