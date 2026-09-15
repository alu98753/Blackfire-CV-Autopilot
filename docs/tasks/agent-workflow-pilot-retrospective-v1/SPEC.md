# agent-workflow-pilot-retrospective-v1

Status: Draft

## Goal

Perform an evidence-backed retrospective of the first production pilot run through the hardened Blackfire AI development workflow (`intent-routing-observability`) and convert observed workflow friction into an explicit, prioritized improvement plan.

This task is an analysis / workflow-governance task. Its purpose is to decide **what should be improved next and why**. It must not silently implement the recommended fixes.

## Observed pilot basis

The completed `intent-routing-observability` task provides the first real production evidence after the recent workflow-hardening tasks. The lightweight survey already confirms several concrete friction points worth retrospective analysis:

- the initial task descriptor omitted required `models` configuration and Scout failed before localization;
- remote-to-local synchronization and branch/worktree state required explicit human handoff;
- the first independent Mimo spec review reached a semantic PASS with zero blocking findings but Gate classified the payload as infrastructure failure because the canonical verdict lines were wrapped in Markdown bold;
- the infrastructure failure prevented the regression reviewer from running in that Gate attempt;
- a non-independent Gemini degraded review was created and correctly labelled `LOW_EVIDENCE / NOT_INDEPENDENT`, but could not count as a normal Gate PASS;
- after syncing latest `main` and explicitly selecting BigPickle, the normal Gate completed successfully with spec-reviewer PASS in ~80.2s and regression-reviewer PASS in ~119.1s;
- human intervention was required to diagnose the failure, choose the rerun strategy, synchronize the branch, rerun Gate, and complete integration;
- commit quality / semantic consistency emerged as a separate convenience concern during the pilot, motivating but not yet authorizing the proposed Semantic Commit Agent roadmap item.

These observations are inputs to the retrospective, not pre-decided fixes.

## Scope

- Reconstruct the actual lifecycle of `intent-routing-observability` from tracked GitHub evidence and relevant workflow contracts.
- Separate failures/friction into categories such as:
  - contract/schema validation;
  - remote/local worktree handoff;
  - Scout model routing and execution;
  - writer handoff / implementation friction;
  - Gate reviewer execution, payload extraction, sequencing, and fallback behavior;
  - model latency / timeout / step-budget calibration;
  - artifact promotion / evidence quality;
  - manual intervention / copy-paste / command burden;
  - commit/history clarity.
- Quantify evidence where the repository contains reliable measurements (for example reviewer elapsed times, attempt counts, result types, test counts, reruns).
- Distinguish **semantic failure**, **infrastructure failure**, **contract brittleness**, and **human convenience friction**; do not collapse them into one severity class.
- Produce a concise tracked retrospective report under this task package with:
  - timeline / lifecycle reconstruction;
  - findings with evidence and confidence;
  - root-cause vs symptom classification;
  - KEEP / CHANGE / MEASURE MORE / DEFER decisions;
  - prioritized follow-up task candidates;
  - recommended ordering for workflow v1.2 / v2;
  - explicit recommendation on Semantic Commit Agent timing;
  - explicit interruptibility requirements to carry into `workflow-interruptibility-v2`.
- Update the canonical `docs/tasks/BACKLOG.md` roadmap only after the retrospective conclusions are evidence-backed and the Final SPEC authorizes the exact roadmap changes.

## Known invariants

- ChatGPT + user remain architecture / workflow contract owners; retrospective evidence does not self-authorize policy changes.
- Scout is an evidence provider, not the retrospective conclusion owner.
- Gemini/Antigravity remains the writer for tracked task outputs after Final SPEC, but must not implement workflow fixes unless those fixes are explicitly part of a later task.
- OpenCode reviewers remain read-only verification roles.
- A semantic reviewer PASS that is mechanically rejected must be recorded distinctly from a semantic BLOCK; infrastructure classification must not rewrite the reviewer meaning.
- Degraded / non-independent evidence must remain visibly distinct from normal independent Gate evidence.
- Model fallback remains an infrastructure-reliability mechanism, not review-shopping.
- Current workflow behavior remains unchanged by this retrospective unless Final SPEC explicitly identifies a documentation-only clarification as part of this task.
- Recommendations must be grounded in repository evidence or explicitly marked as hypotheses requiring more measurement.
- Do not generalize a single pilot observation into a global policy change without stating the confidence / evidence limitation.

## Non-goals

