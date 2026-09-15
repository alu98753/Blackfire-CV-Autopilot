# Implementation Review — opencode-launcher-version-compatibility

Status: CHANGES_REQUIRED

Reviewed implementation commit: `bd6ac3bde84360b53887fe7036c8a751e67850aa`

## What is accepted

- Production Scout/Gate launchers no longer pass unsupported `--standalone`.
- `--pure` was not substituted as a process-isolation surrogate.
- Shared OpenCode version contract was introduced with exact supported version `1.18.31`.
- Version validation occurs before normal Scout/Gate model routing.
- Existing PowerShell-owned process-safety behavior remains in place: explicit repo working directory, redirected stdio, closed stdin, bounded timeout, termination handling, streaming/capture, fail-closed behavior and canonical artifact safety.
- Architecture documentation was updated in the intended direction.

## Must-fix 1 — version mismatch remediation is not actionable

Current contract diagnostics direct an unsupported-version user toward `scripts/bootstrap_opencode.ps1`, but bootstrap itself rejects an already-installed unsupported version rather than replacing it. Therefore the advertised remediation path cannot resolve the condition.

Required outcome:

- Preserve exact supported version `1.18.31`.
- Either make bootstrap deterministically repair an unsupported installed OpenCode to exactly `opencode-ai@1.18.31`, or keep bootstrap fail-only but make the mismatch diagnostic provide an actually executable exact-version remediation command.
- Do not install unbounded latest.
- Do not broaden into general package-manager/version-manager redesign.
- Add deterministic coverage proving the mismatch diagnostic/remediation contract is internally consistent.

Preferred minimum: if repository policy does not explicitly authorize automatic replacement of an existing global installation, keep bootstrap conservative and make the error tell the operator exactly how to install the supported version, then rerun bootstrap/validation.

## Must-fix 2 — production invocation compatibility boundary is not exercised

The harness currently statically checks that production sources do not contain `--standalone` / `--pure`, while spawned deterministic Scout/Gate cases still use `_ExecutableOverride` / test arguments. This proves child-process machinery plus textual absence, but not the Final SPEC requirement that the actual production invocation construction path is covered.

Required outcome:

- Introduce the smallest testable seam for the exact production OpenCode argument construction used by Scout and Gate.
- Deterministic tests must exercise the same builder/path used by production, without network/provider inference.
- Assert at minimum:
  - Scout production args contain `run`, `--agent`, `scout`, optional model and prompt, with neither `--standalone` nor `--pure`.
  - Gate production args use the intended reviewer agent/model/prompt shape with neither unsupported flag.
  - version mismatch stops before model routing.
- Avoid duplicating production argument logic only inside tests, because that can drift independently.

A small shared or script-local argument-builder function exposed through an existing test seam is acceptable. Do not refactor unrelated workflow code.

## Canonical Scout follow-up blocker

After the parser fix, canonical Scout advances beyond the former `--standalone` rejection but currently fails in local OpenCode state with:

`Database is not empty and has no session table`

Classification:

- this is no longer the launcher parser regression;
- it is not provider/model compatibility evidence;
- upstream OpenCode source contains this as a database migration/schema guard for a non-empty DB missing the expected `session` table;
- local OpenCode data must not be deleted or mutated blindly because it may contain session/history state.

Do not work around this inside production Scout/Gate code. Resolve it separately as an operator/local-state recovery after the two code must-fixes are pushed.

## Required implementation handoff

Work only in:

`E:\Side_Project\wt-opencode-launcher-version-compatibility`

Branch:

`task-opencode-launcher-version-compatibility`

Implement only the two must-fixes above, run the focused workflow harness and `git diff --check`, commit, and push. Do not merge and do not run Gate until canonical Scout succeeds.