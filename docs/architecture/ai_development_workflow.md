# AI Development Verification Workflow v1

> Status: experimental development workflow. This document defines the repository contract for AI-assisted task localization and read-only verification. It does not change game runtime behavior.

## 1. Purpose

The project already uses a human + ChatGPT architecture/review loop and Gemini/Antigravity as the primary implementation writer. The main workflow problem is manual context transfer: specifications, implementation summaries, review findings, and test evidence are repeatedly copied between tools.

This workflow uses GitHub-tracked task artifacts as the shared handoff surface:

```text
Human / ChatGPT
  -> canonical task spec in docs/todos/
  -> task descriptor in .ai/tasks/<task-id>/task.json
  -> OpenCode Scout produces CONTEXT.md
  -> Gemini/Antigravity implements the smallest compliant patch
  -> OpenCode read-only reviewers produce review evidence
  -> focused tests run under project test policy
  -> EVIDENCE.md is committed with the candidate patch
  -> ChatGPT performs final semantic / architecture review from GitHub
```

GitHub is the message bus. The user should not need to copy reviewer output between ChatGPT and the IDE when the same information can be committed as task evidence.

## 2. v1 scope

Version 1 deliberately keeps write ownership simple:

- ChatGPT / human defines the task contract and acceptance criteria.
- OpenCode Scout and reviewers are read-only with respect to repository code.
- Gemini/Antigravity remains the only implementation writer during the coding phase.
- The PowerShell orchestration scripts may write task evidence under `.ai/tasks/<task-id>/` and ephemeral runtime data under `.runtime/`.
- No OpenCode repair agent is enabled in v1.
- No automatic merge, force push, branch deletion, or production deployment is performed.

A later version may add a bounded repair loop after reviewer quality has been validated on several real tasks.

## 3. Canonical artifacts and ownership

### 3.1 Task specification

The canonical behavioral contract remains under `docs/todos/` while a task is active. A specification should define, as applicable:

- goal and observed behavior;
- expected behavior;
- scope and non-goals;
- invariants;
- acceptance criteria;
- regression risks;
- required focused tests;
- forbidden shortcuts.

The `.ai/` directory must not become a second behavioral source of truth.

### 3.2 Task descriptor

Each active automated workflow uses:

```text
.ai/tasks/<task-id>/task.json
```

The descriptor points to the canonical spec and declares execution metadata such as the base ref, expected change scope, focused tests, and optional model preferences. JSON is used instead of YAML so the Windows PowerShell scripts can parse it with built-in `ConvertFrom-Json` and no additional parser dependency.

### 3.3 Scout context

`CONTEXT.md` records localization evidence before implementation where possible:

- relevant files and symbols;
- current control flow;
- existing tests;
- shared-state or lifecycle dependencies;
- architecture conflicts;
- uncertainty;
- recommended minimal change surface.

Scout output is evidence, not authority. If it conflicts with the canonical spec or current code, the conflict must be surfaced rather than silently resolved.

### 3.4 Review evidence

The verification gate stores independent reviewer output under:

```text
.ai/tasks/<task-id>/reviews/
```

and writes a summary to:

```text
.ai/tasks/<task-id>/EVIDENCE.md
```

A blocking reviewer finding must identify a concrete contract clause or regression risk and include code evidence. Style preference, unsupported speculation, or architecture taste without evidence is advisory and must not block the gate.

## 4. Roles

### Contract owner

Usually ChatGPT + user. Defines what completion means and decides architecture trade-offs. It must not encode implementation guesses as requirements unless supported by current repository evidence.

### Scout

The OpenCode `scout` agent localizes relevant code and tests. It may read, search, and reason about the repository but may not edit files or execute shell commands. `scripts/ai_scout.ps1` captures its response into the task directory.

### Writer

Gemini/Antigravity reads the canonical spec and `CONTEXT.md`, implements the smallest coherent solution, runs only focused tests allowed by project policy, and invokes the verification gate before declaring the implementation ready for final review.

### Spec reviewer

The OpenCode `spec-reviewer` agent checks the candidate patch against explicit scope, invariants, acceptance criteria, and non-goals. It must not edit code.

### Regression reviewer

The OpenCode `regression-reviewer` agent independently checks callers, shared state, lifecycle boundaries, timing/concurrency implications, sibling paths, and architecture drift. It must not edit code.

