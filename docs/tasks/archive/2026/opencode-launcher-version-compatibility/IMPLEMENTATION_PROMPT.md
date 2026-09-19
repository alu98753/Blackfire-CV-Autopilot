# Implementation Handoff — opencode-launcher-version-compatibility

You are the sole v1 production implementation writer for this task.

## Mandatory working directory

Perform all repository operations from:

`E:\Side_Project\wt-opencode-launcher-version-compatibility`

Before editing, verify:

- current worktree path is exactly the dedicated task worktree above;
- current branch is `task-opencode-launcher-version-compatibility`;
- worktree is not detached HEAD;
- remote task artifacts are synchronized.

Do NOT edit from `E:\Side_Project\BlackfireCrusade_tool` or `E:\Side_Project\temp-main`.

For every non-interactive command, follow the repository/user Windows execution policy and invoke through `cmd.exe /d /s /c`. Do not start interactive commands. Redirect stdin from NUL where a child CLI may wait for input.

## Source of truth

Read before editing:

1. `docs/tasks/opencode-launcher-version-compatibility/SPEC.md` — Final and authoritative.
2. `docs/tasks/opencode-launcher-version-compatibility/SCOUT_BLOCKER.md` — canonical pre-fix failure evidence.
3. `docs/tasks/opencode-launcher-version-compatibility/task.json`.
4. `docs/architecture/ai_development_workflow.md`.
5. nearby implementation/tests only as needed to satisfy the Final SPEC.

Do not broaden into a general workflow refactor.

## Required implementation outcome

Implement the smallest architecture-consistent fix satisfying the Final SPEC:

- supported OpenCode CLI version is exactly `1.18.31`;
- establish one authoritative repository declaration for that version;
- production Scout and Gate invocation must no longer emit unsupported `--standalone`;
- do NOT replace it with `--pure`;
- process isolation/lifecycle safety remains owned by the existing PowerShell wrapper;
- preserve repo working directory, closed stdin, redirected stdout/stderr, timeout/kill handling, fail-closed behavior, streaming behavior, and artifact safety;
- bootstrap must accept exactly 1.18.31, reject an installed mismatch with an actionable diagnostic, and pin any install to `opencode-ai@1.18.31` rather than unbounded latest;
- add deterministic regression coverage for the real production invocation/version contract, not only `_ArgumentsOverride` child-process tests;
- synchronize `docs/architecture/ai_development_workflow.md` with the actual version/isolation contract.

## Behavior that must not change

Do not change:

- Scout/Gate prompts or semantic responsibilities;
- agent permissions;
- provider/model routing;
- infrastructure-only fallback semantics;
- Gate structured-output PASS/BLOCK contract;
- model budgets/timeouts;
- game/runtime behavior;
- the blocked `opencode-structured-review-provider-compatibility` task.

Do not upgrade OpenCode or probe paid providers.

## Testing

Add/run focused deterministic tests proving at minimum:

- Scout production invocation contains neither `--standalone` nor `--pure` and is compatible with the declared 1.18.31 CLI surface;
- Gate production invocation contains neither `--standalone` nor `--pure` and is compatible with the declared 1.18.31 CLI surface;
- version contract accepts exactly 1.18.31 and rejects mismatch before normal model routing where practical;
- missing bootstrap install uses exactly `opencode-ai@1.18.31`;
- existing workflow timeout/streaming/fail-closed/artifact-safety tests remain green.

Tests must not require paid inference, provider credentials, or network access where deterministic seams can prove the behavior.

## Completion handoff

When implementation and focused tests pass:

1. Review the diff for scope drift and dead logic.
2. Commit all implementation/test/doc changes to `task-opencode-launcher-version-compatibility`.
3. Push the branch to origin.
4. Report the commit SHA, changed files, focused test commands/results, and any unresolved uncertainty.
5. Do NOT merge the branch.
6. Do NOT run production implementation in another worktree.
7. Do NOT modify the Final SPEC unless an actual contradiction is discovered; if so, stop and report it instead of silently changing architecture.
