# Node Workflow Dependency Bootstrap

Status: Draft

## Goal

Define and implement a clear, repeatable, multi-worktree-safe bootstrap contract for repository-owned Node workflow dependencies so every runnable Blackfire worktree can reliably execute repository Node tooling such as `scripts/opencode_structured_review.mjs` without depending on another worktree's incidental `node_modules` state.

The current blocking symptom is a repository workflow consumer failing before reviewer startup because Node ESM cannot resolve the declared `undici` package. The dependency is already declared and locked; the missing contract is how a fresh/runnable worktree materializes and validates repository-local Node dependencies.

## Observed Problem / Lightweight Survey

Current `main` at task creation: `cce3f30ea65c090a40b6d69d73e76455bb7e9b79`.

Confirmed repository facts:

- `package.json` exists at repository root and declares exact versions:
  - `@opencode-ai/sdk`: `1.18.31`
  - `cross-spawn`: `7.0.6`
  - `undici`: `6.28.1`
- `package.json` declares `engines.node >=18.17`.
- root `package-lock.json` exists (`lockfileVersion: 2`) and locks the same dependency set, including `undici@6.28.1`.
- `.gitignore` excludes `node_modules/`; therefore installed packages are intentionally local machine state rather than tracked task state.
- tracked repository search found no existing `npm ci`, `npm install`, or explicit `node_modules` ownership/bootstrap flow for repository-local Node packages.
- `scripts/bootstrap_opencode.ps1` bootstraps/verifies the globally available OpenCode CLI only. It does not materialize repository-local package dependencies.
- `scripts/ai_gate.ps1` launches the structured-review adapter as `node <repoRoot>\scripts\opencode_structured_review.mjs ...` with the current worktree repository root as working directory. It does not provision dependencies.
- `scripts/opencode_structured_review.mjs` has a static `undici` import and dynamically imports `@opencode-ai/sdk/v2`; those packages therefore belong to the repository workflow runtime dependency boundary.
- deterministic Node workflow tests already exist under `tests/workflow_scripts/`; `tests/test_opencode_structured_review_probe.py` demonstrates the existing pattern of invoking Node tests without a real LLM call.
- the canonical AI workflow already establishes that normal Scout/Gate/tests/runtime are environment consumers and that Git worktree topology must be inspected rather than guessed.
- the canonical shared Python environment contract is separate and remains unchanged by this task.

The user-provided local evidence additionally confirms that both the blocked task worktree and main worktree currently lack `node_modules/undici`, and that the formal Gate fails with `ERR_MODULE_NOT_FOUND` before the Node adapter can start its reviewer work.

## Responsibility Boundary

This task owns repository workflow **Node dependency materialization, validation, bootstrap guidance, and consumer fail-fast behavior**.

It does not own:

- OpenCode reviewer semantics;
- the structured-review protocol itself;
- Gate parallelism/resume behavior;
- Python environment ownership;
- game/runtime dependencies or behavior.

Dependency declaration (`package.json` / lockfile) is already present. This task should establish who performs installation, where installed dependencies live, how a worktree becomes runnable, and how consumers report an unbootstrapped or incompatible state.

## Ownership Models Under Evaluation

### Option A — Per-worktree install

Each runnable worktree owns its own untracked `node_modules` materialized from the repository lockfile with an explicit bootstrap operation such as `npm ci`.

Preliminary assessment:

- **Reproducibility:** strong when `npm ci` is driven by the committed lockfile.
- **Multi-worktree correctness:** naturally strong because Node resolves packages from the current worktree and no worktree depends on another worktree's mutable installation.
- **Portability:** straightforward; standard npm behavior with no custom resolution layer.
- **Bootstrap complexity:** low; requires a dedicated/documented explicit operation plus consumer readiness checks.
- **Disk cost:** duplicated across runnable worktrees.
- **Install frequency:** once per fresh worktree, and again when the committed dependency state changes or local install state is invalidated.
- **Mutation boundary:** `npm ci` must be an explicit repository/worktree bootstrap action, never an implicit Scout/Gate/test/runtime side effect.
- **Failure mode:** local and diagnosable; an unbootstrapped worktree should fail fast with exact bootstrap guidance.

### Option B — Repository-level canonical shared Node dependency environment

One physical dependency installation would be shared by all worktrees through a resolution mechanism such as worktree-local junctions/symlinks or another explicit Node/package-manager-compatible indirection.

Preliminary assessment:

