# agent-role-contract-hardening-v1-1

Status: Draft

## Goal

Make local OpenCode Scout/reviewer roles intentionally fast, concise, scope-disciplined, and genuinely read-only. Local free models should provide enough first-pass evidence for ChatGPT to perform the deeper architecture/specification/final review, rather than attempting an exhaustive repository audit themselves.

## Observed problem

The current Scout is already externally bounded but still allows up to 10 files and targets up to 1500 words. The current reviewers encourage broad/exhaustive coverage: the spec reviewer asks for per-clause coverage, while the regression reviewer asks for callers/callees/sibling paths/state/timing/dead logic/testability/architecture drift. Real runs showed useful analysis but also format drift and long exploratory loops that reached the 480-second hard timeout.

A real Scout run for this task using `opencode/mimo-v2.5-free` on OpenCode 2.0.3 reached the full 480-second external timeout and produced no canonical `CONTEXT.md`. This confirms the current role contract/process bound prevents indefinite hangs but does not yet reliably force early convergence.

A separate Antigravity IDE smoke-test matrix also showed that finite Windows terminal commands complete reliably when Gemini invokes them through `cmd.exe /d /s /c`, with stdin redirected from `NUL` for CLIs that may inspect stdin. Both `opencode/mimo-v2.5-free` and `opencode/big-pickle` completed normally under `opencode run --standalone ... < NUL`. This is an IDE/terminal operational workaround, not a repository architecture invariant; repository scripts must remain correct outside Antigravity.

The current agent frontmatter uses legacy `permission` / `bash` / `task` style controls. OpenCode 2.0.3 runtime inspection confirms a compatibility layer maps these to V2-style `permissions` rules such as `shell` and `subagent`. Direct runtime probes now also confirm that V2 rules can deny execution capability and that native step bounding forces graceful final text generation.

## Verified OpenCode 2.0.3 runtime facts

The following facts were collected locally from `opencode v2.0.3` using CLI/API inspection plus disposable runtime probes. They are evidence for this task and should not be re-litigated by Scout unless contradictory runtime behavior is observed.

1. Installed runtime is `opencode v2.0.3`.
2. Agent config schema supports a positive integer `steps` field.
3. Current project agents have `steps: null`, so no native step budget is active today.
4. V2 agent config schema uses `permissions` as an ordered array of `{ action, resource, effect }` rules where `effect` is `allow`, `deny`, or `ask`.
5. The installed runtime accepts legacy `permission` frontmatter and maps legacy `bash` to `shell` and legacy `task` to `subagent` in the resolved permission list.
6. `opencode debug agents` shows current Scout rules resolve to explicit denies for `edit`, `shell`, `subagent`, `external_directory`, `webfetch`, and `websearch`, after the runtime's broader base rules.
7. The OpenAPI schema types `Permission.Rule.action` as a free-form string rather than a closed enum, so resolved-rule listings are not a complete enum of supported action names.
8. A disposable `steps: 2` probe proved native final-step behavior: step 1 used a discovery tool; on step 2 the runtime rejected another tool call with `Tools are disabled after the maximum agent steps`, then the model still emitted a complete final text response and exited 0 in about 33 seconds.
9. A disposable V2 permissions probe with broad deny plus narrow `read` / `glob` / `grep` allows loaded an explicit `execute: deny` rule successfully. When asked to execute `node -v`, the model reported that no shell execution tool was available; no command, child process, or repository mutation occurred.
10. A disposable standalone lifecycle probe showed `opencode run --standalone` owns a private child/server lifecycle that terminates with the client; killing the client left no orphan private-server PID.
11. The above probes were cleaned up completely and produced zero working-tree delta relative to their pre-probe status.
12. Antigravity-specific `cmd.exe /d /s /c ... < NUL` wrapping is useful for reliable IDE tool completion, but it must not be required for repository correctness. Repository automation should establish its own deterministic child-process boundary.

## Scope

Provisional change surface:

- `.opencode/agents/scout.md`
- `.opencode/agents/spec-reviewer.md`
- `.opencode/agents/regression-reviewer.md`
- `scripts/ai_scout.ps1`
- `scripts/ai_gate.ps1`
- `docs/architecture/ai_development_workflow.md` if durable workflow semantics change
- focused deterministic/runtime probes needed to prove role limits, invocation isolation, and read-only behavior

