# Development Tasks

`docs/tasks/` is the canonical home for new development work that is ready to be specified, implemented, reviewed, or verified.

## Task package

Each active task uses one directory:

```text
docs/tasks/active/<task-id>/
├─ SPEC.md
├─ task.json
├─ CONTEXT.md
├─ EVIDENCE.md
└─ reviews/
   ├─ spec-review.md
   └─ regression-review.md
```

Only `SPEC.md` is the normative behavioral contract. The other files are execution metadata or evidence and must not silently redefine the spec.

## Contract maturity

An active task normally passes through two specification states:

```text
Draft SPEC -> Scout evidence -> Final SPEC -> implementation
```

`SPEC.md` should state its maturity near the top as either:

```text
Status: Draft
```

or:

```text
Status: Final
```

Rules:

- `Draft` means the contract is framed well enough for repository localization, but assumptions may still change after Scout evidence.
- OpenCode Scout may inspect a Draft task and produce `CONTEXT.md` under a light-by-default budget (<= 10 files, <= 1500 words, 8-minute timeout, real-time terminal streaming).
- Scout is an evidence provider, not the contract owner; it must not rewrite `SPEC.md`.
- Failed or timed-out Scout runs never overwrite an existing canonical `CONTEXT.md`.
- Verification infrastructure failure never overwrites the failed reviewer's canonical review and never promotes a new completed `EVIDENCE.md`. A trusted sibling review may be promoted independently and reused on a later identical-input Gate run.
- ChatGPT + user own the architecture/behavior decision and finalize the contract after reviewing Scout evidence and current code.
- Gemini/Antigravity must not begin production implementation while `SPEC.md` is explicitly `Status: Draft`.
- Once `Status: Final`, implementation may proceed. Any later material contract change must be surfaced explicitly rather than silently inferred by the writer.

## Lifecycle

```text
idea / future work
  -> docs/tasks/BACKLOG.md
  -> ChatGPT lightweight repository survey
  -> promote to docs/tasks/active/<task-id>/
  -> Draft SPEC.md + task.json
  -> OpenCode Scout creates CONTEXT.md
  -> ChatGPT re-checks code / architecture using Scout evidence
  -> Final SPEC.md
  -> Gemini/Antigravity implements
  -> verification gate creates/updates reviews/* + completed EVIDENCE.md
  -> push candidate + applicable evidence to GitHub
  -> ChatGPT / human final review
  -> explicit user-authorized integration (package remains ACTIVE)
  -> task_archive.ps1 prepares a detached closeout and pushes archive closeout branch
  -> closeout branch integration and resolver verification (ARCHIVED)
  -> task_cleanup.ps1 removes local task execution/worktree state
  -> tracked task package remains repository history until explicit archival/deletion policy
```

The initial ChatGPT survey should be deep enough to establish the real problem boundary, architecture parent, known invariants, and plausible scope, but should not duplicate the exhaustive localization work delegated to Scout.

Do not create a global `current-task` marker. This repository uses multiple permanent worktrees, so every script requires an explicit task id.

## Backlog ownership

`docs/tasks/BACKLOG.md` is the single shared intake/index for new ideas, unresolved bugs, follow-up observations, and future task candidates that are not yet promoted into a formal task.

- Do **not** create `docs/tasks/active/<task-id>/backlog.md` for task-local follow-up ideas.
- While a task is active, append short follow-up observations to the shared `docs/tasks/BACKLOG.md`; include enough context or the originating task id to recover intent later.
- Once a backlog item is activated, promote it into its own `docs/tasks/active/<new-task-id>/SPEC.md` + `task.json` and avoid keeping two active SSOT descriptions.
- AI-workflow roadmap items remain owned by `docs/architecture/ai_development_workflow_roadmap.md`; the shared backlog may hold a brief intake note only until that item is promoted or incorporated into the roadmap.

This convention is exemplified by commit `7862384c7321b2e370691e5b3c22b96f0f7a4cd7`, which moved a Nemesis/Supervisor follow-up out of a task-local `backlog.md` and into `docs/tasks/BACKLOG.md`.

## Verification gate, parallel reviewers, and resume

Verification runs through:

```powershell
.\scripts\ai_gate.ps1 -Task <task-id>
```

Key execution contracts:
- `spec-reviewer` and `regression-reviewer` execute concurrently using an isolated two-slot process coordinator.
- Each canonical review artifact (`docs/tasks/active/<task-id>/reviews/*.md`) carries an embedded machine-readable fingerprint comment:
  `<!-- blackfire-gate-fingerprint: {"schema":1,"role":"...","hash":"..."} -->`
- Each reviewer stage is independently evaluated on each Gate run:
  - If a valid canonical review artifact exists with a matching input fingerprint, the stage is reused without launching that reviewer process.
  - If missing, stale, or mismatched, that reviewer reruns fresh.
  - Reviewer artifacts are stage-level durable results. If one reviewer suffers infrastructure failure, a trusted sibling result may remain canonical and reusable; the failed reviewer's canonical artifact is not overwritten.
- `EVIDENCE.md` is completed-Gate aggregate evidence and is only regenerated/promoted after all required reviewer stages resolve. Verification-unavailable runs do not promote a new completed `EVIDENCE.md`.
- Pass `-ForceRefresh` to explicitly bypass cached reviewer artifacts and re-execute both reviewers fresh:
  `.\scripts\ai_gate.ps1 -Task <task-id> -ForceRefresh`
- When formal Gate evidence is required for remote final review, the canonical `reviews/*.md` and `EVIDENCE.md` must be committed and pushed to the task branch before ChatGPT's GitHub-based final review.

## Task-history retention vs local cleanup

After task integration, the package remains ACTIVE until explicit `task_archive.ps1` closeout is integrated and the resolver confirms ARCHIVED. `task_cleanup.ps1` only handles local execution/worktree state; it never moves an active package to archive.

Tracked task packages remain repository history unless an explicit archival/deletion policy or user-authorized task says otherwise. Do not equate branch/worktree cleanup with tracked-history deletion.

## task.json

`task.json` contains automation metadata only. `SPEC.md` is always discovered by convention from the same directory and therefore is not repeated as a configurable path.

Example:

```json
{
  "id": "intent-routing-observability",
  "base_ref": "origin/main",
  "scope": [
    "states/navigation_routing.py",
    "tests/"
  ],
  "focused_tests": [
    "tests.test_behavior_navigation_intent",
    "tests.test_behavior_runtime_ports"
  ],
  "models": {
    "scout": null,
    "review": null
  }
}
```

Rules:

- `id` must exactly match the task directory name.
- `SPEC.md` must exist in the same task directory.
- `base_ref` is the comparison baseline used by the verification gate. Before formal Gate, the current configured baseline must be reconciled into the task branch so the Gate snapshot represents task-owned changes rather than stale-branch drift.
- `scope` helps reviewers detect scope creep; it does not override `SPEC.md`.
- `focused_tests` contains Python `unittest` module/class/method targets only and must never contain a full-suite discovery command.
- `models.scout` and `models.review` are optional `provider/model` overrides. `null` uses the locally configured OpenCode default.

## Legacy `docs/todos/`

`docs/todos/` is frozen legacy storage. Do not add new tasks there. When an existing legacy item becomes active work, migrate the relevant material into a new `docs/tasks/active/<task-id>/SPEC.md` and then handle cleanup through the normal branch closeout / canonical archival process.
