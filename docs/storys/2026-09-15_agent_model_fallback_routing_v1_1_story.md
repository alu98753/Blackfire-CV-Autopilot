# Agent Model Fallback Routing v1.1 — Development Story

## Problem

The formal Blackfire agent workflow had become structurally safer, but its Scout and Gate paths still depended on one configured OpenCode model per role. A provider failure, timeout, malformed structured response, or other infrastructure fault could therefore stop the workflow even when the implementation itself was reviewable.

The goal was not to make the Gate "always pass." It was to remove model availability as a single point of failure without weakening independent review semantics or allowing review-shopping.

## Architecture decision

The routing layer now treats normal reviewer models as finite, ordered, role-specific configuration. `models.scout` and `models.review` accept either the legacy scalar form or an ordered array. Mimo remains the current first/default model because it has the strongest operational evidence, but routing code does not special-case it.

Fallback is deliberately narrow: only mechanically classified infrastructure failures may advance to the next model. A structurally valid `PASS` or `BLOCK` is terminal. This prevents a negative review from being bypassed merely by asking another model.

Each attempt keeps the full 480-second timeout. We accepted larger worst-case latency rather than prematurely optimizing a timeout calibrated for single-model runs. Latency, step budgets, and candidate ordering are deferred to the production-pilot retrospective, where real evidence will exist.

## Qualification before admission

Availability is not qualification. A model must demonstrate that it can satisfy the actual role contract before it becomes a recommended fallback.

`opencode/big-pickle` was therefore tested separately for Scout and Gate review. It qualified for Scout: the live invocation completed in 127 seconds and produced a structurally usable Scout report. It did not qualify for Gate review because its provider JSONL contained malformed escaping. The parser was intentionally not weakened to accommodate it.

The resulting policy is asymmetric by evidence:

```text
Scout: Mimo -> BigPickle
Gate:  Mimo
```

This is a useful consequence of role-specific routing rather than a defect: model suitability is a property of the role contract, not merely of the model name.

## The failed design and what it exposed

An early implementation represented the last-resort Gemini reviewer as `degraded_review: "gemini"` and routed it through the same OpenCode invocation machinery as normal candidates. Mechanically this looked convenient, but it encoded the wrong responsibility boundary.

The Gemini in this workflow is the interactive Google Antigravity IDE agent that also writes the production implementation. It is not an OpenCode model. More importantly, self-review by the implementation writer is epistemically different from an independent Gate review.

The design was corrected instead of teaching the Gate to pretend those two things were equivalent.

## Final responsibility boundary

`ai_gate.ps1` owns only automated independent OpenCode review. If every configured normal reviewer candidate fails infrastructurally, Gate returns `1 = INFRASTRUCTURE_BLOCKED`, leaves canonical independent review artifacts untouched, and emits `MANUAL_DEGRADED_REVIEW_REQUIRED`.

The outer workflow may then hand the task to the already-running Antigravity Gemini implementation agent for an interactive degraded self-review. That artifact must explicitly state:

```text
REVIEW_MODE: DEGRADED
EVIDENCE_CONFIDENCE: LOW
INDEPENDENCE: NOT_INDEPENDENT
REVIEWER: ANTIGRAVITY_GEMINI
```

This degraded path preserves workflow continuity but never manufactures independent evidence. ChatGPT + user remain the final semantic and architecture authority.

## Evidence and observability

Gate records compact attempt provenance: role, attempt type/index, model, elapsed time, normalized outcome, and selected status. Failed raw provider output remains runtime-only. Canonical reviews and `EVIDENCE.md` retain transactional promotion semantics.

The final independent Gate reviewed implementation commit `bd32801657ebc0f335ade5baaf2a9942c69041f5`:

- spec reviewer: PASS, NORMAL, Mimo, 80.7s
- regression reviewer: PASS, NORMAL, Mimo, 124s
- Gate exit: 0

The evidence-only follow-up commit was `b051f10f46d66e73fef397e435dfe98853bb0c36`.

## Trade-offs

The design intentionally chooses reliability and evidence honesty over minimum latency. Multiple 480-second attempts can be slow, but each fallback receives a fair execution budget. The workflow also accepts that the final emergency review may be non-independent; instead of hiding that weakness, it makes the evidence grade explicit and moves merge authority upward.

The PowerShell event-stream ordering behavior observed under unrealistically dense mock output was not used to expand this task. Real OpenCode streaming did not demonstrate the same production failure, so optimization remains evidence-driven.

## Outcome

The workflow now has three distinct concepts that were previously easy to conflate:

1. **model fallback** — automated, independent, infrastructure-only;
2. **degraded self-review** — workflow-level continuity mechanism when independent reviewer infrastructure is unavailable;
3. **final authority** — ChatGPT + user semantic/architecture decision.

The task was merged through PR #7 as merge commit `af282364dd2e9f0ba70e29f9ef610471434f0f15`. The full repository test suite was intentionally not run for this closeout; the formal independent AI Gate and task-specific verification were used as the accepted evidence boundary.

The next roadmap step is `intent-routing-observability`, the first production pilot of the hardened agent workflow. Its results will feed `agent-workflow-pilot-retrospective-v1`, where timeout, fallback frequency, model ordering, evidence quality, and step budgets can finally be calibrated from real use rather than speculation.
