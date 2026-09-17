# AI Development Verification Workflow v1

> Status: canonical development workflow contract. This document defines the repository SSOT for AI-assisted task lifecycle, local workspace topology, environment ownership, role boundaries, verification, and integration authority. It does not define game runtime behavior.

## 1. Purpose

The project uses a contract-driven AI workflow:

```text
Human / ChatGPT
  -> lightweight repository survey
  -> Draft SPEC.md + task.json
  -> OpenCode Scout -> CONTEXT.md
  -> ChatGPT + user finalize SPEC.md
  -> Gemini/Antigravity implementation
  -> focused tests
  -> OpenCode read-only reviewers -> reviews/*
  -> EVIDENCE.md
  -> ChatGPT final semantic / architecture review
  -> user-authorized integration
```

GitHub-tracked task artifacts are the handoff surface. Semantic authority is deliberately narrow:

- ChatGPT + user own product intent, architecture, scope, invariants, and Final SPEC.
- OpenCode Scout provides read-only localization evidence.
- Gemini/Antigravity is the production implementation writer in workflow v1.
- OpenCode reviewers provide independent read-only verification evidence.
- Local agents never merge to `main`.
- ChatGPT may integrate through GitHub only after closeout gates pass and the user explicitly authorizes integration.

## 2. Canonical local workspace

Blackfire uses one permanent local `main` worktree and project-scoped task worktrees:

```text
E:\Side_Project\Blackfire-CV-Autopilot\
├─ BlackfireCrusade_tool\
│  └─ .venv -> E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot
│
└─ worktrees\
   └─ <task-id>\
      └─ .venv -> E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot
```

Canonical responsibilities:

```text
E:\Side_Project\Blackfire-CV-Autopilot\BlackfireCrusade_tool
    = permanent checkout of local main
    = canonical integrated runtime home
    = canonical real CV/runtime validation home

E:\Side_Project\Blackfire-CV-Autopilot\worktrees\<task-id>
    = branch-scoped task worktree
    = temporary
```

Local topology is machine state. Before branch switching, task startup, Scout, Gate, migration, or cleanup, inspect actual ownership with:

```powershell
git worktree list --porcelain
```

Never guess branch ownership from a remembered path. Git's one-branch-per-worktree checkout rule remains authoritative.

Existing active worktrees may remain at their current paths until their task closes. New task worktrees use the canonical project-scoped path above.

## 3. Canonical Python environment

Blackfire uses one repository-global Python environment stored outside every Git worktree:

```text
E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot
```

Every runnable worktree exposes its own local `.venv` Windows junction directly to that environment.

Normal commands consume the environment through the worktree-local path:

```text
.\.venv\Scripts\python.exe
```

### Environment invariants

1. `.venv/` is local-only and Git-ignored.
2. No Git worktree owns the physical environment.
3. Main, task worktrees, Scout, Gate, tests, and runtime validation are environment consumers.
4. Consumer workflows must not run `pip install`, `pip uninstall`, recreate the venv, or otherwise mutate dependencies merely to make a command succeed.
5. Consumer workflows must not silently fall back to system Python when the required worktree-local `.venv` is unavailable.
6. Do not use another worktree's absolute interpreter path. Use the current worktree's `.venv\Scripts\python.exe`.
7. Do not run `pip install -e .` or equivalent worktree-specific editable binding into the shared environment.

Worktree closeout has one safety owner: the branch-completion workflow. Before normal
`git worktree remove <path>`, it must invoke the narrow
`scripts\worktree_cleanup_safety.ps1` helper to prove that `<path>\.venv` is the exact
canonical junction, detach only that local reparse object, and verify that the canonical
environment survived. Missing, physical, wrong-target, unsupported, or ambiguous `.venv`
states fail closed. The helper never performs force removal, pruning, branch deletion, or
shared-environment mutation. Partial removal is classified for explicit stale proof; after
that proof, the same helper may be invoked with `-PartialRemovalRecovery` to inspect residual
`.venv` and detach only an exact canonical junction. Only the branch-completion workflow may
run `git worktree prune --verbose`, and it must re-read `git worktree list --porcelain`
afterward. If a normal detach succeeded but a later worktree removal failed,
`-DetachedPendingRemove` is an explicit retry evidence mode, not a general missing-`.venv`
exemption.
8. Dependency mutation is a repository-level environment operation, not ordinary branch-local work.
9. Safe shared-environment mutation/locking/rebuild semantics are deferred to `shared-environment-mutation-protocol` in `docs/tasks/BACKLOG.md`.

## 3.1 Canonical Node workflow environment

AI workflow tooling (including AI Gate reviewer adapters such as `scripts/opencode_structured_review.mjs` and deterministic workflow tests) uses repository-local Node dependencies.

```text
package.json + package-lock.json
          |
          | dependency SSOT
          v
explicit Node bootstrap (npm ci)
          |
          v
<current-worktree>/node_modules
```

### Node environment invariants

