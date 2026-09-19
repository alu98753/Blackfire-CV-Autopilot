# Node Workflow Dependency Bootstrap

Status: Final

## Goal

Define and implement the repository contract that makes Node-based AI workflow tooling runnable from any Blackfire Git worktree without depending on incidental `node_modules` state from another worktree.

The concrete blocker is the formal AI Gate failing before reviewer startup with:

```text
Error [ERR_MODULE_NOT_FOUND]: Cannot find package 'undici'
imported from scripts/opencode_structured_review.mjs
```

The dependency is already declared and locked. The missing architecture is the lifecycle for materializing repository-local Node dependencies in a fresh worktree, validating readiness before production workflow execution, and keeping environment mutation separate from normal consumers.

This task standardizes that lifecycle without changing the existing OpenCode, SDK, Node-package, Python-environment, reviewer, or Gate semantics.

## Final Architecture Decision

Use **per-worktree Node dependency materialization**.

Each runnable Git worktree owns its own untracked `node_modules` directory, materialized from the committed repository lockfile by an explicit bootstrap operation based on `npm ci`.

```text
package.json + package-lock.json
            |
            | dependency SSOT
            v
explicit Node workflow bootstrap
            |
            | npm ci in current worktree root
            v
<current-worktree>/node_modules
            |
            +--> AI Gate
            +--> deterministic workflow tests
            +--> repository Node workflow scripts

Consumers validate and use the environment.
Consumers never install or repair it silently.
```

A canonical shared Node dependency pool, shared `node_modules`, Windows junction scheme, or cross-worktree package store is explicitly rejected for this task.

The current dependency graph is small, cheap to materialize, and branch-local isolation is more valuable than eliminating a few megabytes of duplicate packages.

## Evidence Summary

The temporary Scout fallback established the following repository facts:

- root `package.json` exists and pins:
  - `@opencode-ai/sdk`: `1.18.31`
  - `cross-spawn`: `7.0.6`
  - `undici`: `6.28.1`
- root `package-lock.json` exists and locks the exact graph.
- `package.json` declares `engines.node >=18.17`.
- no alternate package-manager lockfiles or repository-local Node bootstrap contract exist.
- `.gitignore` excludes `node_modules/`.
- fresh Git worktrees therefore do not inherit repository-local Node packages.
- the permanent main worktree can also contain stale local `node_modules`; its existence is not proof of readiness.
- `scripts/bootstrap_opencode.ps1` only installs/verifies the global OpenCode CLI and does not materialize repository-local Node packages.
- `scripts/ai_gate.ps1` currently invokes `node scripts/opencode_structured_review.mjs` without repository Node readiness validation.
- `scripts/opencode_structured_review.mjs` statically imports `undici` and dynamically imports `@opencode-ai/sdk/v2`.
- `scripts/opencode_structured_review_probe.mjs` and `scripts/inspect_mimo_structured.mjs` also use repository Node packages (`cross-spawn`).
- the current locked Node dependency graph contains only 8 packages and is approximately a few megabytes on disk; per-worktree installation is therefore operationally cheap.

## Responsibility Boundary

This task owns:

- repository-local Node workflow dependency materialization;
- explicit bootstrap ownership;
- Node workflow readiness validation;
- actionable fail-fast behavior for unbootstrapped/incompatible worktrees;
- worktree/branch-start discoverability of the bootstrap requirement;
- deterministic tests proving readiness and failure behavior without real LLM/reviewer execution;
- workflow architecture documentation for the above contract.

This task does **not** own:

- OpenCode reviewer semantics;
- structured-review protocol semantics;
- Gate parallelism or resume behavior;
- Gate fingerprint semantics;
- model fallback policy;
- OpenCode provider compatibility beyond preserving the existing pinned contract;
- Python environment ownership;
- game/runtime/CV behavior;
- generic cross-language environment management.

## Dependency and Version Contract

### Versions remain unchanged

This task must not change the currently established versions merely to solve bootstrap readiness:

```text
OpenCode CLI        1.18.31
@opencode-ai/sdk    1.18.31
cross-spawn         7.0.6
undici              6.28.1
Node engine         >=18.17
```

