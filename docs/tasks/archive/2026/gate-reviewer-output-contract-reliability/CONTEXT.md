Now let me read the key implementation files in the scope.
**Maximum steps for this agent have been reached.** I will now provide the scout report based on the 8 files already inspected.

---

# Scout Context

## Relevant files and symbols

| File | Why it matters |
|------|---------------|
| `docs/tasks/gate-reviewer-output-contract-reliability/task.json` | Task descriptor: defines scope, focused tests, model matrix, and base_ref |
| `docs/tasks/gate-reviewer-output-contract-reliability/SPEC.md` | Canonical spec (Draft): defines the full responsibility-boundary contract, failure taxonomy, acceptance criteria, and open policy questions |
| `scripts/opencode_structured_review.mjs` | **Does not exist yet** ??listed in task.json scope but not present in the repo. This is the production adapter the SPEC expects to own SDK-v2 mechanical facts |
| `scripts/opencode_structured_review_probe.mjs` | Compatibility probe: proves SDK v2 structured output transport works. Contains reusable helpers: `validateOutcomeSchema`, `validateOutcomeSemantics`, `hasAuthoritativePromptResponse`, `inspectLifecycle`, `classifyLifecycle`, `normalizeStructuredResult`, `auditSessionMessages`. Diagnostic matrix logic (C1/C2/C3/CONTROL) lives here |
| `scripts/ai_gate.ps1` | **Primary change target**: the Gate orchestrator. Currently parses `opencode run --format json` JSONL text events, extracts last assistant text via `Get-FinalAssistantMessageFromStructuredJson`, then regex-extracts `VERDICT:` / `BLOCKING_FINDINGS:` headers via `Get-CanonicalReviewPayload` and `Test-ReviewVerdictStructure`. Contains transactional promotion with rollback, focused test integration, timeout/process management, and candidate fallback loop |
| `.opencode/agents/spec-reviewer.md` | Agent prompt: demands `VERDICT:` / `BLOCKING_FINDINGS:` header format, read-only permissions, 8-step budget |
| `.opencode/agents/regression-reviewer.md` | Agent prompt: same header format, 10-step budget, regression-focused grounding clauses |
| `scripts/opencode_contract.ps1` | Version pin: enforces `OpenCodeSupportedVersion = "1.18.31"` |

## Current control flow
| `tests/test_opencode_structured_review_probe.py` | Focused test: shells out to Node `--test` for `opencode_structured_review_probe.test.mjs` |

**Gate entry** (`ai_gate.ps1`):
1. Load task.json, validate id match, assert OpenCode version via `opencode_contract.ps1`.
2. Resolve review candidates from `config.models.review` or CLI override.
3. Create runtime + review directories; snapshot `git status` and `git diff`.
4. For each reviewer role (spec-reviewer, regression-reviewer), iterate candidate models:
   - `Get-OpenCodeInvocation` builds `opencode run --format json --agent <name> --model <cand>` (or uses `_ReviewerExecutableOverride` for test seams).
   - `Invoke-BoundedProcess` runs with timeout; captures stdout/stderr.
   - If `IsStructured` is true (the normal path), `Get-FinalAssistantMessageFromStructuredJson` parses JSONL, finds last text event, concatenates by `messageID`.
   - `Get-CanonicalReviewPayload` regex-extracts the `VERDICT:/BLOCKING_FINDINGS:` header from assistant text.
   - On success: store candidate, mark role completed, break. On failure: log provenance, continue to next candidate.
   - `Test-ReviewVerdictStructure` validates the header starts at line 1, cross-checks PASS?? / BLOCK?1.
6. Run focused tests from `config.focused_tests` via Python unittest.
5. If all candidates fail for any role ??`infraBlocked = true`, exit 1.
7. Transactional promotion: backup existing canonical files, copy candidates, rollback on failure.
8. Final exit code: 0 = PASS, 2 = CANDIDATE_BLOCKED, 1 = INFRASTRUCTURE_BLOCKED.

**Critical observation**: The Gate currently receives structured JSONL from `opencode run --format json`, but it does NOT extract `info.structured` (the JSON-Schema machine result). Instead it extracts the last **text** event and regex-parses `VERDICT:` headers from it. The SPEC explicitly says this is wrong ??verdict authority must come from the structured machine object, not from free-form Markdown placement.
## Existing safety mechanisms


- **Timeout + kill confirmation**: `Invoke-BoundedProcess` kills process tree and confirms exit within 3s.
- **Transaction-safe promotion**: backup ??copy ??rollback on failure with per-item try/catch.
- **Candidate fallback loop**: timeout/non-zero-exit/malformed/payload-extraction-failure all trigger fallback to next candidate.
- **Cross-field validation**: `Test-ReviewVerdictStructure` catches PASS+blocking?? and BLOCK+blocking<1.
- **Schema validation** (probe only): `validateOutcomeSchema` and `validateOutcomeSemantics` exist in the probe but are NOT used by Gate.
- **Lifecycle inspection** (probe only): `hasAuthoritativePromptResponse`, `inspectLifecycle`, `classifyLifecycle` exist in probe but are NOT used by Gate.
- **Version pinning**: `opencode_contract.ps1` enforces exact `1.18.31`.
- **Grounding enforcement**: agent prompts require `read`/`glob`/`grep` tool use; step budgets are safety ceilings.

