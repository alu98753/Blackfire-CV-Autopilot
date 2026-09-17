# worktree-shared-venv-cleanup-safety

Status: Draft

## Goal

Make task-worktree closeout safe when each worktree consumes the repository-global Python environment through a local `.venv` Windows junction.

The current closeout contract says an active task worktree with a `.venv` junction can proceed directly to `git worktree remove <path>`. A real closeout demonstrated that this is unsafe on Windows: Git removal traversed into the junction target, attempted to unlink files from the canonical shared environment, hit a locked `.pyd`, partially removed the worktree (including `.git`), and left stale Git worktree metadata that still held the task branch.

This task must make closeout preserve the canonical shared environment, prevent partial-removal failure where practical, and define deterministic recovery when stale worktree metadata already exists.

## Lightweight survey evidence

Verified on `main` commit `4c7c1ec705b19a9cd249f1b3e8550b93856976b0`:

- `docs/architecture/ai_development_workflow.md` is the canonical workflow/workspace/environment SSOT. It defines one repository-global environment at `E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot` and requires each runnable worktree to expose a local `.venv` Windows junction to that environment.
- `.agents/skills/branch_completion_workflow/SKILL.md` is the canonical branch closeout procedure. Its current active-worktree cleanup step explicitly notes that `.venv` is only a junction consumer, but then instructs normal `git worktree remove <path>` without first unlinking/verifying that junction.
- The observed production incident occurred after `git worktree remove` attempted to unlink `...\.venv\Lib\site-packages\bidi\bidi.cp311-win_amd64.pyd`; the operation then left the worktree partially removed. After manually removing the `.venv` junction, a second `git worktree remove` failed because `<worktree>\.git` no longer existed, while `git branch -d` remained blocked because Git still registered the worktree.
- The canonical shared environment itself remained valid after the junction was removed with `rmdir <worktree>\.venv`.
- `docs/tasks/BACKLOG.md` does not currently contain this promoted task. Existing `shared-environment-mutation-protocol` is a different concern: dependency mutation/locking/rebuild. This task must not expand into shared-environment mutation semantics.

This is intentionally a lightweight pre-survey pass. The user explicitly authorized Gemini/Antigravity to replace OpenCode Scout for one read-only evidence survey for this task.

## Scope

- Correct the canonical closeout workflow so a task worktree's `.venv` junction is safely detached before the worktree directory is removed.
- Mechanically verify that a detected `.venv` is the expected Windows junction/reparse point and resolves to the canonical repository-global environment before automatic unlink is permitted.
- Never recursively delete or mutate the physical canonical shared environment during ordinary task closeout.
- Define fail-fast behavior when `.venv` is a normal directory, symlink/reparse point to an unexpected target, missing in a context where the workflow expects it, or otherwise ambiguous.
- Define deterministic recovery for the known partial-removal state where the worktree directory or `.git` marker has already disappeared but `git worktree list` still contains stale metadata. The recovery should use Git-supported stale-metadata cleanup (`git worktree prune`) only after proving the registered worktree is stale; it must not force-delete a live/dirty worktree.
- Preserve the current ancestry, cleanliness, branch ownership, and remote/main synchronization gates before cleanup.
- Update the durable workspace/closeout contract where needed so future ChatGPT/Gemini instructions do not regress to unsafe `git worktree remove` ordering.
- Add the smallest useful deterministic automation/test surface if one already exists or if introducing a narrowly scoped helper is justified by survey evidence. Do not invent a broad worktree manager solely for this task.

## Known invariants

- The canonical physical environment is external to all Git worktrees:
  `E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot`.
- A task worktree owns only its local `.venv` junction, never the target environment.
- Cleanup must never execute recursive deletion against the canonical environment target.
- Ordinary closeout remains an environment-consumer operation: no `pip install`, `pip uninstall`, venv recreation, editable install, or dependency mutation.
- Git worktree topology is live local-machine state; cleanup must inspect `git worktree list --porcelain` instead of assuming remembered ownership.
- Cleanup must verify task ancestry in `origin/main` before deleting the task worktree/branch.
- Dirty or ambiguous worktree state must fail closed; `--force`, `reset --hard`, `clean -fd`, or equivalent destructive shortcuts remain forbidden.
- Local branch deletion happens only after no registered worktree owns the branch.
- `shared-environment-mutation-protocol` remains out of scope.

