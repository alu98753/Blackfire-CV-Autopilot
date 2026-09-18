# Task Lifecycle Active / Archive

Status: Final

## Goal

Separate currently active development tasks from completed task history without losing tracked evidence, and make task-package lookup a single repository-owned responsibility.

Canonical layout:

docs/tasks/active/<task-id>/  = active workflow package
docs/tasks/archive/<integration-year>/<task-id>/ = historical package

Active workflow commands operate only on active packages. Archived packages remain durable repository history and are never silently reactivated.

## Architecture decisions

1. Path is the lifecycle-location SSOT. Do not add task.json.status as lifecycle authority.
2. SPEC.md remains the behavioral contract; task.json remains automation metadata.
3. Add scripts/task_package_resolver.ps1 as the single owner of canonical task-package path semantics.
4. Resolver classifications must cover ACTIVE, ARCHIVED, MISSING, MALFORMED, and AMBIGUOUS_ARCHIVE.
5. Resolver semantics must be usable by both checked-out filesystem consumers and Git-ref/tree consumers.
6. task_start.ps1 may continue using Git plumbing for remote-tree inspection, but must obtain canonical active relative paths from the resolver rather than reconstructing docs/tasks/... itself.
7. ai_scout.ps1 and ai_gate.ps1 must resolve only ACTIVE packages.
8. Archived-only tasks must fail explicitly; no active-command fallback to archive.
9. No long-term fallback from docs/tasks/active/<task-id> back to legacy docs/tasks/<task-id>. A temporary bootstrap bridge is allowed only during this task and must be removed before acceptance.

## Canonical lifecycle

idea -> BACKLOG -> remote task branch -> docs/tasks/active/<task-id>/ Draft SPEC + task.json -> Scout/CONTEXT -> Final SPEC -> implementation -> focused tests/Gate -> push evidence -> final GitHub review -> user-authorized integration into origin/main -> explicit archive closeout -> task_cleanup.ps1

Archive is after integration and before local cleanup. Gate resume/final review/evidence lookup require the package to remain active until integration completes.

## Archive command

Add scripts/task_archive.ps1 -Task <task-id>.

It owns repository task-history closeout only and must:
- resolve exactly one active package;
- verify task integration into current origin/main using Git ancestry/repository evidence;
- derive archive year from the UTC calendar year of the verified integration commit;
- move the full tracked package to docs/tasks/archive/<year>/<task-id>/;
- preserve all tracked artifacts/history;
- fail closed on missing, archived-only, ambiguous, malformed, destination collision, or unproven integration;
- never perform worktree/.venv/local-branch cleanup;
- never use force push, reset --hard, clean -fd, blind prune, or destructive history rewriting;
- preserve canonical-main cleanliness; on failure it must not leave main dirty or locally divergent;
- report exactly what repository state changed and must not claim archival completion unless the archive move is durably represented in repository history.

Status: Final, EVIDENCE.md, reviews, branch deletion, timestamps, or folder age are not sufficient integration proof by themselves.

## Current-task bootstrap migration

This task begins at the legacy flat path docs/tasks/task-lifecycle-active-archive/. Avoid bootstrap deadlock with this sequence:
1. introduce resolver semantics and caller support;
2. update harness/probe/contracts/tests for active-path semantics;
3. move this task package and explicitly selected active packages to docs/tasks/active/;
4. run focused tests/Gate against the active path;
5. remove every temporary flat-layout compatibility path before acceptance.

## Existing task migration

- Move still-active/paused/unresolved formal tasks needed by the workflow to docs/tasks/active/<task-id>/.
- Do not bulk-archive by name, age, Final status, EVIDENCE, or reviews.
- Historical packages may be archived only when integration into origin/main can be mechanically proven.
- Uncertain packages remain unarchived and are reported as migration debt.
- docs/todos/ remains frozen legacy storage.

## Confirmed affected scope

Production/scripts:
- scripts/task_package_resolver.ps1 (new)
- scripts/task_archive.ps1 (new)
- scripts/task_start.ps1
- scripts/ai_scout.ps1
- scripts/ai_gate.ps1
- scripts/task_cleanup.ps1 only for boundary/documentation integration if required
- scripts/opencode_structured_review_probe.mjs
- scripts/README.md

Tests/harness:
- tests/test_task_start_behavioral.py
- tests/test_workflow_scripts.py
- tests/test_task_cleanup_behavioral.py if cleanup-boundary assertions change
- tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1
- new resolver/archive focused tests

Documentation/contracts:
- docs/tasks/README.md
- docs/tasks/BACKLOG.md
- docs/architecture/ai_development_workflow.md
- .agents/rules/ai-verification-gate.md
- .agents/skills/branch_start_workflow/SKILL.md
- .agents/skills/branch_completion_workflow/SKILL.md
- docs/todos/README.md

## Invariants

- GitHub remains task/history SSOT.
- Task id must match package directory name.
- No global current-task marker.
- task_cleanup.ps1 remains local worktree/branch/environment cleanup only.
- Existing worktree topology, branch exclusivity, shared Python environment, Gate, and cleanup safety contracts remain intact.
- No silent dependency/environment mutation.
- Runtime game behavior is untouched.
- Task-package path semantics have one implementation owner.

## Non-goals

- Redesign Scout/Gate model routing or reviewer execution.
- Replace task_start.ps1 worktree orchestration.
- Change shared Python environment ownership.
- Delete completed task history.
- Add a task database/global mutable state.
- Reorganize docs/todos/.
- Guess legacy completion.
- Archive before final review/integration.

## Required deterministic tests

Resolver:
- ACTIVE
- MISSING
- ARCHIVED-only
- malformed/missing artifact
- task.json id mismatch
- ambiguous archive
- canonical relative path generation for local and Git-ref consumers

Archive:
- successful mechanically integrated archive
- destination collision
- missing active package
- archived-only request
- not-integrated/incomplete task
- ambiguous integration evidence
- deterministic integration-year selection
- tracked move without artifact deletion
- failure leaves protected repository state safe/clean

Workflow regression:
- task_start remote preflight uses active path and preserves startup guarantees
- Scout prompt/path resolves active package
- Gate prompt/excludes/reviews/EVIDENCE resolve under active package
- harness fixture uses active layout
- current-task bootstrap reaches Gate after migration
- archived-only rejected by start/Scout/Gate
- task_cleanup remains local-cleanup-only

## Acceptance criteria

1. Canonical active location is docs/tasks/active/<task-id>/.
2. Canonical archive location is docs/tasks/archive/<verified-integration-year>/<task-id>/.
3. One shared resolver owns task-package path semantics.
4. Start, Scout, and Gate no longer independently construct the active package root.
5. Active commands fail explicitly for archived-only tasks.
6. Remote Git-tree and local filesystem validation share canonical path semantics.
7. task_archive.ps1 exists and fails closed unless integration into origin/main is mechanically verified.
8. Archive year comes from verified integration commit metadata.
9. Archive preserves the entire tracked package and performs no local cleanup.
10. task_cleanup.ps1 behavior/safety remain unchanged.
11. Current task migrates without bootstrap deadlock.
12. No temporary flat-layout compatibility remains.
13. Docs, agent rules/skills, harness, and probe no longer teach flat active layout.
14. Existing migration is explicit; uncertain historical tasks are not guessed into archive.
15. Focused deterministic tests pass without environment mutation.
16. Final GitHub review can still locate active SPEC/context/evidence before integration; archive is a distinct post-integration closeout action.