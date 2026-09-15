# opencode-launcher-version-compatibility

Status: Draft

## Goal

Restore reliable Scout/Gate launcher compatibility under an explicit, repository-enforced OpenCode CLI version contract, without weakening the workflow's process-safety invariants or changing agent/provider/model/review semantics.

The immediate observed blocker is that the production launcher currently emits `opencode run --standalone ...`, while the deployed OpenCode 1.18.31 CLI rejects `--standalone` for `run`. This task owns the launcher/version contract needed to make Scout and Gate executable again before provider compatibility work resumes.

## Lightweight survey baseline

Base branch: latest `main` at `ade1ea1297510207faa48f41c81a66aa5eb9dec7`.

Known nearby workflow history:

- commit `3e204b943184d23e66fe301c94b419d765b9c847` added `--standalone` to both Scout and Gate while documenting it as process isolation;
- current `scripts/ai_scout.ps1` still builds `opencode run --standalone --agent scout ...` on its production path;
- the existing workflow harness focuses on bounded process behavior and can use argument/executable overrides, so it does not currently prove parser compatibility of the real production OpenCode invocation;
- `scripts/bootstrap_opencode.ps1` accepts any already-installed OpenCode version and installs unbounded `opencode-ai` latest when missing, so repository compatibility is not presently enforced by a version contract;
- the blocked `opencode-structured-review-provider-compatibility` task records OpenCode 1.18.31 as its current compatibility baseline and must remain blocked until this launcher/version issue is resolved.

## Scope

Provisional scope:

- production OpenCode invocation construction used by `scripts/ai_scout.ps1`;
- sibling production invocation construction used by `scripts/ai_gate.ps1`;
- one authoritative repository declaration of the supported/tested OpenCode CLI version contract;
- `scripts/bootstrap_opencode.ps1` behavior needed to validate or enforce that version contract;
- deterministic workflow tests that exercise the real production invocation/version compatibility boundary rather than only overridden child-process arguments;
- `docs/architecture/ai_development_workflow.md` synchronization with the actual supported launcher and version policy;
- narrowly scoped task evidence needed to unblock `opencode-structured-review-provider-compatibility` after this task merges.

Possible implementation shape is intentionally left open for Scout evidence. A shared launcher/version helper may be justified, but this Draft SPEC does not require one.

## Known invariants

1. The observed deployed baseline is OpenCode 1.18.31, and its `opencode run --help` does not advertise or accept `--standalone`.
2. `--pure` must NOT be treated as semantically equivalent to `--standalone` merely because it is accepted by OpenCode 1.18.31; equivalence must be proven against the required workflow invariants before any such substitution is allowed.
3. Scout and Gate must preserve explicit repository working directory ownership.
4. Child execution must remain non-interactive with stdin closed.
5. stdout/stderr capture and real-time visibility must remain intact.
6. bounded timeout, termination handling/confirmation, fail-closed behavior, and canonical artifact safety/atomic promotion must remain intact.
7. Scout/Gate agent permissions, prompts, model routing, provider selection, fallback semantics, and Gate PASS/BLOCK verdict semantics are outside the behavior-change scope.
8. A CLI-parser failure occurring before provider/model invocation is infrastructure compatibility evidence, not provider compatibility evidence.
9. No production/game automation behavior is in scope.
10. No production implementation starts while this SPEC remains Draft.

## OpenCode version contract requirements

The Final SPEC must establish a concrete policy rather than relying on a locally remembered pin. At minimum:

- the repository has one authoritative declaration of supported OpenCode CLI version(s), preferably an exact pin unless Scout evidence justifies a tested range;
- bootstrap/diagnostics can detect the installed version and clearly distinguish supported from unsupported environments;
- an unsupported already-installed version must not be silently accepted as compatible;
- installing OpenCode must not silently float to an unbounded latest release when workflow behavior depends on CLI compatibility;
- any automatic install/upgrade/downgrade policy must be explicit and deterministic;
- changing the supported version requires corresponding launcher compatibility evidence and focused tests.

## Non-goals

- implementing or continuing `opencode-structured-review-provider-compatibility` inside this task;
- paid provider/model probes or provider qualification;
- changing structured-review semantics or reviewer verdict contracts;
- changing agent permissions or increasing model budgets/timeouts as a launcher workaround;
- broad package/dependency-management redesign beyond the OpenCode version contract;
- broad workflow refactoring unrelated to launcher/version compatibility;
- game/runtime automation changes;
- assuming a newer OpenCode release is preferable without isolated evidence;
- replacing `--standalone` with `--pure` without semantic evidence.

## Provisional acceptance criteria

1. The repository contains exactly one authoritative declaration of the supported/tested OpenCode CLI version contract.
2. `scripts/bootstrap_opencode.ps1` validates/enforces that contract so arbitrary installed versions are not silently accepted and missing installs do not silently float to an unbounded latest version.
3. Production Scout invocation is parser-valid on every declared supported OpenCode version.
4. Production Gate reviewer invocation is parser-valid on every declared supported OpenCode version.
5. Focused deterministic tests exercise production invocation construction and version-mismatch behavior without requiring network access, provider credentials, or paid inference.
6. Required process-safety invariants remain preserved: explicit repo working directory, closed stdin, bounded child process, timeout/termination handling, stdout/stderr capture, fail-closed behavior, and canonical artifact safety.
7. Architecture/workflow documentation describes the actual supported OpenCode version policy and actual isolation mechanism; it does not claim unsupported CLI flags.
8. `--pure` is not used as an isolation surrogate unless Scout/follow-up evidence establishes that its semantics satisfy the relevant invariant and the Final SPEC explicitly approves it.
9. Parser/version incompatibility produces an actionable diagnostic as early as reasonably possible, before provider/model routing where practical.
10. No launcher failure from this task is counted as provider/model compatibility evidence.
11. After this task merges, the blocked `opencode-structured-review-provider-compatibility` branch can be rebased/synchronized and its canonical Scout can execute under the supported launcher/version contract.

## Uncertainty to resolve in Scout

- whether the repository should use an exact OpenCode pin or a narrowly tested supported-version range;
- whether a newer OpenCode version actually provides a `run --standalone` option and, if so, whether its semantics match the process-isolation property previously documented;
- whether the required isolation properties are already fully provided by the existing `ProcessStartInfo` wrapper independently of an OpenCode-specific flag;
- whether Scout and Gate should share a small launcher/version compatibility helper or retain duplicated explicit construction;
- whether bootstrap should automatically install the supported version, fail with an actionable command, or support both modes;
- what is the smallest deterministic parser-level compatibility probe that exercises the production invocation builder without requiring a real provider/model call;
- how to handle the self-hosting constraint that canonical Scout currently traverses the broken launcher path; if Scout cannot start, that failure must be preserved as task evidence rather than bypassed silently.