No game/runtime code is in scope.

## Known invariants

1. Scout remains evidence-only. It does not own or finalize `SPEC.md`.
2. Spec reviewer and regression reviewer remain independent, read-only roles.
3. Gemini/Antigravity remains the sole production implementation writer after Final SPEC.
4. ChatGPT + user remain contract owners and ChatGPT remains the final semantic/architecture reviewer.
5. Gate verdict semantics remain `VERDICT: PASS|BLOCK` + `BLOCKING_FINDINGS`, with process outcomes 0=PASS, 1=INFRASTRUCTURE_BLOCKED, 2=CANDIDATE_BLOCKED.
6. A semantic BLOCK must not be weakened merely to shorten output.
7. Local-agent uncertainty should be reported explicitly instead of triggering open-ended repository exploration.
8. Existing 480-second process timeout remains the hard safety boundary.
9. Read-only agents must not gain repository-mutating shell/code-execution/subagent capability through an unguarded OpenCode permission path.
10. This task changes workflow/tooling behavior only; production/game behavior must remain unchanged.
11. Native step-bounding is a convergence mechanism, not a replacement for the hard wall-clock timeout.
12. Repository automation must not rely on Antigravity Global Rules, an interactive terminal, a shared OpenCode daemon, or implicit parent-process CWD/stdin state for correctness.
13. Probe/verification logic must preserve pre-existing unrelated working-tree state and may judge safety by before/after delta rather than requiring a globally clean tree.

## Provisional target behavior

### Scout

- First-pass localization, not exhaustive audit.
- Target about 5-6 directly relevant files; absolute ceiling 8.
- Target 600-800 words; hard output ceiling 1000 words where enforceable by contract/probe.
- Stop once ownership/control flow/relevant tests/material risks/minimal surface are sufficiently localized.
- Put unproven items in `Uncertainty` rather than expanding the audit.
- Do not reconstruct full repository history or prove every sibling-path non-problem that ChatGPT will independently re-check later.
- Initial native step budget should be `steps: 6`, subject to one real Scout calibration run after implementation; lowering to 5 is allowed if evidence remains sufficient, while raising above 6 requires evidence of missing essential localization.

### Reviewers

- Preserve two sequential roles: `spec-reviewer` and `regression-reviewer`.
- Operate as bounded blocker detectors, not exhaustive proof engines.
- PASS output should normally be about 300-600 words: required header, compact coverage summary, `Blocking findings: None`, and only a small number of advisories/evidence gaps.
- BLOCK may expand only concrete blocking findings needed to support the verdict.
- Stop exploring once enough grounded evidence exists to return PASS/BLOCK within the role boundary.
- Avoid exhaustive PASS tables, repository-history archaeology, broad sibling traversal, and low-value prose.
- Initial native step budget should be `steps: 5` for both reviewer roles, subject to real Gate calibration; lowering to 4 is allowed if blocker-detection evidence remains adequate.

### Convergence controls

- Use OpenCode's native positive-integer `steps` budget in each local role. Runtime probing confirmed that the last allowed step disables tools and still permits a final text response.
- Treat `steps` as an iteration bound, not a wall-clock deadline. A slow provider/model request can still consume substantial time.
- Desired normal operating result is roughly 1-3 minutes for Scout and 2-4 minutes per reviewer, materially earlier than the 480-second hard timeout.
- Keep the external 480-second child-process timeout as the hard safety boundary.
- Do not add a custom timer/plugin/session-interrupt control plane in this v1.1 task.

### Read-only boundary

- Migrate custom agents to explicit V2 `permissions` rules for clarity and forward maintenance.
- Use broad deny followed by narrow allows for only `read`, `glob`, and `grep`, plus any strictly necessary non-mutating capability proven by implementation-time probes.
- Explicitly deny `edit`, `shell`, `subagent`, `execute`, `external_directory`, `webfetch`, and `websearch` even if some capabilities are already removed by broad deny; the explicit entries document critical boundaries and aid runtime inspection.
- A real runtime probe must continue to prove that command execution is unavailable and repository mutation does not occur.

### Invocation isolation

