# Spec Review

Gate-accepted verdict: PASS
Blocking findings: 0

# Spec Review

## Clause coverage

- **Final architecture (per-worktree `npm ci`)**: `scripts/bootstrap_node_workflow_deps.ps1` (new) derives worktree root from `$PSScriptRoot`, validates `package.json`/`package-lock.json`/`engines.node`, checks Node + npm availability and version, runs `npm ci` via `cmd.exe /d /s /c` (invariant 18), fails closed on non-zero exit, and re-verifies readiness after install. No junctions/shared pools; `node_modules/` remains untracked (`.gitignore` untouched).
- **Version/SSOT invariants 1-6**: `package.json` still pins `@opencode-ai/sdk@1.18.31`, `cross-spawn@7.0.6`, `undici@6.28.1`, `engines.node >=18.17`; neither manifest nor lockfile changed in the diff. No version allowlist invented for Node.
- **Readiness contract**: `scripts/node_workflow_contract.ps1` exposes `Test-NodeWorkflowDependencies`/`Assert-NodeWorkflowDependenciesReady` covering all six minimum checks (manifest, engine spec from SSOT, Node executable, version, lockfile, `node_modules`, and deterministic `undici`+`@opencode-ai/sdk/v2` import probe). No `npm` invocation inside the readiness helper; no fingerprint/stamp database.
- **Gate fail-fast boundary**: `scripts/ai_gate.ps1:18-20` calls `Assert-NodeWorkflowDependenciesReady` immediately after task/OpenCode contract validation and before the reviewer loop (`:82+`), candidate fallback, and adapter spawning. `_NodeExecutableOverride`/`_NodeVersionOverride` provide the deterministic version-rejection seam; `_SkipNodeReadinessCheck` is the explicit test bypass. Gate text contains no `npm ci`/`npm install`.
- **Consumer/mutator boundary**: Scout untouched (no Node coupling, per decision); bootstrap is the only mutator. Static tests assert gate/contract contain no hidden install paths.
- **Lifecycle/docs**: `branch_start_workflow` SKILL.md Phase 6.2 and `ai_development_workflow.md` 禮3.1 document per-worktree `node_modules`, explicit bootstrap, and consumer fail-fast.
- **Deterministic tests**: Python + harness cover unbootstrapped fail-fast with remediation (and reviewer-not-invoked marker proof), ready-state package-boundary success, version rejection via override/fixtures, and non-mutation static assertions. Focused test targets match `task.json` scope.

## Blocking findings

None

## Advisory findings

1. `ai_development_workflow.md` diff also carries minor doc clarifications unrelated to Node bootstrap (reviewer step counts, "exactly OpenCode CLI version 1.18.31"). They describe existing pinned contracts and are consistent with harness assertions; doc-only noise.
2. `_SkipNodeReadinessCheck` is a production-visible bypass switch; consistent with the existing `_`-prefixed override pattern and needed for deterministic harness testing, but worth keeping internal-only.
3. `status.txt` snapshot is blank; expected for a clean working tree (`git status --short` empty) and consistent with the implementation being committed.

## Test evidence gaps

Focused tests were not executed in this read-only review. Grounding confirms the worktree is bootstrapped (`node_modules` present with all 8 locked packages incl. `undici`; Node v24.19.0, npm 11.17.0), so ready-state tests and the harness invocation-probe case are runnable. The unbootstrapped/version-rejection cases are deterministic (fixture dirs and overrides; no host Node change required). Remaining verification: run `tests.test_opencode_structured_review_probe` and `tests.test_workflow_scripts` in a bootstrapped worktree, plus a real `ai_gate.ps1` run per SPEC post-implementation validation.
