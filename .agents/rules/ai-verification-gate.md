# AI Verification Gate Writer Rule

This rule applies when the current branch contains an active task descriptor at `.ai/tasks/<task-id>/task.json`.

Before implementation:

1. Read `.agents/AGENTS.md` and all repository skills that apply to the task.
2. Read the task descriptor completely.
3. Read the canonical specification referenced by `task.json`.
4. Read `.ai/tasks/<task-id>/CONTEXT.md` when it exists.
5. Treat the canonical spec's scope, invariants, acceptance criteria, and non-goals as authoritative. Scout output is supporting evidence, not a replacement specification.
6. If the spec and current implementation materially conflict in a way that changes the requested behavior, stop and report the conflict instead of silently reinterpreting the task.

During implementation:

1. Implement the smallest coherent change that satisfies the contract.
2. Preserve verified existing behavior outside the explicit change scope.
3. Do not opportunistically perform unrelated lifecycle migration, architecture cleanup, or shared-framework extraction.
4. Run only the smallest directly relevant focused tests allowed by the project test policy. Never run the full suite on your own.

Before declaring the task ready for final review:

1. Run the repository verification gate with the explicit task id:

   ```powershell
   .\scripts\ai_gate.ps1 -Task <task-id>
   ```

2. If the gate returns BLOCK, do not claim completion. Read `.ai/tasks/<task-id>/EVIDENCE.md` and both reviewer reports, validate every blocking claim against code/tests, and fix only findings that are supported by evidence.
3. Do not let OpenCode reviewers edit production code in v1.
4. A PASS from the local gate is not final approval; ChatGPT/human final review remains required.
5. After focused verification passes, ask the user to run the full suite manually when required by `.agents/AGENTS.md`.

Never create a global `.ai/current-task` marker. This project uses multiple permanent worktrees; all workflow commands must name the task explicitly.