- OpenCode calls launched by `ai_scout.ps1` and `ai_gate.ps1` should use `--standalone` by default so formal workflow jobs do not depend on shared background-service state.
- Each child process must receive an explicit repository `WorkingDirectory` rather than relying only on inherited current directory.
- Child stdin must be deterministically non-interactive/closed so wrapper or CLI behavior cannot wait on input EOF indefinitely.
- Existing stdout/stderr streaming, timeout handling, client-only ownership semantics, and artifact-safety rules remain required.
- Direct invocation of a discovered native `opencode.exe` may be considered if it materially simplifies deterministic stdin/process behavior, but hard-coded installation paths are forbidden and the installed wrapper must remain supported unless evidence shows it is unsafe.
- Antigravity may continue using `cmd.exe /d /s /c ... < NUL` as a local IDE workaround, but repository scripts must not encode Antigravity-specific behavior as a correctness dependency.

## Non-goals

- No model fallback routing; that is `agent-model-fallback-routing-v1-1`.
- No retries after a semantic BLOCK.
- No parallel reviewers or reviewer voting/racing.
- No Gemini self-review as a normal independent Gate PASS.
- No user pause/amend/resume control plane.
- No shared generalized process framework extraction.
- No production/game behavior changes.
- No custom timer/plugin solely to simulate a six-minute clock.
- No requirement to eliminate the shared OpenCode service for interactive developer use; isolation applies to formal Scout/Gate automation.

## Provisional acceptance criteria

1. Scout contract clearly encodes the tighter file/output/early-stop policy without losing required ownership/control-flow/test/risk evidence.
2. Spec/regression reviewer PASS outputs are materially shorter and blocker-first while preserving valid BLOCK detail.
3. Real role runs normally converge materially earlier than the 480-second timeout.
4. Scout uses an evidence-backed native step budget, initially 6; reviewer roles initially use 5.
5. Read-only permissions are expressed in V2 rules and real probes demonstrate that shell/code execution and repository mutation are unavailable.
6. Formal Scout/Gate OpenCode jobs use isolated standalone execution with explicit repository working directory and deterministic non-interactive stdin handling.
7. Killing/timing out a standalone OpenCode client leaves no private-server orphan process.
8. `scripts/ai_scout.ps1 -Task <id>` and `scripts/ai_gate.ps1 -Task <id>` remain compatible.
9. Gate 0/1/2 classification and canonical artifact safety remain unchanged.
10. No game/runtime files change.
11. Durable workflow docs are updated to describe local agents as bounded first-pass evidence providers and ChatGPT as the deeper analysis/final-review layer.
12. Runtime probes preserve pre-existing unrelated working-tree state and introduce zero new status delta after cleanup.
13. A representative post-change Scout run successfully produces structurally valid `CONTEXT.md`; a representative Gate run produces valid structured reviewer output without requiring Antigravity-specific shell rules.

## Bootstrap note before Final SPEC

This task initially could not obtain canonical Scout evidence because the current Scout itself is one of the components being hardened and timed out at the 480-second bound. Runtime probes have now established a safe bounded configuration (`steps`, V2 read-only permissions, standalone lifecycle). Before promoting this SPEC to Final, run Scout once using a **temporary local bootstrap override** of the Scout agent contract that applies the verified bounded settings without committing production implementation:

- use `steps: 6`;
- use V2 read-only permissions with only `read` / `glob` / `grep` allowed;
- tighten the Scout prompt to the provisional 5-6 file / 600-800 word / early-stop policy;
- invoke through the existing `ai_scout.ps1` path, with a temporary local invocation adjustment only if needed to supply `--standalone` / explicit process isolation;
- restore all temporary local agent/script changes immediately after the run;
- commit/push only the resulting canonical `CONTEXT.md` if structurally valid;
- verify before/after working-tree delta contains no leftover bootstrap modifications.

This bootstrap exception exists only to resolve the self-hosting dependency of the Scout-hardening task. It must not become a general lifecycle shortcut.

## Remaining uncertainty before Final

1. Whether `steps: 6` gives Scout enough repository evidence on this real task while remaining concise.
2. Whether `steps: 5` is sufficient for both reviewer roles on real candidate diffs; this may be finalized as an implementation-time calibration requirement if Scout finds no stronger evidence.
3. Whether the repository scripts should invoke the npm PowerShell wrapper or discovered native binary after explicit WorkingDirectory/stdin/standalone isolation is added; portability and testability should decide, not convenience.
4. Whether any non-mutating OpenCode permission beyond `read` / `glob` / `grep` is genuinely required by Scout/reviewers.
