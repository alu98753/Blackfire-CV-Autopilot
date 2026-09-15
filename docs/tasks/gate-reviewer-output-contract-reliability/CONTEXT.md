Now let me read the workflow harness and the architecture doc for context.
Let me check the fake reviewer fixture and look for any structured output patterns in the codebase.
# Scout Context

**Maximum steps reached.** Here is the completed localization report based on the 6 files inspected within budget.

---

## Relevant files and symbols

| File | Why it matters |
|------|---------------|
| `docs/tasks/gate-reviewer-output-contract-reliability/task.json` | Task descriptor; defines scope, base_ref, review models, and focused_tests (currently empty). |
| `docs/tasks/gate-reviewer-output-contract-reliability/SPEC.md` | Canonical spec (Draft status). Defines the goal: decouple machine verdict extraction from free-form Markdown placement. |
| `scripts/ai_gate.ps1` | **Primary change target.** Contains `Get-OpenCodeInvocation`, `Get-FinalAssistantMessageFromStructuredJson`, `Get-CanonicalReviewPayload`, `Test-ReviewVerdictStructure`, and the main gate orchestration loop (lines 257??89). |
| `.opencode/agents/spec-reviewer.md` | Agent contract requiring `VERDICT:` / `BLOCKING_FINDINGS:` as the mandatory two-line header. **Spec says this header placement must NOT be the transport protocol.** |
| `.opencode/agents/regression-reviewer.md` | Same contract as spec-reviewer; same dependency on header-first free-form text. |
| `tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1` | Workflow harness test; exercises gate with fake reviewer via `--format json` output. Verifies PASS, BLOCK, malformed, and Markdown-wrapped verdict rejection. |

## Current control flow

1. **OpenCode invocation** (`Get-OpenCodeInvocation`, line 257): calls `opencode run --standalone --format json --agent <name> --model <candidate>` with the review prompt piped as final arg.
2. **Structured JSON extraction** (`Get-FinalAssistantMessageFromStructuredJson`, line 308): parses the JSONL stream, collects all `type: "text"` events, groups by `messageID`, concatenates the final assistant message text.
3. **Verdict header extraction** (`Get-CanonicalReviewPayload`, line 384): regex-searches the concatenated text for `^VERDICT: (PASS|BLOCK)\nBLOCKING_FINDINGS: \d+`. Requires the header to exist exactly once, anywhere in the text. Strips everything before the match.
4. **Verdict structure validation** (`Test-ReviewVerdictStructure`, line 438): **requires the output to begin on line 1** with `\AVERDICT: ...` (the `\A` anchor). This is the exact conflict point with the spec's goal of allowing verdict-last presentation.
5. **Candidate promotion** (lines 802??79): transactional backup/promote/rollback of `spec-review.md`, `regression-review.md`, and `EVIDENCE.md`.

**Key architectural conflict:** `Get-CanonicalReviewPayload` (step 3) already searches anywhere in the text and re-slices to begin at the match. But `Test-ReviewVerdictStructure` (step 4) applies `\A` (start-of-string) validation on the payload **returned by step 3**, which already re-slices. This means the current code *does* allow verdict-last in the raw text but normalizes it before validation. The spec's stated problem is that this normalization + free-form text parsing is fragile and should be replaced with structured output.

## Existing safety mechanisms

- **Bounded process execution** (`Invoke-BoundedProcess`, line 124): timeout, kill confirmation, stdout/stderr capture with thread-safe locking.
- **Candidate fallback loop** (lines 501??46): retries with next model candidate on timeout, non-zero exit, malformed JSON, extraction failure, or invalid verdict structure.
- **Transaction-safe promotion** (lines 802??79): backup-then-promote with rollback on failure.
- **Infrastructure block propagation**: `infraBlocked` flag prevents promotion and canon reviews are untouched on any infrastructure failure.
- **Markdown verdict rejection** (harness line 77/105-107): test case confirms bold-wrapped `**VERDICT: PASS**` is rejected as malformed.

