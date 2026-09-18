# Spec Review

Gate-accepted verdict: PASS
Blocking findings: 0

# Spec Review

## Clause coverage

**Goal / canonical layout (SPEC 禮Goal, decisions 1??):** Resolved. `docs/tasks/active/<task-id>/` package present and tracked (SPEC.md, task.json, CONTEXT.md, reviews/); ~31 legacy packages renamed to `docs/tasks/archive/2026/<task-id>/` with 100% similarity (no artifact loss); path remains the lifecycle SSOT ??no task.json.status authority added.

**Resolver (decisions 3??, 7??; acceptance 3??):** `scripts/task_package_resolver.ps1` is the single owner of path semantics (`Get-TaskPackageRelativePath`, `Resolve-TaskPackage`, `Get-TaskPackageGitPath`) and produces ACTIVE / ARCHIVED / MISSING / MALFORMED / AMBIGUOUS_ARCHIVE with `-RequireActive` fail-closed. `task_start.ps1`, `ai_scout.ps1`, `ai_gate.ps1` all consume the resolver; grep confirms zero remaining `docs/tasks/$Task` constructions in `scripts/`. No flat-layout compatibility fallback exists (acceptance 12 holds for the code paths).

**Archive command (SPEC 禮Archive; acceptance 7??):** `scripts/task_archive.ps1` fails closed on missing/archived/ambiguous/malformed/non-ACTIVE classification; requires clean canonical main at `origin/main`; maps exactly one clean task worktree; proves integration by unique first-parent merge boundary containing task HEAD; derives year from UTC committer date of the verified integration commit; performs `git mv` in an isolated detached worktree and pushes `archive/<task-id>-<year>`; performs no local cleanup and no destructive git operations (`git worktree remove --force` absent).

**Reviewer-model contract (SPEC non-goals):** `ai_gate.ps1` `Resolve-Candidates` requires one explicit `provider/model` string (`^[^/\s]+/[^/\s]+$`), rejects missing/null/array, and removes candidate fallback; infrastructure failure is terminal (exit 1); CLI/override remain test seams. Task `models.review` = `opencode/big-pickle`. Harness cases converted from fallback semantics to no-fallback assertions.

**Bootstrap migration:** Current package resolves ACTIVE under `docs/tasks/active/`; the migrating gate itself produced the active-path snapshot (empty status.txt; diff excludes active-path reviews/EVIDENCE/CONTEXT).

**Docs/contracts (acceptance 13):** `docs/tasks/README.md`, `BACKLOG.md`, `docs/todos/README.md`, `docs/architecture/ai_development_workflow.md`, `.agents/rules/ai-verification-gate.md`, both `.agents/skills/...` files, harness, and probe now teach active-path semantics. Tree-art and prose verified clean on disk.

**Required tests (SPEC 禮Required deterministic tests):** `tests/test_task_package_resolver.py` (ACTIVE/MISSING/ARCHIVED/MALFORMED/AMBIGUOUS_ARCHIVE, caller wiring), `tests/test_task_archive.py` (integrated closeout, destination/branch collision tokens, fail-closed integration/missing, UTC boundary year 2025, per-step git failure, real push failure, protected repository state), updated `test_task_start_behavioral.py` (active-path fixtures), `test_workflow_scripts.py` grouped harness runs.

## Blocking findings

None.

## Advisory findings

1. **Snapshot-pipeline encoding:** `.runtime/ai_gate/task-lifecycle-active-archive/diff.patch` contains mojibake (`??`, `?ㄗmport`, `?` in tree art/em-dashes). Verified on disk that all affected working-tree files are clean (`# Legacy Todos`, `import { execFile...`, `param(`, tree art, SKILL prose). Artifact-only, but it degrades reviewer consumption of diff.patch; the gate's `chcp 65001` snapshot writer should be hardened.
2. **`task_archive.ps1` hardcodes the move source** (`git mv -- "docs/tasks/active/$Task"` at line 56) instead of `Get-TaskPackageRelativePath`, despite dot-sourcing the resolver. Same result today; mild drift against "single owner of path semantics" (already noted in the package's regression-review).
3. **Skill vs. behavior drift:** `branch_start_workflow/SKILL.md` states the start wrapper "requires every formal task `task.json` to contain one explicit `models.review`"; `task_start.ps1` validates only id/JSON/SPEC presence. Fail-fast enforcement lives in the Gate, which satisfies the SPEC contract; the SKILL wording overstates the wrapper.
4. **Unclassified flat packages:** six legacy flat packages remain at `docs/tasks/<id>/` (e.g., `generic-domain-catalog-expansion`, `domain-lobby-primary-start-boundary`); the resolver reports MISSING for them. This matches SPEC's "uncertain tasks are not guessed into archive", but they need explicit classification (active-move or archive) on their owning branches before acceptance criterion 14 is fully closed.

## Test evidence gaps

Focused deterministic tests exist for resolver classifications, archive fail-closed paths (incl. real push failure and UTC year boundary), active-path task_start fixtures, and grouped harness runs. Not executed here per read-only policy. Remaining evidence gaps: `task_archive.ps1` live run against a real `origin/main` with >1 matching worktree, and the five unclassified flat packages' migration/archive classification.

<!-- blackfire-gate-fingerprint: {"schema":1,"role":"spec-reviewer","hash":"0895fe58332b4d02ec41b98d66480a962836954a1c23cf580d5a5b0fb8fe9eb7"} -->
