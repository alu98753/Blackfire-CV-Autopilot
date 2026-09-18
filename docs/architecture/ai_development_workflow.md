# AI Development Verification Workflow v1

> Status: canonical development workflow contract. This document is the repository SSOT for AI-assisted task lifecycle, local workspace topology, environment ownership, role boundaries, verification, integration, and task-worktree lifecycle. It does not define game runtime behavior.

## 1. Purpose

Blackfire uses a contract-driven AI workflow in which semantic authority stays narrow while mechanical setup/teardown is repository-owned automation.

```text
Human / ChatGPT
  -> lightweight repository survey
  -> remote task branch + Draft SPEC.md + task.json
  -> task_start.ps1 -> TASK_READY
  -> Scout evidence
  -> ChatGPT + user finalize SPEC
  -> Gemini/Antigravity implementation
  -> focused tests
  -> independent verification when available/required
  -> ChatGPT final semantic / architecture review
  -> user-authorized integration
  -> explicit task_archive.ps1 closeout
  -> closeout branch integration into origin/main
  -> resolver confirms ARCHIVED
  -> task_cleanup.ps1
```

GitHub-tracked task artifacts are the handoff surface.

Authority boundaries:

- ChatGPT + user own product intent, architecture, scope, invariants, and Final SPEC.
- OpenCode Scout is a read-only evidence provider.
- Gemini/Antigravity is the production implementation writer in workflow v1.
- OpenCode reviewers are independent read-only verification providers when the Gate workflow is used.
- Local agents never merge to `main`.
- ChatGPT may integrate through GitHub only after the applicable closeout requirements pass and the user explicitly authorizes integration.
- Repository scripts own deterministic workspace mechanics; they do not inherit semantic authority.

## 2. Canonical local workspace

```text
E:\Side_Project\Blackfire-CV-Autopilot\
├─ BlackfireCrusade_tool\
│  └─ .venv -> E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot
│
└─ worktrees\
   └─ <task-id>\
      └─ .venv -> E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot
```

`E:\Side_Project\Blackfire-CV-Autopilot\BlackfireCrusade_tool` is the permanent local `main` worktree and canonical integrated runtime/CV validation home. It remains attached to `main`; the old permanent temp-main / detached-main convention is retired.

`E:\Side_Project\Blackfire-CV-Autopilot\worktrees\<task-id>` is the canonical path for new branch-scoped temporary task worktrees.

Existing legacy active worktrees may remain where they are until their task closes. Do not move dirty/active worktrees merely to normalize paths.

Git worktree topology is machine state. Repository automation must inspect `git worktree list --porcelain`; branch ownership must never be guessed from remembered paths.

## 3. Canonical Python environment

Blackfire uses one repository-global Python environment:

```text
E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot
```

Every runnable worktree exposes a local `.venv` Windows junction to that environment and consumes Python through its own path:

```text
.\.venv\Scripts\python.exe
```

Environment invariants:

1. `.venv/` is local-only and Git-ignored.
2. No Git worktree owns the physical environment.
3. Main, task worktrees, Scout, Gate, tests, and runtime validation are environment consumers.
4. Consumer workflows do not run `pip install`, `pip uninstall`, recreate the environment, or silently fall back to system Python.
5. Do not use another worktree's absolute interpreter path.
6. Do not use `pip install -e .` or equivalent worktree-specific editable binding in the shared environment.
7. Shared dependency mutation is a repository-level operation and remains deferred to `shared-environment-mutation-protocol` until explicitly activated.

### 3.1 Python worktree bootstrap ownership

The repository-owned primitive is:

```powershell
.\scripts\worktree_environment_bootstrap.ps1 -WorktreePath <worktree>
```

It validates the registered worktree, validates the canonical environment/interpreter, creates an exact junction when safely absent, verifies the worktree-local interpreter, and fails closed on physical/wrong-target/unsupported/ambiguous states.

For formal AI tasks, users normally do **not** invoke this primitive directly. `scripts/task_start.ps1` owns calling it and validating its JSON result. Direct use is for diagnostics, recovery, or non-standard/manual workflows.

### 3.2 Canonical Node workflow environment

Node workflow tooling uses per-worktree untracked `node_modules` governed by root `package.json` and `package-lock.json`.

```text
package.json + package-lock.json
          |
          v
explicit Node bootstrap (npm ci)
          |
          v
<current-worktree>/node_modules
```

Node invariants:

