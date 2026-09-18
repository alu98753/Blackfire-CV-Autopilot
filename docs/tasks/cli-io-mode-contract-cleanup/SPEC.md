# cli-io-mode-contract-cleanup

Status: Draft

## Goal

Align the public CLI and launcher surface with the post-isolation runtime contract:

- production runtime uses backend Win32 I/O by default;
- foreground visible/physical I/O is an explicit `--foreground` demo/compatibility path;
- the CLI must no longer present backend operation as an opt-in production feature;
- determine whether the legacy `--backend` flag still has any real semantic responsibility. If it has none, remove it completely rather than hiding/deprecating it.

## Scope

- `run.bat` main-mode menu, default command construction, subflow menu, and CLI help text.
- `cli/arguments.py` I/O-mode flags and resolved-mode contract.
- restart/resume/supervisor command preservation where I/O-mode tokens may survive.
- dev/diagnostic scripts that expose `--backend` as a public or test-facing selector, but only where they are materially part of the same CLI contract.
- directly affected CLI/runtime composition tests.
- directly affected user documentation, especially stale Traditional Chinese examples.
- startup observability for the selected I/O family if this can be added without changing runtime behavior.

## Known invariants

1. Production runtime is backend by default.
2. `--foreground` explicitly selects foreground demo/compatibility I/O.
3. Backend and foreground concrete adapters are selected at composition time.
4. Backend failure must never silently fall back to foreground capture or physical input.
5. Gameplay/state-machine code must not become an I/O-selection owner.
6. Win32 capture/input mechanics, pyautogui mechanics, timing, coordinate transforms, pause behavior, callbacks, and gameplay behavior are out of scope for semantic changes.
7. Existing target/profile/native/sandbox/supervisor/subflow flows must remain behavior-preserving.
8. No shared Python environment mutation.

## Provisional CLI target

Normal launcher/menu usage should represent backend as the production default rather than as an explicit token.

Examples:

```text
--mode daily
--mode mix
--subflow chest
```

Foreground demo remains explicit:

```text
--mode daily --foreground
```

The normal launcher should not generate `--backend`.

## Core uncertainty: does `--backend` still have meaning?

Scout must not assume compatibility retention.

Scout must inventory every current `--backend` reference and classify each one:

- real semantic selector;
- compatibility-only parser acceptance;
- launcher-generated redundant token;
- restart/resume preservation artifact;
- dev/diagnostic-only surface;
- stale documentation/test residue;
- other independently justified responsibility.

Scout must determine whether any current behavior exists that cannot be expressed by:

```text
no I/O flag  -> backend production
--foreground -> foreground demo
```

### Decision rule

If `--backend` has no independent semantic responsibility:

- remove it from `cli/arguments.py`;
- remove all generation from `run.bat`;
- remove it from normal help/output;
- remove or migrate tests that assert acceptance;
- remove stale documentation/examples;
- remove restart/resume logic whose only purpose is preserving this dead flag;
- migrate dev/diagnostic scripts where their `--backend` option is likewise redundant;
- do not leave a hidden/deprecated no-op alias solely for historical compatibility.

If Scout finds a real independent responsibility:

- document the exact behavior;
- identify concrete call sites depending on it;
- explain why backend-by-default plus `--foreground` cannot represent that behavior;
- propose the smallest explicit contract that preserves the responsibility without reviving broad mixed-mode selection.

The Final SPEC must resolve this uncertainty before implementation.

## Non-goals

- Reworking backend/foreground adapter internals.
- Reintroducing symmetric production `--backend` / `--foreground` mode switching without evidence.
- Introducing a new `--io backend|foreground` abstraction solely for aesthetics.
- Gameplay, scheduler, CV, navigation, recovery, or domain behavior changes.
- Broad refactors outside CLI/public contract alignment.
- Shared environment/dependency changes.

## Provisional acceptance criteria

1. Normal `run.bat` mode choices no longer require or generate an explicit backend token.
2. Normal subflow choices no longer require or generate an explicit backend token.
3. No I/O flag resolves backend production.
4. `--foreground` resolves foreground demo I/O.
5. Launcher help accurately describes the asymmetric production/default vs demo/opt-in relationship.
6. Startup output makes the selected I/O family observable if implemented.
7. Traditional Chinese documentation no longer instructs users to add `--backend` for normal production use.
8. Runtime composition and fail-closed behavior remain unchanged.
9. Target/profile/native/sandbox/supervisor/restart behavior remains unchanged.
10. Final SPEC explicitly resolves whether `--backend` is deleted or retained, with evidence.
11. If `--backend` is determined redundant, removal is complete across parser, launcher generation, relevant tests, docs, restart/resume handling, and materially affected dev utilities.
12. No unrelated behavior changes.

## Scout questions

1. List every current repository reference to literal `--backend` and every code path that derives runtime I/O mode.
2. Does `args.backend` or an equivalent parser field influence runtime behavior anywhere?
3. Does preserving `--backend` across supervisor restart/resume change behavior, or is it inert?
4. Are there scripts, shortcuts, tests, or docs where `--backend` is still a real selector rather than redundant syntax?
5. Does any code need an explicit force-backend override when `--foreground` is also present? If yes, is that behavior intentional and documented?
6. Can `backend_mode` runtime metadata remain while removing the public `--backend` flag, and which consumers still require that metadata?
7. What focused tests are sufficient to prove CLI alignment without reopening runtime I/O mechanics?

## Expected Scout evidence

Inspect at minimum:

- `run.bat`
- `cli/arguments.py`
- `main.py`
- `runtime/bootstrap.py`
- `runtime/io_adapters.py`
- `runtime/supervisor.py`
- game relaunch/restart paths
- `scripts/test_single_click.py` and nearby I/O diagnostics
- focused foreground/backend composition tests
- README / README.zh-TW.md
- prior backend-default and foreground-isolation task contracts for historical intent only

Scout is evidence provider only. It must not finalize this SPEC or implement production changes.