1. **Per-worktree `node_modules`**: Every runnable worktree owns its own untracked, local `node_modules`.
2. **SSOT**: Root `package.json` and `package-lock.json` are the exclusive dependency single source of truth. Exact package versions (`@opencode-ai/sdk@1.18.31`, `cross-spawn@7.0.6`, `undici@6.28.1`) and `engines.node >=18.17` are locked.
3. **No junctions / shared pools**: Node dependencies are small (~3.5 MB) and cheap to materialize; they are **not** shared across worktrees through Windows junctions or external pools. The Python shared venv design is intentionally separate.
4. **Explicit bootstrap only**: Node dependency materialization is an explicit worktree-level operation via `.\scripts\bootstrap_node_workflow_deps.ps1` (or `npm ci` at the worktree root).
5. **Consumer / mutator separation**: Scout, Gate, reviewers, and tests are strict consumers. They must never silently run `npm install` or `npm ci`.
6. **Gate fail-fast preflight**: `scripts/ai_gate.ps1` validates Node executable availability, Node version (`>=18.17`), manifest/lockfile presence, and required package resolvability (`undici`, `@opencode-ai/sdk/v2`) before spawning reviewers. Unbootstrapped worktrees fail fast with clear bootstrap remediation.
7. **Scout isolation**: `scripts/ai_scout.ps1` consumes the global OpenCode CLI and does not depend on repository `node_modules`.

## 4. Canonical task package

Every active AI-assisted task uses:

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

`SPEC.md` is the normative task contract. Other task files are metadata or evidence and must not silently redefine it.

`task.json` contains automation metadata. Scripts resolve `docs/tasks/<task-id>/SPEC.md` directly.

## 5. Specification maturity

The normal task lifecycle is:

```text
Draft SPEC
  -> Scout evidence
  -> Final SPEC
  -> implementation
```

### Draft

A Draft contains enough information to localize the problem:

- goal / observed problem;
- initial scope;
- known invariants;
- non-goals;
- provisional acceptance criteria;
- explicit uncertainty.

ChatGPT performs only the lightweight survey needed to validate the problem, responsibility boundary, architecture parent, known invariants, and plausible scope before creating the Draft.

### Scout

OpenCode Scout is a bounded read-only evidence provider. It localizes actual code, tests, callers, ownership, timing, state, architecture conflicts, and regression risks and writes `CONTEXT.md`.

Scout does not own the spec and cannot promote Draft to Final.

### Final

ChatGPT + user re-read the Draft, Scout evidence, current code/tests, and architecture contracts, resolve unsupported assumptions, and set:

```text
Status: Final
```

Production implementation must not begin while a task SPEC is Draft.

If Scout infrastructure is unavailable and the user explicitly authorizes a temporary fallback, an interactive model may perform one read-only evidence survey. That fallback is not the spec owner and cannot begin production implementation while the SPEC remains Draft.

## 6. Roles and write ownership

### Contract owner

ChatGPT + user own task intent, architecture trade-offs, scope, invariants, acceptance criteria, and Final SPEC.

### Scout

OpenCode Scout is read-only and produces localization evidence.

### Writer

Gemini/Antigravity is the production implementation writer in workflow v1. It implements only the Final contract and preserves verified behavior outside scope.

### Reviewers

OpenCode `spec-reviewer` (`steps: 8`) and `regression-reviewer` (`steps: 10`) are independent read-only blocker detectors. They check contract compliance, callers, sibling paths, shared state, lifecycle/ownership, timing/concurrency, testability, dead logic, and architecture drift. Completed valid StructuredOutput is the terminal reviewer result.

Completed valid StructuredOutput is the terminal reviewer result. Valid structured PASS/BLOCK output is terminal for the reviewer role. Reviewer fallback is for infrastructure failure, never semantic review-shopping.

### Final reviewer / remote orchestrator

ChatGPT performs final semantic and architecture review from GitHub using the Final SPEC, current diff/commit, evidence artifacts, and current implementation.

### Integration authority

- Local Gemini/Antigravity/OpenCode must not merge, push to `main`, delete integrated branches, or perform equivalent integration actions.
- ChatGPT may integrate via GitHub only after required closeout gates pass and the user explicitly authorizes integration.
- Integration uses merge-commit semantics; squash/rebase must not silently replace repository history policy.
- The user remains the ultimate integration authority and may perform the manual merge when preferred.

## 7. Remote-to-local task handoff

After ChatGPT creates or updates task artifacts on GitHub and before any local task command runs:

1. `git fetch origin`.
2. Inspect `git worktree list --porcelain`.
3. Ensure the intended task worktree is attached to the expected task branch.
4. If the task worktree is detached, restore it to the expected task branch before Scout/Gate/implementation.
5. Synchronize the task branch with remote using non-destructive fast-forward semantics where applicable.
6. Respect branch exclusivity; never checkout a branch already attached to another worktree.

Canonical new task path:

```text
E:\Side_Project\Blackfire-CV-Autopilot\worktrees\<task-id>
```

The detailed startup sequence belongs to `.agents/skills/branch_start_workflow/SKILL.md`.

## 8. Task lifecycle

