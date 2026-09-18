# Gemini Scout Context — task-lifecycle-active-archive

Read-only Scout completed on the task branch; no files were modified by Scout.

## Confirmed affected surface

- Runtime: scripts/task_start.ps1, scripts/ai_scout.ps1, scripts/ai_gate.ps1
- Additional path consumers: tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1, scripts/opencode_structured_review_probe.mjs
- Contracts/docs: docs/tasks/README.md, docs/tasks/BACKLOG.md, docs/architecture/ai_development_workflow.md, .agents/rules/ai-verification-gate.md, .agents/skills/branch_start_workflow/SKILL.md, .agents/skills/branch_completion_workflow/SKILL.md, scripts/README.md, docs/todos/README.md
- Tests: tests/test_task_start_behavioral.py, tests/test_workflow_scripts.py, tests/test_task_cleanup_behavioral.py, plus new resolver/archive tests

## Confirmed lifecycle findings

- Repository still uses flat docs/tasks/<task-id>/ layout.
- No task resolver or archive command exists.
- task_cleanup.ps1 owns local worktree/branch cleanup only.
- task.json is not a lifecycle-state SSOT.
- Final SPEC, EVIDENCE.md, reviews, or branch deletion individually do not prove integration.
- Safe historical migration requires mechanically verified integration into origin/main.
- Active workflow must never silently fall back to archive.

## Recommended order

resolver + caller migration -> current-task bootstrap migration -> Gate/focused tests -> push evidence -> final GitHub review -> merge main -> explicit post-integration archive operation -> task_cleanup.ps1

Archive-before-merge is rejected because Gate resume/final review/evidence lookup still require the canonical active package.

## Bootstrap risk

Moving the current task package before callers understand docs/tasks/active/<task-id>/ creates a bootstrap deadlock. Resolver/caller migration and current-task path migration must be one coherent implementation sequence.

## Required tests

active, missing, archived-only, malformed/id mismatch, ambiguous archive, archive success, destination collision, missing active package, not-integrated closeout, no-deletion, and current-task bootstrap/Gate continuity.