- **Disk cost:** lower than repeated per-worktree installations.
- **Install frequency:** potentially lower for identical lockfile state.
- **Complexity:** materially higher because worktrees may temporarily carry different `package.json`/lockfile revisions during concurrent branch work.
- **Lockfile correctness:** a single mutable shared installation risks coupling worktrees whose checked-out dependency declarations differ.
- **Node resolution:** a worktree-local `node_modules` link could technically fit Node resolution, but link ownership, replacement, validation, and cleanup become additional repository machinery.
- **Concurrent usage/mutation:** consumers can safely read a stable installation, but mutation semantics require synchronization/version-state ownership that is currently absent.
- **Portability:** Windows junction/link mechanics and package-manager assumptions would become part of the repository contract.
- **Architecture risk:** may recreate unnecessary shared-environment mutation complexity merely to save a small dependency install.

### Draft direction

Prefer **Option A: explicit per-runnable-worktree `npm ci` + lockfile + fail-fast consumers**, unless Scout finds evidence that install cost, existing tooling, or package-manager behavior makes a shared canonical Node installation clearly simpler and safer.

The Python shared-venv architecture is not precedent for Node ownership; Node should follow its own resolution and lockfile semantics.

## Scope

The likely implementation surface is intentionally narrow and remains provisional until Scout evidence:

- repository architecture/workflow documentation for Node dependency ownership;
- a dedicated explicit Node workflow dependency bootstrap/readiness script or similarly narrow bootstrap surface;
- consumer-side fail-fast validation at the earliest shared workflow boundary(s) that execute repository Node tooling;
- task/worktree startup documentation or skill integration only to make the explicit bootstrap requirement discoverable and repeatable;
- deterministic tests for bootstrap/readiness behavior and adapter import/startup readiness without a real LLM call;
- `package.json` / `package-lock.json` only if required to encode validated scripts/metadata, not to change pinned dependency versions without evidence.

Scout should identify the smallest shared boundary rather than duplicating checks in every caller.

## Known Invariants

1. OpenCode remains pinned to `1.18.31` for this task unless evidence proves the version itself is the root cause; current evidence says it is not.
2. `@opencode-ai/sdk` remains pinned to `1.18.31`; this task does not opportunistically change SDK versions.
3. Normal Scout, Gate, tests, reviewers, and runtime validation are dependency consumers. They must not silently run `npm install`, `npm ci`, or otherwise mutate dependency state merely to succeed.
4. Node dependency mutation/materialization, if required, is an explicit repository/worktree bootstrap/environment operation.
5. Missing dependencies must fail fast with actionable bootstrap guidance rather than triggering a hidden install.
6. Python dependency ownership remains unchanged. The canonical physical Python environment is `E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot`, consumed through worktree-local `.venv` junctions.
7. No `pip install`, `pip uninstall`, `pip install -e .`, or Python environment redesign is in scope.
8. New task worktrees use `E:\Side_Project\Blackfire-CV-Autopilot\worktrees\<task-id>`.
9. Before local branch/worktree operations, remote freshness and actual branch ownership must be inspected with `git fetch origin` and `git worktree list --porcelain`.
10. Windows non-interactive workflow commands follow the repository `cmd.exe /d /s /c "<command>"` policy.
11. Node bootstrap must use the committed dependency declaration/lockfile rather than a hand-maintained package list.
12. A worktree must not rely on another Git worktree's physical `node_modules` directory by absolute path.
13. Behavior outside workflow dependency readiness must be preserved.

## Provisional Acceptance Criteria

1. The repository defines one unambiguous owner and lifecycle for repository workflow Node dependencies.
2. A fresh runnable worktree has a documented, explicit, non-interactive bootstrap path that deterministically materializes the exact committed dependency graph.
3. Normal Scout/Gate/reviewer/test consumers never silently install or mutate Node dependencies.
4. An unbootstrapped worktree fails before reviewer/LLM work with a concise diagnostic that identifies the missing/incompatible Node dependency state and gives the exact bootstrap action.
5. Readiness validation covers at minimum:
   - required Node executable/version contract;
   - root dependency declaration + lockfile presence/usable consistency;
   - resolvability of repository workflow packages required by `scripts/opencode_structured_review.mjs`.
