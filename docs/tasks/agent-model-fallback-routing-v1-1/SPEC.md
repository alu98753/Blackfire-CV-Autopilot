# agent-model-fallback-routing-v1-1

Status: Final

## Goal

Add deterministic, role-specific model fallback to formal Scout and Gate execution so temporary model/provider infrastructure failures do not become a single point of failure for the Blackfire Agent Workflow.

The normal path uses an ordered, configurable chain of independent reviewer models, with `opencode/mimo-v2.5-free` as the current default first candidate because it has been operationally stable. The architecture must not hard-code Mimo: candidate models are data/configuration passed into the routing logic and may be reordered or replaced later.

If all normal independent reviewer candidates fail infrastructurally, the workflow may use Gemini/Antigravity as an explicit last-resort degraded reviewer so useful evidence can still reach ChatGPT + user. Such evidence must be unmistakably marked low-confidence/non-independent and must never masquerade as a normal independent Gate PASS.

This task also qualifies candidate fallback models before placing them into the default production chain. Existing operational evidence makes `opencode/big-pickle` the first candidate to qualify, but prior ability to inspect a repository is not by itself evidence that it can reliably satisfy the formal Scout or Gate output contracts.

No game/runtime behavior is in scope.

## Verified current state

Scout evidence confirms:

- `ai_scout.ps1` resolves one scalar model and performs one isolated OpenCode invocation; any infrastructure failure terminates Scout.
- `ai_gate.ps1` resolves one scalar review model; each reviewer gets one invocation, and infrastructure failure currently aborts the reviewer sequence.
- Gate already has narrow mechanical classification boundaries for timeout/non-zero exit, structured transport extraction, canonical payload extraction, verdict structure validation, and semantic PASS/BLOCK.
- Existing task descriptors use scalar `models.scout` / `models.review`.
- Gate already exposes a reusable bounded-process primitive and deterministic executable/argument override seams; Scout has equivalent lifecycle behavior inline.
- Existing canonical artifact promotion and Gate rollback semantics must remain unchanged.
- `opencode/mimo-v2.5-free` has repeated real workflow evidence across Scout/Gate and remains the current default first candidate.
- `opencode/big-pickle` has useful prior repository-inspection/Scout-like evidence, but its reliability against the formal structured Scout and reviewer contracts is not yet established. It is a qualification candidate, not an assumed production fallback.

## Scope

Production change surface is limited to:

- `scripts/ai_scout.ps1`
- `scripts/ai_gate.ps1`
- `docs/architecture/ai_development_workflow.md`
- `docs/tasks/<task-id>/task.json` model-routing metadata consumption contract
- `docs/tasks/BACKLOG.md` retrospective calibration note
- small deterministic/runtime probes needed to verify fallback routing, timeout semantics, provenance, degraded evidence, artifact safety, and candidate qualification

`.opencode/agents/*` role contracts are out of scope unless implementation proves a minimal compatibility change is strictly required. Their permissions, step budgets, and responsibility boundaries must not be loosened.

## Invariants

1. Scout remains evidence-only; ChatGPT + user own and finalize `SPEC.md`.
2. Gemini/Antigravity remains the sole production implementation writer after Final SPEC.
3. Spec reviewer and regression reviewer remain separate, sequential, read-only roles.
4. A structurally valid reviewer PASS or BLOCK is terminal for that reviewer. No later normal candidate or degraded reviewer may be tried after either result.
5. A structurally valid Scout report is terminal and is promoted exactly once.
6. Candidate semantic BLOCK and focused-test failure are candidate failures, never fallback triggers.
7. Formal invocations retain `--standalone`, explicit repository working directory, closed stdin, stdout/stderr observability, bounded termination, and kill confirmation.
8. Canonical `CONTEXT.md`, `reviews/*`, and `EVIDENCE.md` remain transaction-safe. Failed infrastructure attempts must never partially promote canonical role output.
9. Fallback ordering is deterministic and role-specific. No voting, racing, randomization, quality scoring, or verdict shopping.
10. Provider credentials remain local and must never be committed.
11. Attempt provenance must identify ordered candidate/model, outcome classification, elapsed time, and selected result without exposing credentials or promoting raw failed output.
12. Existing single-model task descriptors remain valid.
13. Mimo is a configurable current default, not a code-level dependency or special case.
14. Every model attempt receives the full configured per-attempt timeout. Fallback latency may therefore grow linearly with the number of attempted candidates; this is an accepted v1.1 reliability-over-latency tradeoff.
15. A degraded Gemini review is explicitly non-independent/low-evidence and cannot be represented as a normal independent Gate PASS.
16. ChatGPT + user remain final semantic/architecture review authority after Gate evidence, including degraded evidence.
17. A model is not admitted to the default normal fallback chain merely because it is available or can read code. It must first demonstrate role-contract compatibility under the qualification rules in this SPEC.
18. Qualification is role-specific. A model may qualify for Scout without qualifying for Gate review, or vice versa.
19. No game/runtime behavior changes.

