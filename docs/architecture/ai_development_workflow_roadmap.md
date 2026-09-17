# AI Development Workflow Roadmap

> Document role: **roadmap SSOT** for Blackfire's AI-assisted development workflow. This file records only (1) capabilities already completed and (2) future work that still represents a real unresolved direction or debt.
>
> It does **not** define current operational behavior. Current workflow rules live in [`ai_development_workflow.md`](./ai_development_workflow.md). New unspecced work is indexed from [`../tasks/BACKLOG.md`](../tasks/BACKLOG.md). Historical detail belongs in Git history and completed task packages, not here.

## Current north star

Reduce human copy/paste and repetitive orchestration while keeping semantic authority narrow and auditable.

```text
ChatGPT + user
  -> lightweight repository survey
  -> remote task branch + Draft SPEC/task.json
  -> task_start.ps1 -> TASK_READY
  -> OpenCode Scout (read-only evidence)
  -> ChatGPT + user Final SPEC
  -> Gemini/Antigravity implementation writer
  -> focused verification
  -> fresh base/main ancestry check
  -> OpenCode Gate
       spec-reviewer || regression-reviewer
       deterministic fan-in
       reviewer fingerprint reuse / partial resume
  -> canonical reviews + EVIDENCE pushed to GitHub
  -> ChatGPT final semantic / architecture review
  -> explicit user-authorized merge-commit
  -> task_cleanup.ps1
```

The workflow may become more automated over time, but orchestration must not inherit specification, architecture, implementation, reviewer semantics, or merge authority.

## Completed foundation

### Contract and role foundation

- `scout-efficiency-v1` — bounded Scout localization rather than broad codebase audit.
- `agent-role-contract-hardening-v1-1` — explicit responsibility boundaries among contract owner, Scout, Writer, reviewers, and integration authority.
- `agent-model-fallback-routing-v1-1` — ordered role-specific fallback for infrastructure failures; semantic PASS/BLOCK remains terminal and fallback is not review-shopping.
- `intent-routing-observability` — first production pilot through the hardened workflow.
- `agent-workflow-pilot-retrospective-v1` — completed evidence-backed retrospective; its former Active roadmap state is retired.

### Workflow verification reliability

- `workflow-script-testing-harness` — offline deterministic regression harness for workflow scripts; no longer future work.
- `ai-gate-execution-resilience` — bounded execution and fail-closed process behavior.
- `gate-reviewer-output-contract-reliability` — hardened trusted reviewer-output contract and failure taxonomy.
- `opencode-structured-review-provider-compatibility` — proved OpenCode `1.18.31` + `@opencode-ai/sdk 1.18.31` official v2 structured-output transport.
- Production formal reviewer route with `opencode/big-pickle` — **proven in a real Gate run**: both spec-reviewer and regression-reviewer produced trusted PASS results in `ai-workflow-resume-parallel-gate`.
- `ai-workflow-resume-parallel-gate` — concurrent reviewer fan-out, deterministic fan-in, role-specific fingerprints, reuse, partial resume, `-ForceRefresh`, stale-candidate invalidation, and deterministic coverage.

### Local workspace and dependency foundation

- Per-worktree Node dependency bootstrap/readiness — root manifest/lockfile remain SSOT; Node dependencies are materialized explicitly and Gate fails fast when required dependencies are missing.
- `worktree-environment-junction-bootstrap` — repository-owned Python `.venv` junction bootstrap to the canonical shared environment with fail-closed Windows reparse handling.
- `task-start-orchestration-wrapper` — `task_start.ps1` owns canonical main validation, worktree topology, remote task validation, safe worktree materialization/reuse, `.venv` bootstrap, and `TASK_READY`.
- Safe task cleanup path — `task_cleanup.ps1` owns integrated-ancestry/topology/cleanliness checks and local worktree/branch teardown; native Git stderr handling was hardened so exit code remains authoritative.

### Closeout and GitHub handoff foundation

- `ai-workflow-closeout-contract-convergence` — formalized base freshness before Gate, stage-level reviewer artifact persistence, Gate-level `EVIDENCE.md`, GitHub evidence push before remote final review, user-authorized merge, and separation of local cleanup from tracked task-history retention.

## Future work

### P0 paused — immutable Gate review baseline

#### `gate-immutable-review-baseline-contract`

Status: **Draft task exists; paused by explicit user decision before Scout/implementation.**

Existing remote branch:

```text
task-gate-immutable-review-baseline-contract
```

Purpose:

- make Gate review input reproducible against an exact immutable task baseline rather than a moving symbolic ref;
- record exact baseline SHA and candidate HEAD in reviewer/evidence provenance;
- make malformed/partial reviewer-attempt fallback fail closed unless cleanup safety is mechanically proven;
- distinguish focused-test infrastructure failure from a real completed non-zero test result.

