# AI Task Artifacts

This directory stores tracked handoff artifacts for AI-assisted development tasks.

Each active task uses its own namespace:

```text
.ai/tasks/<task-id>/
```

Required descriptor:

```text
task.json
```

Typical generated artifacts:

```text
CONTEXT.md
EVIDENCE.md
reviews/spec-review.md
reviews/regression-review.md
```

The canonical behavioral specification remains under `docs/todos/`; `.ai/tasks/` must not become a second source of truth.

## task.json schema

Example:

```json
{
  "id": "intent-routing-observability",
  "spec": "docs/todos/intent_routing_observability_spec.md",
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
- `spec` must be a repository-relative Markdown file and is the canonical contract.
- `base_ref` is the comparison baseline used by the verification gate.
- `scope` is descriptive and helps reviewers detect scope creep; it does not override the spec.
- `focused_tests` contains Python `unittest` module/class/method targets only. It must never contain a full-suite discovery command.
- `models.scout` and `models.review` are optional `provider/model` overrides. Leave them null to use the locally configured OpenCode default model.

Because the project uses multiple permanent worktrees, scripts always require an explicit task id. Do not add a global `.ai/current-task` file.