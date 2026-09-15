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

### Resource / responsibility principle

Local free agents provide fast, bounded, concise first-pass evidence and explicit uncertainty. ChatGPT + user perform the deeper architecture/specification/final semantic analysis. Gemini/Antigravity remains the production implementation writer after Final SPEC.

Completed prerequisites:
- `scout-efficiency-v1` — merged.
- `ai-gate-execution-resilience` — merged.
- AI workflow roadmap planning — merged via PR #5.
- `agent-role-contract-hardening-v1-1` — completed and merged.

### Active

2. `agent-model-fallback-routing-v1-1`
   - Depends on task 1.
   - Add ordered, configurable role-specific normal-model fallback only for infrastructure failures; Mimo is the current default first candidate but is not hard-coded.
   - Valid semantic PASS/BLOCK is terminal; no review-shopping.
   - Each model attempt retains the full currently validated timeout (480s by default); longer worst-case fallback latency is an accepted reliability tradeoff for v1.1.
   - After all normal independent Gate reviewer candidates fail infrastructurally, an explicitly configured Gemini/Antigravity degraded reviewer may provide `LOW_EVIDENCE / NOT_INDEPENDENT` last-resort evidence rather than making reviewer infrastructure a single point of failure.
   - Degraded evidence must never masquerade as a normal independent Gate PASS; ChatGPT + user remain final semantic/architecture review authority.
   - Record ordered attempt provenance and preserve transactional artifact safety.

### Planned next

3. `intent-routing-observability`
   - Depends on task 2.
   - First production pilot of the hardened workflow.
   - Separate this-tick selected decision fields from progress observed for a prior `InFlightAction`.
   - Preserve navigation behavior unless Final SPEC explicitly requires otherwise.

4. `agent-workflow-pilot-retrospective-v1`
   - Depends on successful closeout of task 3.
   - Analyze actual elapsed time, fallbacks, degraded-review usage, manual interventions, handoffs, and workflow friction.
   - Calibrate model routing from production evidence rather than speculation: per-model latency, timeout frequency, fallback recovery rate, degraded evidence quality, candidate ordering, and observable agent step-budget utilization.
   - Re-evaluate the initial 480s-per-attempt policy and role/model step limits; adjust timeout/steps/order only when pilot evidence justifies it.
   - Intended optimization sequence: reliability first -> production pilot -> collect evidence -> calibrate time/steps/order.
   - Produce evidence-backed V2 interruptibility decisions; no pause/resume implementation yet.

5. `workflow-interruptibility-v2`
   - Depends on task 4.
   - Add safe `Pause -> Amend -> Resume` control semantics.
   - Material contract changes invalidate downstream evidence as appropriate.
   - No live message injection into an already-running generation; no partial canonical promotion.

## Deferred candidates after V2 evidence

Not scheduled until pilot/interruptibility evidence justifies them:
- human-readable workflow/status dashboard;
- autonomous repair/retry loops;
- parallel or multi-model reviewer voting/racing.
