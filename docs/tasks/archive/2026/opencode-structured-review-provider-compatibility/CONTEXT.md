# Maximum Steps Reached - Localization Audit Summary

## Status: Scout Context Established (Budget Reached)

I have completed the read-only localization audit within the exploration budget. Here is the synthesized report based on the 8 files inspected:

---

# Scout Context

## Relevant files and symbols

1. **`docs/tasks/opencode-structured-review-provider-compatibility/task.json`** - Task descriptor defining scope, base ref, and model candidates (Big Pickle, MiMo v2.5)
2. **`docs/tasks/opencode-structured-review-provider-compatibility/SPEC.md`** - Canonical draft spec defining the structured-output lifecycle requirement and capability classification contract
3. **`scripts/opencode_contract.ps1`** - Version gate (`$OpenCodeSupportedVersion = "1.18.31"`) and `Assert-OpenCodeSupportedVersion` function that enforces exact version match
5. **`scripts/ai_scout.ps1`** - Scout orchestrator with model candidate fallback and structural output validation (`hasHeading` check for `# Scout Context`)
6. **`.opencode/agents/regression-reviewer.md`** - Reviewer agent definition with `VERDICT: PASS|BLOCK` contract and `steps: 10` budget
4. **`scripts/ai_gate.ps1`** - Gate orchestrator containing `Get-OpenCodeInvocation` (constructs `opencode run --format json --agent ... --model ...`), `Get-FinalAssistantMessageFromStructuredJson`, `Get-CanonicalReviewPayload`, and `Test-ReviewVerdictStructure` - the complete structured output parsing chain

## Current control flow

1. `ai_gate.ps1` resolves review candidates from `task.json` `models.review` array
The structured-output lifecycle under investigation runs:
2. For each reviewer (spec-reviewer, regression-reviewer), it iterates candidates
3. `Get-OpenCodeInvocation` builds: `opencode run --format json --agent <agent> --model <candidate>` with `IsStructured = $true`
4. `Invoke-BoundedProcess` runs the process with timeout (480s default)
5. **Key extraction path**: `Get-FinalAssistantMessageFromStructuredJson` parses JSONL lines, finds `type: "text"` events, extracts last assistant message text
7. `Test-ReviewVerdictStructure` validates the header format

6. `Get-CanonicalReviewPayload` extracts the `VERDICT: PASS|BLOCK` header from extracted text
**Critical observation**: The gate currently parses `--format json` JSONL output for `text` type events containing the verdict prose. It does NOT use `structured_output` as a JSON-Schema mechanism. The spec's target lifecycle requires `structured_output` payload validation against a JSON Schema - this is a **different mechanism** than the current text-in-JSONL approach.

## Existing safety mechanisms

- Version assertion: `Assert-OpenCodeSupportedVersion` enforces exactly `1.18.31`
- Process isolation: `Invoke-BoundedProcess` with stdin closed, timeout, kill confirmation
- Candidate fallback: Both gate and scout iterate model candidates on infrastructure failure
- Atomic promotion: Backup-then-promote pattern for canonical artifacts
- Verdict terminality: Valid PASS/BLOCK stops candidate iteration; fallback only on infrastructure failure
- Structured JSON extraction: `Get-FinalAssistantMessageFromStructuredJson` handles JSONL parsing
- Malformed output detection: Multiple failure classes (TIMEOUT, MALFORMED_OUTPUT, PAYLOAD_EXTRACTION_FAILED, etc.)

## Existing tests

- No existing tests specifically validate structured_output JSON-Schema lifecycle

## Regression and architecture risks
- **`tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1`** - Test harness infrastructure exists but focused test declarations for this task are empty (`"focused_tests": []`)

- **Version lock**: `opencode_contract.ps1` hardcodes `1.18.31`. Any isolated version probe for newer OpenCode versions must bypass or override this gate. The gate script has `_OpenCodeVersionOverride` test seam parameter.
- **`--format json` vs `structured_output`**: The current gate uses `--format json` which produces JSONL events. The spec targets `structured_output` JSON-Schema validation. These may be different OpenCode CLI features. The `IsStructured` flag in the gate means "output is JSONL format", not "JSON-Schema structured_output was used".
- **Provider/model capability boundary**: Historical evidence shows `finish: tool-calls` failures (Big Pickle, MiMo) where models never left the tool-calling loop. This is a model/provider behavior, not a launcher issue.
- **No probe infrastructure**: The task requires a "bounded live probe" but no existing test infrastructure exercises the structured_output lifecycle end-to-end with model invocation.

## Uncertainty

Cannot be proven from files inspected within budget:
- **Exactly what OpenCode CLI flag/mechanism produces JSON-Schema `structured_output`** (vs `--format json` JSONL). The spec mentions `structured_output` but the current gate only uses `--format json`.
- **Whether `structured_output` is a CLI flag, agent config field, or API parameter** in OpenCode 1.18.31.
- **Whether Big Pickle / MiMo `finish: tool-calls` failures reproduce** after the launcher/DB repair baseline.
- **The safest reversible method for multi-version isolation** on this Windows environment.
- **Which additional providers/models are available** to the user.
- **Whether a minimal probe agent** (simpler prompt, explicit tool-call-then-stop instruction) or the actual reviewer agent is the better qualification surface.

## Minimal proposed change surface
- **Task package**: `docs/tasks/opencode-structured-review-provider-compatibility/` (CONTEXT.md, probe evidence, compatibility matrix)
- **Probe tooling**: New script under `scripts/` (e.g., `Test-StructuredOutputProbe.ps1`) to exercise the target lifecycle with bounded attempts

- **`scripts/opencode_contract.ps1`**: May need version override mechanism for isolated version probes (test seams already exist in gate/scout)
- **`.opencode/`**: Possibly a minimal probe agent definition if the actual reviewer agent is too heavy for qualification

## Recommendation

**GO WITH SPEC CHANGES** - The task is well-defined and the repository has sufficient infrastructure to support it. However, the spec needs clarification on:

1. **The exact OpenCode mechanism for `structured_output`** - The current gate uses `--format json` JSONL, not JSON-Schema structured_output. The spec should clarify whether the target is (a) the existing JSONL text-extraction path (which is already proven working for text verdicts), or (b) a distinct OpenCode `structured_output` feature that requires different invocation.
2. **Probe agent vs actual reviewer** - The spec should decide whether to use the actual reviewer agents (with their full permission sets and prompt complexity) or a minimal dedicated probe agent for qualification.
3. **Version override mechanism** - For Phase 2 isolated probes, the spec should acknowledge that `opencode_contract.ps1` version gate has test seams (`_OpenCodeVersionOverride`) that can be used without modifying production code.

The infrastructure is sound. The primary uncertainty is semantic (what exactly `structured_output` means in the OpenCode CLI context) rather than architectural.
