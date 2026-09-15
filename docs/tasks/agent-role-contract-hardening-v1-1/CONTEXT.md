Now let me read the scoped agent contracts and scripts:
Now let me check for the bootstrap scout agent and any existing tests for these scripts:
# Scout Context

## Relevant files and symbols

**1. `docs/tasks/agent-role-contract-hardening-v1-1/task.json`** ??Task descriptor declaring scope: 3 agent contracts, 2 scripts, 1 architecture doc. Models: `opencode/mimo-v2.5-free`. No `focused_tests` declared.

**2. `docs/tasks/agent-role-contract-hardening-v1-1/SPEC.md`** ??Canonical spec (Status: Draft) defining tighter Scout budgets (5-6 files, 600-800 words, `steps: 6`), reviewer budgets (`steps: 5`), V2 `permissions` migration, `--standalone` invocation isolation, and 13 acceptance criteria.

**3. `.opencode/agents/scout.md`** ??Current Scout contract. Uses legacy `permission`/`bash`/`task` frontmatter (not V2 `permissions`). File budget is 10 files / 1500 words. **No `steps` field** (spec wants `steps: 6`).

**4. `.opencode/agents/spec-reviewer.md`** ??Current spec reviewer. Same legacy permission style, no `steps`. Spec wants `steps: 5` and tighter 300-600 word PASS output.

**5. `.opencode/agents/regression-reviewer.md`** ??Current regression reviewer. Legacy permissions, no `steps`. Expects callers/callees/sibling traversal (spec wants bounded blocker-detection only).
**6. `scripts/ai_scout.ps1`** ??Scout invocation script (237 lines). Already uses `--standalone`, explicit `$repoRoot` WorkingDirectory, `StandardInput.Close()`, 480s timeout. Calls `--agent bootstrap-scout` (which doesn't exist yet). No V2 permissions. Has test seam `$_ExecutableOverride`.

**7. `scripts/ai_gate.ps1`** ??Gate invocation script (568 lines). Has `Invoke-BoundedProcess` helper, `Test-ReviewVerdictStructure`, sequential spec?egression reviewer execution, focused test runner, transaction-safe promotion with rollback. Calls `--agent spec-reviewer` / `--agent regression-reviewer`. Uses `--agent` without `--standalone` (spec wants `--standalone`). Has rich test seams.


**8. `docs/architecture/ai_development_workflow.md`** ??Workflow doc (351 lines). Describes Scout as "inspecting <= 10 directly relevant files, concise output <= 1500 words, and an 8-minute execution timeout." Needs update to reflect local agents as "bounded first-pass evidence providers."


1. **Scout path**: `ai_scout.ps1 -Task <id>` ??reads `task.json` ??resolves model ??builds prompt ??invokes `opencode run --standalone --agent bootstrap-scout --model <model> <prompt>` ??captures stdout via async events ??480s timeout ??structural validation (`# Scout Context` heading) ??atomic promotion to `CONTEXT.md`.

2. **Gate path**: `ai_gate.ps1 -Task <id>` ??snapshots git status/diff ??runs spec-reviewer then regression-reviewer sequentially (each via `opencode run --agent <name>`, **no `--standalone` flag**) ??validates `VERDICT: PASS|BLOCK` + `BLOCKING_FINDINGS` header ??optionally runs `focused_tests` ??transaction-safe promotion of `reviews/*` and `EVIDENCE.md` with rollback on failure.

## Current control flow
3. **Agent permissions**: All three agents use legacy frontmatter (`permission: edit/bash/task: deny`). The OpenCode 2.0.3 runtime maps these to V2 rules, but they are not explicitly V2 `permissions` format.
## Existing safety mechanisms

- `StandardInput.Close()` in both scripts to prevent stdin hangs
- 480-second hard timeout in both scripts
- Explicit `$repoRoot` WorkingDirectory
- `--standalone` in scout script (not yet in gate script)
- Verdict header structural validation in gate
- Transaction-safe promotion with backup/rollback in gate


## Existing tests

**None found.** No Pester test files (`.Tests.ps1`) exist in the repository. The scripts have internal test seams (`$_ExecutableOverride`, etc.) but no automated test harness wraps them.

## Regression and architecture risks

1. **`bootstrap-scout` agent referenced but doesn't exist** ??`ai_scout.ps1` line 75/83 passes `--agent bootstrap-scout` but `.opencode/agents/bootstrap-scout.md` does not exist. This is either a pre-existing issue or the production agent should be `scout`, not `bootstrap-scout`.
- Process kill confirmation with 3-second wait

- Focused test rejection of full-suite discovery targets
2. **Gate script lacks `--standalone`** ??`ai_gate.ps1` line 231 uses `opencode run --agent <name>` without `--standalone`, violating spec requirement for isolation in formal Gate jobs.

3. **Legacy permissions across all agents** ??All three agents need migration to V2 `permissions` array format with explicit deny/allow rules for `read`, `glob`, `grep` only.

4. **No step budgets anywhere** ??No agent has a `steps` field. Spec requires `steps: 6` for Scout, `steps: 5` for reviewers.

5. **Workflow doc describes 10-file/1500-word budget** ??Must be updated to match new 5-6 file / 600-800 word / early-stop policy.

6. **No automated tests** ??No regression coverage exists for script changes. Any modification to `ai_scout.ps1` or `ai_gate.ps1` has zero automated regression protection.

## Uncertainty

1. Whether `bootstrap-scout` is intentionally a temporary name or a bug ??needs clarification.
2. Whether the gate script should also use `--standalone` (spec says yes for "formal Scout/Gate automation").
3. Whether `steps: 6` and `steps: 5` produce adequate real-world results (spec marks this as a calibration requirement).
4. Whether any non-mutating permission beyond `read`/`glob`/`grep` is needed (spec flags this as open).

## Minimal proposed change surface

- **`.opencode/agents/scout.md`** ??Add `steps: 6`, migrate to V2 `permissions`, tighten prompt to 5-6 files / 600-800 words / early-stop.
- **`.opencode/agents/spec-reviewer.md`** ??Add `steps: 5`, migrate to V2 `permissions`, tighten PASS output expectations.
- **`.opencode/agents/regression-reviewer.md`** ??Add `steps: 5`, migrate to V2 `permissions`, narrow to bounded blocker detection.
- **`scripts/ai_scout.ps1`** ??Fix `--agent bootstrap-scout` ??`--agent scout`, update prompt text, verify `--standalone` preserved.
- **`scripts/ai_gate.ps1`** ??Add `--standalone` to reviewer invocations, add explicit `WorkingDirectory` if missing.
- **`docs/architecture/ai_development_workflow.md`** ??Update Scout description to match new tighter budgets.

## Recommendation

**GO WITH SPEC CHANGES** ??The spec is well-defined and the change surface is clear and bounded. However: (a) the `bootstrap-scout` agent name referenced in `ai_scout.ps1` does not exist and must be resolved before implementation; (b) no automated tests exist for these scripts, which is a material risk for script modifications ??the spec should recommend creating at least a basic Pester test suite as a prerequisite or parallel work item; (c) the spec should clarify whether the gate script's `--standalone` addition is in scope or deferred.

---

**Maximum steps reached.** All 8 scoped files have been read. The report above is complete based on the files inspected within budget. Remaining uncertainty items are documented above.
