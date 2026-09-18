# AI Verification Gate Writer Rule

This rule applies when the current branch contains an active task package at `docs/tasks/active/<task-id>/` with both `SPEC.md` and `task.json`.

Before implementation:

1. Read `.agents/AGENTS.md` and all repository skills that apply to the task.
2. Read `docs/tasks/active/<task-id>/task.json` completely.
3. Read the canonical `docs/tasks/active/<task-id>/SPEC.md` completely.
4. Read `docs/tasks/active/<task-id>/CONTEXT.md` when it exists.
5. Treat `SPEC.md` scope, invariants, acceptance criteria, and non-goals as authoritative. `task.json` is automation metadata only; Scout output is supporting evidence only.
6. If `SPEC.md` is explicitly marked `Status: Draft`, stop before production implementation and report that the contract still requires ChatGPT/user finalization after Scout evidence.
7. If the spec and current implementation materially conflict in a way that changes the requested behavior, stop and report the conflict instead of silently reinterpreting the task.

During implementation:

1. Implement the smallest coherent change that satisfies the Final contract.
2. Preserve verified existing behavior outside the explicit change scope.
3. Do not opportunistically perform unrelated lifecycle migration, architecture cleanup, or shared-framework extraction.
4. Run only the smallest directly relevant focused tests allowed by the project test policy. Never run the full suite on your own.
5. Do not modify `SPEC.md` merely to make the implementation appear compliant. Material contract changes belong to the contract owner.

Before declaring the task ready for final review:

1. Run the repository verification gate with the explicit task id:

   ```powershell
   .\scripts\ai_gate.ps1 -Task <task-id>
   ```

2. If the gate returns BLOCK, do not claim completion. Read `docs/tasks/active/<task-id>/EVIDENCE.md` and both reviewer reports, validate every blocking claim against code/tests, and fix only findings supported by evidence.
3. Do not let OpenCode reviewers edit production code in v1.
4. A PASS from the local gate is not final approval; ChatGPT/human final review remains required.
5. After focused verification passes, ask the user to run the full suite manually when required by `.agents/AGENTS.md`.

Never create `.ai/current-task`, `docs/tasks/active/current`, or another global mutable task marker. This project uses multiple permanent worktrees; all workflow commands must name the task explicitly.

