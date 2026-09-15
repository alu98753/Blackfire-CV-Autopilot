# agent-model-fallback-routing-v1-1

Status: Draft

## Goal

Add bounded, role-specific model fallback for the Blackfire AI workflow so Scout and Gate can recover from genuine model/provider infrastructure failures without weakening semantic review authority, enabling review-shopping, or making model availability part of repository correctness.

## Problem statement

The hardened workflow now gives Scout/reviewers bounded read-only roles, isolated OpenCode processes, strict timeout handling, and transactional artifact promotion. However, each formal role invocation still resolves to one model (`task.json.models.scout` / `task.json.models.review` or a CLI override). If that model/provider is unavailable, times out, crashes, or otherwise fails infrastructurally, the whole Scout/Gate attempt stops even when another compatible low-cost model could provide the same bounded role.

The next roadmap slice should add fallback only at this infrastructure boundary. It must not retry a valid semantic result merely because another model might be more favorable.

No game/runtime behavior is in scope.

## Scope

Provisional production change surface:

- `scripts/ai_scout.ps1`
- `scripts/ai_gate.ps1`
- task model-routing metadata consumed from `docs/tasks/<task-id>/task.json`
- `docs/architecture/ai_development_workflow.md`
- small deterministic/runtime verification probes or focused tests needed to prove routing, classification, timing bounds, provenance, and artifact safety

Agent role contracts under `.opencode/agents/` are out of scope unless Scout evidence proves a minimal compatibility/documentation adjustment is required. Their read-only permissions and step budgets must not be loosened.

## Known invariants

1. Scout remains evidence-only; ChatGPT + user own and finalize `SPEC.md`.
2. Gemini/Antigravity remains the sole production implementation writer after Final SPEC.
3. Spec reviewer and regression reviewer remain separate sequential read-only roles.
4. A syntactically valid reviewer `VERDICT: PASS|BLOCK` with structurally valid `BLOCKING_FINDINGS` is a semantic terminal result for that reviewer attempt. Fallback must not be used to shop for a different verdict.
5. Gate public process outcomes remain `0=PASS`, `1=INFRASTRUCTURE_BLOCKED`, `2=CANDIDATE_BLOCKED` unless Final SPEC explicitly proves a compatible extension is necessary.
6. Candidate semantic BLOCK and focused-test failure remain candidate failures, not infrastructure failures.
7. Formal invocations retain standalone process isolation, explicit repo working directory, closed stdin, stdout/stderr observability, bounded termination, and no dependence on Antigravity shell state.
8. Existing canonical `CONTEXT.md`, `reviews/*`, and `EVIDENCE.md` must remain transaction-safe: infrastructure failure must not partially promote a failed attempt.
9. Local reviewer/Scout roles remain genuinely read-only and bounded by their existing role contracts.
10. Fallback ordering must be deterministic and role-specific; model/provider credentials remain local configuration and must never be committed.
11. Total fallback execution must be bounded. A fallback chain must not multiply the existing 480-second safety wall into an effectively unbounded workflow.
12. Attempt provenance must be observable enough to explain which model(s) were tried, why an attempt was classified as infrastructure failure, and which attempt produced the canonical artifact.
13. No game/runtime behavior changes.

## Provisional required behavior

### 1. Routing contract

Introduce an ordered model-candidate representation for Scout and review roles while preserving a reasonable compatibility path for existing single-model task metadata and explicit command-line model selection.

The exact `task.json` schema and CLI override precedence are intentionally left for Scout evidence and Final SPEC. Avoid introducing a general provider/router framework if a small script-level routing contract is sufficient.

### 2. Fallback eligibility

Fallback is allowed only when the current model attempt fails for an infrastructure reason, such as launch/provider failure, timeout/termination failure, or unusable/malformed transport/output that cannot yield the role's required canonical structure.

Fallback is forbidden after:

- a structurally valid Scout report has been produced;
- a structurally valid reviewer PASS;
- a structurally valid reviewer BLOCK;
- a focused test failure;
- any other result already classified as candidate/semantic failure rather than infrastructure failure.

The implementation must classify failures at the narrowest existing boundary instead of asking another model to reinterpret prose.