`package.json` and `package-lock.json` remain the dependency SSOT.

The existing `engines.node >=18.17` declaration remains the authoritative Node compatibility contract for this task. Do not introduce a new allowlist such as only Node 18/20/22/24 unless separate future evidence requires it.

The host version observed during this task (`v24.19.0`) satisfies the existing contract and is not itself the root cause.

### No opportunistic dependency cleanup

`cross-spawn` remains pinned and declared. This task does not remove or reclassify dependencies merely because some are also reachable transitively; repository probe/diagnostic tooling currently uses `cross-spawn` directly.

## Materialization Contract

### Canonical model

Every runnable worktree that needs repository Node tooling owns:

```text
<worktree>/node_modules
```

The directory remains untracked and worktree-local.

It must not point by absolute path to another Git worktree's `node_modules`.

### Canonical bootstrap operation

The repository must provide one explicit, discoverable bootstrap surface, preferably:

```text
scripts/bootstrap_node_workflow_deps.ps1
```

Its responsibility is to materialize the dependency graph for the **current worktree** using the committed lockfile.

The canonical package-manager operation is:

```text
npm ci
```

run from the current repository/worktree root.

The bootstrap surface must be non-interactive and compatible with the repository Windows command policy.

### Bootstrap responsibilities

The dedicated bootstrap operation should:

1. determine the current worktree repository root from the script location rather than from a hard-coded path;
2. verify `node` is available;
3. verify the installed Node version satisfies the repository contract (`>=18.17`);
4. verify `npm` is available;
5. verify root `package.json` exists;
6. verify root `package-lock.json` exists;
7. execute `npm ci` from that worktree root;
8. fail closed if `npm ci` fails;
9. verify the required repository workflow package boundary is resolvable after bootstrap;
10. report success concisely.

The bootstrap script may mutate only the current worktree's local Node dependency state through the standard package-manager operation. It must not mutate Python state or another worktree's Node state.

## Consumer / Mutator Boundary

### Mutator

Only an explicit bootstrap/environment operation may install or repair Node workflow dependencies.

Examples:

```text
scripts/bootstrap_node_workflow_deps.ps1
npm ci    # when explicitly invoked as documented bootstrap
```

### Consumers

Normal workflow execution is read-only with respect to dependency materialization.

Consumers include, when applicable:

- `scripts/ai_gate.ps1`;
- Node workflow adapters;
- workflow deterministic tests;
- reviewer processes;
- diagnostic/probe scripts when run normally.

They must not silently execute:

```text
npm install
npm ci
npm update
npm install --package-lock-only
```

or any equivalent hidden dependency repair.

### Scout-specific decision

`scripts/ai_scout.ps1` currently invokes the global OpenCode CLI directly and does not depend on repository `node_modules`.

Therefore this task must **not** add Node dependency preflight to Scout merely for symmetry.

Readiness checks belong only at boundaries that actually consume repository Node packages.

## Readiness Contract

Repository Node workflow readiness is a small, reusable contract rather than reviewer-specific business logic.

The implementation should expose a narrow readiness/preflight surface that can be called by `ai_gate.ps1` and tested deterministically.

The exact implementation may be a helper script/function or another small shared workflow surface, but it must not become a general-purpose environment framework.

### Minimum readiness checks

Before production Node workflow execution, readiness validation must cover:

1. **Node executable availability**.
2. **Node version compatibility** with `package.json`'s `>=18.17` contract.
3. **Repository manifest presence** (`package.json`).
4. **Repository lockfile presence** (`package-lock.json`).
5. **Required package resolvability** for the production adapter boundary, at minimum:
   - `undici`
   - `@opencode-ai/sdk/v2`
6. failure diagnostics that identify an unbootstrapped/incomplete environment and provide the exact bootstrap remediation.

### Readiness does not become a second package manager

Do not create a custom dependency fingerprint database, custom lock graph parser, package cache manager, or install-state stamp system unless implementation evidence proves a simple import/package-manager validation cannot satisfy the acceptance criteria.

The standard package-manager model remains:

```text
package.json + package-lock.json
        -> npm ci
        -> local node_modules
```

A stale or incomplete local installation is repaired by rerunning the explicit bootstrap, not by consumer-side mutation.

## Gate Fail-Fast Boundary

`ai_gate.ps1` is the current production workflow caller that executes repository Node packages and is therefore the required fail-fast integration point.

Before starting reviewer work, candidate fallback, adapter servers, or real LLM/model activity, Gate must validate Node workflow readiness.

Conceptually:

```text
AI Gate
  |
  +--> existing task/OpenCode contract validation
  |
  +--> Node workflow readiness preflight
          |
          +--> ready ------> continue reviewer orchestration
          |
          +--> not ready --> stop immediately
                              print bootstrap guidance
                              no reviewer/model work
```

The preflight must happen before the first real reviewer adapter invocation.

It must not be deferred until `opencode_structured_review.mjs` is already loading, because the adapter's static `undici` import can fail during ESM module linking before script-level recovery logic executes.

### Diagnostic behavior

An unbootstrapped/incomplete worktree should produce a concise actionable error equivalent in meaning to:

```text
Node workflow dependencies are not ready for this worktree.
Run: .\scripts\bootstrap_node_workflow_deps.ps1
```

The diagnostic may include the specific failed check (missing Node, unsupported Node version, missing manifest/lockfile, unresolved package), but must not expose the user to an opaque downstream `ERR_MODULE_NOT_FOUND` as the primary workflow failure.

## Branch / Worktree Lifecycle Integration

The branch/worktree startup workflow must surface the Node bootstrap requirement where relevant.

`.agents/skills/branch_start_workflow/SKILL.md` may be updated so a newly created runnable task worktree has an explicit environment-preparation step that distinguishes:

```text
Python environment readiness
Node workflow dependency readiness
```

This integration must preserve the architecture boundary:

- branch-start/environment setup may explicitly tell the operator to bootstrap or invoke the dedicated bootstrap as a deliberate environment setup step;
- Gate/Scout/tests must not silently install dependencies merely because environment setup was skipped;
- Git worktree topology must still be inspected before branch/worktree operations;
- Node state remains local to the current worktree.

The Final implementation should choose the smallest wording/flow change that makes the contract discoverable without turning branch startup into a generic package-management framework.

## Shared Node Environment — Rejected

A repository-wide canonical physical Node installation or Windows junction-based shared `node_modules` is not part of this design.

Reasons:

1. the current package graph is very small;
2. `npm ci` is cheap enough per worktree;
3. task branches may temporarily contain different manifests/lockfiles;
4. local `node_modules` gives native Node resolution with no indirection;
5. per-worktree installations eliminate cross-branch mutation coupling;
6. no concurrent install locking protocol is required;
7. no Windows junction ownership/cleanup semantics are required;
8. no task worktree depends on main or another task worktree remaining present.

The existing shared Python venv architecture is intentionally **not** used as precedent for Node. The two ecosystems have different cost and isolation tradeoffs.

## Deterministic Test Strategy

Tests must prove the bootstrap/readiness architecture without making a real OpenCode/LLM request.

The implementation should reuse the repository's existing workflow-script harness patterns where practical.

### Required deterministic behaviors

At minimum tests must prove:

1. **Unbootstrapped/incomplete state fails fast**
   - readiness reports failure;
   - diagnostic contains explicit bootstrap remediation;
   - no install command is invoked by the consumer;
   - Gate does not proceed to real reviewer execution.

2. **Ready state succeeds**
   - Node can load the production repository package boundary;
   - at minimum `undici` and `@opencode-ai/sdk/v2` resolve/import successfully;
   - no real OpenCode server/model/reviewer request is required.

3. **Consumer remains non-mutating**
   - Gate/readiness implementation contains no hidden `npm ci` / `npm install` recovery path.

4. **Node version failure is deterministic**
   - the readiness seam can be exercised or overridden so an unsupported Node version is rejected without requiring the developer machine to actually install another Node version.

### Suitable readiness probe

A deterministic package boundary probe may use semantics equivalent to:

```text
node --input-type=module -e "import('undici'); import('@opencode-ai/sdk/v2')"
```

provided the final implementation keeps quoting, working-directory behavior, and process execution deterministic on Windows.

The test should validate the same package boundary that production Gate relies on rather than a separate hand-maintained list that can silently drift.

## Scope

Implementation is intentionally narrow.

Expected files/surfaces include:

- `scripts/bootstrap_node_workflow_deps.ps1`;
- a minimal reusable Node workflow readiness/preflight surface;
- `scripts/ai_gate.ps1` integration before reviewer execution;
- `.agents/skills/branch_start_workflow/SKILL.md` for explicit environment handoff/discoverability;
- `docs/architecture/ai_development_workflow.md` for the canonical Node worktree dependency contract;
- existing workflow test harnesses / deterministic tests under `tests/` and `tests/workflow_scripts/`;
- this task's tracked artifacts.

`package.json`, `package-lock.json`, and `.gitignore` should change only if implementation evidence requires metadata/script wiring. Dependency versions themselves must remain unchanged.

## Known Invariants

1. OpenCode remains pinned to `1.18.31`.
2. `@opencode-ai/sdk` remains pinned to `1.18.31`.
3. `cross-spawn` remains pinned to `7.0.6`.
4. `undici` remains pinned to `6.28.1`.
5. Node compatibility remains `>=18.17` for this task.
6. `package.json` + `package-lock.json` are the Node dependency SSOT.
7. Every runnable worktree uses its own untracked `node_modules`.
8. No Node dependency path may rely on another Git worktree's physical `node_modules`.
9. Normal Gate/tests/reviewers are dependency consumers and must not silently install dependencies.
10. Scout currently does not consume repository Node packages and should not gain unnecessary Node bootstrap coupling.
11. Dependency materialization is an explicit worktree-level repository operation.
12. Missing/incompatible dependency state fails fast with exact bootstrap guidance.
13. Python dependency ownership is unchanged.
14. The canonical physical Python environment remains `E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot` through worktree-local `.venv` junctions.
15. No `pip install`, `pip uninstall`, `pip install -e .`, or Python environment redesign is in scope.
16. New task worktrees remain under `E:\Side_Project\Blackfire-CV-Autopilot\worktrees\<task-id>`.
17. Git multi-worktree branch ownership must be inspected rather than guessed.
18. Windows non-interactive execution continues to use `cmd.exe /d /s /c "<command>"` and the repository's existing shell policy.
19. Existing structured-review behavior, reviewer semantics, Gate classifications, and fallback behavior remain unchanged except that missing Node readiness now fails earlier and more clearly.
20. Behavior outside dependency bootstrap/readiness remains preserved.

## Acceptance Criteria

1. The repository has one explicit bootstrap owner for repository-local Node workflow dependencies.
2. A fresh runnable worktree can execute one documented non-interactive bootstrap operation that materializes its own local `node_modules` from the committed lockfile using `npm ci` semantics.
3. Bootstrap operates on the current worktree and never installs into main, another task worktree, a shared Node pool, or the Python environment.
4. Bootstrap validates Node availability, npm availability, the repository Node version contract, manifest/lockfile presence, and successful package readiness.
5. `package.json` and `package-lock.json` remain the dependency SSOT; dependency versions remain unchanged.
6. `ai_gate.ps1` performs Node workflow readiness validation before any real reviewer/model execution that requires `opencode_structured_review.mjs`.
7. Missing `node_modules`, missing required packages, stale/incomplete local package state, missing Node, or unsupported Node version result in fail-fast behavior with an exact bootstrap remediation command.
8. Gate does not silently execute `npm ci`, `npm install`, or another dependency mutation operation.
9. Tests and normal Node workflow consumers do not silently repair dependencies.
10. Scout remains free of repository Node readiness coupling while it continues not to consume repository Node packages.
11. The implementation works independently in multiple concurrent Git worktrees without sharing physical `node_modules`.
12. No Windows `node_modules` junction/shared-pool lifecycle is introduced.
13. Deterministic tests prove an unbootstrapped/incomplete environment fails before real reviewer/LLM work and provides bootstrap guidance.
14. Deterministic tests prove a bootstrapped environment resolves/imports the production Node adapter dependency boundary without a real LLM/OpenCode reviewer call.
15. Deterministic tests prove the consumer path does not contain hidden install behavior.
16. Node version rejection is testable deterministically without requiring the host to install an unsupported Node runtime.
17. Branch/worktree lifecycle documentation or skill guidance clearly tells operators how a fresh runnable worktree becomes Node-ready.
18. `docs/architecture/ai_development_workflow.md` documents per-worktree `node_modules`, explicit bootstrap ownership, and consumer fail-fast behavior.
19. Existing OpenCode CLI/SDK versions, structured-review protocol, Gate result semantics, model fallback semantics, and Python shared environment behavior remain unchanged.
20. After this task completes and passes its own Gate/review, `ai-workflow-resume-parallel-gate` can rerun its previously blocked formal `scripts/ai_gate.ps1 -Task ai-workflow-resume-parallel-gate` without requiring changes to that task's implementation solely to locate `undici`.

