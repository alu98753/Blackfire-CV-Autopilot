# AI Workflow Resume + Parallel Gate

Status: Final

## Goal

Reduce AI Gate latency and allow interrupted/repeated Gate runs to continue from still-valid reviewer artifacts instead of always rerunning both reviewers.

This task does exactly two things:

1. run `spec-reviewer` and `regression-reviewer` concurrently, then deterministically fan-in their terminal results; and
2. make each reviewer result reusable when its persisted input fingerprint still matches the current logical inputs.

Do not build a generic workflow engine or broader DAG system.

## Target Architecture

```text
Implementation revision
        |
        +-------------------+
        v                   v
 spec-reviewer       regression-reviewer
        |                   |
 spec-review.md      regression-review.md
 + fingerprint       + fingerprint
        |                   |
        +---------+---------+
                  v
        deterministic Gate aggregate
                  |
                  v
         PASS / CANDIDATE_BLOCKED /
         VERIFICATION_UNAVAILABLE
```

On every Gate invocation, each reviewer stage follows:

```text
canonical review artifact exists
AND
stored fingerprint == current fingerprint
        -> reuse / do not launch reviewer
otherwise
        -> execute reviewer and replace artifact only after valid completion
```

Therefore a partial run such as:

```text
spec-reviewer       PASS
regression-reviewer infrastructure failure
```

may resume later as:

```text
spec-reviewer       REUSE
regression-reviewer RERUN
        \           /
         Gate fan-in
```

provided the spec-reviewer fingerprint is still current.

## Scope

Primary change surface:

- `scripts/ai_gate.ps1`
- focused deterministic workflow-script tests/harness as needed
- `docs/architecture/ai_development_workflow.md`
- `docs/tasks/README.md` only where user-facing Gate resume behavior needs documentation
- task artifacts under `docs/tasks/ai-workflow-resume-parallel-gate/`

A small local helper inside `ai_gate.ps1` may be introduced if needed to keep reviewer-slot execution coherent. Do not extract a repository-wide workflow framework.

## Required Behavior

### 1. Reviewer fan-out

When both reviewers require execution:

- launch `spec-reviewer` and `regression-reviewer` concurrently;
- each reviewer owns its own process, timeout, model-candidate attempts, logs, staging output, and terminal execution result;
- one reviewer failure must not cancel or corrupt the sibling reviewer;
- both reviewers evaluate the same frozen Gate input snapshot;
- wait for both required reviewer stages to reach a terminal result before aggregate classification.

Use the smallest reliable Windows/PowerShell design compatible with the current implementation. Prefer one coordinator managing two independent `.NET Diagnostics.Process` execution slots over PowerShell background-job/runspace infrastructure unless implementation evidence proves otherwise.

### 2. Deterministic fan-in

Do not add a third AI judge.

After both reviewer stages are resolved, aggregate deterministically using the existing Gate meanings:

- all required reviewers valid `PASS` and focused tests pass -> Gate `PASS` / exit `0`;
- any valid semantic reviewer `BLOCK`, or a focused test that completes and fails -> `CANDIDATE_BLOCKED` / exit `2`;
- any required reviewer result unavailable because of launch/timeout/crash/malformed/unsafe cleanup -> `VERIFICATION_UNAVAILABLE` / exit `1`.

Infrastructure failure must remain fail-closed.

### 3. Persistent reviewer artifacts

Canonical reviewer artifacts remain:

- `docs/tasks/<task-id>/reviews/spec-review.md`
- `docs/tasks/<task-id>/reviews/regression-review.md`

Each promoted canonical review must also carry a compact machine-readable fingerprint describing the logical inputs that make that review valid.

The fingerprint metadata should travel with the canonical review artifact itself so reuse still works after a fresh clone/worktree without depending on `.runtime/` state.

Keep the metadata compact; an embedded machine-readable comment/header is sufficient. Do not create a database or separate global cache service.

### 4. Reviewer fingerprint inputs

The fingerprint must be role-specific and responsibility-aware.

At minimum it must change when any input that can materially change that reviewer result changes, including:

- reviewer role;
- Final `SPEC.md` content identity;
- implementation/review snapshot identity used by Gate;
- reviewer contract/prompt identity relevant to that role;
- reviewer model/configuration inputs that materially affect the stage contract.

Do not hash the entire repository indiscriminately. Unrelated repository changes should not invalidate a current review.

The implementation may use deterministic content hashes and/or stable Git identities as long as the resulting validity rule is explicit and testable.

### 5. Reuse / invalidation

For each reviewer independently:

- artifact missing -> run reviewer;
- fingerprint missing or unparsable -> treat as stale and run reviewer;
- fingerprint mismatch -> run reviewer;
- artifact malformed or not a valid completed reviewer result -> run reviewer;
- fingerprint match + valid completed review -> reuse reviewer result without launching that reviewer.

