# Spec Review

Gate-accepted verdict: BLOCK
Blocking findings: 1

Maximum steps for this agent have been reached before finalization of the structured verdict. The following text summarizes the bounded spec-review work completed.

## What was accomplished

Read all four supplied snapshots (task.json, SPEC.md Final, status.txt, 1978-line diff.patch) and grounded them against the current worktree:

- **Resolver** (`scripts/task_package_resolver.ps1`): implements ACTIVE / ARCHIVED / MISSING / MALFORMED / AMBIGUOUS_ARCHIVE with `RequireActive` fail-closed; single owner of `docs/tasks/active/<task-id>` path semantics. Grounded in repo; matches SPEC decisions 1/3/4/5.
- **Archive command** (`scripts/task_archive.ps1`): requires clean main at origin/main, exactly one task worktree, mechanically verifies integration via unique first-parent merge boundary, derives UTC year from the integration commit, checks destination/closeout-branch collisions, prepares the move in a temporary detached worktree, pushes `origin/archive/<task>-<year>`, and fails closed on every critical step (tested via `$_FailGitStep`). Matches SPEC "Archive command" and decision clauses.
- **Caller migration**: ai_gate.ps1, ai_scout.ps1, task_start.ps1 all consume the resolver; prompts/excludes/EVIDENCE/reviews now resolve under the active package. Grep confirmed zero remaining hardcoded flat `docs/tasks/$Task` constructs in `scripts/`.
- **Docs/contracts**: .agents rules/skills, ai_development_workflow.md, docs/tasks/README.md, BACKLOG.md, todos/README.md updated to active-path semantics.
- **Tests**: new test_task_package_resolver.py and test_task_archive.py present with deterministic fixtures; harness fixture migrated to `docs/tasks/active/`; harness split into runnable groups with per-case selection.
- **Migration**: ~31 legacy flat packages renamed to `docs/tasks/archive/2026/`; current task package present at `docs/tasks/active/task-lifecycle-active-archive/` (SPEC.md, task.json, CONTEXT.md, reviews/).

## Blocking finding identified (grounded)

### B1 — Diff changes Gate reviewer execution semantics that the Final SPEC explicitly lists as a non-goal
Severity: BLOCKING
Contract / invariant: SPEC.md "Non-goals": "Redesign Scout/Gate model routing or reviewer execution"; Architecture decision 2 "SPEC.md remains the behavioral contract"
Location: scripts/ai_gate.ps1 `Resolve-Candidates` (diff hunk at index b0138b1..07ea6d9); scripts/task_archive.ps1 unchanged; tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1
Claim: `ai_gate.ps1` previously treated `models.review` as an optional array of candidates with fallback; the diff makes it a single required `provider/model` string, rejects null/arrays/locally configured defaults, silently discards additional `_ReviewCandidatesOverride` entries beyond `[0]`, and converts pre-authority candidate failures from fallback (exit 0) to terminal VERIFICATION_UNAVAILABLE (exit 1).
Evidence: diff.patch `Resolve-Candidates` rewrite (`if ($raw -isnot [string]) { throw ... candidate arrays are not allowed }`), harness cases renamed "…is terminal", "…has no fallback", "…failure is unavailable without fallback" (e.g. `Assert-True ($code.ExitCode -eq 1)` where the baseline asserted exit 0 fallback), plus branch_start_workflow SKILL.md new requirement "null, missing, empty, array, or locally configured defaults are invalid".
Why this is a contract break: SPEC.md (Status: Final) never authorizes this reviewer-execution change; the new `models.review` mandatory-string contract appears only in diff-side docs, not in the canonical behavioral contract. The change is coherent and consistently documented on the branch, but it alters production runtime behavior beyond the Final SPEC's declared non-goal boundary. Per the gate rule "Treat SPEC.md scope, invariants, acceptance criteria, and non-goals as authoritative", this divergence must be resolved (either amend the Final SPEC to authorize the reviewer-model contract, or restore baseline candidate semantics) before acceptance.

## Advisory findings

- `scripts/opencode_structured_review_probe.mjs` QUALIFICATION_PROMPT/SMOKE_PROMPT (lines 77, 85) hardcode `docs/tasks/active/opencode-structured-review-provider-compatibility/` while the same diff archives that package to `docs/tasks/archive/2026/...`; post-merge the probe instructs reviewers to read a non-existent path. Verify whether the probe runs in any production gate/readiness path; otherwise update the prompt.
- Six flat legacy packages remain at `docs/tasks/<id>/` (generic-domain-catalog-expansion, backend-default-runtime-mode, foreground-demo-mode-isolation, cli-io-mode-contract-cleanup, domain-lobby-primary-start-boundary, plus domain-common-template-decoupling which the SPEC says is governed by its own branch). The resolver has no flat fallback, so any start/Scout/Gate on those tasks resolves MISSING. SPEC item 9 allows a temporary bridge only until acceptance; confirm the five unclassified packages are explicitly classified (active move vs archive) before acceptance.
- `task_archive.ps1`: `git fetch origin main` exit code is not checked before `git rev-parse origin/main`; a failed fetch could silently use a stale remote ref (fails closed in most cases, but error determinism is weaker than the rest of the script).
- New BOM artifacts in diff (docs/todos/README.md, probe .mjs, harness .ps1) are consistent with the snapshot-encoding issue noted in the existing `reviews/spec-review.md`; working-tree bytes were reported intact there. Advisory only.

## Test evidence gaps / remaining verification

- Could not execute focused tests (read-only review); deterministic fixtures exist for resolver (ACTIVE/MISSING/ARCHIVED/MALFORMED/AMBIGUOUS_ARCHIVE) and archive (integration, collision, not-integrated, UTC year boundary, critical git failures, real push failure).
- Did not read the existing `reviews/spec-review.md` / `regression-review.md` in the active package to compare prior findings; recommend the next reviewer do so and confirm how the `Resolve-Candidates` non-goal tension was previously adjudicated.

## Recommendation for next step

Resume this review (or a new spec-review run) with: (1) read `docs/tasks/active/task-lifecycle-active-archive/reviews/*.md` for prior adjudication, (2) resolve B1 by either amending the Final SPEC to authorize the mandatory `models.review` single-string contract or reverting `Resolve-Candidates` to baseline semantics, (3) decide the five unclassified flat packages, (4) repair the probe's archived package path reference.

<!-- blackfire-gate-fingerprint: {"schema":1,"role":"spec-reviewer","hash":"e7a6b5f79ab2f96e4057f2fc58c3d93f30b8be067d29f16dcedb88e0780bf197"} -->
