# Context — node-workflow-dependency-bootstrap

## Executive finding

The blocking Gate failure (`Error [ERR_MODULE_NOT_FOUND]: Cannot find package 'undici'`) is caused by an architectural gap: the repository declares and locks Node workflow dependencies in `package.json` and `package-lock.json`, but defines **zero bootstrap ownership, zero worktree materialization contract, and zero consumer preflight validation** for repository-local Node packages.

Key survey findings:
1. `undici@6.28.1` was added to `package.json` and `package-lock.json` in commit `0a01864` (2026-09-16) to align reviewer transport timeouts.
2. `node_modules/` is Git-ignored. Fresh worktrees created via `git worktree add` (including `worktrees/ai-workflow-resume-parallel-gate` and `worktrees/node-workflow-dependency-bootstrap`) do not inherit `node_modules/`.
3. Even the permanent `BlackfireCrusade_tool` worktree has a stale `node_modules` directory from 2026-09-15 that completely lacks `undici`.
4. `scripts/bootstrap_opencode.ps1` only installs the global OpenCode CLI (`npm install -g opencode-ai@1.18.31`). It never installs repository-local packages.
5. `scripts/ai_gate.ps1` invokes `node <repoRoot>/scripts/opencode_structured_review.mjs` with no prior check for Node executable availability, Node version, `node_modules` presence, or dependency resolvability.
6. The entire locked Node dependency graph is minuscule: exactly 3 top-level packages (`@opencode-ai/sdk`, `cross-spawn`, `undici`) and 5 transitive dependencies, totaling 8 packages and ~3.5 MB uncompressed.
7. **Option A (per-worktree `npm ci`)** is the minimal, correct, and robust architecture. Unlike Python where a multi-hundred-megabyte virtualenv justifies a shared pool, Node dependencies here take ~3.5 MB and ~2 seconds to install, with native ESM resolution and complete branch isolation. Option B (shared Node environment via junctions) introduces severe complexity, Windows link lifecycle overhead, and cross-worktree mutation races for zero practical gain.

---

## Current repository facts

- **Manifest files**:
  - `package.json` exists at repository root:
    - `"name": "blackfirecrusade-opencode-structured-review-probe"`
    - `"private": true`
    - `"type": "module"`
    - `"engines": { "node": ">=18.17" }`
    - `"dependencies": { "@opencode-ai/sdk": "1.18.31", "cross-spawn": "7.0.6", "undici": "6.28.1" }`
  - `package-lock.json` exists at repository root (`lockfileVersion: 2`):
    - Locks exact versions: `@opencode-ai/sdk@1.18.31`, `cross-spawn@7.0.6`, `undici@6.28.1`.
    - Locks exact transitive dependencies: `isexe@2.0.0`, `path-key@3.1.1`, `shebang-command@2.0.0`, `shebang-regex@3.0.0`, `which@2.0.2`.
    - No caret (`^`) or tilde (`~`) range divergence.
  - No other package manager files exist: no `pnpm-lock.yaml`, no `yarn.lock`, no `.npmrc`, no `bun.lockb`.
  - No `"packageManager"` field declared in `package.json`.
- **Git ignore contract**:
  - `.gitignore` line 56 contains `node_modules/`.
- **Installed toolchain versions** (verified on host):
  - Node: `v24.19.0` (satisfies `engines.node >=18.17`)
  - npm: `11.17.0`
  - OpenCode CLI: `1.18.31` (matches pinned `$OpenCodeSupportedVersion`)
- **Worktree state across disk**:
  - `E:\Side_Project\Blackfire-CV-Autopilot\BlackfireCrusade_tool\node_modules`:
    - Created 2026-09-15 19:35:10.
    - Contains `@opencode-ai`, `cross-spawn`, `isexe`, `path-key`, `shebang-command`, `shebang-regex`, `which`.
    - Size: ~828 KB.
    - **Missing `undici`**.
  - `E:\Side_Project\Blackfire-CV-Autopilot\worktrees\ai-workflow-resume-parallel-gate\node_modules`:
    - **Does not exist**.
  - `E:\Side_Project\Blackfire-CV-Autopilot\worktrees\node-workflow-dependency-bootstrap\node_modules`:
    - **Does not exist**.

---

## Node dependency boundary

