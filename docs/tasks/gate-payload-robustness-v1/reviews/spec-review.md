VERDICT: PASS
BLOCKING_FINDINGS: 0

# Spec Review

## Clause coverage

- **§1 Narrow payload normalization**: `Get-CanonicalReviewPayload` now splits on `\n`, matches both raw (`^VERDICT:...$`) and bold (`^**VERDICT:...**$`) line forms, requires both lines to use the same form (raw+raw or bold+bold), and normalizes by stripping one outer `**...**` wrapper. Mixed raw/bold and multiple-match ambiguity checks are in place. Covered.
- **§2 Semantic strictness after normalization**: `Test-ReviewVerdictStructure` receives the already-normalized payload; its `\AVERDICT:` regex is unchanged. Semantic consistency (PASS→0, BLOCK≥1) remains authoritative. Covered.
- **§3 Durable attempt history**: `ATTEMPT_HISTORY.md` is built from `$provenanceRecords` (not raw logs or parsed Markdown), labeled "Historical observability only," append-only, with required fields (timestamp, branch, HEAD, role, attempt index/type, model, elapsed, outcome, selected/fallback). Covered.
- **§4 Transaction-safe promotion**: `ATTEMPT_HISTORY.md` is added to the `$promotionItems` array alongside evidence/reviews; the generic backup-then-copy-rollback loop covers it. Covered.
- **§5 Offline regression harness**: All 11 parser cases and 4 history cases are implemented. The markdown-bold case flipped from exit 1 → exit 0. Covered.
- **Expected change surface**: Only `ai_gate.ps1`, the harness, and task docs are modified. `ai_scout.ps1` is untouched. Covered.
- **Acceptance criteria 1–20**: All addressed by the diff.

## Blocking findings

None.

## Advisory findings

1. **Out-of-scope file added**: `.agents/rules/windows_shell_execution.md` is introduced in the diff but is not listed in the task.json `scope` array and is not referenced in the SPEC. This is not a blocking finding (it does not violate any spec clause), but it widens the change surface beyond the declared scope. It would be cleaner to either add it to the scope list or commit it separately.

2. **`Test-ReviewVerdictStructure` not independently updated**: The SPEC (CONTEXT.md uncertainty section) raised whether `Test-ReviewVerdictStructure` should independently normalize. The implementation relies solely on upstream normalization in `Get-CanonicalReviewPayload`, which is acceptable — the downstream regex stays strict and receives clean input. No blocking concern, but a future refactor adding a second entry point would silently reject bold input.

## Test evidence gaps

- All 15 required harness cases (11 parser + 4 history) are present in the committed harness, including: markdown bold acceptance (red→green), rejection of mixed/duplicate/competing/heading/backtick forms, history creation on first run, append on rerun, rollback preservation, and fallback attempt recording.
- No raw runtime `.runtime` fixture leaks were observed in the diff.
- The harness timeout was increased to 5 seconds for gate invocations, appropriate for the offline harness.

**Confidence**: 0.92 — The diff cleanly implements all five SPEC sections with correct integration into the existing promotion/rollback transaction. The only non-spec-conformant item is the out-of-scope agent rules file.