### Final reviewer

ChatGPT performs final architecture and semantic review from GitHub using the canonical spec, current diff/commit, evidence artifacts, and relevant repository implementation.

## 5. Task lifecycle

### Phase A — Contract

Create or update the canonical spec and `.ai/tasks/<task-id>/task.json`. The task descriptor must use a unique task id; there is no global `current-task` file because the project uses multiple permanent worktrees.

### Phase B — Localization

From the task worktree:

```powershell
.\scripts\ai_scout.ps1 -Task <task-id>
```

This creates or replaces `CONTEXT.md`. The writer reads it before implementation.

### Phase C — Implementation

Gemini/Antigravity implements only the requested scope. Existing project invariants, `.agents/AGENTS.md`, project skills, and the canonical spec remain authoritative.

### Phase D — Read-only verification

Run:

```powershell
.\scripts\ai_gate.ps1 -Task <task-id>
```

The gate snapshots repository status/diff into ignored `.runtime/` files, invokes the two read-only reviewers, optionally runs only the focused tests declared in `task.json`, and writes `EVIDENCE.md`.

The gate never runs the full test suite. Full-suite execution remains user-only under the project test policy.

### Phase E — Final review

Commit/push the candidate patch and tracked evidence. The user can then ask ChatGPT to review the branch or PR directly from GitHub. Final review must compare the implementation with the canonical spec and current architecture, not merely trust `EVIDENCE.md`.

## 6. Reviewer finding contract

Reviewer output begins with:

```text
VERDICT: PASS | BLOCK
BLOCKING_FINDINGS: <integer>
```

Each blocking finding should contain:

```text
ID:
Severity:
Contract / invariant:
Location:
Claim:
Evidence:
Suggested validation:
Confidence:
```

`BLOCK` is appropriate only for concrete correctness, regression, contract, or architecture-boundary problems. Unsupported possibilities should be marked `ADVISORY`.

The orchestration script parses only the explicit verdict header. It does not ask a model to judge another model's prose.

## 7. Test policy

This workflow inherits the repository's mandatory test rules in [AGENTS.md](../../.agents/AGENTS.md) and the [project test rules](../../.agents/skills/project-test-rules/SKILL.md):

- AI agents may execute only the smallest directly relevant tests.
- The gate rejects obvious full-suite discovery commands such as `unittest discover tests`.
- The full suite is always executed manually by the user when required.
- A reviewer finding is not proof of a bug; tests, direct control-flow evidence, or reproducible behavior should validate blocking claims where practical.

## 8. Multi-worktree invariant

Task state is namespaced by task id:

```text
.ai/tasks/<task-id>/
```

Do not introduce `.ai/current-task`, global mutable task state, or another singleton that would collide across worktrees. Scripts always require an explicit `-Task` parameter.

## 9. Model selection

Agent roles are stable; model names are not. `.opencode/agents/*.md` therefore define role and permission boundaries without hard-coding a model.

Model choice may be supplied by `task.json` or PowerShell arguments. This allows a current low-cost model such as Big Pickle to be used without making repository architecture depend on its continued availability.

Provider credentials are local user configuration and must never be committed.

## 10. Installation boundary

Repository configuration does not install or authenticate OpenCode automatically during normal task execution. Bootstrap is explicit:

```powershell
.\scripts\bootstrap_opencode.ps1
```

After installation, the user completes the interactive OpenCode `/connect` flow. Secrets remain outside the repository.

## 11. v1 non-goals

Version 1 does not implement:

- autonomous repair loops;
- multiple parallel candidate patches;
- automatic PR creation or merge;
- automatic handling of ChatGPT review comments;
- a second task scheduler;
- replacement of existing `.agents/` skills;
- a new test framework;
- automatic full-suite execution.

## 12. Success criteria for the pilot

The workflow is useful if several real tasks show that:

1. Scout context reduces writer localization mistakes.
2. Independent reviewers identify concrete spec/regression problems before final ChatGPT review.
3. Reviewer noise is low enough that findings are actionable.
4. Final ChatGPT review typically requires fewer implementation-repair cycles.
5. The user no longer needs to copy specifications, implementation summaries, or review findings between ChatGPT and the IDE.

IntentRouting Observability is a suitable first pilot because its change surface is small, behavior should remain unchanged, and its logging contract can be verified independently of routing policy.