### 1. Direct dependencies of `scripts/opencode_structured_review.mjs`
- **Node built-ins**: `node:fs/promises`, `node:path`, `node:url`, `node:child_process`, `node:fs`.
- **External packages**:
  - `undici` (imported statically at top of file, line 6: `import { Agent } from "undici";`).
  - `@opencode-ai/sdk/v2` (imported dynamically in `run()`, line 190: `const sdk = await import("@opencode-ai/sdk/v2");`).

### 2. Transitive dependency graph
- `@opencode-ai/sdk@1.18.31` -> `cross-spawn@7.0.6` -> `path-key@3.1.1`, `shebang-command@2.0.0` (`shebang-regex@3.0.0`), `which@2.0.2` (`isexe@2.0.0`).
- `undici@6.28.1` has 0 dependencies.
- Total package count in `package-lock.json`: exactly 8 packages.

### 3. Consumers of repository Node tooling
Across the entire repository, only four JavaScript/MJS files exist:
1. `scripts/opencode_structured_review.mjs`:
   - Launched by `scripts/ai_gate.ps1` (line 53) via `node scripts/opencode_structured_review.mjs`.
   - Functions and transport exports tested by `tests/test_workflow_scripts.py`.
2. `scripts/opencode_structured_review_probe.mjs`:
   - Standalone probe CLI tool. Imports `cross-spawn`.
   - Tested by `tests/workflow_scripts/opencode_structured_review_probe.test.mjs`.
3. `scripts/inspect_mimo_structured.mjs`:
   - Standalone diagnostic script. Imports `cross-spawn`.
4. `tests/workflow_scripts/opencode_structured_review_probe.test.mjs`:
   - Uses `node:test` and `node:assert/strict` built-in test runner.
   - Executed deterministically via `tests/test_opencode_structured_review_probe.py` (`node --test ...`).

### 4. Consumer analysis by workflow component
- **`scripts/ai_scout.ps1`**:
  - Does **NOT** execute Node.
  - Calls `opencode run --agent scout ...` directly using the global OpenCode CLI executable.
  - Does **NOT** depend on repository `node_modules`.
- **`scripts/ai_gate.ps1`**:
  - Executes `node <repoRoot>/scripts/opencode_structured_review.mjs`.
  - Directly depends on repository `node_modules` (`undici` and `@opencode-ai/sdk`).
- **`tests/test_workflow_scripts.py`**:
  - Spawns `node --input-type=module -e ...` importing from `scripts/opencode_structured_review.mjs`.
  - Because line 6 of `opencode_structured_review.mjs` is a static `import { Agent } from "undici";`, the Node module loader evaluates the static import before any exported function can be called.
  - If `undici` is absent, the test fails immediately with `ERR_MODULE_NOT_FOUND`.
- **`tests/test_opencode_structured_review_probe.py`**:
  - Executes `node --test tests/workflow_scripts/opencode_structured_review_probe.test.mjs`.
  - Depends on `opencode_structured_review_probe.mjs` (which dynamically imports `cross-spawn`).

---

## Existing bootstrap ownership

### Repository search findings
- `scripts/bootstrap_opencode.ps1`:
  - Sole purpose: install and verify the global OpenCode CLI executable (`npm install -g opencode-ai@$OpenCodeSupportedVersion`).
  - Contains no logic for local `package.json`, `package-lock.json`, or local `node_modules`.
- `docs/architecture/ai_development_workflow.md`:
  - Section 3 defines the canonical Python environment (`E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot` via worktree-local `.venv` junctions).
  - Contains **zero mention of Node environments, npm, or node_modules**.
- `.agents/skills/branch_start_workflow/SKILL.md`:
  - Phase 6 (Environment preflight) checks only `<task-worktree>\.venv`.
  - Contains **zero mention of Node or npm preflight**.
- Commit history:
  - `0a01864` added `undici` to `package.json` and `package-lock.json`, but did not update or create any bootstrap scripts.
  - `e48d1e1` created `package.json` for the structured review probe, but provided no bootstrap mechanism.

### Conclusion on historical ownership
**There is currently no repository owner for Node workflow dependency bootstrap.**
Fresh worktrees are created without `node_modules`, and no documented or scripted mechanism exists to materialize them.

---

## Option A — per-worktree npm ci

