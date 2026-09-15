Now let me quickly check if there's any existing EVIDENCE.md to understand the current artifact, and also look at the relevant promotions/rollback area more carefully.
I have enough context. Let me finalize the scout report.

---

# Scout Context

## Relevant files and symbols

| File | Why it matters |
|------|---------------|
| `scripts/ai_gate.ps1` (lines 384-464) | Contains `Get-CanonicalReviewPayload` and `Test-ReviewVerdictStructure` ??the two parsing functions that reject Markdown-wrapped headers. Primary change surface for normalization. |
| `scripts/ai_gate.ps1` (lines 466-773) | Candidate loop, `$provenanceRecords` collection, EVIDENCE.md generation, and attempt-provenance writing. Provenance retention gap lives here. |
| `scripts/ai_gate.ps1` (lines 796-889) | Transaction-safe promotion and rollback of `EVIDENCE.md` alongside reviewer reports. Current promotion completely overwrites prior `EVIDENCE.md`, erasing failed-attempt history. |
| `tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1` (lines 53-89) | Fake reviewer output modes (`pass`, `block`, `malformed`, `markdown`); the `Gate Markdown verdict remains rejected` case (line 86-89) is the red?reen regression target. |

## Current control flow

1. **Reviewer invocation** (line 502-646): For each reviewer target, normal candidates are tried sequentially. Raw stdout/stderr is captured by `Invoke-BoundedProcess`.
2. **Structured JSON extraction** (line 565-582): If `IsStructured`, `Get-FinalAssistantMessageFromStructuredJson` pulls the final assistant text from JSONL events.
3. **Payload extraction** (line 584-598): `Get-CanonicalReviewPayload` searches the assistant text for `^VERDICT: (PASS|BLOCK)\nBLOCKING_FINDINGS: \d+` (line 411). This regex requires literal `VERDICT:` at line start ??**Markdown bold, headings, backticks all cause `PAYLOAD_EXTRACTION_FAILED`**.
4. **Structure validation** (line 600-614): `Test-ReviewVerdictStructure` applies the same strict `\AVERDICT:` regex (line 448) and enforces PASS?? / BLOCK?1 semantic consistency. Input comes directly from `Get-CanonicalReviewPayload`'s payload, which already failed before reaching here for Markdown-wrapped input.
5. **Provenance collection** (line 478, appended at lines 520-626): `$provenanceRecords` collects structured records for every attempt (outcomes: `TIMEOUT`, `NON_ZERO_EXIT`, `PAYLOAD_EXTRACTION_FAILED`, `MALFORMED_STRUCTURED_JSON`, `INVALID_VERDICT_STRUCTURE`, `VALID_VERDICT`).
6. **EVIDENCE.md generation** (lines 746-795): Current run's `$provenanceRecords` are rendered into the `## Attempt provenance` section, then written to `candidate_EVIDENCE.md` and promoted to canonical `EVIDENCE.md`.
7. **Promotion** (lines 803-889): Backup existing canonical artifacts, copy candidates, rollback on failure. `EVIDENCE.md` is fully overwritten ??**no historical merge occurs**.

## Existing safety mechanisms

- **Duplicate-header rejection** (line 421-427): `Get-CanonicalReviewPayload` rejects `Count -gt 1` matches, producing an ambiguous error. This invariant must survive normalization.
- **Semantic consistency gate** (lines 456-460): PASS must have 0 blocking; BLOCK must have ??.
- **Transaction-safe promotion** (lines 803-867): Backup-then-copy with rollback on failure, including simulated failure seam `$_FailPromotionOnTarget`.
- **`$provenanceRecords`** already tracks role, type, index, model, elapsed, outcome, and selection state ??reusable for historical retention without changing reviewer semantics.
- **Fake reviewer `markdown` mode** (harness line 58): Currently produces `**VERDICT: PASS**\n**BLOCKING_FINDINGS: 0**\n` ??the exact production-failure pattern.

## Existing tests

| Case | Current behavior | Post-change expectation |
|------|-----------------|------------------------|
| `Gate Markdown verdict remains rejected` (line 86) | Exit code 1 (INFRASTRUCTURE_BLOCKED) | **Must flip to exit code 0 (PASS)** ??this is the red?reen regression test |
| `Gate PASS and candidate override resolution` (line 74) | Exit 0 | Unchanged |
| `Gate BLOCK returns 2` (line 78) | Exit 2 | Unchanged |
| `Gate malformed output returns 1` (line 82) | Exit 1 | Unchanged |
| `Gate promotion rollback preserves prior artifacts` (line 97) | Exit 1, EVIDENCE.md preserved | Unchanged |