## Required behavior

### 1. Normal model metadata contract

`task.json.models.scout` and `task.json.models.review` become backward-compatible scalar-or-array fields:

```json
{
  "models": {
    "scout": [
      "opencode/mimo-v2.5-free",
      "qualified-fallback-model"
    ],
    "review": [
      "opencode/mimo-v2.5-free",
      "qualified-fallback-model"
    ]
  }
}
```

A scalar string remains equivalent to a one-element ordered candidate list.

Mimo is the current recommended/default first candidate because of observed response stability, but routing code must treat it exactly like any other model identifier. Future changes to default model/order must be configuration changes, not routing-code changes.

Do not introduce parallel normal-policy fields such as `review_candidates` in addition to `models.review`. Candidate lists must be finite, ordered, non-empty after normalization, and contain non-blank identifiers. Invalid configured metadata is an infrastructure/configuration error and must not silently choose an implicit model.

Only models that have passed the role-specific qualification gate defined below may be added to the repository's recommended/default normal fallback chain. Arbitrary task-local explicit model configuration remains possible for experimentation, but it must not be documented as a qualified default without evidence.

### 2. Degraded reviewer metadata

The last-resort degraded reviewer is a separate policy from the normal independent candidate chain because its evidence semantics are different.

Allow an optional explicit configuration under `models`, for example:

```json
{
  "models": {
    "review": [
      "opencode/mimo-v2.5-free",
      "qualified-fallback-model"
    ],
    "degraded_review": "gemini"
  }
}
```

The implementation may choose the smallest concrete identifier/configuration shape compatible with the existing local invocation mechanism, but it must preserve these semantics:

- degraded review is optional and explicit;
- it is attempted only after every normal independent reviewer candidate for that reviewer role has failed for eligible infrastructure reasons;
- it is never mixed into the normal candidate list;
- it must be recorded as `DEGRADED`, `LOW_EVIDENCE`, and `NOT_INDEPENDENT` (or equivalently unambiguous canonical labels);
- absence/unavailability/failure of the degraded reviewer falls back to the existing infrastructure-blocked outcome.

Do not infer degraded status from arbitrary model-name substring matching. The policy distinction must come from explicit configuration/routing position.

### 3. CLI override semantics

Existing `-Model` and `-ReviewModel` remain strict single-model overrides for the normal candidate route.

If supplied, the explicit CLI model replaces the configured normal candidate chain with exactly one normal candidate. This preserves current operator expectations and makes manual debugging deterministic.

CLI override does not silently erase the explicitly configured degraded-review policy unless implementation constraints make that unavoidable; if such a constraint exists, document the behavior explicitly in the architecture contract. Do not add a public chain-valued CLI syntax in v1.1.

Existing internal executable/argument override seams must continue to work. Minimal additional internal seams are allowed where necessary to deterministically exercise multiple candidates, degraded routing, and qualification without live provider failures.

### 4. Normal fallback eligibility

Fallback is permitted only after an attempt is classified as infrastructure failure at an existing mechanical boundary.

Eligible examples:

