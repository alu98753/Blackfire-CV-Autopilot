# cli-io-mode-contract-cleanup

Status: Final

## Goal

Align the public CLI with the post-isolation runtime contract:
- production runtime uses backend Win32 I/O by default;
- `--foreground` is the only explicit I/O selector and selects foreground demo/compatibility I/O;
- remove the legacy public `--backend` flag completely because it has no independent runtime semantic responsibility;
- preserve internal `backend_mode` metadata only where it remains useful as metadata/config propagation and does not select I/O implementations.

## Scout conclusion

Scout commit `73304d597bfdb00f160c2e3b6cedd04d577c4b9b`, followed by ChatGPT review of the nearby implementation, resolves the central uncertainty:

- `cli/arguments.py` stores `args.backend`, but no production runtime consumer reads it.
- Runtime mode is derived solely from `args.foreground` through `args.backend_mode = not args.foreground`.
- `main.py` and `runtime/bootstrap.py` compose explicit backend/foreground adapters from the resolved mode.
- `run.bat`, quest command generators, tests, and docs still emit or mention `--backend`, but those uses are redundant.
- Supervisor restart preserves the token only incidentally because it preserves the original command list wholesale.
- `scripts/test_single_click.py` has a separate parser, but its `--backend` option is still redundant because default/no flag already means backend.

Therefore `--backend` has no behavior that cannot be represented by:

```text
no I/O flag  -> backend production
--foreground -> foreground demo
```

The public flag is to be removed rather than hidden or deprecated.

## Architecture contract

```text
CLI / launcher
  |
  +-- no I/O flag
  |     -> BackendScreenCapturer + BackendMouseController
  |
  \-- --foreground
        -> ForegroundScreenCapturer + ForegroundMouseController
```

There is no public `--backend` selector.

Internal `backend_mode` state/config metadata may remain temporarily where existing code consumes or propagates it, but it is not a public CLI contract and must not become a second I/O-selection authority.

## Scope

- `run.bat` main-mode menu, defaults, subflow menu, generated arguments, and help text.
- `cli/arguments.py` public I/O-mode contract.
- `utils/quest_mapper.py` and `utils/quest_scheduler.py` generated command strings.
- `scripts/test_single_click.py` CLI alignment.
- directly affected parser/composition/restart tests.
- active user-facing documentation and active architecture/dev guidance that still presents `--backend` as current.
- bounded startup observability for the selected I/O family.

Historical task artifacts may retain historical `--backend` references when changing them would falsify the historical record.

## Required behavior

Normal production:
```text
python main.py --mode daily
```
selects backend production I/O.

Foreground demo:
```text
python main.py --mode daily --foreground
```
selects foreground demo I/O.

`python main.py --backend ...` is no longer part of the supported CLI contract. Do not keep a hidden/deprecated no-op alias.

## Launcher requirements

- `run.bat` must stop displaying and generating `--backend` in main modes, defaults, and subflows.
- Launcher help must describe backend as the production default and `--foreground` as the visible/physical demo path.
- Target/profile/native/sandbox/blessing/supervisor/hotkey flows remain unchanged.

## Generated command requirements

Remove `--backend` from active generated command strings, including `utils/quest_mapper.py`, `utils/quest_scheduler.py`, and any other active command builder discovered during implementation.

## Supervisor / restart contract

- Do not add compatibility logic solely to preserve or translate the removed `--backend` token.
- Active launchers and command generators must stop producing it, so supported new runs and their restarts remain valid.
- Restart/resume must preserve `--foreground` when originally selected.
- Backward compatibility for an already-running pre-upgrade supervisor whose original child command contains `--backend` while the codebase is live-upgraded underneath it is not an invariant.

## Dev diagnostic script

`scripts/test_single_click.py` must use the same model:
- no I/O flag -> backend adapter;
- `--foreground` -> foreground adapter;
- remove redundant `--backend` / `-b`.

## Internal metadata

Existing internal `backend_mode` propagation may remain in places such as `cli/mode_setup.py`, `state_machine.backend_mode`, and quest config propagation. This task does not require broad metadata cleanup. It must remain metadata only and must not select/reconstruct I/O implementations.

## Startup observability

Preferred bounded output:
```text
[*] I/O 模式: Backend Production (Win32)
```
or:
```text
[*] I/O 模式: Foreground Demo (Visible Capture + Physical Mouse)
```

This is observability only.

## Known invariants

1. Production runtime is backend by default.
2. `--foreground` explicitly selects foreground demo I/O.
3. Adapter selection occurs at composition time.
4. Backend failure never silently falls back to foreground capture or physical input.
5. Gameplay/state-machine code does not own I/O selection.
6. Win32/pyautogui mechanics, timing, message ordering, jitter, coordinates, pause behavior, callbacks, and gameplay behavior remain unchanged.
7. Target/profile/native/sandbox/subflow/supervisor behavior remains unchanged except removal of redundant `--backend` syntax.
8. No shared Python environment mutation.

## Non-goals

- Reworking backend/foreground adapter internals.
- Introducing symmetric `--backend` / `--foreground` modes.
- Introducing `--io backend|foreground`.
- Removing `--foreground`.
- Broad cleanup of internal `backend_mode` metadata.
- Gameplay, scheduler policy, CV, navigation, recovery, or domain behavior changes.
- Rewriting historical task records merely to remove old terminology.
- Supporting live-code-upgrade compatibility for an already-running old supervisor command containing `--backend`.

## Acceptance criteria

1. `cli/arguments.py` no longer defines or accepts main CLI `--backend`.
2. No I/O flag resolves backend production.
3. `--foreground` resolves foreground demo I/O.
4. `run.bat` main choices, subflows, help, and default Enter path no longer display or generate `--backend`.
5. `utils/quest_mapper.py` and `utils/quest_scheduler.py` active generated commands contain no `--backend`.
6. `scripts/test_single_click.py` removes redundant `--backend` / `-b` while preserving default backend and explicit foreground behavior.
7. Directly affected tests no longer assert legacy `--backend` acceptance.
8. Deterministic tests still prove default backend and explicit foreground composition.
9. Restart/resume preserves `--foreground` and never synthesizes a backend token.
10. Active user-facing docs no longer tell users to pass `--backend` for production.
11. Active architecture/dev guidance no longer presents `--backend` as a current composition entry point.
12. Internal `backend_mode` metadata, if retained, remains metadata only.
13. Backend fail-closed and foreground demo behavior remain unchanged.
14. No unrelated runtime/gameplay semantic changes.

## Focused verification

At minimum:
```text
tests.test_runtime_io_composition
tests.test_foreground_demo_mode_isolation
tests.test_behavior_main_entrypoint
```

Also run deterministic supervisor/restart tests covering argument preservation if they exist or are added.

Add focused assertions for parser removal of `--backend`, default backend, explicit `--foreground`, launcher/generated command cleanup, dev single-click selection, and restart/resume preservation of `--foreground`.

## Lifecycle

Scout evidence has been reviewed and the central uncertainty is resolved: `--backend` has no independent semantic responsibility.

`Status: Final`

Gemini/Antigravity may now perform production implementation under this contract. OpenCode Scout/reviewers remain read-only.