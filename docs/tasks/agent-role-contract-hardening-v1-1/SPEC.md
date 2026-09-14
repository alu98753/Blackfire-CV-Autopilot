# agent-role-contract-hardening-v1-1

Status: Draft

## Goal

Make local OpenCode Scout/reviewer roles intentionally fast, concise, scope-disciplined, and genuinely read-only. Local free models should provide enough first-pass evidence for ChatGPT to perform the deeper architecture/specification/final review, rather than attempting an exhaustive repository audit themselves.

## Observed problem

The current Scout is already externally bounded but still allows up to 10 files and targets up to 1500 words. The current reviewers encourage broad/exhaustive coverage: the spec reviewer asks for per-clause coverage, while the regression reviewer asks for callers/callees/sibling paths/state/timing/dead logic/testability/architecture drift. Real runs showed useful analysis but also format drift and long exploratory loops that reached the 480-second hard timeout.

A real Scout run for this task using `opencode/mimo-v2.5-free` on OpenCode 2.0.3 reached the full 480-second external timeout and produced no canonical `CONTEXT.md`. This confirms the current role contract/process bound prevents indefinite hangs but does not yet reliably force early convergence.

The current agent frontmatter uses legacy `permission` / `bash` / `task` style controls. OpenCode 2.0.3 runtime inspection confirms a compatibility layer maps these to V2-style `permissions` rules such as `shell` and `subagent`, but the runtime behavior of all execution-capability paths still requires a direct probe because a previous reviewer session visibly reached an `execute`-style tool despite the intended read-only role.

## Verified OpenCode 2.0.3 runtime facts

The following facts were collected locally from `opencode v2.0.3` using `opencode --help`, `opencode run --help`, `opencode debug agents`, `opencode debug config`, `opencode api get /openapi.json`, and the installed CLI/runtime. They are evidence for this task and should not be re-litigated by Scout unless contradictory runtime behavior is observed.

1. Installed runtime is `opencode v2.0.3`.
2. Agent config schema supports a positive integer `steps` field.
3. Current project agents have `steps: null`, so no native step budget is active today.
4. V2 agent config schema uses `permissions` as an ordered array of `{ action, resource, effect }` rules where `effect` is `allow`, `deny`, or `ask`.
5. The installed runtime accepts legacy `permission` frontmatter and maps legacy `bash` to `shell` and legacy `task` to `subagent` in the resolved permission list.
6. `opencode debug agents` shows current Scout rules resolve to explicit denies for `edit`, `shell`, `subagent`, `external_directory`, `webfetch`, and `websearch`, after the runtime's broader base rules.
7. The OpenAPI schema types `Permission.Rule.action` as a free-form string rather than a closed enum. Therefore the set of actions appearing in `debug agents` output is not proof of the complete set of supported permission actions.
8. The installed CLI/runtime evidence is sufficient to establish that `steps` and V2 `permissions` are real runtime concepts; the exact last-step behavior and the treatment of the observed `execute`-style path still require direct execution probes.

## Verified Antigravity/Windows execution-substrate evidence

A controlled 5-command smoke test from Antigravity succeeded when finite commands were wrapped with `cmd.exe /d /s /c`, and OpenCode calls additionally used `< NUL` plus `--standalone`:

- `echo hello` -> exit 0, self-terminated.
- `git status --short` -> exit 0, self-terminated.
- nested `powershell.exe -NoProfile -Command ...` -> exit 0, self-terminated.
- `opencode run --standalone --model opencode/mimo-v2.5-free ... < NUL` -> exit 0, self-terminated.
- `opencode run --standalone --model opencode/big-pickle ... < NUL` -> exit 0, self-terminated.

This is operational evidence that the Antigravity terminal substrate can reliably observe completion/EOF under that wrapper. It is **not** an architecture invariant for repository automation: `ai_scout.ps1` / `ai_gate.ps1` must still establish their own deterministic child-process working directory, stdin, isolation, timeout, and cleanup behavior independent of IDE global rules.

The pre-probe working tree already contained unrelated user-owned untracked material under `meta_data/...`; subsequent probes must preserve the pre-existing status rather than deleting unrelated files merely to make `git status` globally clean.

