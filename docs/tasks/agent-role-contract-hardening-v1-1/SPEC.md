# agent-role-contract-hardening-v1-1

Status: Final

## Goal

Make local OpenCode Scout/reviewer roles intentionally fast, concise, scope-disciplined, deterministic to invoke, and genuinely read-only. Local free models provide bounded first-pass evidence; ChatGPT + user retain contract ownership and deeper architecture/final semantic review; Gemini/Antigravity remains the production implementation writer after this Final SPEC.

## Problem statement

Current local-role contracts and invocation paths are safe against indefinite hangs but are still too permissive and slow:

- Scout allows up to 10 files / 1500 words and has no native step budget.
- Reviewers encourage broad/exhaustive exploration and have no native step budget.
- Agent frontmatter uses legacy permission syntax.
- Scout budget numbers are duplicated in both the agent contract and `ai_scout.ps1` prompt, creating drift risk.
- Formal Scout/Gate runs depend on default OpenCode service/process behavior rather than an explicit isolated invocation contract.
- Real Mimo runs reached the 480-second hard timeout before this task; a bounded bootstrap Scout using `steps: 6` completed in about 139 seconds and produced valid canonical context.

No game/runtime behavior is in scope.

## Verified runtime evidence

All of the following were verified locally on OpenCode 2.0.3 before Finalization:

1. Agent config supports positive integer `steps`.
2. V2 agent config supports ordered `permissions` rules of `{ action, resource, effect }`.
3. Legacy `permission` / `bash` / `task` is compatibility-mapped, but V2 rules are clearer and are the target representation.
4. A `steps: 2` probe showed final-step tool calls are rejected with `Tools are disabled after the maximum agent steps`, after which the model still emitted usable final text and exited 0.
5. A V2 read-only probe with broad deny plus narrow `read` / `glob` / `grep` allows loaded `execute: deny`; shell/code execution was not exposed and no side effect occurred.
6. A `--standalone` lifecycle probe showed the private child/server exits with the client and leaves no orphan PID when the client is killed.
7. Antigravity finite-command smoke tests succeeded with `cmd.exe /d /s /c ... < NUL`; that is an IDE workaround only, not a repository correctness dependency.
8. A bounded bootstrap Scout using Mimo + `steps: 6` completed in about 139 seconds versus the prior 480-second timeout and produced valid `CONTEXT.md`.

## Scope

Production change surface is limited to:

- `.opencode/agents/scout.md`
- `.opencode/agents/spec-reviewer.md`
- `.opencode/agents/regression-reviewer.md`
- `scripts/ai_scout.ps1`
- `scripts/ai_gate.ps1`
- `docs/architecture/ai_development_workflow.md`
- small deterministic/runtime verification probes only where needed to prove this SPEC

`task.json` may be updated only if needed to reflect focused verification metadata; no model fallback policy belongs in this task.

## Invariants

1. Scout remains evidence-only and never owns/finalizes `SPEC.md`.
2. Spec reviewer and regression reviewer remain separate sequential read-only roles.
3. Gemini/Antigravity remains the sole production implementation writer after Final SPEC.
4. ChatGPT + user remain contract owners; ChatGPT remains final semantic/architecture reviewer.
5. Gate semantic contract remains `VERDICT: PASS|BLOCK` + `BLOCKING_FINDINGS`.
6. Gate process outcomes remain 0=PASS, 1=INFRASTRUCTURE_BLOCKED, 2=CANDIDATE_BLOCKED.
7. A real semantic BLOCK must never be weakened merely to shorten output.
8. Uncertainty is preferred over open-ended exploration when local evidence budget is exhausted.
9. External 480-second timeout remains the hard wall-clock safety boundary.
10. `steps` is an agentic-iteration convergence bound, not a wall-clock replacement.
11. Local roles must not gain repository-mutating edit/shell/code-execution/subagent/web/external-directory capability.
12. Formal Scout/Gate automation must not depend on Antigravity Global Rules, interactive terminal state, shared OpenCode daemon state, inherited CWD, or open stdin for correctness.
13. Existing stdout/stderr observability, kill-confirmation behavior, Gate artifact safety, and transaction-safe promotion semantics remain intact.
14. Existing unrelated working-tree state must be preserved; verification compares before/after delta rather than assuming a globally clean tree.
15. No production/game behavior changes.

## Required behavior

### 1. Scout contract

`scout.md` must:

- use explicit V2 `permissions`;
- use `steps: 6` initially;
- act as a first-pass localizer, not an exhaustive auditor;
- target 5-6 directly relevant files;
- stop at an absolute ceiling of 8 directly relevant files;
- target 600-800 words and remain <=1000 words by role contract;
- stop once owner/control-flow/tests/material risks/minimal surface are sufficiently localized;
- place unresolved items in `Uncertainty` rather than continuing broad exploration;
- avoid repository-history archaeology and proving every sibling-path non-problem that ChatGPT will independently re-check.

A post-change real Scout run may justify lowering `steps` to 5 if evidence quality remains sufficient. Raising above 6 requires concrete evidence that essential localization is being lost.

### 2. Reviewer contracts

Both reviewers must use `steps: 5` initially and explicit V2 read-only permissions.

They are bounded blocker detectors, not exhaustive proof engines.

PASS behavior:

- first two lines remain exactly the existing machine-readable header;
- normally 300-600 words total;
- compact coverage/behavior summary;
- `Blocking findings: None`;
- at most a small number of evidence-based advisories/evidence gaps;
- no exhaustive per-clause PASS tables or repository-history narrative.

BLOCK behavior:

- may expand only the concrete blocking findings required to justify the verdict;
- preserve falsifiable claim, location, evidence, validation suggestion, and confidence;
- stop after enough grounded blocker evidence exists.