6. The solution works independently in multiple Git worktrees and does not depend on `BlackfireCrusade_tool\node_modules` or any other specific worktree.
7. If Option A is finalized, each runnable worktree's `node_modules` remains untracked and local to that worktree; `npm ci` is explicit bootstrap, not a consumer side effect.
8. If Option B is selected instead, Final SPEC must first define lockfile/version identity, link ownership, concurrent mutation, validation, and cleanup semantics strongly enough that two worktrees at different dependency revisions cannot silently corrupt or misresolve each other.
9. No automatic shared Node junction/link is added unless Scout demonstrates a concrete advantage that outweighs the added lifecycle complexity.
10. Deterministic validation proves that after bootstrap a fresh-worktree-equivalent fixture/state can load the adapter's repository package boundary without making a real OpenCode/LLM request.
11. Deterministic validation proves missing-package/unbootstrapped states fail closed with bootstrap guidance and do not invoke an install.
12. Existing OpenCode structured-review behavior, reviewer semantics, Gate result semantics, and pinned versions remain unchanged.
13. Python shared-environment behavior remains unchanged.
14. The blocked `ai-workflow-resume-parallel-gate` task can subsequently retry its formal Gate after this task is completed; this task does not itself alter that task's implementation.

## Fail-Fast Questions for Scout / Finalization

The Final SPEC must decide the minimum reliable checks for these cases:

- **Missing `node_modules`:** whether to detect directory absence directly or rely on package resolution checks; diagnostic must point to bootstrap.
- **Missing package:** use Node/package-manager resolution or an import/load probe that catches the actual ESM dependency boundary before real reviewer work.
- **Wrong lockfile/install state:** determine whether `npm ci`-style materialization plus package resolution is sufficient, or whether a lightweight lock/install-state verification is justified without inventing a custom package manager.
- **Wrong Node version:** decide whether `engines.node >=18.17` is sufficient as the authoritative contract and where to enforce it before adapter execution.

## Bootstrap Placement Questions for Scout / Finalization

Compare these possible surfaces and select the smallest owner:

- a dedicated script such as a Node workflow bootstrap/readiness command;
- branch/worktree creation flow invoking or clearly surfacing an explicit bootstrap step;
- documented manual repository-level/worktree bootstrap operation.

A branch-start flow may orchestrate the explicit bootstrap operation, but Scout/Gate/reviewers/tests themselves must remain consumers and must not silently provision dependencies.

## Testing Direction

Testing must avoid a real LLM call. Candidate evidence paths include:

- a deterministic package-resolution/import-readiness probe against the same package boundary used by `scripts/opencode_structured_review.mjs`;
- a temporary/fresh-worktree-equivalent fixture with copied manifest/lockfile and controlled `node_modules` state;
- tests proving the consumer readiness check fails before spawning the real adapter/OpenCode server when dependencies are unavailable;
- existing workflow script harness patterns and the existing Python-to-Node deterministic test wrapper where appropriate.

Scout should identify the lowest-cost test seam and existing harness conventions before Final SPEC fixes exact test files.

## Non-Goals

- fixing `ai-workflow-resume-parallel-gate` implementation itself;
- changing reviewer semantics;
- changing Gate parallel/resume architecture;
- changing workflow fingerprint semantics;
- changing the OpenCode structured-review protocol;
- upgrading/downgrading OpenCode solely as a workaround;
- changing SDK major/minor versions solely as a workaround;
- adding speculative OpenCode CLI flags such as `--standalone` or `--pure`;
- changing game/runtime/CV code;
- redesigning Python environment ownership;
- creating a generic environment manager;
- designing a cross-language dependency platform;
- implementing a generalized shared-dependency locking/atomic-swap system without demonstrated need.

## Uncertainty Requiring Scout Evidence

1. Whether any less-obvious historical/local bootstrap convention exists outside the obvious tracked `npm ci` / `npm install` search surface.
2. Whether repository workflow Node dependencies are used by scripts beyond the structured-review adapter/probe and therefore need a shared readiness owner higher than Gate.
3. Whether `cross-spawn` is still a direct runtime requirement or only retained through SDK/history; Final SPEC should not remove dependencies during this task without evidence.
4. Whether Node `>=18.17` is intentionally broad or whether workflow compatibility needs a narrower supported-version contract based on existing CI/local assumptions.
5. Whether existing branch-start skills are the correct place to surface explicit Node bootstrap, or whether a dedicated documented command is sufficient.
6. Whether validating installed state against the lockfile needs anything beyond standard `npm ci` semantics plus deterministic package-resolution checks.
7. Whether disk/install cost is materially high enough to reconsider Option B. Current evidence does not justify a shared Node environment.
8. The exact deterministic test seam that proves a fresh worktree can reach adapter readiness without making a real OpenCode/LLM call.

Production implementation must not begin until Scout evidence is reviewed and this SPEC is promoted to `Status: Final` by ChatGPT + user.