Current architecture already requires a fresh base/main ancestry check before Gate. This paused task is the deeper immutable-provenance design; do not duplicate it as a separate base-ref-preflight roadmap item.

Resume only when the user explicitly unpauses it, then continue from its existing Draft task package/branch rather than recreating it.

### Remaining v1 hardening

#### Task descriptor schema linting

Status: **partially addressed, not complete.**

Current scripts already fail on some missing/mismatched fields such as task id, `base_ref`, or model configuration, so the original failure mode is less severe than during the first pilot. A complete descriptor contract is still unresolved if we want one deterministic validation layer covering required keys, value types, model lists, scope shape, and actionable diagnostics before external agent execution.

Do not create this task solely to duplicate checks that already exist. Promote it only when a concrete schema gap or maintenance need justifies a single canonical validator.

#### Gate diagnostics wording cleanup

Status: **low-priority implementation debt.**

Some human-facing Gate warnings still reflect older all-or-nothing artifact wording even though trusted sibling reviews may now be promoted independently during partial infrastructure failure. Fix only the diagnostic text; do not reopen artifact semantics.

### Trigger-based environment debt

#### `shared-environment-mutation-protocol`

Status: **deferred until dependency mutation becomes real.**

Blackfire intentionally uses one repository-global canonical Python environment consumed through per-worktree `.venv` junctions. Normal Scout/Gate/tests/runtime flows are consumers and must not mutate dependencies as a side effect.

Promote this into a formal task before ad-hoc mutation when any of these occurs:

- Python dependency add/remove/upgrade;
- canonical environment rebuild/migration;
- concurrent processes need to mutate shared dependency state;
- environment drift becomes a demonstrated failure source.

The future task should decide locking/lease semantics, update-vs-build-and-swap, deterministic dependency synchronization, rollback, and whether singleton shared-env ownership remains the right trade-off.

### Measurement track — Writer model calibration

Canonical measurement log: [`../tasks/WRITER_MODEL_BENCHMARK.md`](../tasks/WRITER_MODEL_BENCHMARK.md).

Continue collecting accepted production-task evidence before changing default Writer routing. Record observed implementation/verification time, iteration count, accepted outcome, and unknown values explicitly. Do not derive dynamic routing policy from one or two anecdotes.

### Deferred workflow v2

#### `semantic-commit-agent-v1`

Goal: produce consistent semantic commit metadata from grounded staged diff + Final SPEC/task artifacts without giving another agent architecture authority.

Preferred evolution:

1. deterministic commit helper first;
2. optional schema-constrained local semantic compression only after deterministic behavior is trustworthy;
3. lifecycle-aware commit semantics only after grounding quality is measured.

It must never stage unrelated files, claim unverified tests/Gate status, change task semantics, push, or merge.

#### `workflow-interruptibility-v2`

Goal: explicit `Pause -> Amend -> Resume` semantics for long-running workflow stages.

Must define material-change detection, downstream artifact invalidation, process cancellation/restart, and safe worktree recovery. No live prompt injection into an already-running generation.

#### `workflow-orchestrator-v2`

Goal: automate sequencing across already-proven primitives rather than recreate them.

Potential sequence:

```text
create task package
-> task_start
-> Scout
-> wait for contract-owner Final SPEC
-> Writer handoff
-> focused verification
-> Gate
-> GitHub final-review handoff
-> explicit integration authority
-> cleanup
```

Hard boundary: orchestrator owns sequencing only. It cannot finalize a Draft SPEC, reinterpret reviewer blockers, silently write production code through an unowned role, or merge without explicit authority.

### Future ideas requiring evidence first

Do not schedule these until production evidence shows a real need:

- workflow/status dashboard derived from canonical artifacts;
- autonomous repair/retry loops;
- multi-model reviewer voting/racing beyond the current independent dual-role Gate;
- dynamic local/cloud model routing based on measured latency/cost/quality;
- automatic commit grouping/splitting suggestions;
- richer per-agent execution telemetry;
- near-autonomous orchestration beyond deterministic sequencing.

## Roadmap maintenance rule

When workflow capabilities change:

- update [`ai_development_workflow.md`](./ai_development_workflow.md) if **current operational truth/contract** changes;
- update this roadmap if a meaningful capability becomes **completed** or a still-valid **future direction** changes;
- keep `BACKLOG.md` as an intake/index and link here instead of copying this roadmap;
- omit superseded proposals once their intent has been absorbed by completed work;
- keep historical detail in task packages and Git history rather than growing a permanent graveyard section here.