Regression reviewer may inspect callers/siblings/state/timing only where they are the highest-risk reachable paths for the actual diff; broad traversal is not mandatory coverage.

A real Gate calibration may justify lowering reviewer `steps` to 4 if blocker detection and structured output remain adequate. Raising above 5 requires evidence.

### 3. Read-only permission boundary

All three local roles must migrate to explicit V2 `permissions` rules.

Required policy:

- broad deny by default;
- narrow allow only `read`, `glob`, `grep` unless a strictly necessary non-mutating capability is proven;
- explicit deny entries for critical boundaries including `edit`, `shell`, `subagent`, `execute`, `external_directory`, `webfetch`, and `websearch`.

Implementation verification must prove that a role asked to run a harmless command cannot execute it and introduces no repository/process side effect attributable to the role.

### 4. Scout prompt authority

The current duplicated Scout budget numbers in `scout.md` and `ai_scout.ps1` are a drift risk.

The production solution must make the agent role contract the canonical budget policy. `ai_scout.ps1` must not maintain a second independently editable copy of the concrete 5-6 / 8 / 600-800 / 1000 numbers.

The script prompt may say to follow the Scout contract and stop early, but concrete policy numbers must live in one authoritative surface unless implementation provides a real single-source mechanism.

### 5. Formal OpenCode invocation isolation

`ai_scout.ps1` and reviewer invocation in `ai_gate.ps1` must:

- use `opencode run --standalone` by default for formal jobs;
- explicitly set child `WorkingDirectory = $repoRoot`;
- make child stdin deterministically non-interactive/closed;
- preserve stdout/stderr streaming and existing timeout behavior;
- keep executable/argument override seams working;
- avoid hard-coded OpenCode installation paths.

Using the discovered npm PowerShell wrapper is acceptable if the above contract is satisfied. Direct native-binary discovery is not required and should not be added unless needed by evidence.

`--standalone` is for formal Scout/Gate automation only; this task does not remove or forbid shared OpenCode service use for interactive development.

### 6. Workflow documentation

`docs/architecture/ai_development_workflow.md` must reflect the durable responsibility model:

- local free agents = fast/bounded first-pass evidence and blocker detection;
- uncertainty over exhaustive exploration;
- ChatGPT + user = deeper contract/architecture analysis and final semantic review;
- Gemini/Antigravity = production implementation writer after Final SPEC;
- Scout initial bound: `steps: 6`, 5-6 target / 8 file ceiling, 600-800 target / 1000-word ceiling;
- reviewers remain two separate roles with initial `steps: 5` and concise/blocker-first output;
- formal Scout/Gate OpenCode execution is isolated/non-interactive and still protected by the 480-second hard timeout.

## Acceptance criteria

1. `scout.md` implements the Final Scout limits, `steps: 6`, early-stop semantics, and V2 read-only permissions.
2. `spec-reviewer.md` and `regression-reviewer.md` implement `steps: 5`, V2 read-only permissions, blocker-first output, and concise PASS behavior.
3. `ai_scout.ps1` no longer duplicates concrete Scout budget numbers as an independent policy surface.
4. `ai_scout.ps1 -Task <id>` remains compatible and formal Scout invocation uses standalone + explicit repo WorkingDirectory + closed/non-interactive stdin.
5. `ai_gate.ps1 -Task <id>` remains compatible and both reviewer invocations use the same isolated process boundary.
6. Existing Gate VERDICT parsing, 0/1/2 outcome semantics, focused-test behavior, canonical artifact preservation, promotion/rollback, and timeout classification remain unchanged.
7. Read-only runtime probe demonstrates shell/code execution is unavailable and no new working-tree/process side effect occurs.
8. Standalone timeout/lifecycle probe demonstrates no orphan private-server process remains after forced client termination.
9. A representative real Scout run with Mimo successfully produces structurally valid `CONTEXT.md` materially before 480 seconds; expected order of magnitude is the already observed ~139 seconds, not a strict SLA.
10. A representative real Gate run with the current preferred compatible reviewer model produces valid structured outputs from both reviewers without Antigravity-specific shell rules.
11. Reviewer PASS output is materially shorter than the previous exhaustive format while semantic BLOCK detail remains sufficient.
12. Architecture workflow documentation matches the implemented durable semantics.
13. Verification preserves pre-existing unrelated working-tree state and leaves zero new delta after disposable probes are cleaned up.
14. No game/runtime files change.

## Required verification

Use small deterministic/runtime probes and real smoke runs; do not introduce a generalized PowerShell test framework solely for this task.

At minimum verify:

- resolved agent configs show expected `steps` and V2 permission rules;
- forbidden command-execution attempt is unavailable;
- Scout step-bound finalization still yields valid final text;
- Scout script uses isolated process invocation and can produce valid `CONTEXT.md`;
- Gate reviewers use isolated process invocation and still satisfy header validation;
- forced standalone termination leaves no orphan server;
- override seams still work for bounded deterministic process tests;
- before/after git status delta contains no probe pollution.

AI agents must not run the repository full test suite. User-owned branch completion/full-suite rules remain unchanged.

## Non-goals

- model fallback routing (`agent-model-fallback-routing-v1-1` owns that);
- retry after semantic BLOCK;
- parallel reviewer execution, voting, or racing;
- Gemini self-review as a normal independent Gate PASS;
- human pause/amend/resume control plane;
- custom timer/plugin to simulate a six-minute wall-clock soft deadline;
- shared generalized process-framework extraction;
- new Pester/test-framework infrastructure solely for these scripts;
- eliminating shared OpenCode service for interactive developer use;
- production/game behavior changes.