### Backlog

New ideas and not-yet-specified work go to:

```text
docs/tasks/BACKLOG.md
```

When work becomes active, promote it into a unique `docs/tasks/<task-id>/` package. Do not maintain two active SSOT descriptions.

### Phase A1 — Contract framing

ChatGPT checks current GitHub `main`, relevant architecture contracts, nearby implementation, tests, and backlog/task material, then creates a Draft SPEC and task descriptor.

### Phase B — Localization

From the correctly attached task worktree:

```powershell
.\scripts\ai_scout.ps1 -Task <task-id>
```

Production Scout supports the repository-pinned OpenCode contract. The wrapper owns non-interactive process handling, timeouts, artifact validation, and safe promotion of `CONTEXT.md`.

### Phase A2 — Contract finalization

ChatGPT + user reconcile Draft assumptions against evidence and produce Final SPEC.

### Phase C — Implementation

Gemini/Antigravity implements the Final SPEC. `.agents/AGENTS.md`, applicable skills, architecture contracts, and Final SPEC remain authoritative.

### Phase D — Verification

Run:

```powershell
.\scripts\ai_gate.ps1 -Task <task-id>
```

Gate executes `spec-reviewer` and `regression-reviewer` concurrently using a dual-slot coordinator loop, optionally runs declared focused tests, and promotes trusted review/evidence artifacts. It never substitutes full-suite execution.

Reviewer persistence and resume follow:

- Canonical reviews carry an embedded input fingerprint comment:
  `<!-- blackfire-gate-fingerprint: {"schema":1,"role":"...","hash":"..."} -->`
- Each reviewer stage is independently evaluated:
  - If a valid canonical review exists with a matching input fingerprint, it is reused and its reviewer process is not launched.
  - If missing, stale, or mismatched, the reviewer is executed fresh.
- Interrupted or partially failed runs can resume: an infrastructure failure in one reviewer does not discard a valid sibling result.
- `-ForceRefresh` explicitly bypasses cached reviewer artifacts and forces fresh execution of both reviewers.

Gate outcomes remain mechanically distinct:

- `0`: trusted verification passed (all reviewers PASS + focused tests pass);
- `2`: trusted candidate blocker or configured focused-test failure;
- `1`: verification infrastructure unavailable / no trusted verdict.

### Phase E — Final review and closeout

Commit/push the candidate and tracked task evidence. ChatGPT performs final semantic/architecture review from GitHub. Branch closeout follows `.agents/skills/branch_completion_workflow/SKILL.md`.

## 9. Test policy

This workflow inherits `.agents/AGENTS.md` and `.agents/skills/project-test-rules/SKILL.md`:

- AI agents run only the smallest directly relevant tests.
- Gate rejects obvious full-suite discovery targets.
- Full-suite execution remains user-only when required.
- Baseline comparisons must execute each worktree through its own `.venv\Scripts\python.exe` path.
- If tests share runtime/game/user-data resources, execute them serially rather than concurrently.

A reviewer finding is not proof of a bug; blocking claims require concrete contract/regression evidence.

## 10. Multi-worktree task-state invariant

Task state is namespaced by task id under:

```text
docs/tasks/<task-id>/
```

Do not introduce a global mutable current-task singleton. Scripts require explicit task identity.

## 11. OpenCode compatibility and fallback

Repository automation follows the pinned OpenCode version, launcher contract, CLI contract, and provider compatibility baseline documented by the repository, requiring exactly OpenCode CLI version 1.18.31.

Do not add unverified CLI flags or guess alternate invocation forms. Version/contract mismatch must fail fast.

Model routing rules:

- role boundaries remain stable even if candidate models change;
- ordered fallback is permitted only for mechanically classified infrastructure failures;
- a valid semantic PASS/BLOCK is terminal;
- reviewer infrastructure exhaustion must not silently substitute Gemini as an independent reviewer;
- degraded interactive review, when explicitly used by the outer workflow, is labeled non-independent and does not create Gate PASS authority;
- provider credentials remain local and untracked.

## 12. Installation boundary

Task execution does not silently install or authenticate OpenCode. Bootstrap is explicit through repository-owned setup tooling. Secrets remain outside the repository.

Python project dependency provisioning is likewise outside Scout/Gate/normal test responsibility; the worktree-local `.venv` must already resolve to the canonical environment.

## 13. Windows shell policy

Non-interactive agent shell/tool execution uses:

```text
cmd.exe /d /s /c "<command>"
```

Commands must not wait for stdin. PowerShell automation is wrapped through non-interactive `cmd.exe` execution. Preserve the intended repository working directory and never silently switch to the user home directory.

## 14. Non-goals

Workflow v1 does not add:

- autonomous repair loops;
- competing implementation patches;
- automatic semantic authority transfer;
- automatic full-suite execution;
- dependency mutation orchestration;
- shared-environment mutation locking/rebuild machinery;
- automatic merge without explicit user authorization.

The north star is a contract-driven development pipeline with increasingly automated mechanics and deliberately narrow semantic authority.
