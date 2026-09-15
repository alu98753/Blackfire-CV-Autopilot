# opencode-launcher-version-compatibility

Status: Final

## Goal

Restore reliable Scout/Gate launcher compatibility under an explicit, repository-enforced OpenCode CLI version contract, without weakening process-safety invariants or changing agent/provider/model/review semantics.

The immediate regression is confirmed: production Scout/Gate invocation construction emits `opencode run --standalone ...`, while the deployed and compatibility-baseline OpenCode 1.18.31 CLI rejects `--standalone` for `run` before any provider/model inference begins.

## Evidence baseline

Base branch: `main` at `ade1ea1297510207faa48f41c81a66aa5eb9dec7`.

Tracked self-hosting evidence is in `SCOUT_BLOCKER.md`. Canonical Scout was executed from the dedicated task worktree and both configured candidates exited code 1 at the CLI parser/help stage. `CONTEXT.md` remained untouched. These failures are launcher/version infrastructure evidence, not provider/model evidence.

Relevant implementation evidence:

- commit `3e204b943184d23e66fe301c94b419d765b9c847` introduced `--standalone` to Scout/Gate and documented it as process isolation;
- OpenCode 1.18.31 `run --help` does not expose `--standalone`;
- upstream `--pure` means `run without external plugins`; it is not a process-isolation synonym and must not be substituted for `--standalone` in this task;
- existing Scout/Gate `ProcessStartInfo` wrappers already own the relevant process boundary: explicit repository working directory, `UseShellExecute = false`, redirected stdin/stdout/stderr, closed stdin, bounded timeout, termination handling, fail-closed behavior, and artifact-safety handling;
- `scripts/bootstrap_opencode.ps1` currently accepts any installed version and installs unbounded `opencode-ai` latest when OpenCode is missing.

## Self-hosting Scout exception

This task is the narrow exception to the ordinary Draft -> canonical Scout -> Final transition because the canonical Scout launcher itself is the component under repair and is proven unable to reach model execution.

For this task only, `SCOUT_BLOCKER.md` plus the narrow GitHub source/contract review serve as the pre-Final localization evidence. This exception MUST NOT be generalized to normal tasks.

After implementation, canonical `scripts/ai_scout.ps1 -Task opencode-launcher-version-compatibility` MUST be rerun successfully to close the self-hosting evidence gap before final Gate/review.

## Required working directory

All implementation, focused tests, post-implementation Scout, and Gate commands for this task must execute from the dedicated attached task worktree:

`E:\Side_Project\wt-opencode-launcher-version-compatibility`

Do not implement from `E:\Side_Project\BlackfireCrusade_tool` or `E:\Side_Project\temp-main`. Before work, verify the worktree is attached to `task-opencode-launcher-version-compatibility` and synchronized with origin.

## Architecture decision

### Process isolation ownership

Process isolation/lifecycle safety belongs to the repository wrapper, not to an assumed OpenCode `run` flag.

For v1:

- remove unsupported `--standalone` from production Scout and Gate OpenCode invocation construction;
- do NOT replace it with `--pure`;
- retain the existing PowerShell-owned process-safety mechanics and behavior;
- keep normal OpenCode agent/model/prompt arguments unchanged except as strictly necessary for parser-valid invocation.

`--pure` may be considered later only as a separate plugin-loading policy decision with explicit evidence and architecture approval.

### OpenCode version contract

The authoritative supported/tested OpenCode CLI version for this task is an exact pin:

`1.18.31`

This task does not upgrade OpenCode. The exact pin is chosen because it is the deployed baseline and the existing provider compatibility evidence baseline.

The repository must expose one authoritative declaration of this pin. Implementation may choose the smallest maintainable representation, but there must not be multiple drifting authoritative values.

Bootstrap/version behavior must satisfy:

- installed `1.18.31` -> accepted;
- installed version other than `1.18.31` -> fail early with an actionable diagnostic before normal Scout/Gate routing;
- missing OpenCode -> any installation path must install exactly `opencode-ai@1.18.31`, never unbounded latest;
- no automatic upgrade/downgrade to an unproven version;
- a future version change requires corresponding launcher compatibility evidence and focused test updates.

## Scope

