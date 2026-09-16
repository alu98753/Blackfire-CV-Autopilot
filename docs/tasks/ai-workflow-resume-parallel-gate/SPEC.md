# AI Workflow Resume + Parallel Gate

Status: Draft

## Goal

Reduce end-to-end AI workflow latency and make interrupted workflow execution safely resumable by evolving the current linear orchestration into a small persistent-stage dependency model, without introducing a generalized workflow engine.

This task has two coupled goals:

1. run `spec-reviewer` and `regression-reviewer` concurrently when both are required, then deterministically fan-in their completed outcomes into the existing gate decision; and
2. persist enough stage-result identity/validity metadata that a later invocation can reuse a completed artifact only when it is still valid for the current inputs, otherwise rerun the stale/missing stage and the minimum necessary downstream work.

## Current evidence from initial repository survey

- `scripts/ai_gate.ps1` currently selects `spec-reviewer` and `regression-reviewer` and executes them through one sequential reviewer loop.
- The reviewers are architecturally independent, read-only roles and consume substantially overlapping frozen task/spec/implementation evidence, so they are natural fan-out siblings rather than producer/consumer stages.
- Existing task handoff is already artifact-oriented: `SPEC.md`, `CONTEXT.md`, implementation results, per-reviewer result artifacts, gate reports/evidence, and task metadata are tracked or otherwise persisted.
- Existing gate logic already contains narrower reuse concepts such as prior review artifact handling, generation state, current implementation revision checks, and `-ForceRefresh`; this task should converge those mechanisms instead of building an unrelated cache.
- The earlier `ai-gate-execution-resilience` task deliberately kept reviewers sequential in v1. This task is the explicit follow-up that may parallelize them while preserving its bounded-process, fail-closed, canonical-artifact-safety invariants.
- Latest `main` at task creation is `63d5c93ce88dda7bc580645f664f5efaa4adaf88`, which includes the canonical project worktree/shared-environment convention migration.

## Scope

Primary expected change surface:

- `scripts/ai_gate.ps1`
- existing AI workflow/task-runner helpers used by gate artifact state, generation state, or task transitions, only where required by the final design
- `docs/architecture/ai_development_workflow.md`
- `docs/tasks/README.md` where persistent-stage/resume semantics become user-visible contract
- focused deterministic workflow-script tests/probes
- this task's tracked artifacts under `docs/tasks/ai-workflow-resume-parallel-gate/`

The final implementation surface must be narrowed after the temporary Gemini read-only survey establishes the actual helper ownership and concurrency hazards.

## Known invariants

1. User + ChatGPT remain task/spec owners. Scout/review evidence may challenge assumptions but does not own or finalize the specification.
2. Production implementation remains closed while this SPEC is Draft.
3. Gemini/Antigravity may be used in this round only as an explicitly authorized temporary read-only Scout/evidence provider before SPEC finalization.
4. After SPEC Final, Gemini/Antigravity remains the production implementation writer; OpenCode reviewers remain read-only.
5. GitHub tracked task artifacts remain the principal handoff surface.
6. `spec-reviewer` and `regression-reviewer` remain independent read-only semantic reviewers. Parallel execution must not introduce reviewer-to-reviewer dependency or shared mutable semantic state.
7. Gate remains fail-closed. Missing, malformed, timed-out, crashed, or otherwise unavailable required verification may not be converted into PASS.
8. Existing execution-resilience semantics remain intact: bounded child execution, client-only termination, structural output validation, canonical artifact promotion only from valid completed results, and preservation of previous valid canonical evidence across infrastructure failure.
9. A semantic reviewer `BLOCK` remains distinct from infrastructure failure.
10. Gate aggregation after reviewer fan-in should be deterministic and must not add another LLM reasoning stage merely to combine reviewer outcomes.
11. Parallel reviewers must evaluate the same frozen logical input revision for a gate attempt.
12. Reuse must be input-aware. Artifact existence alone is never sufficient to skip a stage.
13. No stale artifact may silently survive a relevant SPEC, implementation, contract, or stage-configuration change.
14. `-ForceRefresh` must continue to mean an explicit bypass/invalidation of otherwise reusable workflow evidence according to a documented boundary.
15. `task.json` may index/project workflow state, but must not become the storage location for full Scout/reviewer prose or evolve into a workflow God Object.
16. Resume/persistence must preserve multi-worktree/task-id isolation.
17. No production/game runtime behavior changes are allowed.
18. Normal workflow operations are environment consumers. They may not mutate the canonical shared Python environment, perform editable installs, or silently fall back to system Python.
19. Local execution remains non-interactive and follows the repository-pinned OpenCode launcher/CLI/provider contracts; no invented CLI flags are permitted.