## Scope

Provisional change surface:

- `.opencode/agents/scout.md`
- `.opencode/agents/spec-reviewer.md`
- `.opencode/agents/regression-reviewer.md`
- `scripts/ai_scout.ps1`
- `scripts/ai_gate.ps1`
- `docs/architecture/ai_development_workflow.md` if durable workflow semantics change
- focused deterministic/runtime probes needed to prove role limits and read-only behavior

No game/runtime code is in scope.

## Known invariants

1. Scout remains evidence-only. It does not own or finalize `SPEC.md`.
2. Spec reviewer and regression reviewer remain independent, read-only roles.
3. Gemini/Antigravity remains the sole production implementation writer after Final SPEC.
4. ChatGPT + user remain contract owners and ChatGPT remains the final semantic/architecture reviewer.
5. Gate verdict semantics remain `VERDICT: PASS|BLOCK` + `BLOCKING_FINDINGS`, with process outcomes 0=PASS, 1=INFRASTRUCTURE_BLOCKED, 2=CANDIDATE_BLOCKED.
6. A semantic BLOCK must not be weakened merely to shorten output.
7. Local-agent uncertainty should be reported explicitly instead of triggering open-ended repository exploration.
8. Existing 480-second process timeout remains the hard safety boundary unless Final SPEC identifies a better compatible mechanism.
9. Read-only agents must not gain repository-mutating shell/code-execution/subagent capability through an unguarded OpenCode permission path.
10. This task changes workflow/tooling behavior only; production/game behavior must remain unchanged.
11. Native step-bounding is a convergence mechanism, not a replacement for the hard wall-clock timeout.
12. No implementation may rely on undocumented assumptions about OpenCode permission action names or final-step behavior; disputed behavior must be runtime-probed first.
13. Repository automation must not depend on Antigravity-specific global shell rules for correctness.
14. Runtime probes must preserve unrelated pre-existing working-tree state.

## Provisional target behavior

### Scout

- First-pass localization, not exhaustive audit.
- Target about 5-6 directly relevant files; absolute ceiling 8.
- Target 600-800 words; hard output ceiling 1000 words where enforceable by contract/probe.
- Stop once ownership/control flow/relevant tests/material risks/minimal surface are sufficiently localized.
- Put unproven items in `Uncertainty` rather than expanding the audit.
- Do not reconstruct full repository history or prove every sibling-path non-problem that ChatGPT will independently re-check later.

### Reviewers

- Preserve two sequential roles: `spec-reviewer` and `regression-reviewer`.
- Operate as bounded blocker detectors, not exhaustive proof engines.
- PASS output should normally be about 300-600 words: required header, compact coverage summary, `Blocking findings: None`, and only a small number of advisories/evidence gaps.
- BLOCK may expand only concrete blocking findings needed to support the verdict.
- Stop exploring once enough grounded evidence exists to return PASS/BLOCK within the role boundary.
- Avoid exhaustive PASS tables, repository-history archaeology, broad sibling traversal, and low-value prose.

### Convergence controls

- Use OpenCode's native positive-integer `steps` budget if the direct runtime probe confirms the final-step behavior is suitable for graceful text finalization.
- Calibrate `steps` per role rather than treating model steps as wall-clock minutes. Initial probe range is approximately 5-7 total model steps, chosen to leave enough room for minimal evidence gathering plus final response generation.
- Desired normal operating result is roughly 2-4 minutes per reviewer and materially earlier than the 480-second hard timeout.
- Keep the external 480-second child-process timeout as the hard safety boundary because one slow provider/model request may consume substantial wall-clock time even with a small step budget.
- Do not substitute a prompt-only statement such as "finish within 6 minutes" for a runtime-enforced iteration budget.
- Do not add a custom timer/plugin/session-interrupt control plane in this v1.1 task unless direct evidence shows native `steps` cannot provide graceful convergence; explicit pause/amend/resume belongs to later V2 work.

### Read-only boundary

