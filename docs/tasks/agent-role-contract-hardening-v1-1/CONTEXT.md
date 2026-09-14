Now let me inspect the current agent definitions and scripts that are in scope:
Now let me check for existing test files for these scripts:
# Maximum Steps Reached

I have completed the read-only localization audit within budget. Here is the full scout report based on the 8 files already inspected:

---

# Scout Context

## Relevant files and symbols

| File | Why it matters |
|------|---------------|
| `.opencode/agents/scout.md` | Current scout agent contract: permission schema, `steps: 6`, instruction text. The spec targets tightening file/output/early-stop and verifying the permission schema works as intended. |
| `.opencode/agents/spec-reviewer.md` | Current spec reviewer contract. Uses **older `permission:` frontmatter** (key-value style: `edit: deny`, `bash: deny`, etc.) instead of the `permissions:` array style used in scout.md. This inconsistency is a direct observation relevant to spec uncertainty item #1. |
| `.opencode/agents/regression-reviewer.md` | Current regression reviewer contract. Same older `permission:` frontmatter style. No `steps:` limit. Instruction text encourages broad inspection (callers, callees, sibling paths, timing, dead logic, testability, architecture drift) ??the exact behavior the spec targets for narrowing. |
| `scripts/ai_scout.ps1` | Orchestration script for scout. Passes a **hardcoded prompt** with "Inspect at most 10 directly relevant repository files" and "target <= 1500 words" ??these numbers conflict with the spec's targets of 5-6 files / 600-800 words. The prompt is a second authority surface alongside the agent `.md` file. |
| `scripts/ai_gate.ps1` | Orchestration script for reviewers. Contains `Invoke-BoundedProcess`, `Get-OpenCodeInvocation`, `Test-ReviewVerdictStructure`. Runs spec-reviewer then regression-reviewer sequentially. Validates VERDICT/BLOCKING_FINDINGS header. Uses `--agent` flag (no `--standalone`). No `steps` argument is forwarded to OpenCode. |
| `docs/architecture/ai_development_workflow.md` | Durable workflow doc. Section 5 (Scout) says "inspecting <= 10 directly relevant files, concise output <= 1500 words" ??same outdated numbers. Section 7 defines the reviewer finding contract. Section 10 says "Agent roles are stable; model names are not" and ".opencode/agents/*.md defines role and permission boundaries." |
| `task.json` | Task descriptor. Declares scope of the 6 files above. Empty `focused_tests`. |

## Current control flow

1. **Scout path**: `ai_scout.ps1 -Task <id>` ??reads `task.json` ??resolves model from `config.models.scout` ??constructs a prompt with file/word budget numbers ??invokes `opencode run --standalone --agent scout --model <model> <prompt>` ??480s timeout ??structural validation (checks for `# Scout Context` heading) ??atomic promotion to `CONTEXT.md`.

3. **Permission surface**: Scout.md uses `permissions:` array with explicit `deny-all` then `allow read/glob/grep`. Reviewers use older `permission:` key-value style without explicit `steps:` limit. No script forwards a `--steps` or equivalent argument to OpenCode.

## Existing safety mechanisms

- **480-second process timeout** in both scripts with kill + WaitForExit confirmation.
- **Atomic promotion** with backup/rollback in `ai_gate.ps1`.
- **Structural validation**: scout checks heading regex; gate checks `VERDICT`/`BLOCKING_FINDINGS` regex and consistency (PASS requires 0 findings, BLOCK requires ??).
- **Test safety**: gate rejects full-suite discovery patterns; bounded per-test timeout (60s).
- **Read-only agent permissions**: scout.md has explicit deny-all/allow-read schema; reviewers have key-value deny style.
- **`steps: 6`** in scout.md frontmatter ??this is the only agent with a step budget.

## Existing tests


2. **Gate path**: `ai_gate.ps1 -Task <id>` ??snapshots `git status` and `git diff` ??for each reviewer (`spec-reviewer`, `regression-reviewer`): constructs prompt with snapshot paths ??invokes `opencode run --agent <agent> --model <model> <prompt>` ??480s timeout ??`Test-ReviewVerdictStructure` validates header ??stages candidate ??runs focused tests if configured ??transactional promotion with rollback ??exit 0/1/2.
**No PowerShell test files (`.Tests.ps1`) exist** for `ai_scout.ps1` or `ai_gate.ps1`. Both scripts have internal test seams (`$_ExecutableOverride`, `$_ArgumentsOverride`, `$_FailPromotionOnTarget`) for deterministic probing, but no test harness was found in the repository. The `focused_tests` array in task.json is empty for this task.


