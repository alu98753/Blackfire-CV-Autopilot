# task-cleanup-native-stderr-handling

Status: Draft

## Goal

Fix `scripts/task_cleanup.ps1` so successful native Git commands that write normal progress text to stderr do not terminate the wrapper under PowerShell `$ErrorActionPreference = 'Stop'`.

The wrapper must continue to classify command success/failure from the native process exit code while preserving stderr as bounded diagnostic evidence.

## Observed problem

First real dogfood of `task_cleanup.ps1` successfully progressed through worktree removal, local branch deletion, and remote branch deletion, but the wrapper terminated with a PowerShell `NativeCommandError` on the successful command:

```text
git push origin --delete <branch>
```

Git emitted normal progress such as:

```text
To https://github.com/...
```

on stderr. Current `Invoke-Git` merges stderr into the PowerShell pipeline:

```powershell
$output = @(& $gitExe @Arguments 2>&1 | ForEach-Object { [string]$_ })
```

With `$ErrorActionPreference = 'Stop'`, PowerShell may promote native stderr records into terminating `NativeCommandError` before the wrapper can inspect `$LASTEXITCODE`.

The remote branch was in fact deleted, showing that native stderr text is not itself failure evidence.

## Scope

### 1. Harden native Git invocation boundary

Update the Git execution seam used by `scripts/task_cleanup.ps1` so that:

- stdout and stderr are captured without native stderr becoming a PowerShell terminating error;
- command success/failure is determined by process exit code;
- stderr remains available in returned diagnostics;
- existing cwd relocation and command ordering are preserved;
- normal commands that emit stderr with exit code 0 complete successfully;
- nonzero exit codes still fail closed with useful diagnostics.

### 2. Preserve cleanup semantics

Do not change:

- canonical-main resolution;
- topology-first task resolution;
- `.venv` helper ownership;
- helper JSON / `DETACHED` contract;
- worktree removal ordering;
- local safe branch deletion;
- explicit-only remote deletion;
- stale/partial recovery policy;
- force/prune/pull/reset/clean prohibitions.

### 3. Behavioral regression tests

Extend `tests/test_task_cleanup_behavioral.py` so the fake Git seam can emit stderr independently of exit code.

Required regression cases should include at least:

1. exit code 0 + stderr text during remote branch deletion => wrapper succeeds;
2. exit code 0 + stderr text during another Git phase => wrapper succeeds;
3. nonzero exit code + stderr text => wrapper fails according to existing boundary and diagnostic contains the stderr evidence;
4. no later destructive step occurs after a genuine nonzero failure.

## Known invariants

- `$ErrorActionPreference = 'Stop'` remains valid for PowerShell/script errors; native process stderr must not be conflated with those errors.
- Native process exit code is the authoritative Git success/failure signal.
- Git commonly writes progress/status text to stderr even on success.
- `Invoke-Git` is the central Git execution seam and should remain the owner of native process capture semantics.
- Failure diagnostics should preserve both stdout and stderr without allowing either stream alone to redefine process success.
- Existing Windows non-interactive shell policy remains unchanged.

## Non-goals

- No redesign of `task_cleanup.ps1` orchestration.
- No changes to `worktree_cleanup_safety.ps1`.
- No changes to shared environment or branch-start/bootstrap behavior.
- No automatic retry of failed Git commands.
- No suppression/discarding of stderr diagnostics.
- No change to remote deletion default policy.
- No general PowerShell process runner framework unless the nearby code proves one already exists and reuse is smaller than a local fix.

## Provisional acceptance criteria

1. `task_cleanup.ps1` no longer throws `NativeCommandError` solely because a Git command writes stderr while returning exit code 0.
2. `Invoke-Git` returns separable or otherwise clearly preserved stdout/stderr diagnostic evidence and the native exit code.
3. Exit code 0 is treated as success even with stderr text.
4. Nonzero exit code remains failure even if stdout/stderr text is otherwise benign-looking.
5. Existing cleanup phase ordering and fail-closed boundaries remain unchanged.
6. A behavioral test reproduces the real dogfood pattern: successful remote deletion emits stderr and wrapper exits 0.
7. Behavioral tests also prove a real nonzero Git failure still stops later destructive actions.
8. Existing task-cleanup behavioral tests remain green.
9. PowerShell parse validation and `git diff --check` pass.
10. No unrelated workflow/game files change.

## Uncertainty to resolve via Scout

1. Which PowerShell/native-process capture mechanism best fits the repository's supported PowerShell/runtime version while preserving separate stdout/stderr and exit code?
2. Whether a nearby repository script already provides a reusable native-process execution seam that should be reused instead of adding new local plumbing.
3. Whether tests should specifically exercise stderr on `git push --delete`, or parameterize stderr injection across multiple phases to protect the generic `Invoke-Git` contract.

## Expected implementation surface

Likely minimal surface:

- `scripts/task_cleanup.ps1`
- `tests/test_task_cleanup_behavioral.py`
- task artifacts only

No architecture contract change is expected unless Scout finds an existing canonical native-process execution contract that must be referenced.
