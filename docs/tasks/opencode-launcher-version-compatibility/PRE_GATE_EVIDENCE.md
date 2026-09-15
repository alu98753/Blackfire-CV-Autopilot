# Pre-Gate Evidence

Task: `opencode-launcher-version-compatibility`

This note records focused verification completed before the canonical Gate run.

## Implementation verification

Implementation commit: `aa083a298b492e652d371c3df753e4baadac056f`

Reported focused verification from the dedicated task worktree:

- `tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1`: 16 cases passed.
- OpenCode bootstrap/version check: installed `1.18.31` accepted.
- `git diff --check`: passed.
- Branch was attached and synchronized with origin.

The workflow harness is a PowerShell harness, not a Python `unittest` target. Therefore `task.json.focused_tests` is intentionally empty for Gate instead of encoding descriptive strings that `ai_gate.ps1` would incorrectly pass to `python -m unittest`.

## Post-implementation self-hosting proof

After recovering the local OpenCode data state without deleting the incompatible database backup:

- direct smoke test `opencode run --agent scout --model opencode/big-pickle "Reply only OK"` reached model execution and returned `OK`;
- canonical `scripts/ai_scout.ps1 -Task opencode-launcher-version-compatibility` reached `opencode/mimo-v2.5-free`, completed successfully, and promoted `CONTEXT.md`;
- the original `--standalone` parser blocker did not recur.

## Local OpenCode state note

The prior local database failure was independently reproduced outside the repository launcher as `Database is not empty and has no session table`. Read-only SQLite inspection showed an integrity-clean database (`PRAGMA integrity_check = ok`) with `session_v2`/related tables but no legacy `session` table. The incompatible database was preserved via backup/rename, and OpenCode 1.18.31 then created a fresh database successfully.

This local state/schema issue is not treated as a production launcher defect and is outside this task's implementation scope.