## Regression and architecture risks

1. **Normalization scope leak**: `**VERDICT: PASS**` stripping must not be overly permissive (e.g., `# VERDICT: PASS` inside headings, or arbitrary inline markdown like `text **VERDICT: PASS** text`). The regex must remain anchored and deterministic.
2. **Multiple-header rejection after normalization**: If normalization strips `**` from two competing headers, both could become visible and correctly rejected. But if one header is normalized and one is not, the count may drop from 2??, incorrectly accepting an ambiguous payload. **The normalization must apply uniformly to all matches, or rejection logic must operate on the pre-normalized text**.
3. **`Test-ReviewVerdictStructure` receives pre-extracted payload**: Since `Get-CanonicalReviewPayload` already extracts the header substring (line 429), normalization should happen in `Get-CanonicalReviewPayload` before the match. `Test-ReviewVerdictStructure` then validates the clean payload. Both functions' regexes must agree.
4. **Provenance erosion on rerun**: Currently, a successful rerun generates a fresh `EVIDENCE.md` with only the current run's `$provenanceRecords`. Failed-attempt history from prior runs is lost. The fix requires reading/merging the existing `EVIDENCE.md` provenance section before overwrite, or storing history separately.
5. **No existing test for historical provenance retention**: The harness does not test that a second successful run preserves first-run failure records. New test cases needed.


- **Exact allowed Markdown wrapper grammar**: The SPEC says "narrow, explicitly defined set" but does not enumerate. Candidate set: `**...**` (bold), `` `...` `` (inline code), leading/trailing whitespace/newlines. Headings (`#`) and arbitrary inline wrapping are explicitly out. **This must be finalized in SPEC before implementation.**
## Uncertainty
- **Whether `Test-ReviewVerdictStructure` needs its own normalization or can rely solely on upstream extraction**: Since it only receives the extracted payload from `Get-CanonicalReviewPayload`, if normalization happens upstream, its own regex can stay strict. But if `Test-ReviewVerdictStructure` is ever called independently in the future, it would silently reject normalized input.
- **Historical provenance merge design**: Two options ??(a) parse existing `EVIDENCE.md` provenance section and merge, or (b) write a separate `ATTEMPT_HISTORY.md` tracked artifact. Option (a) risks fragile Markdown parsing; option (b) adds a new artifact to the promotion transaction. **Not resolvable from current codebase alone.**
- **Whether the reviewer prompt (line 486-497) should be updated to explicitly prohibit Markdown formatting**, or whether parser tolerance alone is sufficient. The SPEC flags this as an open question.

- **No existing harness case for contradictory normalized headers** (e.g., two `**VERDICT: PASS**` blocks). Needs to be added.
## Minimal proposed change surface

1. **`scripts/ai_gate.ps1` ??`Get-CanonicalReviewPayload`** (lines 384-436): Add a narrow Markdown-stripping normalization step before the regex matching. Strip `**`, `` ` ``, and trim whitespace around `VERDICT:` and `BLOCKING_FINDINGS:` tokens. Apply to all matches uniformly to preserve duplicate-header rejection.
3. **`scripts/ai_gate.ps1` ??EVIDENCE.md generation** (lines 746-799): Read existing `EVIDENCE.md` provenance section if present; merge/append historical attempt records into the new provenance section before writing `candidate_EVIDENCE.md`. Add the merge logic to the promotion transaction (line 803-819).
2. **`scripts/ai_gate.ps1` ??`Test-ReviewVerdictStructure`** (lines 438-464): Apply matching normalization or confirm it inherits clean input from upstream. Ensure regex still anchors at `\A`.
4. **`tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1`**: Flip `Gate Markdown verdict remains rejected` case expectation from exit 1 ??exit 0. Add new cases: (a) contradictory normalized headers still rejected, (b) historical provenance survives rerun, (c) non-Markdown prose still rejected.
## Recommendation


**GO WITH SPEC CHANGES**

The parsing change surface is well-localized (two functions in one file, one harness case to flip, plus new negative cases). The provenance retention feature is additive and contained in the evidence-generation/promotion block. However, the SPEC must be finalized before implementation with: (a) an explicit enumeration of accepted Markdown wrapper patterns, (b) a decision on historical provenance representation (merged `EVIDENCE.md` section vs. separate artifact), and (c) resolution of whether `Test-ReviewVerdictStructure` should independently normalize or rely on upstream extraction.
