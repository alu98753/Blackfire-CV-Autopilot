# Regression Review

Gate-accepted verdict: PASS
Blocking findings: 0

# Regression Review

## Behavior-preservation assessment

The diff adds a Node dependency lifecycle (bootstrap + readiness + fail-fast) without altering existing OpenCode/structured-review/Gate semantics. Verified preserved behaviors:

- `scripts/ai_gate.ps1` retains its task-package validation, OpenCode version assertion, reviewer envelope classification, bounded process capture, fallback rules, promotion/rollback, and exit-code contract (0 PASS / 1 unavailable / 2 blocked). The new readiness assertion is inserted after task/OpenCode contract checks and before candidate resolution and the first reviewer spawn (`ai_gate.ps1:18-20` vs. review loop at `:93-95`), so the adapter's static `undici` import (`opencode_structured_review.mjs:6`) can no longer fail during ESM linking at reviewer startup ??the intended change.
- Readiness is pure: `node_workflow_contract.ps1` only probes (`node --input-type=module -e "import('undici')...import('@opencode-ai/sdk/v2')"` with `WorkingDirectory = $RepoRoot`) and never invokes npm; gate text contains no `npm install`/`npm ci`. Mutation is confined to `bootstrap_node_workflow_deps.ps1` (explicit `cmd.exe /d /s /c "npm ci"` + post-install verification), matching SPEC invariants 8-9, 11-12, 18.
- Engine-spec SSOT: `Get-RequiredNodeEngineSpec` reads `engines.node` (`>=18.17`) from `package.json`; no hardcoded constant (harness and unit tests assert this). Version compare handles `v18.17.0`-style and rejects `18.16.0`; `$Matches` population semantics of `-notmatch` are safe because spec groups are extracted before the version regex overwrites them.
- Scout is untouched (no Node coupling), dependency versions unchanged, `package.json`/`package-lock.json`/`.gitignore` not modified.
- Doc claims are grounded: `steps: 8` / `steps: 10` match `.opencode/agents/spec-reviewer.md` and `regression-reviewer.md` frontmatter; "terminal StructuredOutput" repeats existing adjacent contract language.

## Blocking findings

None

## Advisory findings

- `ai_gate.ps1 -_InvocationProbe` now requires Node readiness and fails in an unbootstrapped worktree where it previously printed probe args; this is deliberate fail-fast behavior with `_SkipNodeReadinessCheck` as the escape hatch, but the harness now implicitly depends on a bootstrapped worktree.
- The import probe relies on Node (>=18.17) exiting non-zero on unhandled promise rejection of a failed dynamic import; stdout is redirected but never read (harmless today because the probe prints nothing). An explicit `catch`/`process.exitCode` would harden the seam.
- `Assert-NodeSupportedVersion` accepts only `>=x.y[.z]` engine specs; other semver ranges would fail closed with "unsupported or malformed" ??acceptable for the pinned contract but a future `engines.node` change requires parser maintenance.
- Bootstrap success output claims `cross-spawn` "ready" though the probe only imports `undici` + `@opencode-ai/sdk/v2` (cosmetic; `cross-spawn` is verified transitively via the SDK).
- `docs/architecture/ai_development_workflow.md` reviewer-paragraph edits (step counts, exact CLI version) are outside the strict bootstrap scope but are evidence-grounded and internally consistent.
