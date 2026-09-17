# task-cleanup-native-stderr-handling

Status: Final

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

on stderr. The prior `Invoke-Git` merged stderr into the PowerShell pipeline:

```powershell
$output = @(& $gitExe @Arguments 2>&1 | ForEach-Object { [string]$_ })
```

With `$ErrorActionPreference = 'Stop'`, Windows PowerShell could promote native stderr records into terminating `NativeCommandError` before the wrapper could inspect `$LASTEXITCODE`.

The remote branch was in fact deleted, proving native stderr text is not itself failure evidence.

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

Required regression cases:

1. exit code 0 + stderr text during remote branch deletion => wrapper succeeds;
2. exit code 0 + stderr text during another Git phase => wrapper succeeds;
3. nonzero exit code + stderr text => wrapper fails according to the existing boundary and diagnostic contains stderr evidence;
4. no later destructive step occurs after a genuine nonzero failure.

## Known invariants

- `$ErrorActionPreference = 'Stop'` remains valid for PowerShell/script errors; native process stderr must not be conflated with those errors.
- Native process exit code is the authoritative Git success/failure signal.
- Git commonly writes progress/status text to stderr even on success.
- `Invoke-Git` is the central Git execution seam and remains the owner of native process capture semantics.
- Failure diagnostics preserve stdout/stderr without allowing either stream alone to redefine process success.
- Existing Windows non-interactive shell policy remains unchanged.

## Non-goals

- No redesign of `task_cleanup.ps1` orchestration.
- No changes to `worktree_cleanup_safety.ps1`.
- No changes to shared environment or branch-start/bootstrap behavior.
- No automatic retry of failed Git commands.
- No suppression/discarding of stderr diagnostics.
- No change to remote deletion default policy.
- No general PowerShell process runner framework.

## Acceptance criteria

1. `task_cleanup.ps1` no longer throws `NativeCommandError` solely because a Git command writes stderr while returning exit code 0.
2. `Invoke-Git` preserves stdout, stderr, and native exit code as diagnostic/process evidence.
3. Exit code 0 is treated as success even with stderr text.
4. Nonzero exit code remains failure even if stdout/stderr text is otherwise benign-looking.
5. Existing cleanup phase ordering and fail-closed boundaries remain unchanged.
6. A behavioral test reproduces the real dogfood pattern: successful remote deletion emits stderr and wrapper exits 0.
7. Behavioral tests prove a real nonzero Git failure still stops later destructive actions.
8. Existing task-cleanup behavioral tests remain green.
9. PowerShell parse validation and `git diff --check` pass.
10. No unrelated workflow/game files change.

## Implementation decision

Use a local native-process boundary inside `Invoke-Git`:

- redirect stdout and stderr to separate temporary files;
- locally prevent native stderr from becoming a terminating PowerShell error;
- restore the script-wide `$ErrorActionPreference = 'Stop'` immediately after the native call;
- classify success/failure only from `$LASTEXITCODE`;
- return stdout/stderr diagnostic evidence to callers;
- delete temporary capture artifacts in `finally`.

This keeps the fix local to the existing Git execution seam and does not alter orchestration ownership or cleanup ordering.

## Verification evidence

Implementation commit:

`bed6f49950e7955c40b597457658b158db0a95e5`

Reported verification:

- wrapper behavioral tests: 7/7 passed;
- PowerShell parse validation: passed;
- `git diff --check`: passed.

ChatGPT semantic review confirmed the implementation preserves native exit-code authority, retains stderr diagnostics, and does not alter cleanup ordering or safety ownership.

## Expected implementation surface

- `scripts/task_cleanup.ps1`
- `tests/test_task_cleanup_behavioral.py`
- task artifacts

No architecture contract or `.venv` safety-helper change is required.
