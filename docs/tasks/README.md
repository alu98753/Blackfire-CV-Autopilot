# Development Tasks

`docs/tasks/` is the canonical home for new development work that is ready to be specified, implemented, reviewed, or verified.

## Task package

Each active task uses one directory:

```text
docs/tasks/<task-id>/
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
- OpenCode Scout may inspect a Draft task and produce `CONTEXT.md`.
- Scout is an evidence provider, not the contract owner; it must not rewrite `SPEC.md`.
- ChatGPT + user own the architecture/behavior decision and finalize the contract after reviewing Scout evidence and current code.
- Gemini/Antigravity must not begin production implementation while `SPEC.md` is explicitly `Status: Draft`.
- Once `Status: Final`, implementation may proceed. Any later material contract change must be surfaced explicitly rather than silently inferred by the writer.

## Lifecycle

```text
idea / future work
  -> docs/tasks/BACKLOG.md
  -> ChatGPT lightweight repository survey
  -> promote to docs/tasks/<task-id>/
  -> Draft SPEC.md + task.json
  -> OpenCode Scout creates CONTEXT.md
  -> ChatGPT re-checks code / architecture using Scout evidence
  -> Final SPEC.md
  -> Gemini/Antigravity implements
  -> verification gate creates reviews/* + EVIDENCE.md
  -> ChatGPT / human final review
  -> branch closeout extracts durable contracts
  -> task package is deleted when no longer needed
```

The initial ChatGPT survey should be deep enough to establish the real problem boundary, architecture parent, known invariants, and plausible scope, but should not duplicate the exhaustive localization work delegated to Scout.

Do not create a global `current-task` marker. This repository uses multiple permanent worktrees, so every script requires an explicit task id.

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
- `base_ref` is the comparison baseline used by the verification gate.
- `scope` helps reviewers detect scope creep; it does not override `SPEC.md`.
- `focused_tests` contains Python `unittest` module/class/method targets only and must never contain a full-suite discovery command.
- `models.scout` and `models.review` are optional `provider/model` overrides. `null` uses the locally configured OpenCode default.

## Legacy `docs/todos/`

`docs/todos/` is frozen legacy storage. Do not add new tasks there. When an existing legacy item becomes active work, migrate the relevant material into a new `docs/tasks/<task-id>/SPEC.md` and then handle cleanup through the normal branch closeout / canonical archival process.