1. Node dependencies are not shared through junctions.
2. Exact package/version requirements come from the tracked manifest/lockfile and repository Node contract.
3. Materialization is explicit through `.\scripts\bootstrap_node_workflow_deps.ps1` (or repository-approved `npm ci`).
4. Scout/Gate/reviewers/tests do not silently install dependencies.
5. `task_start.ps1` intentionally does **not** bootstrap Node.
6. Scout uses the global OpenCode CLI and does not require repo-local `node_modules`.
7. Node bootstrap is performed only when a later Node consumer actually requires it.

## 4. Canonical task package

Every active AI-assisted task uses:

```text
docs/tasks/active/<task-id>/
├─ SPEC.md
├─ task.json
├─ CONTEXT.md        # after Scout when used
├─ EVIDENCE.md       # after verification when used
└─ reviews/          # reviewer evidence when used
```

`SPEC.md` is the normative task contract. `task.json` is automation metadata. Other files are evidence and must not silently redefine the spec.

## 5. Specification maturity

```text
Draft SPEC
  -> Scout evidence
  -> Final SPEC
  -> implementation
```

Before Draft creation, ChatGPT performs only the lightweight survey needed to establish problem reality, responsibility boundary, architecture parent, known invariants, plausible scope, and uncertainty.

Scout is a bounded read-only evidence provider. It does not own the spec and cannot promote Draft to Final.

ChatGPT + user reconcile Draft assumptions against current code/tests/contracts and set `Status: Final`. Production implementation must not begin while the SPEC is Draft.

If Scout infrastructure is unavailable and the user explicitly authorizes a temporary fallback, an interactive model may perform one read-only evidence survey. That fallback is not the spec owner and cannot begin production implementation while the SPEC remains Draft.

## 6. Roles and write ownership

### Contract owner

ChatGPT + user own task intent, architecture trade-offs, scope, invariants, acceptance criteria, and Final SPEC.

### Scout

OpenCode Scout is read-only and produces localization evidence.

### Writer

Gemini/Antigravity is the production implementation writer in workflow v1 and implements only the Final contract.

### Reviewers

OpenCode `spec-reviewer` (`steps: 8`) and `regression-reviewer` (`steps: 10`) are independent read-only blocker detectors. They check contract compliance, callers, sibling paths, shared state, lifecycle/ownership, timing/concurrency, testability, dead logic, and architecture drift. Valid structured PASS/BLOCK output is terminal for the reviewer role. Reviewer fallback is for infrastructure failure, never semantic review-shopping.

### Final reviewer / remote orchestrator

ChatGPT performs final semantic/architecture review from GitHub using the Final SPEC, current diff/commit, current implementation, tests, and available evidence.

### Integration authority

- Local Gemini/Antigravity/OpenCode do not merge, push to `main`, or delete integrated branches.
- ChatGPT may integrate via GitHub only after the applicable closeout requirements pass and the user explicitly authorizes integration.
- Integration uses merge-commit semantics; squash/rebase must not silently replace repository history policy.
- The user remains the ultimate integration authority.

## 7. Formal remote-to-local task handoff

For formal AI tasks, GitHub already contains:

```text
origin/<approved-task-branch>
docs/tasks/active/<task-id>/SPEC.md
docs/tasks/active/<task-id>/task.json
```

The normal user-facing handoff is exactly the repository wrapper:

```powershell
.\scripts\task_start.ps1 -Task <task-id>
```

For legacy/nonstandard approved branch names:

```powershell
.\scripts\task_start.ps1 -Task <task-id> -Branch <branch-name>
```

`task_start.ps1` owns the mechanical startup sequence:

- discover and validate canonical main;
- inspect actual worktree topology;
- require clean attached `main`;
- `git fetch origin`;
- safely fast-forward canonical main when possible;
- validate the approved remote task branch and current-main ancestry;
- validate remote task artifacts;
- create or safely reuse the canonical task worktree;
- safely fast-forward the task branch to its remote when allowed;
- enforce branch exclusivity/path ownership;
- invoke `worktree_environment_bootstrap.ps1`;
- return exactly one JSON result with `TASK_READY` on success.

It fails closed on dirty/diverged/detached/conflicting/stale states and preserves evidence. It does not merge/rebase stale task branches, synthesize task artifacts, bootstrap Node, launch Scout/Gate, or perform cleanup.

### Manual startup operations are recovery, not the normal path

Users should not manually execute the underlying fetch/worktree-add/branch-switch/junction sequence when `task_start.ps1` can own it. Low-level Git/worktree/bootstrap commands are retained only for:

- diagnosing a fail-closed result;
- repairing a state the wrapper intentionally refuses to mutate;
- non-AI/manual workflows outside the formal task contract.

The detailed recovery rules live in `.agents/skills/branch_start_workflow/SKILL.md`.

## 8. Task lifecycle

### Backlog

Unspecified ideas live in `docs/tasks/BACKLOG.md`. When activated, they are promoted into a unique task package; do not keep two active SSOT descriptions.

### Phase A1 — Contract framing

ChatGPT checks current GitHub `main`, architecture contracts, nearby implementation/tests, and backlog context, then creates the remote task branch plus Draft `SPEC.md` and `task.json`.

### Phase A1.5 — Workspace materialization

The user runs the single repository-owned startup command supplied by ChatGPT:

```powershell
.\scripts\task_start.ps1 -Task <task-id>
```

Success is `TASK_READY`. The user is not expected to manually recreate the internal Git/worktree/.venv steps.

### Phase B — Localization

From the `TASK_READY` worktree:

```powershell
.\scripts\ai_scout.ps1 -Task <task-id>
```

Scout remains an explicit lifecycle step; startup does not invoke it automatically.

### Phase A2 — Contract finalization

ChatGPT + user reconcile Draft assumptions against evidence and publish Final SPEC.

### Phase C — Implementation

Gemini/Antigravity implements the Final SPEC. Applicable repository rules/contracts remain authoritative.

### Phase D — Verification

Before formal Gate, refresh the configured comparison baseline and require the current `base_ref` (normally fetched `origin/main`) to be an ancestor of the task HEAD. A long-lived task branch that is stale or diverged from the current baseline must be reconciled with the latest baseline through repository-approved non-destructive merge semantics and re-verified before Gate. Do not review a stale branch against a newer baseline in a way that makes newer-base files appear to be task-owned deletions or unrelated changes.

When the task/lifecycle requires AI Gate and its infrastructure is available:

```powershell
.\scripts\ai_gate.ps1 -Task <task-id>
```

Gate executes `spec-reviewer` and `regression-reviewer` concurrently using a dual-slot coordinator loop, optionally runs declared focused tests, and promotes trusted review/evidence artifacts. It never substitutes full-suite execution.

Gate aggregate meanings remain:

- `0`: trusted verification passed (all required reviewers PASS + focused tests pass);
- `2`: trusted candidate blocker or configured focused-test failure;
- `1`: verification infrastructure unavailable / no trusted verdict.

Reviewer persistence and resume follow:

- Canonical reviews carry an embedded input fingerprint comment:
  `<!-- blackfire-gate-fingerprint: {"schema":1,"role":"...","hash":"..."} -->`
- Each reviewer stage is independently evaluated:
  - If a valid canonical review exists with a matching input fingerprint, it is reused and its reviewer process is not launched.
  - If missing, stale, or mismatched, the reviewer is executed fresh.
- Reviewer artifacts are stage-level durable results. During a partial infrastructure failure, a trusted sibling reviewer result may be promoted and remain reusable; the failed reviewer's canonical artifact is not overwritten.
- `EVIDENCE.md` is completed-Gate aggregate evidence. A new completed `EVIDENCE.md` is promoted only after all required reviewer stages resolve; verification-unavailable runs do not promote completed Gate evidence.
- `-ForceRefresh` explicitly bypasses cached reviewer artifacts and forces fresh execution of both reviewers.

When formal Gate succeeds and remote ChatGPT final review is required, the canonical `reviews/*.md` and `EVIDENCE.md` must be committed and pushed to the task branch before handoff. Local-only Gate evidence is not sufficient for the GitHub-based final-review step.

### Phase E — Final review, integration, archive closeout, cleanup

Phase E begins only after the applicable verification path is complete and the candidate/evidence required for remote review is available on GitHub.

Preferred closeout path:

1. Push the current task HEAD and applicable canonical review/evidence artifacts.
2. ChatGPT re-checks the expected task HEAD and current base on GitHub and performs final semantic/architecture review.
3. The user explicitly authorizes integration.
4. ChatGPT integrates the task branch through GitHub using merge-commit semantics. The task package remains ACTIVE after this integration.
5. Run `scripts\task_archive.ps1 -Task <task-id>`; it prepares the move in a temporary detached worktree, pushes an isolated remote archive closeout branch, and reports `ARCHIVE_CLOSEOUT_READY`. No persistent local closeout branch is created, and this is not yet `ARCHIVED`.
6. ChatGPT/user integrates the closeout branch through the existing merge authority. The resolver must then find exactly one ARCHIVED package in `origin/main`.
7. Only after closeout integration and ARCHIVED verification is local cleanup delegated to `task_cleanup.ps1`.