- process launch/provider failure;
- timeout with confirmed termination;
- non-zero model-process exit;
- empty/unusable Scout output;
- malformed structured reviewer transport;
- canonical review payload extraction failure;
- invalid/missing required reviewer verdict structure.

A timeout whose process termination cannot be confirmed is terminal infrastructure failure: do not launch another process while ownership of the previous process is uncertain, including the degraded reviewer.

Fallback is forbidden after:

- structurally valid Scout output;
- structurally valid reviewer PASS;
- structurally valid reviewer BLOCK;
- focused-test failure;
- artifact-promotion failure;
- any already-classified candidate/semantic result.

No model may reinterpret another model's prose to decide fallback eligibility.

### 5. Gate routing boundary

Fallback belongs inside each reviewer role invocation, not around the entire Gate.

For each reviewer in the existing sequential order:

```text
reviewer role
  -> normal candidate 1 (full timeout)
     -> valid PASS/BLOCK: terminal for this reviewer
     -> eligible infrastructure failure: normal candidate 2
  -> ...
  -> normal candidate N
  -> all normal candidates infrastructurally exhausted
     -> optional degraded Gemini reviewer (full timeout)
        -> valid degraded PASS/BLOCK: terminal degraded evidence
        -> infrastructure failure: INFRASTRUCTURE_BLOCKED
```

Only after one reviewer obtains a valid terminal normal or degraded result may Gate proceed according to the outcome semantics below.

A valid semantic BLOCK is always terminal. A normal candidate BLOCK must never be bypassed to obtain a more favorable result from another normal or degraded model.

Focused tests remain outside model fallback routing and run only under the existing Gate conditions.

### 6. Timeout policy: full timeout per attempt

The existing public `TimeoutSeconds` / `ReviewTimeoutSeconds` remains a per-model-attempt timeout. Default remains 480 seconds for every attempted model.

Examples:

```text
Mimo            <= 480s
Fallback A      <= 480s
Fallback B      <= 480s
Degraded Gemini <= 480s
```

Thus a four-attempt worst case may legitimately approach 1920 seconds plus small bounded process/cleanup overhead.

This is intentional for v1.1. The 480-second value was established around single-model execution, and a fallback model should receive a fair opportunity to complete rather than inherit only the remainder of time consumed by a failed predecessor.

Do not add exponential retry, background retry daemons, or parallel racing. The fallback list itself is finite, so total execution remains finitely bounded by approximately:

```text
attempt_timeout * maximum_attempt_count + bounded cleanup overhead
```

Timeout and role-step optimization are explicitly deferred until production-pilot evidence exists. See the roadmap retrospective requirement below.

### 7. Scout routing

Scout uses the ordered normal `models.scout` chain with the same infrastructure-only fallback rule and full timeout per candidate.

A structurally valid Scout report terminates routing and is promoted exactly once. If all configured Scout candidates fail infrastructurally, Scout remains infrastructure-blocked under its existing command failure semantics.

Automated degraded Gemini Scout routing is not required for v1.1. Gemini may still provide manual degraded Scout/advisory evidence. The required automated degraded safety net in this task applies to Gate review, where avoiding a review-infrastructure single point of failure is the primary goal.

### 8. Fallback candidate qualification

This task must distinguish routing-mechanism verification from live model qualification.

The routing mechanism itself must be deterministically testable without depending on provider availability. Separately, before a model is added to the recommended/default fallback chain, perform a bounded live smoke qualification using the actual formal role contract.

The first qualification target is `opencode/big-pickle` because it has prior useful repository-inspection/Scout-like evidence and is currently available as a plausible free fallback. Do not assume it passes.

Qualification is role-specific:

#### Scout qualification

A candidate qualifies for `models.scout` default fallback only if a live bounded invocation using the real Scout role contract:

- starts and completes within the existing per-attempt timeout;
- respects standalone/read-only execution boundaries;
- produces a non-empty structurally usable Scout report;
- does not require manual prompt repair or output rewriting;
- leaves canonical promotion and repository state safe.