## Existing tests

| Test | What it covers |
|------|---------------|
| `tests/test_opencode_structured_review_probe.py` | Shells out to `opencode_structured_review_probe.test.mjs` ??validates probe deterministic helpers (schema validation, lifecycle classification, outcome semantics) |
| **No ai_gate workflow tests** | There are no deterministic tests exercising the Gate's verdict extraction, fallback, promotion, or rollback paths. The task.json `focused_tests` only includes the probe test |

## Regression and architecture risks

1. **Responsibility boundary gap**: The SPEC mandates 10 distinct responsibility layers (grounding ??lifecycle ??semantic ??transport ??schema ??cross-field ??rendering ??promotion ??failure ??fallback). The current Gate only implements transport (JSONL parsing) + text-header extraction + cross-field check. Layers 1-5 and 7-9 are either missing or conflated.

| `tests/workflow_scripts/opencode_structured_review_probe.test.mjs` | Node built-in test for probe exports (not read, but referenced) |
2. **Missing adapter**: `scripts/opencode_structured_review.mjs` does not exist. The SPEC expects a dedicated SDK-v2 adapter owning mechanical facts. Without it, Gate must either absorb adapter responsibilities or remain incomplete.

3. **Probe-Gate coupling risk**: The probe contains production-relevant helpers (`validateOutcomeSchema`, `validateOutcomeSemantics`, `hasAuthoritativePromptResponse`, `inspectLifecycle`) that the SPEC says should be "reused without coupling production Gate to diagnostic matrix logic." The exact reuse boundary is unresolved.

4. **Agent prompt format conflict**: Both reviewer agents still demand `VERDICT:` / `BLOCKING_FINDINGS:` as the first two lines of the final text response. The SPEC says verdict must come from the structured machine object, not text headers. The prompts need updating to emit structured output instead of (or in addition to) text headers.

5. **No grounding proof in Gate**: The SPEC requires Gate to prove the reviewer was grounded in repository evidence. Currently Gate has no lifecycle audit capability ??it trusts whatever the process returns.

6. **No max-step exhaustion signal**: The SPEC explicitly says `finish == "tool-calls"` is not proof of max-step exhaustion. The probe's `inspectLifecycle` checks for `step-finish` parts with forced reasons, but Gate has no equivalent. The SPEC leaves this as an open policy question.

## Uncertainty

1. **Does `opencode run --format json` return `info.structured`?** The probe proves the SDK v2 `session.prompt` API returns `info.structured` for structured output requests. But the Gate uses `opencode run --format json` (CLI), not the SDK directly. It is unclear whether the CLI JSONL output includes structured output data that the Gate could extract, or whether a direct SDK adapter (`opencode_structured_review.mjs`) is mandatory.

2. **What exact files will change?** The SPEC's "Draft scope" is provisional. The Final SPEC may add or remove files. The absence of `opencode_structured_review.mjs` suggests either it was never created or was removed.

3. **Unresolved policy questions from SPEC**: 6 open questions remain, including max-step signal, grounding requirement flexibility, fallback eligibility, validation layering, provenance split, and probe-to-production helper reuse.

4. **Test seam for structured adapter**: The SPEC asks what the "smallest test seam" is for structured adapter envelopes. No ai_gate workflow tests exist currently, so the entire test infrastructure for Gate verdict extraction needs to be created.


## Minimal proposed change surface
Based on SPEC "Draft scope" and current code gaps:

- **`scripts/ai_gate.ps1`**: Replace `Get-FinalAssistantMessageFromStructuredJson` + `Get-CanonicalReviewPayload` + `Test-ReviewVerdictStructure` with structured-output-aware extraction (from `info.structured` or equivalent), add lifecycle/grounding audit, add schema+semantic validation, preserve existing timeout/fallback/promotion/test infrastructure.
- **`scripts/opencode_structured_review.mjs`** (new): SDK-v2 adapter owning session lifecycle, structured result extraction, and deterministic machine envelope to Gate.
- **`.opencode/agents/spec-reviewer.md`** and **`.opencode/agents/regression-reviewer.md`**: Update prompt to emit structured JSON-Schema output instead of (or in addition to) text headers; remove obsolete "line 1" header requirement.
- **`tests/workflow_scripts/`**: New deterministic tests exercising structured adapter/Gate seam and all failure classifications.

## Recommendation

**GO WITH SPEC CHANGES**

Evidence: The current Gate implementation (`ai_gate.ps1`) is functional but architecturally misaligned with the SPEC's 10-layer responsibility model. The SPEC itself is Draft with 6 open policy questions and acknowledges that "no production implementation may begin until fresh Scout evidence is pushed and ChatGPT + user converge this contract to Final." The adapter file (`opencode_structured_review.mjs`) does not exist yet. The probe proves the transport layer works and contains reusable helpers, but the production Gate has no lifecycle audit, no schema validation against structured output, and no grounding proof. The gap is well-understood and bounded ??the minimal change surface is 4-6 files ??but the SPEC must be finalized before implementation begins. This scout report provides the localization evidence needed to finalize the SPEC.
