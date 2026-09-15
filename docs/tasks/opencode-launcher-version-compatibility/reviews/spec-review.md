VERDICT: PASS
BLOCKING_FINDINGS: 0

# Spec Review

## Clause coverage

- **AC1** (single authoritative 1.18.31 declaration): satisfied ??only `opencode_contract.ps1` declares it; all launchers source it; test asserts declaration text.
- **AC2** (bootstrap accept/reject/pin): satisfied ??accept path asserts `Get-OpenCodeVersion`, mismatch throws actionable exact-version command, install path uses pinned `opencode-ai@$OpenCodeSupportedVersion`.
- **AC3/AC4** (no `--standalone` in Scout/Gate production builders): satisfied ??verified in current scripts plus repo-wide grep.
- **AC5** (no `--pure`): satisfied ??grep over `scripts/` shows none; static harness case forbids it.
- **AC6** (tests exercise real production builders): satisfied ??`_InvocationProbe` calls `Get-ScoutOpenCodeArguments` / `Get-OpenCodeInvocation` (the exact production paths), and static flag/version-drift assertions cover reintroduction.
- **AC7** (fail before routing): satisfied ??both scripts assert before candidate resolution/model routing.
- **AC8** (process-safety preserved): satisfied ??`Invoke-ScoutProcessAttempt` retains working directory, closed stdin, redirected stdio, bounded timeout, kill confirmation; Gate uses unchanged `Invoke-BoundedProcess`; only the argument string changed.
- **AC9** (architecture doc): satisfied ??verified lines 209/231 wording.
- **AC10-12** (tests pass, post-implementation Scout, Gate): attestation evidence in `PRE_GATE_EVIDENCE.md` (16/16 harness cases; Scout reached model execution and promoted `CONTEXT.md`). Environmental self-hosting evidence is reported, not independently reproducible here.
- **AC13-14** (evidence classification, downstream sync): no code regression observed; non-goals respected (no provider/agent/model/routing/timeout changes in the diff).

## Blocking findings

None.

## Advisory findings

1. Scout/Gate `_InvocationProbe` tests require a live `opencode` 1.18.31 on PATH (probe path intentionally hits the real version assertion). This is environment-dependent, matching the repository contract, but the harness should document the precondition.
2. The diff snapshot of `Invoke-WorkflowScriptHarness.ps1` was truncated at the "Gate PASS" case; the live-file tail ordering (`$scoutCmd`/`$reviewerCmd` defined before the version-rejection cases) was not fully re-read. The mount of new cases and reported 16-case green run support correctness, but this is the single remaining unread surface.

## Test evidence gaps

- Harness execution was not re-run (shell execution is outside this reviewer's contract); green status relies on `PRE_GATE_EVIDENCE.md` attestation.
- Post-implementation canonical Scout/Gate self-hosting runs are attested only in task-local evidence, not re-proven here.

## Recommendation for next step

If desired, the next reviewer pass should read the tail of `tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1` (test-case ordering and the `$scoutCmd`/`$reviewerCmd` fixture setup) to close the single remaining evidence gap; otherwise the patch is ready for canonical Gate/merge processing per SPEC acceptance criteria 11-14.