## Non-goals

- No redesign of the shared Python environment topology.
- No dependency mutation, locking, rebuild, or package-management protocol.
- No general Git worktree orchestration framework unless existing repository structure already has the correct owner and only a narrow extension is needed.
- No automatic deletion of unknown `.venv` directories or reparse points.
- No `git worktree remove --force` fallback for unknown/dirty state.
- No unrelated changes to Scout/Gate/model routing or game runtime behavior.
- No production implementation while this SPEC remains Draft.

## Provisional acceptance criteria

1. Canonical closeout no longer instructs `git worktree remove` while an attached worktree-local `.venv` junction still points at the canonical shared environment.
2. Before unlinking `.venv`, cleanup verifies it is a junction/reparse point and that its resolved target equals the canonical environment path.
3. A verified junction is removed by unlinking the junction itself only; the canonical environment remains present and usable afterward.
4. If `.venv` is a real directory or points anywhere unexpected, cleanup stops with an actionable diagnostic and does not remove either `.venv` or the worktree.
5. After safe junction detach, normal clean-worktree removal proceeds without `--force`.
6. If an earlier failed removal already deleted `.git` / enough of the worktree that Git considers the registration stale, the workflow can detect that state and use `git worktree prune --verbose` as bounded recovery, then re-check `git worktree list --porcelain` before branch deletion.
7. A live registered worktree is never pruned merely because cleanup encountered an unrelated error.
8. Branch deletion remains blocked until the worktree registration no longer owns the branch.
9. The durable contract documents the safe order and recovery path once, without creating contradictory SSOTs.
10. If implementation adds automation/helper logic, deterministic tests cover at minimum: expected junction target, missing junction, real directory, wrong-target junction, normal removal handoff, and stale-registration recovery without touching a live worktree.

## Uncertainty for Gemini read-only survey

Gemini must resolve these facts before this SPEC becomes Final:

- Whether branch completion is intentionally instruction-only (`SKILL.md`) or whether an existing repository-owned cleanup/helper script should be the mechanical owner of junction inspection/unlink/recovery.
- Whether Windows-native commands already used by the repository can reliably distinguish junction vs directory and resolve the junction target without external dependencies; identify the safest non-interactive command/API contract.
- Whether `git worktree prune` can be safely bounded by prior checks to the exact stale state observed, and what evidence should be re-checked after pruning.
- Whether cleanup should treat a missing `.venv` as acceptable for non-runnable/legacy worktrees or as a fail-fast condition; preserve existing legacy-path policy.
- The smallest useful test strategy for a Windows/junction cleanup contract: docs/skill-only validation, PowerShell/Python helper tests using temporary directories, or an existing workflow test harness.
- Whether `docs/architecture/ai_development_workflow.md`, `.agents/skills/branch_completion_workflow/SKILL.md`, and any related startup/environment skill need synchronized wording to avoid future contradictory commands.
- Any repository convention for recovery after partially removed/stale worktrees that should be reused instead of adding new mechanics.

## Gemini survey evidence requested

Gemini/Antigravity must remain read-only and report:

- exact current closeout ownership/call surface;
- exact unsafe cleanup instruction(s) and why the junction can be traversed;
- existing helper/script/test infrastructure relevant to safe Windows worktree cleanup;
- recommended minimal implementation surface;
- exact junction verification + target-resolution mechanism supported by current Windows tooling;
- bounded stale-worktree recovery decision tree;
- nearby tests/contracts that must be updated;
- hidden risks such as locked handles, partial directory removal, branch exclusivity, stale registry entries, legacy worktree paths, or canonical-env target mismatch.

Gemini must not edit files, implement production changes, merge, or promote this Draft SPEC to Final.

## Completion gate

This SPEC is **Draft**. Do not start production implementation.

After Gemini pushes or returns read-only survey evidence, ChatGPT + user will reconcile this Draft against the evidence and current code/contracts, then explicitly promote it to `Status: Final` before Gemini/Antigravity implementation is allowed.