# agent-model-fallback-routing-v1-1

Status: Final

## Goal

Add bounded, deterministic, role-specific model fallback to formal Scout and Gate execution so genuine model/provider infrastructure failures can recover without weakening semantic authority, enabling review-shopping, or multiplying the existing timeout into an unbounded workflow.

No game/runtime behavior is in scope.

## Verified current state

Scout evidence confirms:

- `ai_scout.ps1` resolves one scalar model and performs one isolated OpenCode invocation; any infrastructure failure terminates Scout.
- `ai_gate.ps1` resolves one scalar review model; each reviewer gets one invocation, and infrastructure failure currently aborts the reviewer sequence.
- Gate already has the correct narrow classification boundaries: process timeout/non-zero exit, structured transport extraction, canonical payload extraction, verdict structure validation, and semantic PASS/BLOCK.
- Existing task descriptors use scalar `models.scout` / `models.review`.
- Gate already exposes a reusable bounded-process primitive and deterministic executable/argument override seams; Scout has equivalent lifecycle behavior inline.
- Existing canonical artifact promotion and Gate rollback semantics must remain unchanged.

## Scope

Production change surface is limited to:

- `scripts/ai_scout.ps1`
- `scripts/ai_gate.ps1`
- `docs/architecture/ai_development_workflow.md`
- `docs/tasks/<task-id>/task.json` model metadata consumption contract
- small deterministic/runtime probes needed to verify fallback routing, time bounds, provenance, and artifact safety

`.opencode/agents/*` role contracts are out of scope. Their permissions, step budgets, and responsibility boundaries must not be loosened.

## Invariants

1. Scout remains evidence-only; ChatGPT + user own and finalize `SPEC.md`.
2. Gemini/Antigravity remains the sole production implementation writer after Final SPEC.
3. Spec reviewer and regression reviewer remain separate, sequential, read-only roles.
4. A structurally valid reviewer PASS or BLOCK is terminal for that reviewer. No later candidate may be tried after either result.
5. A structurally valid Scout report is terminal and is promoted exactly once.
6. Gate public outcomes remain `0=PASS`, `1=INFRASTRUCTURE_BLOCKED`, `2=CANDIDATE_BLOCKED`.
7. Candidate semantic BLOCK and focused-test failure are candidate failures, never fallback triggers.
8. Formal invocations retain `--standalone`, explicit repository working directory, closed stdin, stdout/stderr observability, bounded termination, and kill confirmation.
9. Canonical `CONTEXT.md`, `reviews/*`, and `EVIDENCE.md` remain transaction-safe. Failed infrastructure attempts must never partially promote canonical role output.
10. Fallback ordering is deterministic and role-specific. No voting, racing, randomization, quality scoring, or verdict comparison.
11. Provider credentials remain local and must never be committed.
12. Attempt provenance must identify ordered candidate/model, outcome classification, elapsed time, and selected successful attempt without exposing credentials or promoting raw failed output.
13. Existing single-model task descriptors remain valid.
14. No game/runtime behavior changes.

## Required behavior

### 1. Model metadata contract

`task.json.models.scout` and `task.json.models.review` become backward-compatible scalar-or-array fields:

```json
{
  "models": {
    "scout": ["model-a", "model-b"],
    "review": ["model-a", "model-b"]
  }
}
```

A scalar string remains equivalent to a one-element ordered candidate list. Do not introduce parallel `*_candidates` fields or a generalized provider/router object; model policy must have one source per role.

Candidate lists must be finite, ordered, non-empty after normalization, and contain non-blank model identifiers. Invalid configured metadata is a configuration/infrastructure error and must not silently fall back to an implicit model.

### 2. CLI override semantics

Existing `-Model` and `-ReviewModel` remain strict single-model overrides.

If supplied, the explicit CLI model replaces the configured candidate chain with exactly one candidate. This preserves current operator expectations and makes manual debugging deterministic. This task does not add a chain-valued CLI syntax.

Existing internal executable/argument override seams must continue to work for deterministic probes. A minimal additional internal seam is allowed only if needed to deterministically exercise multiple candidate attempts without live providers; it must not become public workflow policy.