#### Gate reviewer qualification

A candidate qualifies for `models.review` default fallback only if live bounded invocation(s) using the real formal reviewer contract demonstrate that it can:

- complete within the existing per-attempt timeout;
- preserve read-only/standalone boundaries;
- emit transport/payload/verdict structure accepted by the existing mechanical parser without manual repair;
- produce a valid terminal PASS or BLOCK rather than malformed/unclassifiable prose;
- leave canonical review/evidence transaction safety intact.

At least one successful live smoke is required for the relevant role before default admission. If a candidate fails qualification because of provider infrastructure, record the result as inconclusive/failed qualification rather than weakening the parser or role contract merely to admit that model.

Qualification evidence must record at least model, role, elapsed time, structural result, and pass/fail/inconclusive classification. Keep it compact; raw provider output remains runtime-only unless already part of a validated canonical artifact.

A candidate may have different outcomes per role. For example:

```text
model                    Scout       Gate Review
opencode/mimo-v2.5-free  qualified   qualified/current default
opencode/big-pickle      PASS/FAIL   PASS/FAIL
```

The implementation must update the task/default model metadata only according to observed qualification:

- if BigPickle qualifies for both roles: Mimo -> BigPickle becomes the recommended normal chain for both;
- if BigPickle qualifies only for Scout: add it only to `models.scout`;
- if BigPickle qualifies only for Gate review: add it only to `models.review`;
- if it qualifies for neither or qualification is inconclusive: keep Mimo as the only qualified normal default and rely on degraded review only where configured; do not fabricate a second normal fallback.

This task is not required to search indefinitely for additional free models. One evidence-backed candidate qualification target is sufficient for v1.1. Additional candidates belong in later evidence-driven calibration unless a trivially available already-tested candidate exists.

### 9. Degraded Gate evidence semantics

The degraded reviewer exists to preserve workflow continuity, not to manufacture independence.

When invoked, tracked evidence must state at minimum:

```text
Review mode: DEGRADED
Evidence confidence: LOW
Independence: NOT_INDEPENDENT
Reason: independent reviewer infrastructure exhausted
Reviewer: <configured degraded reviewer>
```

Equivalent machine-readable/unambiguous wording is acceptable.

A degraded PASS means only:

> the last-resort reviewer found no blocking issue under degraded/non-independent conditions.

It does NOT mean:

> independent Gate review passed.

A degraded BLOCK remains meaningful negative evidence and must stop candidate progression as a candidate-blocked result.

### 10. Gate process outcomes

Preserve the existing public exit-code vocabulary:

- `0 = PASS`
- `1 = INFRASTRUCTURE_BLOCKED`
- `2 = CANDIDATE_BLOCKED`

Interpretation is tightened as follows:

- normal independent reviewers all valid PASS + focused tests pass -> exit `0`, normal PASS;
- any valid normal or degraded reviewer BLOCK, or focused-test failure -> exit `2`, CANDIDATE_BLOCKED;
- all normal reviewer candidates fail infrastructurally and degraded reviewer is absent or also fails -> exit `1`, INFRASTRUCTURE_BLOCKED;
- degraded reviewer PASS is **not sufficient to claim a normal independent Gate PASS**.

For v1.1, when degraded PASS is the only review result available for a reviewer role, Gate may complete the mechanical checks and produce tracked degraded evidence, but its evidence/status must explicitly require ChatGPT + user final semantic review before merge. The script must not label that path as `NORMAL PASS` or `INDEPENDENT PASS` anywhere.

To avoid introducing a fourth public exit code in this task, degraded PASS may use exit `0` only as a process-success signal **provided** `EVIDENCE.md` and console status unambiguously identify the result as `DEGRADED / LOW_EVIDENCE / NOT_INDEPENDENT` and the architecture contract states that exit `0` alone is not merge authority. Merge authority remains governed by the workflow lifecycle and ChatGPT + user final review.

### 11. Attempt provenance

Every attempted candidate, including degraded review, must produce compact provenance containing at least:

- role / reviewer identity;
- attempt type (`NORMAL` or `DEGRADED`);
- 1-based attempt index within its route;
- model/reviewer identifier;
- elapsed seconds;
- normalized outcome classification/reason;
- whether it produced the selected canonical result.

Raw stdout/stderr from failed attempts remains under ignored `.runtime/` diagnostics and must not be copied wholesale into tracked evidence.

For Scout, successful console output should make selected attempt and preceding fallback failures operator-visible; tracked `CONTEXT.md` remains only the validated Scout report.

For Gate, compact provenance must be included in `EVIDENCE.md`. Existing canonical `reviews/*.md` remain validated reviewer payloads; when a payload came from degraded review, evidence must make that provenance impossible to confuse with independent evidence.

No secrets, tokens, environment values, or credential material may be recorded.

### 12. Implementation shape

Scout currently owns its process lifecycle inline. Refactoring that lifecycle into a small bounded attempt helper is allowed and preferred if it avoids duplicating timeout/kill/streaming logic across fallback attempts.

Gate should reuse `Invoke-BoundedProcess` and place candidate iteration around the existing mechanical result-classification boundary for each reviewer.

Do not introduce a generalized provider abstraction, model-quality framework, or repository-wide process framework solely for this task. The routing mechanism should be a small parameter/config-driven layer.

### 13. Architecture documentation

`docs/architecture/ai_development_workflow.md` must document:

- Mimo as the current configurable default first candidate, not a hard-coded dependency;
- scalar-or-array ordered normal model metadata;
- explicit separate degraded-review configuration;
- qualification-before-default-admission and role-specific qualification;
- strict single-model CLI override semantics;
- infrastructure-only fallback;
- semantic PASS/BLOCK terminality and no review-shopping;
- full 480-second default timeout per model attempt;
- accepted worst-case latency multiplication across a finite candidate chain;
- provenance behavior;
- degraded Gemini semantics (`LOW_EVIDENCE`, `NOT_INDEPENDENT`);
- unchanged 0/1/2 process exit-code vocabulary and the fact that exit code alone is not merge authority;
- ChatGPT + user final semantic/architecture review requirement.

### 14. Roadmap retrospective requirement

Update `docs/tasks/BACKLOG.md` under `agent-workflow-pilot-retrospective-v1` to explicitly include evidence-based calibration of model routing after the first production pilot.

The retrospective must analyze at least:

- per-model attempt elapsed time;
- timeout frequency;
- fallback frequency and which candidates actually recover failures;
- degraded-review frequency;
- normal vs degraded evidence quality;
- agent step-budget utilization where observable;
- whether 480 seconds per attempt is materially over/under-provisioned;
- whether candidate ordering should change;
- whether role-specific timeout/step limits should be adjusted.

Do not optimize these values speculatively in v1.1. The intended sequence is:

```text
reliability first -> production pilot -> collect evidence -> calibrate time/steps/order
```

## Acceptance criteria