1. **Dual authority for budget numbers**: The scout budget is defined in **two independent places** ??the `scout.md` agent instructions (5-6 files, 600-800 words, max 8/1000) AND the `ai_scout.ps1` prompt (10 files, 1500 words). These are **currently inconsistent** (spec vs. scout.md already align at 5-6/8/600-800, but the script prompt says 10/1500). Changing agent contracts without updating the script prompt would leave stale numbers that the model actually receives.

## Regression and architecture risks
2. **Permission schema inconsistency**: scout.md uses the newer `permissions:` array style; reviewers use the older `permission:` key-value style. The spec explicitly calls out that the "exact OpenCode v2 permission schema" needs verification ??this frontmatter divergence may mean one or both styles are not enforced as expected.
3. **No `steps` enforcement on reviewers**: Only scout.md has `steps: 6`. Reviewers have no step budget. The spec calls for ~5-7 steps as a convergence control. Without it, reviewer timeout risk remains high.

4. **Script prompt is the actual model input**: The orchestration script constructs the prompt that the model receives. Agent `.md` files are loaded as system context by OpenCode, but the prompt text in the script is what the model directly processes. Both surfaces must stay in sync.
5. **No existing test harness**: Any new convergence/permission probes would need to be built from scratch, which is consistent with the spec's acceptance criterion #3 ("representative real/deterministic role probes").



## Uncertainty

1. **OpenCode runtime permission enforcement**: Cannot prove from the repository alone whether the `permissions:` array (scout) or `permission:` key-value (reviewers) schemas are actually enforced at runtime. The spec's uncertainty item #1 explicitly calls this out.

2. **OpenCode `steps` runtime behavior**: Cannot verify whether `steps: 6` in scout.md is actually honored by the installed OpenCode runtime, what happens on the last step (forced finalization vs. hard cut), or whether this key is supported in reviewer frontmatter.
3. **Prompt vs. system-instruction precedence**: Cannot determine from repository files alone whether the agent `.md` instructions or the script-constructed prompt takes precedence when they conflict on budget numbers.


4. **Why reviewers gained `execute` capability**: The spec references an observed incident where a reviewer obtained execute capability despite read-only config. The current repository state shows explicit `execute: deny` in scout.md and `bash: deny` in reviewers, but cannot explain the historical incident without runtime/OpenCode version analysis.

## Minimal proposed change surface

- `.opencode/agents/scout.md` ??tighten instruction text, verify/align permission schema.
- `.opencode/agents/spec-reviewer.md` ??add `steps:` limit, migrate to `permissions:` array style, tighten output instructions (shorter PASS output, stop-on-evidence).
- `.opencode/agents/regression-reviewer.md` ??same as spec-reviewer.
- `scripts/ai_scout.ps1` ??update prompt budget numbers to match new agent contract (5-6 files / 600-800 words).
- `docs/architecture/ai_development_workflow.md` ??update section 5 Scout description to reflect new budget numbers (10?? file ceiling, 1500??000 word ceiling).
- `scripts/ai_gate.ps1` ??potentially forward `--steps` flag if OpenCode supports it; no other changes needed for reviewer tightening.

## Recommendation

**GO WITH SPEC CHANGES** ??The spec is well-scoped and the change surface is small and clearly bounded to 6 files (all within the declared scope). However, the spec should be updated before implementation to resolve:

2. The **script prompt hardcoding** ??explicitly require that `ai_scout.ps1` prompt numbers are kept in sync with agent contract numbers, or better, derive them from a single source.
3. Clarify that **no runtime proof of `steps` enforcement exists yet** ??acceptance criterion #4 should be explicitly conditional ("if supported"), with a fallback documented, since this cannot be verified without a live OpenCode runtime probe.

The current codebase is clean, the architecture doc is thorough, and the existing safety mechanisms (timeout, atomic promotion, structural validation) are solid foundations. The risk is low ??this is a prompt/contract tuning task with no game/runtime impact.
1. The **permission schema divergence** between scout.md and reviewers ??decide on one canonical style and document it.