## Target architecture

### 1. Reviewer fan-out / fan-in

Conceptually:

```text
                    ┌─ spec-reviewer ─────────┐
Gate reviewer input ┤                         ├─ deterministic fan-in → gate aggregate
                    └─ regression-reviewer ──┘
```

When both reviewers are required:

- launch them concurrently from one frozen gate input identity;
- keep process ownership, timeout, log/output staging, invocation identity, and canonical result paths isolated per reviewer;
- allow one reviewer to finish independently of the other;
- wait for every required reviewer to reach a terminal execution outcome before aggregate classification;
- preserve a valid completed sibling result if the other reviewer fails at infrastructure level, subject to the final persistence-validity contract;
- aggregate only after fan-in and without another model call.

The temporary Scout must determine the smallest concurrency primitive compatible with the current PowerShell/process wrapper and verify that current shared variables, jobs/event handlers, temp paths, logging, environment state, or task-runner helpers are safe for concurrent use.

### 2. Persistent stage result contract

A stage output is reusable only if both conditions hold:

```text
artifact exists
AND
artifact input identity == current stage input identity
```

The implementation should define the smallest coherent persisted validity record. Exact representation is intentionally provisional until Scout evidence is available.

At minimum the design must account for relevant inputs such as:

- task/stage identity;
- Final SPEC revision/content identity where relevant;
- implementation revision/commit where relevant;
- workflow/reviewer contract version or equivalent code/config identity when it can change stage semantics;
- stage-specific parameters that materially change the result;
- completion/outcome status;
- produced artifact pointer(s).

Do not assume one universal fingerprint must include every repository file. Fingerprints should follow real stage responsibility boundaries so unrelated changes do not invalidate everything.

### 3. Resume / selective invalidation

On a repeated invocation:

- current and valid completed stage → reuse/skip;
- missing stage result → execute;
- stale input identity → execute;
- incomplete/interrupted/infrastructure-failed stage → do not treat as valid completion;
- changed upstream input invalidates only stages whose declared logical inputs changed and downstream results that depend on those outputs;
- an interrupted run may continue from the latest set of independently valid artifacts rather than restart the full pipeline.

The final design should make partial Gate completion useful: for example, if one reviewer completed validly and the sibling was interrupted, a later invocation should be able to reuse the still-current reviewer result if doing so is compatible with the existing canonical-artifact safety model.

### 4. State index versus evidence artifacts

Prefer keeping substantive evidence in dedicated artifacts. `task.json` or another small manifest/index may expose current stage state/pointers/fingerprints if that fits existing ownership, but the final design must avoid duplicating full evidence bodies into task metadata.

### 5. Compatibility with existing gate semantics

This task must explicitly reconcile persistence/resume with:

- prior reviewer artifact reuse;
- generation state;
- implementation commit/revision checks;
- `-ForceRefresh`;
- reviewer timeout/retry behavior;
- canonical versus runtime/staged artifacts;
- `GATE_REPORT.md` / evidence generation;
- any automatic lifecycle/finalization behavior currently triggered after gate success.

Existing overlapping mechanisms should be simplified or made authoritative rather than layered into contradictory caches.

## Provisional acceptance criteria