1. Existing scalar `models.scout` and `models.review` configurations still execute as one-candidate normal routes.
2. Ordered arrays execute normal candidates in declared order.
3. Mimo is the current first/default candidate through configuration and is not special-cased in routing code.
4. CLI `-Model` / `-ReviewModel` replaces the configured normal chain with one explicit normal candidate.
5. Scout falls back after a deterministic simulated eligible infrastructure failure and promotes the first structurally valid Scout result exactly once.
6. Scout does not invoke later candidates after valid output.
7. Each Gate reviewer independently falls back after eligible infrastructure failure without restarting or skipping the other reviewer role.
8. Valid reviewer PASS invokes no later candidate for that reviewer.
9. Valid reviewer BLOCK invokes no later candidate/degraded reviewer and preserves candidate-blocked semantics.
10. Each attempted normal or degraded model receives the full configured timeout independently; timeout is not shared across the chain.
11. Exhausting normal candidates invokes the explicitly configured degraded reviewer exactly once when safe to do so.
12. Degraded review is never invoked after a valid normal semantic result.
13. Degraded PASS produces unmistakable `DEGRADED / LOW_EVIDENCE / NOT_INDEPENDENT` evidence and never claims normal independent Gate PASS.
14. Degraded BLOCK produces candidate-blocked semantics.
15. Failure/absence of the degraded reviewer after normal infrastructure exhaustion produces infrastructure-blocked semantics and preserves prior canonical artifacts.
16. Unconfirmed process termination is terminal infrastructure failure and never launches another normal or degraded process.
17. Provenance identifies every attempted model, order/type, elapsed time, failure reason, and selected result; Gate persists compact provenance in `EVIDENCE.md` while failed raw logs remain runtime-only.
18. Malformed reviewer transport/payload/header can trigger fallback mechanically; semantic prose is never reinterpreted by another model.
19. Existing standalone isolation, working directory, closed stdin, streaming observability, kill confirmation, verdict parsing, focused-test behavior, transactional promotion/rollback, and 0/1/2 process codes remain intact.
20. Deterministic probes cover scalar compatibility, ordered fallback, semantic terminality, normal-chain exhaustion, degraded success/block/failure, per-attempt timeout semantics, and artifact safety without requiring live provider failure.
21. `opencode/big-pickle` receives bounded live role-specific qualification rather than being assumed qualified from unrelated prior use.
22. BigPickle is added only to the role chains it actually qualifies for; failed/inconclusive qualification does not weaken role/parser contracts and does not fabricate a fallback.
23. Qualification evidence records model, role, elapsed time, structural result, and classification without committing raw failed provider output.
24. Architecture documentation matches these semantics.
25. Backlog retrospective explicitly records later evidence-based timeout/step/model-order calibration.
26. Verification leaves no disposable probe pollution and changes no game/runtime files.

## Required verification

Use existing internal override seams plus minimal additional internal routing seams where necessary. Do not introduce a generalized PowerShell test framework solely for this task.

At minimum verify deterministically:

- scalar model normalization;
- ordered array normalization and order preservation;
- strict CLI single-model override;
- first normal attempt infrastructure failure followed by second normal attempt success;
- valid normal PASS stops fallback;
- valid normal BLOCK stops all fallback and remains candidate-blocked;
- malformed reviewer output can fall through to the next normal candidate;
- normal candidate exhaustion invokes degraded reviewer;
- degraded PASS is explicitly low-evidence/non-independent and does not claim normal PASS;
- degraded BLOCK returns candidate-blocked;
- degraded infrastructure failure returns infrastructure-blocked;
- each fallback attempt receives the full configured timeout rather than a shared remainder;
- unconfirmed termination prevents all subsequent attempts;
- Gate `EVIDENCE.md` records compact normal/degraded provenance;
- failed raw output remains runtime-only;
- prior canonical artifacts remain safe when no valid terminal result is obtained;
- promotion rollback and focused-test behavior remain unchanged;
- before/after git status delta contains no disposable probe pollution.

Additionally perform bounded live qualification for `opencode/big-pickle` against the actual Scout contract and actual formal Gate reviewer contract as described in Section 8. Qualification failure is an acceptable task result; silently weakening contracts to force qualification is not.

AI agents must not run the repository full test suite. User-owned branch completion/full-suite rules remain unchanged.

## Non-goals

- guaranteeing BigPickle qualifies;
- searching indefinitely for more free fallback models in this task;
- retrying or overriding semantic BLOCK;
- reviewer voting, consensus, racing, or parallel reviewers;
- autonomous implementation repair loops;
- model quality scoring or dynamic benchmark routing;
- speculative timeout/step optimization before pilot evidence;
- provider credential management or installation automation;
- public chain-valued CLI syntax;
- automatic provider-family inference or Gemini string blacklists;
- representing Gemini/Antigravity self-review as normal independent Gate PASS;
- adding a fourth public Gate exit code solely for degraded evidence;
- changing Scout/reviewer permissions or step budgets in this task;
- pause/amend/resume workflow control plane;
- generalized shared process-framework extraction;
- production/game behavior changes.