## Non-Goals

- changing or fixing `ai-workflow-resume-parallel-gate` production implementation;
- changing reviewer semantics;
- changing Gate parallel/resume architecture;
- changing workflow fingerprint semantics;
- changing structured-review output or transport protocol;
- changing model fallback policy;
- upgrading or downgrading OpenCode;
- upgrading or downgrading `@opencode-ai/sdk`;
- changing `cross-spawn` or `undici` versions;
- adding speculative OpenCode flags such as `--standalone` or `--pure`;
- introducing a shared Node dependency pool;
- introducing `node_modules` junctions/symlinks across worktrees;
- creating a custom dependency fingerprint/stamp database;
- creating a generalized environment manager;
- creating a cross-language dependency platform;
- changing the shared Python environment protocol;
- changing game/runtime/CV behavior.

## Implementation Guidance

Implementation should prefer small reusable boundaries over broad abstraction.

A good shape is:

```text
bootstrap_node_workflow_deps.ps1
        |
        | explicit mutation only
        v
worktree-local node_modules

node workflow readiness helper
        |
        +--> AI Gate preflight
        +--> deterministic tests
```

Do not embed package installation into the readiness helper.

Do not duplicate dependency readiness logic across every Node script if one narrow shared preflight surface can represent the production requirement.

Do not refactor unrelated workflow code while implementing this task.

## Post-Implementation Validation

After production implementation by Gemini/Antigravity:

1. run the task's focused deterministic tests;
2. execute `scripts/ai_gate.ps1 -Task node-workflow-dependency-bootstrap` from a correctly synchronized task worktree;
3. ChatGPT performs final semantic/architecture review from GitHub;
4. after this task is accepted/merged, return to `ai-workflow-resume-parallel-gate`;
5. bootstrap that worktree's Node workflow dependencies under the new contract if necessary;
6. rerun:

```text
scripts/ai_gate.ps1 -Task ai-workflow-resume-parallel-gate
```

The rerun is verification of the previously blocked task, not part of this task's implementation scope.

## Resolved Uncertainty

The Scout fallback resolved the Draft questions as follows:

- **Historical bootstrap owner:** none existed for repository-local Node packages.
- **Fresh worktree behavior:** absence of `node_modules` is expected Git-local state, but lack of an explicit bootstrap lifecycle is an architecture gap.
- **Per-worktree `npm ci`:** sufficient and preferred.
- **Shared Node environment:** not justified by current cost or architecture.
- **Node version contract:** retain existing `>=18.17`; do not invent a new major-version allowlist.
- **Scout dependency:** Scout currently does not require repository Node packages.
- **Gate boundary:** Gate must fail fast before reviewer adapter execution.
- **Static import failure:** adapter-internal recovery is too late for missing `undici`; caller-side readiness is required.
- **Dependency versions:** no version changes are required.
- **Fresh-worktree deterministic seam:** import/readiness validation can cover the production package boundary without real LLM activity.

No unresolved architecture question remains that should block production implementation.