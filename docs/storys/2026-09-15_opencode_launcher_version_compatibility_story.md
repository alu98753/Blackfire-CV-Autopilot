# OpenCode Launcher Version Compatibility — PARS Story

## Problem

The AI workflow regressed after Scout/Gate launchers began emitting `opencode run --standalone ...`. The deployed OpenCode CLI baseline was 1.18.31, where `run` does not accept `--standalone`, so Scout/Gate failed at CLI parsing before provider/model inference. The repository also lacked an enforced OpenCode version contract, allowing local installations to drift.

## Action

- Established exactly OpenCode CLI `1.18.31` as the repository-supported version through `scripts/opencode_contract.ps1`.
- Removed unsupported `--standalone` from production Scout/Gate invocation builders without substituting `--pure`.
- Kept process isolation and lifecycle safety owned by the PowerShell wrappers: repository working directory, closed stdin, redirected stdout/stderr, bounded timeout, termination confirmation, fail-closed behavior, and artifact safety.
- Made bootstrap install the exact pinned package when OpenCode is missing and reject mismatched installed versions with actionable remediation.
- Added deterministic invocation probes and workflow harness coverage for production argument construction and version gating.
- Updated the live AI development workflow contract.
- Recovered a local incompatible OpenCode DB state by preserving the old database and allowing pinned 1.18.31 to create fresh state; this was treated as local state compatibility, not a launcher-code defect.

## Result

- Focused workflow harness: 16/16 cases passed.
- Direct `opencode run` smoke test under 1.18.31 reached model execution successfully.
- Canonical Scout succeeded and promoted `CONTEXT.md`.
- Independent spec reviewer: PASS, 0 blocking findings.
- Independent regression reviewer: PASS, 0 blocking findings.
- Canonical AI Gate: PASS.
- Full game/runtime suite was explicitly waived for closeout because this task changes AI workflow infrastructure rather than game automation behavior.

## Significance

Scout/Gate launcher behavior is now tied to an explicit CLI compatibility contract instead of an assumed flag. Version drift fails early and deterministically, while process isolation remains a repository-owned responsibility. This removes the self-hosting blocker and unblocks the downstream `opencode-structured-review-provider-compatibility` task from rerunning canonical Scout on top of the repaired workflow.