### 3. Gate independence and Gemini degradation rule

Normal Gate PASS must continue to represent independent read-only reviewer evidence about the Gemini/Antigravity implementation.

If Gemini is ever configured as a fallback model, it may provide degraded Scout/advisory evidence when normal local infrastructure is unavailable, but it must not masquerade as a normal independent Gate PASS for implementation produced by Gemini/Antigravity itself. The exact representation/terminal behavior for this degraded path is an explicit uncertainty to resolve before Final SPEC.

### 4. Time budget

The fallback chain must have a bounded total wall-clock policy in addition to per-attempt termination. The Final SPEC must define whether the current 480-second timeout is a total role budget, an attempt cap within a separate total budget, or another simple bounded policy.

Do not add background retry daemons, unbounded exponential retry, or parallel model racing.

### 5. Provenance

Formal Scout/Gate diagnostics and/or tracked evidence must make fallback attempts auditable without leaking credentials. At minimum the design should preserve ordered attempt identity, outcome classification, elapsed time, and selected successful attempt where appropriate.

Canonical artifacts must contain only validated promoted output; raw failed-attempt diagnostics should remain under ignored runtime storage unless Final SPEC identifies a durable evidence need.

## Provisional acceptance criteria

1. Scout and each Gate reviewer can deterministically try an ordered role-specific fallback model after a simulated infrastructure failure.
2. A valid Scout result terminates routing immediately and is promoted exactly once.
3. A valid reviewer PASS terminates that reviewer routing immediately; no later model is invoked.
4. A valid reviewer BLOCK terminates that reviewer routing immediately and preserves `CANDIDATE_BLOCKED` semantics; no later model is invoked.
5. Timeout, process-launch failure, non-zero infrastructure exit, and malformed required output are classified consistently enough to drive fallback without semantic reinterpretation.
6. Exhausting all eligible model candidates produces the existing infrastructure-blocked outcome and preserves prior canonical artifacts.
7. Total fallback wall-clock is explicitly bounded and verified with deterministic process seams; no fallback sequence can expand without a configured finite bound.
8. Attempt provenance records model/candidate identity, order, elapsed time, and infrastructure-failure reason without secrets.
9. Existing single-model task configuration and useful CLI override seams either remain backward compatible or receive an explicit migration path documented by the Final SPEC.
10. Standalone process isolation, read-only agent contracts, Gate header parsing, focused-test semantics, artifact promotion/rollback, and timeout kill-confirmation behavior remain intact.
11. Gemini fallback cannot yield a misleading normal independent Gate PASS for Gemini/Antigravity-authored production implementation.
12. Architecture workflow documentation matches the implemented fallback semantics.
13. Verification introduces no game/runtime changes and leaves no disposable probe pollution.

## Uncertainty / questions for Scout

1. What is the smallest schema extension that supports ordered role-specific candidates without creating two competing sources of model policy? Should compatibility accept both scalar and array forms, or should a new explicit field be introduced?
2. What should CLI `-Model` / `-ReviewModel` mean once a fallback chain exists: strict single-model override, first candidate override, or a separate explicit chain override?
3. Which current `ai_gate.ps1` failure branches already distinguish malformed output, non-zero exit, timeout, termination failure, and semantic BLOCK, and where is the safest single fallback loop boundary?
4. Should the 480-second value become the total role budget, or should there be a separate total budget with smaller per-attempt caps? What preserves current operator expectations with the least complexity?
5. Where should attempt provenance live so normal evidence is auditable without promoting noisy failed raw output?
6. How can a Gemini degraded fallback be represented so Scout/advisory usefulness is retained while Gate independence is never falsely claimed?
7. Are there existing deterministic override seams sufficient to test multi-attempt routing, or is one small additional seam required?

## Non-goals

- retrying or overriding semantic BLOCK;
- reviewer voting, majority consensus, racing, or parallel reviewers;
- autonomous implementation repair loops;
- model quality scoring or dynamic benchmark-based routing;
- cost optimization beyond deterministic ordered fallback;
- provider credential management or installation automation;
- changing Scout/reviewer responsibility boundaries or permissions;
- pause/amend/resume workflow control plane;
- production/game behavior changes.