### Evidence
- Standard npm workflow: running `npm ci` inside a worktree reads `package.json` and `package-lock.json` and writes to `<worktree>/node_modules`.
- Size measurement: the current 8-package dependency set occupies ~3.5 MB on disk.
- Performance: `npm ci` completes in ~2–3 seconds on Windows from the local npm cache.
- Resolution: Node ESM resolutions resolve relative to the script location or current working directory. With `<worktree>/node_modules`, Node resolves packages locally without path traversal or symlink indirection.

### Strengths
1. **Perfect branch isolation**: If one branch modifies `package.json` or `package-lock.json` (e.g. testing an SDK upgrade or adding a tool), other concurrent task worktrees are completely isolated and immune to mutation.
2. **Zero concurrency conflicts**: Multiple worktrees running `ai_gate.ps1` or tests concurrently only read their local `node_modules`. No Windows file locking collisions.
3. **Lockfile reproducibility**: `npm ci` strictly validates that `package-lock.json` matches `package.json`. If they drift, `npm ci` aborts instead of mutating the lockfile.
4. **Clean lifecycle**: When a task worktree is removed via `git worktree remove`, its `node_modules` is cleanly removed. No orphaned symlinks or junctions in external pools.
5. **Simplicity**: No custom link manager, no junction creation permissions, no cross-worktree lock files.

### Risks
- If an operator forgets to run `npm ci` in a fresh worktree, the worktree cannot run Gate or workflow tests until bootstrapped.
- *Mitigation*: Fail-fast preflight in `ai_gate.ps1` and guidance in `branch_start_workflow` skill with a clear, one-line remediation command.

### Operational implications
- Fresh worktree bootstrap requires one explicit command: `npm ci` (or a wrapper script `.\scripts\bootstrap_node_workflow_deps.ps1`).
- Disk overhead across 5 active worktrees is ~17.5 MB total (negligible on modern storage).

---

## Option B — shared canonical Node dependencies