Old historical artifacts without fingerprint metadata require no migration. If encountered by an active Gate run, they are simply stale-once and regenerated.

### 6. Partial resume

Reviewer reuse is independent per role.

If one reviewer completed successfully and the sibling ended with infrastructure failure, the successful reviewer artifact may remain reusable on a later invocation if its fingerprint still matches.

`EVIDENCE.md` remains a completed Gate artifact, not partial success evidence. Do not promote a new completed `EVIDENCE.md` when required verification is unavailable.

### 7. Force refresh

Add a simple Gate switch:

`-ForceRefresh`

Its meaning is only:

> Ignore otherwise reusable reviewer artifacts for this invocation and execute both required reviewers again.

Do not add per-reviewer refresh flags in this task.

`-ForceRefresh` does not trigger implementation work, dependency installation, branch changes, or other workflow stages.

### 8. Artifact safety

Preserve current staged/canonical promotion safety:

- reviewer output is promoted only after the reviewer execution and structural result validation succeed;
- infrastructure-failed execution must not overwrite a previously valid canonical reviewer artifact;
- sibling reviewer execution must not share mutable staging paths;
- `.runtime/ai_gate/<task-id>/` remains runtime scratch/log space, not the authority for long-lived reuse.

### 9. Focused tests

Focused tests remain Gate work and do not need cross-run caching in this task.

This task is specifically about reviewer fan-out and reviewer-result reuse/resume. Do not broaden persistence to every possible workflow stage yet.

## Acceptance Criteria

1. `spec-reviewer` and `regression-reviewer` overlap in execution when both require a fresh run.
2. Deterministic tests prove real overlap without relying on remote LLM timing.
3. Both reviewers receive the same frozen Gate input snapshot.
4. Reviewer timeout/process/log/staging state is isolated per reviewer.
5. One reviewer infrastructure failure does not cancel or corrupt the sibling result.
6. Fan-in waits for every required reviewer stage to resolve.
7. Aggregate result remains deterministic with no additional AI judge.
8. A valid canonical reviewer artifact with matching fingerprint is reused and its reviewer process is not launched.
9. Reviewer reuse is independent: one role may be reused while the other reruns.
10. Final SPEC change invalidates affected reviewer artifacts.
11. Implementation/review snapshot change invalidates affected reviewer artifacts.
12. Relevant reviewer contract/config change invalidates the affected reviewer artifact.
13. Missing/malformed fingerprint or malformed review artifact is treated as stale, never as a cache hit.
14. Historical review artifacts without fingerprints need no migration and are regenerated when next used.
15. `-ForceRefresh` bypasses reviewer reuse and recomputes both reviewers.
16. Infrastructure failure does not overwrite a previously valid canonical reviewer artifact or completed `EVIDENCE.md`.
17. Existing Gate exit meanings remain `0=PASS`, `2=CANDIDATE_BLOCKED`, `1=VERIFICATION_UNAVAILABLE`.
18. Existing focused-test behavior and execution-resilience/provider contracts continue to pass.
19. Architecture/task workflow docs describe parallel reviewers and reviewer artifact reuse/resume.
20. No production/game runtime behavior changes.

## Non-goals

- No generic DAG/workflow engine.
- No workflow database, queue, scheduler, dashboard, or background service.
- No persistence/cache for implementation, Scout, focused tests, or ChatGPT final review in this task.
- No third AI aggregator.
- No reviewer-to-reviewer communication.
- No redesign of reviewer semantic responsibilities.
- No per-reviewer force-refresh flags.
- No migration of completed historical task artifacts.
- No shared Python environment mutation.
- No production/game logic changes.

## Implementation Notes From Scout Evidence

The temporary Gemini read-only survey established that current reviewer serialization is owned by the single synchronous reviewer loop in `scripts/ai_gate.ps1`; the reviewers themselves are architecturally independent.

The OpenCode structured-review adapter already isolates sibling executions using independent child processes, ephemeral ports, in-memory databases, role-specific prompt files, and role-specific candidate artifacts. The main concurrency work therefore belongs in the Gate coordinator, especially replacing shared attempt/unavailable state with reviewer-slot-local state.

The survey also corrected the Draft assumption that Gate already had reuse/generation-state/`-ForceRefresh` behavior. It does not. Reviewer persistence/reuse in this task is a small additive capability, not a consolidation of an existing cache system.

## Ownership

- User + ChatGPT own this Final SPEC.
- Gemini/Antigravity is the production implementation writer for v1.
- OpenCode reviewers remain read-only verification roles.
- GitHub tracked task artifacts remain the handoff surface.