- Do not modify `scripts/ai_gate.ps1`, `scripts/ai_scout.ps1`, OpenCode agent prompts, model routing logic, parser regexes, timeout code, or worktree automation in this task.
- Do not implement Markdown verdict normalization in this task.
- Do not change Gate reviewer sequencing in this task.
- Do not change global model ordering / fallback configuration in this task.
- Do not implement Semantic Commit Agent in this task.
- Do not implement Pause / Amend / Resume or workflow orchestrator behavior.
- Do not add autonomous repair/retry loops or reviewer voting.
- Do not treat the degraded Gemini self-review as equivalent to an independent Gate PASS.
- Do not perform broad codebase architecture refactoring; this task concerns the AI development workflow.

## Provisional acceptance criteria

1. A tracked retrospective report reconstructs the pilot lifecycle from task creation through Scout, Final SPEC, implementation, first Gate failure, degraded evidence, rerun, successful Gate, final review, and merge.
2. Every material finding cites or names concrete tracked evidence where available; unsupported impressions are explicitly labelled hypotheses.
3. The report clearly distinguishes semantic blockers from infrastructure failures and convenience friction.
4. The Mimo Markdown verdict incident is analyzed as a concrete failure mode, including why semantic PASS became `PAYLOAD_EXTRACTION_FAILED`, why regression review was not reached, and what classes of follow-up solutions exist; the report must not directly implement one.
5. Reviewer/model measurements include at least the available BigPickle spec/regression elapsed times (~80.2s / ~119.1s), attempt counts, and known rerun/fallback facts; missing Scout/writer timing is recorded as missing evidence rather than invented.
6. The initial `task.json` schema/config omission is analyzed for whether deterministic task validation/linting deserves promotion from deferred candidate to a scheduled follow-up.
7. Human intervention points are enumerated and separated into necessary semantic approvals vs avoidable mechanical friction.
8. The report produces an evidence-backed ordered recommendation for at least these roadmap decisions:
   - Gate review payload robustness;
   - Gate stage sequencing / infrastructure-failure behavior;
   - task descriptor/schema validation;
   - model timeout / ordering calibration;
   - Semantic Commit Agent timing;
   - workflow interruptibility requirements.
9. Each proposed follow-up task has a narrow responsibility boundary and avoids becoming a catch-all workflow refactor.
10. `docs/tasks/BACKLOG.md` is updated to reflect the retrospective outcome only after Final SPEC and without duplicating active task contracts.
11. No production/game-runtime behavior changes occur.
12. No workflow implementation change is smuggled into the retrospective patch.

## Expected task outputs

Provisional outputs, to be confirmed after Scout:

- `docs/tasks/agent-workflow-pilot-retrospective-v1/RETROSPECTIVE.md` — evidence-backed retrospective and recommendations.
- `docs/tasks/BACKLOG.md` — lifecycle status / prioritized roadmap update derived from the approved retrospective.

No production script modification is expected.

## Uncertainty to resolve with Scout

- Which tracked artifacts preserve enough evidence to reconstruct the first failed Gate attempt after the later successful Gate overwrote canonical `EVIDENCE.md` / review files.
- Whether commit history / task commits contain additional reliable timestamps for Scout, writer, handoff, and rerun stages.
- Whether `.runtime` evidence is intentionally unavailable remotely and therefore must be treated as non-canonical / missing for retrospective purposes.
- Which existing tests or docs define expected `Get-CanonicalReviewPayload` strictness and Gate stop-on-infrastructure behavior, without changing them.
- Whether task descriptor validation already exists elsewhere and the initial `models` omission was a task-creation mistake vs a missing deterministic validation layer.
- Whether the current roadmap should schedule one combined Gate robustness task or separate payload-normalization and stage-resilience tasks.
- Whether model timeout/step calibration has enough samples for a policy recommendation or should remain `MEASURE MORE` after a single production pilot.
- How much commit-message inconsistency was actual pilot friction vs a convenience idea discovered during discussion.

## Scout questions

1. Reconstruct the pilot timeline from canonical GitHub artifacts and commits; identify which stages have reliable timing/attempt evidence and which do not.
2. Locate the exact current contracts/code/tests governing task descriptor validation, Gate payload extraction, reviewer sequencing after infrastructure failure, candidate routing, artifact promotion, and timeout/step limits.
3. Determine which pilot problems are already prevented by current `main` and which remain reproducible workflow gaps.
4. Identify the narrowest plausible follow-up task boundaries for each confirmed gap; do not implement or rewrite the Draft SPEC.
5. Check whether the canonical backlog and architecture workflow docs currently contradict the actual post-pilot behavior or simply need later roadmap status updates.
6. Assess whether one pilot is sufficient to change model ordering/timeouts, or whether the evidence supports only additional measurement.

## Lifecycle gate

This SPEC remains Draft until OpenCode Scout produces and pushes `CONTEXT.md`, and ChatGPT + user re-evaluate the evidence. No retrospective conclusions, roadmap reprioritization, or workflow implementation should be treated as final before that step.
