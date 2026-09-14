# agent-role-contract-hardening-v1-1

Status: Draft

## Goal

Make local OpenCode Scout/reviewer roles intentionally fast, concise, scope-disciplined, and genuinely read-only. Local free models should provide enough first-pass evidence for ChatGPT to perform the deeper architecture/specification/final review, rather than attempting an exhaustive repository audit themselves.

## Observed problem

The current Scout is already bounded but still allows up to 10 files and targets up to 1500 words. The current reviewers encourage broad/exhaustive coverage: the spec reviewer asks for per-clause coverage, while the regression reviewer asks for callers/callees/sibling paths/state/timing/dead logic/testability/architecture drift. Real runs showed useful analysis but also format drift and long exploratory loops that reached the 480-second hard timeout.

The current agent frontmatter also uses `permission` / `bash` / `task` style controls, while an observed reviewer run still gained an `execute`-style capability despite the intended read-only contract. The exact OpenCode v2 permission/step behavior must be verified before Final SPEC.

## Scope

Provisional change surface:

- `.opencode/agents/scout.md`
- `.opencode/agents/spec-reviewer.md`
- `.opencode/agents/regression-reviewer.md`
- `scripts/ai_scout.ps1`
- `scripts/ai_gate.ps1`
- `docs/architecture/ai_development_workflow.md` if durable workflow semantics change
- focused deterministic probes/config validation needed to prove role limits and read-only behavior

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
9. Read-only agents must not gain a repository-mutating shell/code-execution/subagent capability through an unguarded OpenCode permission path.
10. This task changes workflow/tooling behavior only; production/game behavior must remain unchanged.

## Provisional target behavior

### Scout

- First-pass localization, not exhaustive audit.
- Target about 5-6 directly relevant files; absolute ceiling 8.
- Target 600-800 words; hard output ceiling 1000 words where enforceable by contract/probe.
- Stop once ownership/control flow/relevant tests/material risks/minimal surface are sufficiently localized.
- Put unproven items in `Uncertainty` rather than expanding the audit.

### Reviewers

- Preserve two sequential roles: `spec-reviewer` and `regression-reviewer`.
- Operate as bounded blocker detectors, not exhaustive proof engines.
- PASS output should normally be about 300-600 words: required header, compact coverage summary, `Blocking findings: None`, and only a small number of advisories/evidence gaps.
- BLOCK may expand only concrete blocking findings needed to support the verdict.
- Stop exploring once enough grounded evidence exists to return PASS/BLOCK within the role boundary.
- Avoid exhaustive PASS tables, repository-history archaeology, broad sibling traversal, and low-value prose.

### Convergence controls

Investigate and, only if supported by the installed OpenCode runtime, use native controls such as an agent step/tool-call budget that forces final text generation before the external 480-second hard timeout. Initial calibration target is approximately 5-7 model steps, not a fixed architectural constant. The desired operating result is normal completion around 2-4 minutes per reviewer and well before the hard timeout.

A prompt-only statement such as "finish within 6 minutes" is not sufficient by itself because the model may not have reliable wall-clock awareness.

### Read-only boundary

Verify the actual OpenCode v2 permission schema and runtime behavior. Prefer the narrowest practical default-deny/read-search-only contract. Explicitly prove that edit, shell/code execution, subagent/task, web, and external-directory mutation paths cannot be used by Scout/reviewers.

## Non-goals

- No model fallback routing; that is `agent-model-fallback-routing-v1-1`.
- No retries after a semantic BLOCK.
- No parallel reviewers or reviewer voting/racing.
- No Gemini self-review as a normal independent Gate PASS.
- No user pause/amend/resume control plane.
- No shared generalized process framework extraction.
- No production/game behavior changes.

## Provisional acceptance criteria

1. Scout contract clearly encodes the tighter file/output/early-stop policy without losing required ownership/control-flow/test/risk evidence.
2. Spec/regression reviewer PASS outputs are materially shorter and blocker-first while preserving valid BLOCK detail.
3. Representative real/deterministic role probes show normal convergence materially earlier than the 480-second timeout.
4. If OpenCode supports a native `steps`/equivalent limit, its actual installed-runtime semantics are verified and calibrated; if not, the Final SPEC documents the supported alternative rather than assuming it.
5. Read-only permissions are proven against the installed OpenCode runtime, including the previously observed `execute`-style path.
6. No local reviewer can mutate tracked repository content or launch an unrestricted child/subagent through the configured role.
7. `scripts/ai_scout.ps1 -Task <id>` and `scripts/ai_gate.ps1 -Task <id>` remain compatible.
8. Gate 0/1/2 classification and canonical artifact safety remain unchanged.
9. No game/runtime files change.
10. Durable workflow docs are updated only for verified final semantics, not provisional OpenCode assumptions.

## Uncertainty / Scout questions

1. What exact permission keys/schema does the installed OpenCode 2.0.3 runtime honor for custom agents, and why did the observed reviewer obtain an `execute` capability despite the intended read-only configuration?
2. Does the installed runtime support an agent-level `steps` or equivalent max-step/finalization control in the repository agent frontmatter, and what happens on the last step?
3. What step budget gives Mimo and Big Pickle enough evidence to produce a valid Scout/reviewer result without reintroducing timeout risk?
4. Which output constraints can be made reliably enforceable by contract/runtime versus merely advisory prose targets?
5. Are script invocation changes required to activate these controls, or are agent-definition changes sufficient?
6. What focused probes provide convincing evidence without turning this task into a generalized OpenCode test framework?
