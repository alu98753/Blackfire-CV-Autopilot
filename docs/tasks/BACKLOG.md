# Development Backlog

This file is the canonical entry point for new ideas, future work, bugs that still need investigation, and tasks that are not yet ready for a full `SPEC.md`.

Keep entries short. When an item becomes active development work, promote it into:

```text
docs/tasks/<task-id>/SPEC.md
docs/tasks/<task-id>/task.json
```

Do not duplicate a promoted task here. Replace the backlog item with a link to the active task package or remove it as appropriate.

## Backlog

Existing backlog material under `docs/todos/` predates this workflow and remains legacy until touched. New backlog items must be added here, not to `docs/todos/future_work.md` or new files under `docs/todos/`.

## AI workflow roadmap

This roadmap fixes the intended order and responsibility boundaries before individual tasks are activated. Planned tasks stay here until the user explicitly starts one. At activation time, create a fresh task branch from the then-current `main`, promote only that item into `docs/tasks/<task-id>/SPEC.md` + `task.json`, run Scout, and continue the normal Draft -> Scout -> Final -> implementation -> Gate -> ChatGPT review lifecycle. Do not pre-create long-lived branches for later roadmap items because their base and assumptions would become stale.

Completed prerequisites:

- `scout-efficiency-v1` — merged. Scout execution is bounded, observable, and artifact-safe.
- `ai-gate-execution-resilience` — merged. Gate reviewer/test execution is bounded; outcomes are classified as PASS / INFRASTRUCTURE_BLOCKED / CANDIDATE_BLOCKED; canonical review/evidence promotion is transaction-safe.

### 1. `agent-role-contract-hardening-v1-1`

**Goal:** make Scout and reviewer roles more concise, scope-disciplined, and genuinely read-only so weaker/faster models can still be reliable fallback candidates without changing role ownership.

**Depends on:** `ai-gate-execution-resilience`.

**Planned scope / invariants:**
- Preserve role ownership: Scout is evidence-only; reviewers are read-only; Gemini remains the sole production writer after Final SPEC; ChatGPT + user own contract/final review.
- Make reviewer output blocker-first and concise: structured verdict header first, short coverage summary on PASS, expand only concrete blockers, cap advisory/evidence-gap verbosity.
- Add explicit exploration/early-stop guidance so reviewers stop once enough evidence exists for PASS/BLOCK instead of performing open-ended repository archaeology.
- Re-evaluate Scout output/exploration budget only where evidence supports tightening; keep uncertainty explicit rather than expanding scope.
- Investigate the observed OpenCode capability gap where a reviewer with `bash: deny` still reached an `execute`-style tool. Enforce or document the narrowest practical read-only boundary; reviewer execution must not mutate repository state.
- Preserve current reviewer semantic contract (`VERDICT`, `BLOCKING_FINDINGS`) and Gate 0/1/2 outcome semantics.

**Non-goals:** no model fallback routing yet; no parallel reviewers; no retries after semantic BLOCK; no user interrupt/resume system.

**Done when:** role contracts are measurably shorter/bounded, read-only capability is verified or explicitly guarded, and representative models can complete deterministic role-contract probes without weakening review semantics.

### 2. `agent-model-fallback-routing-v1-1`

**Goal:** remove single-model availability as a workflow SPOF with ordered, role-specific fallback while preserving reviewer independence and preventing review-shopping.

**Depends on:** `agent-role-contract-hardening-v1-1`.

**Planned scope / invariants:**
- Support ordered model candidates per role (Scout, spec reviewer, regression reviewer) without making model identity an architecture invariant.
- Fallback is allowed only for `INFRASTRUCTURE_BLOCKED`-class failures such as provider/auth failure, launch failure, timeout, malformed output, or unavailable result.
- A valid semantic `PASS` or `BLOCK` is terminal for that reviewer role; never ask additional models until one returns the preferred answer.
- Bound the total role budget across all fallback attempts so N models cannot multiply the current timeout without limit.
- Record attempt provenance: model, start/end/result, infrastructure failure reason, and which attempt produced the accepted canonical artifact.
- Canonical review/evidence promotion must still use only one accepted valid attempt per role and remain artifact-safe.
- Scout may fall back to Gemini/Antigravity only as explicitly marked degraded evidence if OpenCode candidates are exhausted; ChatGPT must still re-check repository evidence before Final SPEC.
- Gemini/Antigravity self-review must never masquerade as an independent normal Gate PASS for code it authored. If all independent reviewer routes fail, any Gemini review is advisory/degraded evidence and the Gate remains infrastructure-blocked until ChatGPT/user decide how to proceed.

