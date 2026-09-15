# gate-reviewer-step-budget-reliability

Status: Draft

## Goal

Prevent otherwise valid OpenCode Gate reviews from becoming `INFRASTRUCTURE_BLOCKED` solely because a reviewer exhausts its configured tool-step budget and is forced into OpenCode max-step finalization before producing a structurally complete canonical verdict response.

## Observed problem

A real `gate-payload-robustness-v1` closeout run showed `spec-reviewer` configured with `steps: 5` consuming its available tool steps. OpenCode then forced max-step finalization and emitted a text-only terminal response beginning with `Maximum steps for this agent have been reached...` followed later by a semantically valid review and verdict text. The structured stream did not provide a normal completed assistant-message boundary for that terminal response, so Gate correctly classified the reviewer attempt as infrastructure failure and preserved canonical evidence.

The current reviewer contracts simultaneously state:

- `steps: 5`;
- stop early once enough evidence exists;
- never rely on forced max-step finalization.

The observed run demonstrates that the configured budget can be inconsistent with that contract under a realistic review workload.

## Provisional scope

Primary change surface to investigate:

- `.opencode/agents/spec-reviewer.md`
- `.opencode/agents/regression-reviewer.md`
- `docs/architecture/ai_development_workflow.md`
- `tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1` if deterministic coverage is appropriate
- `docs/tasks/gate-reviewer-step-budget-reliability/`

`scripts/ai_gate.ps1` is not in provisional implementation scope. Scout may inspect it to confirm boundaries, but parser/extractor changes belong to `gate-payload-robustness-v1` and must not be duplicated here unless Final SPEC explicitly proves a separate responsibility gap.

## Known invariants

1. OpenCode reviewers remain read-only bounded blocker detectors.
2. Reviewer semantic authority does not change: PASS/BLOCK rules and blocking-finding meaning remain unchanged.
3. Max-step forced finalization must not be treated as an alternate valid verdict carrier merely because its text contains `VERDICT` later in the message.
4. Gate must not search older messages, tool-result content, or partial output to salvage a PASS/BLOCK verdict.
5. Infrastructure failure must continue to preserve canonical `reviews/*` and `EVIDENCE.md`.
6. Model fallback remains an infrastructure mechanism, not review-shopping.
7. No production/game behavior changes.
8. Do not broaden reviewer exploration into an exhaustive proof engine; early-stop pressure remains part of the reviewer contract.

## Non-goals

- changing Gate payload grammar;
- changing the structured-message completion rules introduced by `gate-payload-robustness-v1`;
- changing reviewer PASS/BLOCK semantics;
- adding degraded automatic review fallback;
- changing model routing order;
- changing Gate timeout policy unless Scout evidence shows step budget and timeout are inseparable;
- changing Scout behavior;
- modifying production/game code;
- solving general workflow orchestration or GitHub Actions automation.

## Provisional acceptance criteria

1. A reviewer should have enough bounded step budget to complete representative Gate review work without routinely entering forced max-step finalization.
2. The chosen budget must remain finite and intentionally bounded.
3. `spec-reviewer` and `regression-reviewer` budgets are justified independently if their evidence needs differ; identical values are not required by default.
4. Reviewer contracts continue to instruct early stopping rather than encouraging use of the full budget.
5. Architecture documentation and actual reviewer configuration remain consistent.
6. Any deterministic regression coverage added for reviewer configuration or workflow behavior passes offline.
7. Existing Gate semantic, parser, fallback, timeout, and evidence-promotion behavior remains unchanged outside the explicit Final SPEC.
8. The fix is validated against the real P1 blocker by rerunning `gate-payload-robustness-v1` Gate after this task is integrated; that downstream rerun is evidence of usefulness, not permission for this task to edit P1 implementation.

## Uncertainty / Scout questions

1. Is increasing `steps` alone the smallest reliable fix, or is the reviewer prompt consuming budget inefficiently in a way that should be corrected instead?
2. What step budget is justified by actual reviewer tool-call patterns rather than guesswork?
3. Should `spec-reviewer` and `regression-reviewer` use the same budget?
4. Can the offline workflow harness deterministically protect this contract, or should validation be limited to configuration/contract checks plus real Gate evidence?
5. Does OpenCode expose any stable terminal/max-step signal that should be observed, without changing Gate semantics?
6. Are current 300-600 word PASS-output targets and evidence-reading expectations compatible with the proposed budget?

## Dependency / closeout intent

This is an urgent workflow-infrastructure unblocker for the still-open `gate-payload-robustness-v1` task. After this task is finalized, implemented, Gate-reviewed, and merged, return to P1 and rerun its Gate without further parser/extractor widening unless new evidence proves a distinct defect.