### 3. Fallback eligibility

Fallback is permitted only after an attempt is classified as infrastructure failure at an existing mechanical boundary.

Eligible examples:

- process launch/provider failure;
- timeout with confirmed termination;
- non-zero model-process exit;
- empty/unusable Scout output;
- malformed structured reviewer transport;
- canonical review payload extraction failure;
- invalid/missing required reviewer verdict structure.

A timeout whose process termination cannot be confirmed is terminal infrastructure failure: do not launch another candidate while ownership of the previous process is uncertain.

Fallback is forbidden after:

- structurally valid Scout output;
- structurally valid reviewer PASS;
- structurally valid reviewer BLOCK;
- focused-test failure;
- artifact-promotion failure;
- any already-classified candidate/semantic result.

No model may reinterpret another model's prose to decide fallback eligibility.

### 4. Gate routing boundary

Fallback belongs inside each reviewer role invocation, not around the entire Gate.

For each reviewer in the existing sequential order:

```text
reviewer role
  -> candidate 1
     -> valid PASS/BLOCK: terminal for this reviewer
     -> eligible infrastructure failure: candidate 2 if budget remains
  -> candidate N
  -> exhausted / budget exhausted: INFRASTRUCTURE_BLOCKED
```

Only after one reviewer obtains a valid terminal result may Gate proceed to the next reviewer. A valid BLOCK remains terminal evidence and must not invoke another model.

Focused tests remain outside model fallback routing and run only under the existing Gate conditions.

### 5. Time budget

The existing public `TimeoutSeconds` / `ReviewTimeoutSeconds` value remains the maximum wall-clock budget for one role execution, including all fallback attempts for that role. Default remains 480 seconds.

It is no longer multiplied per candidate.

Before each attempt, compute the remaining role budget. Pass only that remaining duration to the bounded process invocation. Do not start another candidate when no positive usable budget remains.

Therefore:

- Scout: one 480-second total Scout routing budget by default.
- Gate: each reviewer independently receives one 480-second total reviewer routing budget by default, preserving the existing sequential reviewer timeout expectation while preventing candidate multiplication.

No separate configurable per-attempt timeout, exponential backoff, daemon, or parallel race is introduced in v1.1. A candidate may consume the whole remaining role budget; fallback is best-effort within the same safety wall.

### 6. Attempt provenance

Each attempted candidate must produce compact provenance containing at least:

- role / reviewer identity;
- 1-based attempt index;
- model identifier;
- elapsed seconds;
- normalized outcome classification/reason;
- whether it produced the selected canonical result.

Raw stdout/stderr from failed attempts remains under ignored `.runtime/` diagnostics and must not be copied wholesale into tracked evidence.

For Scout, successful command output should make the selected attempt and preceding fallback failures operator-visible; tracked `CONTEXT.md` remains only the validated Scout report, not a provenance wrapper.

For Gate, compact attempt provenance must be included in `EVIDENCE.md` so a PASS/BLOCK can be audited against the model that actually produced each reviewer result. Existing canonical `reviews/*.md` remain only validated reviewer payloads.

No secrets, tokens, environment values, or credential material may be recorded.

### 7. Gemini independence boundary

This task does not add Gemini/Antigravity as a normal Gate reviewer fallback.

The configured Gate review candidate chain must represent independent read-only reviewer models. The production routing mechanism remains model-name based and does not attempt unreliable provider-identity inference from arbitrary strings.

If an operator explicitly configures a Gemini/Antigravity implementation model as a Gate reviewer, that configuration is outside the supported normal-PASS contract: it must not be documented or represented as independent Gate evidence.

Gemini may be used manually for degraded Scout/advisory evidence, but degraded self-review is not promoted to normal Gate PASS by this task. Automated degraded-Gemini Gate semantics are deferred rather than adding a new exit code or fragile model-name blacklist.

### 8. Scout implementation shape

Scout currently owns its process lifecycle inline. Refactoring that lifecycle into a small bounded attempt helper is allowed and preferred if it avoids duplicating timeout/kill/streaming logic across fallback attempts.

This is a local script refactor only. Do not introduce a generalized process framework shared across the repository solely for this task.