A Gate result of `CANDIDATE_BLOCKED` (`2`) or `VERIFICATION_UNAVAILABLE` (`1`) does not advance to integration; it returns to bounded diagnosis/correction/verification.

After archive closeout integration and ARCHIVED verification, normal task cleanup is repository-owned:

```powershell
.\scripts\task_cleanup.ps1 -Task <task-id>
```

Optionally, when repository/user policy calls for deleting the remote branch:

```powershell
.\scripts\task_cleanup.ps1 -Task <task-id> -DeleteRemoteBranch
```

`task_cleanup.ps1` owns the safe teardown mechanics: fetches current remote state, validates topology/cleanliness/integrated ancestry, invokes `worktree_cleanup_safety.ps1` to detach only the exact canonical `.venv` junction, removes the task worktree, verifies topology, and safely deletes the local branch. It fails closed instead of forcing ambiguous or unsafe state.

Local task cleanup removes local execution/worktree state; it does not imply deletion of tracked task-history artifacts. Tracked task packages remain repository history until an explicit archival/deletion policy or user-authorized task says otherwise.

Users should not manually run `worktree_cleanup_safety.ps1`, `git worktree remove`, `git branch -d`, or `git worktree prune` during the normal successful closeout path. Those are lower-level recovery tools only when the wrapper reports a bounded failure requiring diagnosis.

If local permanent `main` must immediately reflect a remote ChatGPT merge for runtime use, synchronize it with a normal fast-forward. Otherwise the next `task_start.ps1` invocation will validate/synchronize canonical main before creating another task workspace.

## 9. Cleanup primitive ownership

`scripts/worktree_cleanup_safety.ps1` is a narrow safety primitive owned by the higher-level cleanup workflow. It classifies/detaches the local `.venv` reparse object only. It does not own ancestry, worktree removal, branch deletion, remote deletion, or general Git repair.

Normal operators should invoke `task_cleanup.ps1`, not manually reconstruct primitive sequencing.

Partial/stale worktree recovery modes remain explicit recovery mechanisms. They are not shortcuts for unknown dirty state and must never become the normal closeout path.

## 10. Test policy

This workflow inherits `.agents/AGENTS.md` and `.agents/skills/project-test-rules/SKILL.md`:

- AI agents run only the smallest directly relevant tests.
- Full-suite execution remains user-only when required.
- Baseline comparisons execute each worktree through its own `.venv\Scripts\python.exe` path.
- Tests that share runtime/game/user-data resources execute serially.
- Docs-only changes do not require unit/full-suite execution; scope still must be audited before commit.

## 11. Multi-worktree task-state invariant

Task state is namespaced by task id under `docs/tasks/active/<task-id>/`. Do not introduce a global mutable current-task singleton. Scripts require explicit task identity.

## 12. OpenCode compatibility and fallback

Repository automation follows the pinned OpenCode version, launcher contract, CLI contract, and provider compatibility baseline documented by the repository. Do not add unverified flags or guess alternate invocation forms. Version/contract mismatch fails fast.

Model fallback is permitted only for mechanically classified infrastructure failures. A valid semantic PASS/BLOCK is terminal. Provider credentials remain local and untracked.

## 13. Windows shell policy

Non-interactive agent shell/tool execution uses:

```text
cmd.exe /d /s /c "<command>"
```

Commands must not wait for stdin. PowerShell automation is wrapped through non-interactive `cmd.exe` execution where commands are being handed to automation/agents. Preserve the intended repository working directory.

For human-facing formal task startup/cleanup, ChatGPT should prefer providing the repository-owned high-level script command rather than exposing the internal command sequence.

## 14. Non-goals

Workflow v1 does not add:

- autonomous repair loops;
- competing implementation patches;
- automatic semantic authority transfer;
- automatic full-suite execution;
- shared-environment mutation locking/rebuild machinery;
- startup-owned Node installation;
- startup-owned Scout/Gate execution;
- cleanup-owned forced repair of ambiguous state;
- automatic merge without explicit user authorization.

The north star is a contract-driven development pipeline with increasingly automated mechanics and deliberately narrow semantic authority.