- Prefer explicit V2 `permissions` rules in custom agents for clarity and forward maintenance, even though OpenCode 2.0.3 currently maps legacy keys through a compatibility layer.
- Use a broad deny followed by narrow discovery allows where runtime rule ordering/probes confirm the intended behavior.
- Discovery roles should need only local read/search capabilities required for their task (`read`, `glob`, `grep`) plus any strictly necessary internal capability proven by probe.
- Explicitly deny mutation/execution/subagent/web/external access paths that are not required.
- The observed `execute`-style tool must be tested directly. The OpenAPI action field being free-form means absence from current resolved rules is not proof that the runtime cannot expose or gate such an action.

### Process invocation isolation

- Repository-owned Scout/Gate execution should be deterministic outside Antigravity as well as inside it.
- Final design should explicitly control the child working directory and stdin semantics rather than relying only on parent-shell inheritance.
- `--standalone` is a strong candidate for formal local-agent jobs because it avoids shared-server state coupling, but its private-server cleanup/orphan behavior must be runtime-probed before becoming a Final SPEC requirement.
- Do not hard-code a global npm/native binary path unless evidence shows the PowerShell wrapper itself is still problematic after process isolation is fixed.

## Non-goals

- No model fallback routing; that is `agent-model-fallback-routing-v1-1`.
- No retries after a semantic BLOCK.
- No parallel reviewers or reviewer voting/racing.
- No Gemini self-review as a normal independent Gate PASS.
- No user pause/amend/resume control plane.
- No shared generalized process framework extraction.
- No production/game behavior changes.
- No custom timer/plugin solely to simulate a six-minute clock unless native step-bounding is proven inadequate.
- No requirement that developers globally use Antigravity-specific `cmd /c` wrapping outside agent automation.

## Provisional acceptance criteria

1. Scout contract clearly encodes the tighter file/output/early-stop policy without losing required ownership/control-flow/test/risk evidence.
2. Spec/regression reviewer PASS outputs are materially shorter and blocker-first while preserving valid BLOCK detail.
3. Representative real/deterministic role probes show normal convergence materially earlier than the 480-second timeout.
4. Installed OpenCode 2.0.3 `steps` behavior is directly verified, including what occurs on the final allowed step and whether valid structured text is still produced.
5. A calibrated step budget is chosen from evidence, not guessed from elapsed minutes.
6. Read-only permissions are directly proven against the installed runtime, including the previously observed `execute`-style path and ordinary shell/edit/subagent mutation attempts.
7. No local reviewer can mutate tracked repository content or launch an unrestricted child/subagent through the configured role.
8. `scripts/ai_scout.ps1 -Task <id>` and `scripts/ai_gate.ps1 -Task <id>` remain compatible.
9. Gate 0/1/2 classification and canonical artifact safety remain unchanged.
10. No game/runtime files change.
11. Durable workflow docs are updated only for verified final semantics, not provisional OpenCode assumptions.
12. Runtime probes introduce no new working-tree delta after cleanup and preserve unrelated pre-existing files.
13. If repository scripts adopt standalone execution, timeout/cancellation probes prove no orphan private OpenCode server remains.
14. Repository scripts do not require Antigravity Global Rules to terminate correctly.

## Remaining uncertainty / required bootstrap probes

1. **Final-step semantics:** with a small `steps` budget on OpenCode 2.0.3, does the last allowed step remove tools and yield a usable final text response, or terminate/truncate in another way?
2. **Execution permission semantics:** can an explicit deny rule for the `execute` action be loaded and enforced by OpenCode 2.0.3, and does it prevent the previously observed `execute`-style code path independently of `shell` denial?
3. **Standalone lifecycle:** when a formal agent process times out or is killed, does its private standalone server terminate with it, or can it leave an orphan process?
4. What smallest step budget gives Mimo enough evidence to produce a valid Scout/reviewer result without reintroducing open-ended exploration? Big Pickle calibration is secondary and should occur only after Mimo behavior is understood.
5. Are agent-definition changes sufficient, or do `ai_scout.ps1` / `ai_gate.ps1` need invocation changes for verified step/permission/isolation behavior to take effect?
6. What is the smallest disposable local probe that answers the above without creating a generalized OpenCode test framework?