- `scripts/ai_scout.ps1` production OpenCode invocation construction;
- `scripts/ai_gate.ps1` production reviewer invocation construction;
- one authoritative repository OpenCode version declaration;
- `scripts/bootstrap_opencode.ps1` version validation/install behavior;
- focused deterministic workflow tests covering production invocation construction and version mismatch behavior;
- `docs/architecture/ai_development_workflow.md` synchronization;
- task-local evidence/artifacts under `docs/tasks/opencode-launcher-version-compatibility/`.

A small shared helper for launcher/version contract is allowed only if it is the simplest way to eliminate duplicated drift. Do not perform broad workflow refactoring.

## Known invariants

1. OpenCode 1.18.31 is the only supported/tested production CLI version for v1 of this task.
2. `--pure` is not equivalent to process isolation and must not replace `--standalone` here.
3. Scout/Gate must preserve explicit repository working directory ownership.
4. Child execution remains non-interactive with stdin closed.
5. stdout/stderr capture and current streaming behavior remain intact.
6. bounded timeout, kill/termination confirmation behavior, fail-closed handling, and canonical artifact safety remain intact.
7. Scout/Gate prompts, agent permissions, model routing, provider selection, fallback semantics, step budgets, and Gate PASS/BLOCK semantics are behavior-preserving unless a tiny mechanical adjustment is strictly required by invocation construction.
8. Parser/version failures before inference are infrastructure failures, never provider/model compatibility evidence.
9. No game/runtime automation behavior changes are allowed.
10. No paid provider probes are required for this task.

## Non-goals

- continuing `opencode-structured-review-provider-compatibility` implementation inside this task;
- upgrading OpenCode beyond 1.18.31;
- proving newer OpenCode releases;
- using `--pure` as an isolation surrogate;
- changing reviewer structured-output or PASS/BLOCK semantics;
- changing agent permissions, model routing, provider routing, fallback policy, budgets, or timeouts;
- broad dependency-management redesign;
- broad workflow refactoring;
- game/runtime behavior changes.

## Acceptance criteria

1. Exactly one authoritative repository declaration states supported OpenCode CLI version `1.18.31`.
2. `scripts/bootstrap_opencode.ps1` accepts installed `1.18.31`, rejects mismatched installed versions with an actionable message, and installs exactly `opencode-ai@1.18.31` when installation is required.
3. Production Scout invocation is parser-valid on OpenCode 1.18.31 and no longer emits `--standalone`.
4. Production Gate reviewer invocation is parser-valid on OpenCode 1.18.31 and no longer emits `--standalone`.
5. Neither launcher introduces `--pure` as part of this fix.
6. Focused deterministic tests exercise the real production invocation/version contract rather than relying only on `_ArgumentsOverride`; they must detect reintroduction of unsupported flags and version drift.
7. Version mismatch fails before normal provider/model routing where practical.
8. Existing process-safety behavior remains preserved: repository working directory, closed stdin, redirected stdout/stderr, bounded child process, timeout/termination handling, fail-closed behavior, and canonical artifact safety.
9. Architecture documentation describes wrapper-owned process isolation and exact OpenCode 1.18.31 compatibility policy; it must not claim `run --standalone` is required.
10. Existing relevant deterministic workflow tests pass.
11. Post-implementation canonical `scripts/ai_scout.ps1 -Task opencode-launcher-version-compatibility` successfully reaches model execution and produces/promotes a valid `CONTEXT.md` from the dedicated task worktree.
12. After successful post-implementation Scout, `scripts/ai_gate.ps1 -Task opencode-launcher-version-compatibility` is run under the same supported version contract, followed by ChatGPT semantic/architecture review from GitHub.
13. Launcher failures from the pre-fix evidence remain classified as infrastructure evidence and are not added to provider compatibility results.
14. After merge, `opencode-structured-review-provider-compatibility` can synchronize from main and rerun its canonical Scout without the `--standalone` parser blocker.

## Implementation constraints

Gemini/Antigravity is the sole v1 production implementation writer for this task. OpenCode remains evidence/review only.

Implementation must begin only after synchronizing this Final SPEC into the dedicated task worktree. Do not edit the blocked provider-compatibility task branch.