**Observed model evidence (2026-09-14, operational only):**
- `opencode/mimo-v2.5-free`: only tested free model that completed both real reviewers within budget with valid headers and Gate PASS; current primary candidate.
- `opencode/big-pickle`: strong analysis but observed header drift and open-ended exploration timeout; candidate only if role hardening makes it reliable.
- `opencode/nemotron-3.5-lightning-free`: observed timeout/stall in Agent mode.
- `opencode/ling-3.0-flash-fin-free`, `opencode/muse-spark-1.2-contributor-free`, `opencode/muse-spark-1.3-contributor-free`: observed provider/API-key failures.
- `opencode/deepseek-v4-flash`: observed insufficient account funds; not a free fallback.

**Non-goals:** no semantic majority vote, no automatic repair loop, no parallel reviewer race, no permanent hard-coded belief that Mimo is always best.

**Done when:** deterministic and real smoke tests prove infra-only fallback, semantic verdict terminality, bounded total time, provenance, and no canonical artifact contamination across failed attempts.

### 3. `intent-routing-observability`

**Goal:** first production feature/refactor pilot for the hardened AI workflow; make navigation logs distinguish the decision selected this tick from progress observed for a previously committed action.

**Depends on:** `agent-model-fallback-routing-v1-1`.

**Known behavior boundary:** current logs can combine a new selected intent/action with `progress` that actually belongs to an older `InFlightAction`, producing temporally misleading diagnostics.

**Planned invariants:**
- Selected/current-decision fields describe this tick only.
- Observed progress fields describe the previously committed `InFlightAction` observed this tick.
- `observed_intent` comes from `observed_action.intent_id`, never inferred from the current active/selected intent.
- No in-flight action uses a stable none/idle representation.
- Preserve existing navigation behavior; this task is observability unless Final SPEC explicitly identifies a required behavior correction.
- Keep existing `key=value` logging style; do not introduce a new JSON logging framework.

**Provisional acceptance anchors:**
- Cross-tick case proves old observed action/progress can coexist with a new selected intent/decision without attribution ambiguity.
- No-in-flight case produces stable none/idle observed fields.
- No responsibility shift between intent selection, routing, committed action ownership, and progress observation.

**Purpose in roadmap:** exercise the full Draft -> Scout -> Final -> Gemini -> fallback-capable Gate -> ChatGPT review -> closeout lifecycle on real game code.

### 4. `agent-workflow-pilot-retrospective-v1`

**Goal:** turn the `intent-routing-observability` pilot into evidence for the next workflow version instead of designing V2 from imagined pain points.

**Depends on:** successful closeout/merge of `intent-routing-observability`.

**Planned scope:**
- Review actual elapsed time, fallback attempts, model failures, manual user actions, artifact handoffs, Gate outcomes, and places where the user wanted to intervene or correct direction.
- Identify which lifecycle stages need an explicit human checkpoint versus which already work safely without interruption.
- Separate workflow defects from model/provider reliability issues and from project-specific implementation problems.
- Produce a concise V2 decision record: required interrupt states, invalidation/resume rules, durable artifacts, and explicit non-goals.

**Non-goals:** no implementation of pause/resume in this task; no dashboard, automatic repair, or parallel-agent expansion.

**Done when:** V2 interruptibility scope is grounded in observed pilot evidence and can be promoted into a Draft SPEC without reopening settled v1 responsibilities.

### 5. `workflow-interruptibility-v2`

**Goal:** add a safe user control plane so the user can change intent during long-running AI workflow stages without waiting for the entire stage to finish and without allowing partial/stale artifacts to become canonical.

**Depends on:** `agent-workflow-pilot-retrospective-v1`.

**Upper invariant:** user intent may update at any time; already committed agent work may only be preempted through an explicit cancel/safe boundary before its output is accepted as canonical.

**Planned semantics:**
- Model the interaction as `Pause -> Amend -> Resume`, not live token/message injection into an already-running model turn.
- Distinguish at least: clarification, material contract/spec amendment, and unrelated/new backlog idea.
- A material spec amendment invalidates downstream implementation/review evidence as appropriate and requires contract re-finalization before production work resumes.
- An interrupt during Scout/reviewer execution must cancel or stop at a safe boundary and must not promote partial canonical artifacts.
- Runtime control state should remain worktree/task-scoped under ignored `.runtime/`; durable user decisions that affect the task contract should be tracked in the task package (exact artifact to be finalized by SPEC, e.g. a decision log).
- Resume must make the prior stage/provenance and invalidated artifacts explicit; no hidden continuation from stale context.

**Non-goals:** no live injection into an in-flight generation, no automatic conflict resolution between user and model, no concurrent multi-agent swarm, no automatic repair loop.

**Done when:** deterministic interruption probes demonstrate safe cancellation, no partial promotion, correct spec-amendment invalidation, and resumable task state without a global singleton that would collide across worktrees.

## Deferred candidates after V2 evidence

The following are intentionally **not yet scheduled tasks**. Reconsider them only after the production pilot and interruptibility work provide evidence that they solve real workflow costs:

- human-readable workflow/status dashboard generated from structured task artifacts;
- autonomous repair/retry loops;
- parallel or multi-model reviewer voting/racing.