1. When semantic review requires both reviewers, `spec-reviewer` and `regression-reviewer` execute concurrently rather than sequentially.
2. Deterministic evidence demonstrates actual overlap/concurrency rather than merely reordered sequential calls.
3. Both reviewers receive the same frozen SPEC/implementation logical revision for one gate attempt.
4. Per-reviewer timeout, retry, stdout/stderr, staging, and canonical promotion remain isolated and safe under concurrency.
5. One reviewer timing out/crashing cannot corrupt, cancel, overwrite, or misclassify the sibling review result.
6. Fan-in waits for terminal outcomes from all required reviewers before aggregate Gate classification.
7. Gate aggregate remains deterministic and introduces no additional LLM judge/aggregation request.
8. Existing PASS / candidate-block / infrastructure-block semantics remain fail-closed and compatible unless the Final SPEC explicitly documents a necessary migration.
9. Every stage made resumable by this task has an explicit validity contract based on its relevant logical inputs, not artifact existence alone.
10. A current valid artifact is reused without rerunning its stage.
11. A stale, missing, incomplete, malformed, or infrastructure-failed artifact is not reused as successful completion.
12. Changing Final SPEC identity cannot silently reuse reviews or implementation evidence tied to the old SPEC when that stage depends on SPEC.
13. Changing implementation revision cannot silently reuse reviewer results tied to the previous implementation.
14. Unrelated repository changes do not unnecessarily invalidate all stages when they are outside a stage's declared inputs.
15. Interrupted Gate execution can resume from still-valid completed reviewer evidence where safe, rerunning only missing/stale required siblings and dependent aggregation.
16. `-ForceRefresh` behavior is explicit, tested, and cannot accidentally reuse a result that the flag promises to recompute.
17. Existing tracked artifact formats remain compatible where practical; any migration is deterministic and documented.
18. `task.json` remains a bounded metadata/index artifact rather than a container for full reviewer/Scout reasoning.
19. Deterministic focused tests cover at least: reviewer overlap; both-pass fan-in; one semantic BLOCK; one infrastructure failure; sibling artifact preservation; interrupted/partial resume; valid cache hit; stale SPEC invalidation; stale implementation invalidation; relevant stage-config invalidation; `-ForceRefresh`; deterministic aggregate; and no shared-path/process leakage.
20. Architecture/task workflow documentation describes fan-out/fan-in and persistence/resume semantics.
21. Existing gate execution-resilience invariants and OpenCode provider/CLI contracts remain passing.
22. No game/runtime behavior changes.

## Non-goals

- Do not build a generic DAG framework, distributed scheduler, queue service, workflow server, or dashboard.
- Do not parallelize stages that have real data dependencies merely for latency.
- Do not add an AI aggregator/judge after the two reviewers.
- Do not make reviewers communicate with or influence each other before fan-in.
- Do not redesign reviewer semantic responsibilities unless Scout evidence reveals a correctness blocker.
- Do not redesign the production implementation agent role.
- Do not mutate shared Python dependencies or invent a shared-environment concurrency protocol; that remains a separate repository-level concern.
- Do not introduce `pip install -e .` or any worktree-specific source binding into the shared environment.
- Do not change production/game logic.
- Do not let the temporary Gemini Scout edit production source, implement this task, or promote this Draft SPEC to Final.

## Uncertainty requiring temporary Scout evidence

Before this SPEC may become Final, establish:

1. Which exact functions/files currently own reviewer child-process execution, generation state, prior-artifact validation, artifact promotion, aggregate report generation, and lifecycle finalization?
2. Are any current reviewer execution variables, event handlers/jobs, environment variables, temp paths, log names, OpenCode session identifiers, or task-runner helpers unsafe when two reviewers run concurrently?
3. What is the smallest reliable PowerShell concurrency mechanism given the current process wrapper and repository-supported Windows/PowerShell environment?
4. Which persisted artifact is currently authoritative for a review's input revision, and where are there duplicate/overlapping cache-validity rules?
5. What exactly does `-ForceRefresh` invalidate today?
6. Can a valid completed canonical reviewer artifact safely survive a sibling infrastructure failure and be reused on the next gate attempt without violating existing `EVIDENCE.md`/gate-attempt semantics?
7. Which logical input components are necessary for each proposed persisted stage fingerprint, and which tempting components would cause needless global invalidation?
8. Should the state index live in existing generation state, `task.json`, a per-stage manifest, or another already-established artifact boundary?
9. How does gate success interact with current auto-finalize/task-lifecycle behavior, and what resumed path must preserve that behavior exactly once?
10. Which deterministic test harnesses already exist for `ai_gate.ps1`, and what minimal new seams are required to prove true overlap and resume behavior without live model calls?
11. Are there backwards-compatibility requirements from completed tasks that already contain older result artifacts without the new validity metadata?

## Temporary Scout rule for this task

The user explicitly authorized Gemini/Antigravity as a one-time temporary Scout fallback for this round. Its role is evidence provider only. It may inspect the repository read-only and produce `CONTEXT.md` as the tracked survey artifact, but it must not modify this SPEC, `task.json`, workflow/production source, tests, or production implementation. ChatGPT + user retain responsibility for resolving the uncertainties above and promoting this SPEC from Draft to Final.