### 9. Documentation

`docs/architecture/ai_development_workflow.md` must document:

- scalar-or-array ordered model metadata;
- strict single-model CLI override semantics;
- infrastructure-only fallback;
- semantic PASS/BLOCK terminality and no review-shopping;
- 480-second default total budget per role, not per candidate;
- provenance behavior;
- Gate independence requirement and unsupported Gemini self-review as normal PASS;
- unchanged 0/1/2 Gate outcome semantics.

## Acceptance criteria

1. Existing scalar `models.scout` and `models.review` configurations still execute as one-candidate routes.
2. Ordered arrays execute candidates in declared order.
3. CLI `-Model` / `-ReviewModel` replaces the configured chain with one explicit candidate.
4. Scout falls back after a deterministic simulated eligible infrastructure failure and promotes the first structurally valid Scout result exactly once.
5. Scout does not invoke later candidates after valid output.
6. Each Gate reviewer independently falls back after eligible infrastructure failure without restarting or skipping the other reviewer role.
7. Valid reviewer PASS invokes no later candidate for that reviewer.
8. Valid reviewer BLOCK invokes no later candidate and preserves exit code 2 semantics.
9. Exhausting candidates or exhausting the total role budget yields infrastructure-blocked behavior and preserves prior canonical artifacts according to existing Scout/Gate safety rules.
10. Unconfirmed process termination is terminal infrastructure failure and never launches another candidate.
11. Total elapsed routing is bounded by the existing role timeout rather than `timeout × candidate_count`, allowing only normal small process/cleanup overhead.
12. Provenance identifies every attempted model, order, elapsed time, failure reason, and selected result; Gate persists compact provenance in `EVIDENCE.md` while failed raw logs remain runtime-only.
13. Malformed reviewer transport/payload/header can trigger fallback mechanically; semantic prose is never reinterpreted by another model.
14. Existing standalone isolation, working directory, closed stdin, streaming observability, kill confirmation, verdict parsing, focused-test behavior, transactional promotion/rollback, and exit codes remain intact.
15. Gate documentation requires independent reviewer candidates and does not claim Gemini/Antigravity self-review is a normal independent PASS.
16. Deterministic probes cover scalar compatibility, ordered fallback, semantic terminality, chain exhaustion, total-budget exhaustion, and artifact safety without requiring live provider failure.
17. Verification leaves no disposable probe pollution and changes no game/runtime files.

## Required verification

Use existing internal override seams plus at most one small additional internal routing seam where necessary. Do not introduce a generalized PowerShell test framework solely for this task.

At minimum verify:

- scalar model normalization;
- ordered array normalization and order preservation;
- strict CLI single-model override;
- first-attempt infrastructure failure followed by second-attempt success;
- valid PASS stops reviewer fallback;
- valid BLOCK stops reviewer fallback and remains candidate-blocked;
- malformed reviewer output can fall through to the next candidate;
- candidate exhaustion returns infrastructure-blocked and leaves prior canonical artifacts untouched;
- role budget is shared across attempts and prevents starting a candidate after exhaustion;
- unconfirmed termination prevents fallback;
- Gate `EVIDENCE.md` records compact provenance for fallback attempts;
- failed raw output remains runtime-only;
- promotion rollback and focused-test behavior remain unchanged;
- before/after git status delta contains no disposable probe pollution.

AI agents must not run the repository full test suite. User-owned branch completion/full-suite rules remain unchanged.

## Non-goals

- retrying or overriding semantic BLOCK;
- reviewer voting, consensus, racing, or parallel reviewers;
- autonomous implementation repair loops;
- model quality scoring or dynamic benchmark routing;
- cost optimization beyond deterministic ordered fallback;
- provider credential management or installation automation;
- public chain-valued CLI syntax;
- automatic provider-family inference or Gemini string blacklists;
- Gemini/Antigravity self-review as normal independent Gate PASS;
- a new Gate exit code for degraded advisory review;
- changing Scout/reviewer permissions or step budgets;
- pause/amend/resume workflow control plane;
- generalized shared process-framework extraction;
- production/game behavior changes.