## Existing tests

`tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1` covers:
- PASS through (exit 0) ??- BLOCK returns exit 2 ??- Malformed output returns exit 1 ??- Markdown-wrapped verdict rejected (exit 1) ??- Focused test override passes ??- Promotion rollback preserves prior artifacts ??- Step budget and forced finalization contract assertions ??
**Missing from existing tests:** no coverage for structured JSON output path (`IsStructured` = true) ??the harness always uses `_ReviewerExecutableOverride` which sets `IsStructured = $false`. No tests for verdict-last ordering. No tests for contradictory fields or stale PASS override.

## Regression and architecture risks

1. **Agent contract drift**: Both reviewer `.md` files instruct the model to place `VERDICT:` as line 1. Changing the machine contract without updating agent prompts risks a period where the agent follows old instructions while Gate expects new structured output.
2. **`--format json` semantics**: The current invocation uses `opencode run --standalone --format json`, which produces JSONL event streams (not JSON-Schema validated output). The spec's open question #1 (whether CLI supports structured output with schema validation) remains unproven from this inspection.
3. **`Test-ReviewVerdictStructure` dual role**: This function is both the "is this valid?" checker and the "normalize to line-1" enforcer. Replacing it requires touching both the extraction and validation paths.
4. **Harness doesn't test `IsStructured = $true` path**: The `Get-FinalAssistantMessageFromStructuredJson` function is untested by the workflow harness, which means changes to it have no automated regression coverage in the existing suite.
5. **Sibling paths**: The `Get-CanonicalReviewPayload` function strips pre-verdict content. A change to structured output must preserve this boundary or the entire artifact promotion chain changes.

## Uncertainty

1. **OpenCode CLI structured output support**: Cannot determine from repository files whether `opencode run --format json` supports JSON-Schema validated output or only raw JSONL event streaming. This is the critical blocker for the spec's preferred architecture direction.
2. **Model compatibility with structured output**: Unknown whether the configured free models (`opencode/mimo-v2.5-free`, `opencode/big-pickle`) support structured output consistently.
3. **OpenCode process model**: Unknown whether a long-lived `opencode serve` process is required or if one-shot `opencode run` suffices for structured output.
4. **Exact structured output schema path**: The spec mentions JSON-Schema structured output in OpenCode SDK documentation, but no evidence of actual schema files or SDK usage exists in the repository.

## Minimal proposed change surface

1. **Agent contracts** (`.opencode/agents/spec-reviewer.md`, `.opencode/agents/regression-reviewer.md`): Update prompt to produce structured output (JSON block or clearly delimited machine-readable section) instead of relying on free-text header placement.
2. **Gate extraction** (`scripts/ai_gate.ps1`): Modify `Get-FinalAssistantMessageFromStructuredJson` and/or replace `Get-CanonicalReviewPayload` + `Test-ReviewVerdictStructure` with a structured output parser that reads machine fields independently of human-readable Markdown.
3. **Gate invocation** (`scripts/ai_gate.ps1`): Potentially modify `Get-OpenCodeInvocation` to use structured output mode if the CLI supports it.
4. **Harness tests** (`tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1`): Add test cases for structured output path, verdict-last rejection acceptance, contradictory fields, and stale PASS override.

## Recommendation

**GO WITH SPEC CHANGES**

The task is well-scoped and the architecture direction is sound. However, the spec must be updated before finalization:

1. **OpenQuestion #1 must be resolved first**: The feasibility of JSON-Schema structured output via the CLI is the pivotal decision point. Without confirming this, the spec cannot choose between native structured output and a fallback delimiter contract. The spec should include a research spike or conditional architecture section.
2. **The spec should explicitly call out that the harness does not test the `IsStructured` code path** and that adding such coverage is part of the task.
3. **The spec should clarify the fallback architecture** (per spec line 66): if native structured output is not available, the narrowest deterministic transport should be specified ??e.g., a JSON code fence or XML-delimited section within the assistant's Markdown output ??rather than leaving the transport contract open.