### Evidence
- Concept: materialize one canonical `node_modules` (e.g. in `E:\Side_Project\NodePools\` or `BlackfireCrusade_tool\node_modules`) and create a Windows junction (`mklink /J node_modules ...`) in each worktree.
- Node resolution behavior: Node resolves symlinks and junctions by following their realpath.
- Multi-worktree inspection: `git worktree list --porcelain` shows multiple concurrent worktrees frequently exist in this repository (`BlackfireCrusade_tool`, `worktrees/ai-workflow-resume-parallel-gate`, `worktrees/node-workflow-dependency-bootstrap`, `worktrees/worktree-shared-venv-cleanup-safety`).

### Strengths
- Avoids running `npm ci` for each worktree when lockfiles are identical.
- Saves ~3.5 MB of disk space per worktree.

### Risks
1. **Cross-worktree mutation corruption**: If Task A updates a dependency or tests an SDK version and mutates the shared `node_modules`, Task B's Gate immediately runs against the mutated dependencies, violating task isolation.
2. **Concurrent write collisions**: If two worktrees attempt to install or update dependencies simultaneously, npm will crash with Windows file-lock errors (`EPERM`/`EBUSY`).
3. **Link lifecycle complexity**: Worktree cleanup, migration, or removal leaves stale or dangling junctions. Windows junctions require careful creation and removal (`rmdir`, never `Remove-Item -Recurse` which can delete target contents).
4. **Architectural asymmetry**: The shared Python venv was justified because Python runtime packages (OpenCV, Torch, NumPy, etc.) are hundreds of megabytes, take minutes to compile/install, and are strictly frozen across the game runtime. In contrast, Node workflow tooling is an 8-package, 3.5 MB development dependency graph.
5. **Violation of SPEC invariant**: SPEC line 112 states: *"A worktree must not rely on another Git worktree's physical node_modules directory by absolute path."*

### Operational implications
- Option B requires building and maintaining a full junction management lifecycle, cross-worktree locking, and version validation mechanism for a 3.5 MB dependency set. It represents unjustifiable architectural overhead.

---

## Consumer / mutator boundary

In the Blackfire architecture:
- **Consumers**: `scripts/ai_gate.ps1`, `scripts/ai_scout.ps1`, `scripts/opencode_structured_review.mjs`, all tests under `tests/`.
- **Mutator**: Explicit bootstrap operations only (`npm ci` or a dedicated bootstrap script `scripts/bootstrap_node_workflow_deps.ps1`).

### Invariant
Consumers must **NEVER** silently mutate the environment:
- No silent `npm install`.
- No silent `npm ci`.
- No opportunistic package downloading.
- If dependencies are missing or stale, consumers must **fail fast** and output clear, actionable bootstrap guidance.

---

## Fail-Fast boundary

### Why `opencode_structured_review.mjs` cannot self-report missing packages
Line 6 of `scripts/opencode_structured_review.mjs`:
```javascript
import { Agent } from "undici";
```
In Node ESM, static imports are evaluated during module linking **before** any top-level or exported script code executes. When `undici` is missing, the Node runtime immediately throws:
```text
Error [ERR_MODULE_NOT_FOUND]: Cannot find package 'undici' imported from ...
```
No `try/catch` or error handler inside `opencode_structured_review.mjs` can intercept this error.

### Recommended fail-fast location
The earliest, cleanest fail-fast boundary is in **`scripts/ai_gate.ps1`** (the caller):
Before starting the candidate review loop or spawning Node, `ai_gate.ps1` should perform a lightweight preflight:
1. **Check `node` command availability**: verify `Get-Command node` succeeds.
2. **Check Node version**: verify `node --version` satisfies `>=18.17`.
3. **Check package readiness**: execute a fast non-destructive import probe:
   ```cmd
   node --input-type=module -e "import('undici'); import('@opencode-ai/sdk/v2')"
   ```
4. **Fail-fast behavior**: if any check fails, abort immediately with exit code and clear message:
   ```text
   ERROR: Node workflow dependencies are unbootstrapped or incomplete.
   Required packages ('undici', '@opencode-ai/sdk') could not be resolved.
   Run: npm ci
   (or .\scripts\bootstrap_node_workflow_deps.ps1)
   ```

This prevents launching reviewers, avoids orphaned server processes, avoids logging misleading `INFRASTRUCTURE_FAILED` transport errors, and immediately directs the operator to the remediation action.

---

## Bootstrap surface options

### 1. Dedicated script: `scripts/bootstrap_node_workflow_deps.ps1`
- **Pattern**: Mirrors `scripts/bootstrap_opencode.ps1`.
- **Behavior**:
  - Verifies `node` is installed and version >= 18.17.
  - Verifies `npm` is installed.
  - Confirms `package.json` and `package-lock.json` exist.
  - Executes `npm ci` in the current worktree repository root.
  - Verifies successful materialization with a deterministic import check (`undici` + `@opencode-ai/sdk/v2`).
- **Strengths**: Highly discoverable, non-interactive, guarantees `npm ci` (not `npm install`), provides consistent console feedback.

### 2. Documented standard command: `npm ci`
- **Pattern**: Documented in `docs/architecture/ai_development_workflow.md` as the canonical worktree bootstrap command.
- **Strengths**: Uses standard Node ecosystem conventions; zero proprietary maintenance.

### 3. Worktree creation integration: `branch_start_workflow` skill
- **Pattern**: Update Phase 6 (Environment preflight) of `.agents/skills/branch_start_workflow/SKILL.md` to check both Python `.venv` and Node `node_modules`.
- **Behavior**: If `node_modules` or required packages are missing, prompt operator or guide execution of `npm ci` / `scripts/bootstrap_node_workflow_deps.ps1`.

### Recommended synthesis
Provide `scripts/bootstrap_node_workflow_deps.ps1` as the primary convenience script, document `npm ci` in `ai_development_workflow.md`, and update `branch_start_workflow` Phase 6 to guide explicit bootstrap on worktree initialization.

---

## Fresh-worktree deterministic test seam

To prove adapter readiness on a fresh worktree without making real LLM / network calls:

1. **Lightweight import-readiness probe**:
   ```cmd
   node --input-type=module -e "import { Agent } from 'undici'; import('@opencode-ai/sdk/v2').then(() => console.log('READY'));"
   ```
   Outputs `READY` and exits 0 when dependencies are present; exits non-zero with `ERR_MODULE_NOT_FOUND` when missing.

2. **Integration into `tests/test_workflow_scripts.py`**:
   - Add test verifying that `scripts/opencode_structured_review.mjs` can be imported and exports expected symbols without runtime errors.
   - Add test verifying `ai_gate.ps1` preflight fails closed when `node_modules` is absent or incomplete.
   - Add test verifying `ai_gate.ps1` does NOT silently execute `npm install` or `npm ci` (static assertion).

3. **Integration into `tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1`**:
   - Add harness test case verifying `ai_gate.ps1` preflight failure messaging and exit code when Node dependencies are not ready.

---

## Historical evidence

| Date | Commit / Event | Fact |
|---|---|---|
| 2026-09-14 | Initial OpenCode setup | `scripts/bootstrap_opencode.ps1` created. It only bootstrapped the global OpenCode CLI (`npm install -g opencode-ai@1.18.31`). No local `package.json` bootstrap was created. |
| 2026-09-15 | Manual install in main | Someone executed `npm install` directly in `BlackfireCrusade_tool`. Packages installed: `@opencode-ai/sdk`, `cross-spawn`. |
| 2026-09-16 | Commit `0a01864` | `undici@6.28.1` added to `package.json` and `package-lock.json` to fix transport timeouts in `scripts/opencode_structured_review.mjs`. Neither `BlackfireCrusade_tool` nor worktrees were updated with `undici`. |
| 2026-09-17 | Task `ai-workflow-resume-parallel-gate` | Gate failed immediately with `ERR_MODULE_NOT_FOUND: Cannot find package 'undici'` because worktree lacked `node_modules` entirely. |

---

## Architecture conflicts / invariants

1. **Consumer Immutability**: Scout, Gate, reviewers, and tests must never modify dependencies. Silent `npm install` or `npm ci` during a Gate run is strictly forbidden.
2. **Worktree Independence**: No worktree may depend on another worktree's physical `node_modules` path (e.g. linked worktree pointing to `BlackfireCrusade_tool\node_modules`).
3. **No Unnecessary Shared State**: Python uses a shared environment because of size (hundreds of MBs) and compile times. Node workflow dependencies are ~3.5 MB and take 2 seconds; sharing them creates severe cross-branch mutation risk for negligible gain.
4. **Lockfile Integrity**: Dependency materialization must always be driven by `package-lock.json` via `npm ci`, never `npm install` which can mutate the lockfile.
5. **Pinned Versions**: `@opencode-ai/sdk@1.18.31`, `cross-spawn@7.0.6`, `undici@6.28.1`, and OpenCode CLI `1.18.31` remain pinned.

---

## Recommended direction for SPEC owner

1. **Adopt Option A (per-worktree `npm ci`)**:
   - Keep `node_modules/` in `.gitignore`.
   - Each runnable worktree materializes its own local `node_modules` from the committed `package-lock.json`.
2. **Add dedicated bootstrap script**:
   - Create `scripts/bootstrap_node_workflow_deps.ps1` that validates Node >= 18.17, npm, and runs `npm ci` non-interactively.
3. **Add fail-fast preflight to `scripts/ai_gate.ps1`**:
   - Check Node availability and execute a deterministic import probe for `undici` and `@opencode-ai/sdk/v2` before entering the review loop.
   - If unbootstrapped, fail immediately with clear instructions to run `npm ci` or `.\scripts\bootstrap_node_workflow_deps.ps1`.
4. **Update workflow documentation**:
   - Add Node workflow dependency lifecycle to `docs/architecture/ai_development_workflow.md`.
   - Add Node preflight check to Phase 6 of `.agents/skills/branch_start_workflow/SKILL.md`.
5. **Add deterministic verification**:
   - Add unit test in `tests/test_workflow_scripts.py` verifying fail-fast diagnostics on unbootstrapped state and successful import on bootstrapped state without LLM calls.

---

## Remaining uncertainty

1. **Node version contract precision**: `package.json` specifies `engines.node >=18.17`. The current local host runs Node `v24.19.0`. Whether the Gate preflight should enforce `>=18.17` or match a more specific range (e.g. `^18.17 || ^20.0 || ^22.0 || ^24.0`).
   - *Recommendation*: Enforcing `>=18.17` matches `package.json` and accommodates standard LTS/current releases.
2. **Direct `cross-spawn` dependency**: `cross-spawn` is directly declared in `package.json`, but only `scripts/opencode_structured_review_probe.mjs` imports it directly (the main adapter relies on `@opencode-ai/sdk` which transitively includes `cross-spawn`). SPEC should retain `cross-spawn` as currently locked.
