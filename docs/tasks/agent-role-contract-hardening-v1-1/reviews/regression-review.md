Now let me inspect the current state of the key files to verify the diff is consistent with what actually exists on the working tree:
Now let me verify one key detail about the scripts - whether `ai_scout.ps1` previously had duplicated budget numbers or was already delegating to the agent contract:
VERDICT: PASS

BLOCKING_FINDINGS: 0
## Behavior-preservation assessment
# Regression Review



- Scout remains evidence-only and never owns `SPEC.md`.
- Spec reviewer and regression reviewer remain separate sequential read-only roles.
- Gemini/Antigravity remains the sole production implementation writer.
The patch migrates three OpenCode agent role contracts (`scout.md`, `spec-reviewer.md`, `regression-reviewer.md`) from legacy V1 permission syntax to V2 `permissions` rules, adds `steps` budgets (6 for scout, 5 for reviewers), tightens exploration/output budgets, adds early-stop semantics, and updates the architecture documentation and backlog to reflect the new durable role model. The two automation scripts (`ai_scout.ps1`, `ai_gate.ps1`) are **not modified by the diff** ??they already implement `--standalone` invocation, explicit `$repoRoot` working directory, `StandardInput.Close()`, and delegated budget authority to the agent contract.
All existing behavioral invariants are preserved:
- ChatGPT + user remain contract owners and final reviewers.
- Gate semantic contract (`VERDICT: PASS|BLOCK` + `BLOCKING_FINDINGS`) is unchanged.
- Gate process outcomes (0=PASS, 1=INFRASTRUCTURE_BLOCKED, 2=CANDIDATE_BLOCKED) are unchanged.
- 480-second hard timeout remains the wall-clock safety boundary.
- V2 permissions correctly deny `edit`, `shell`, `execute`, `subagent`, `external_directory`, `webfetch`, `websearch` and allow only `read`, `glob`, `grep`.
- `ai_scout.ps1` does not duplicate concrete budget numbers; its prompt delegates to the agent contract ("Strictly follow the file and word budget limits defined in the scout agent contract").

## Blocking findings
- No game/runtime files change.

None.

## Advisory findings

1. **BACKLOG.md and CONTEXT.md are outside declared `task.json` scope but within the diff.** BACKLOG.md is reorganized (task 1 promoted to active, future tasks condensed). CONTEXT.md is new Scout output. Neither changes a behavioral contract. This is cosmetic and expected for task activation, but a minor scope discipline note ??the diff includes two files not listed in `task.json` scope.

2. **BACKLOG condensation loses some detail** (e.g., observed model evidence for task 2, detailed planned invariants for task 3). This is acceptable since backlog is explicitly not normative ??`SPEC.md` is the single source of truth ??but future readers may want the detail preserved in the respective SPEC files when those tasks are activated.

3. **Redundant explicit deny entries** after the broad `*/*` deny (e.g., `shell: deny`, `edit: deny` appearing after the broad deny) are harmless ??they serve as explicit documentation of critical boundaries rather than functional policy. No regression risk.
