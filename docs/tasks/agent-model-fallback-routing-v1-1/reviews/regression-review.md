VERDICT: PASS
BLOCKING_FINDINGS: 0

# Regression Review

## Behavior-preservation assessment

All existing single-model behaviors are preserved. When a scalar string is provided for `models.scout` or `models.review` (or via CLI `-Model`/`-ReviewModel`), it is normalized to a one-element candidate list and processed identically to the prior single-invocation path. The inline process lifecycle in Scout is refactored into `Invoke-ScoutProcessAttempt` but retains identical process-start, streaming, timeout/kill-confirmation, and cleanup semantics. Gate continues to reuse `Invoke-BoundedProcess` unchanged. Exit code vocabulary (0/1/2), transactional promotion/rollback, `--standalone` isolation, working directory, closed stdin, and kill confirmation are all preserved. The only behavioral delta is intentional: eligible infrastructure failures now trigger a fallback to the next candidate rather than immediately aborting.

## Blocking findings

None.

## Advisory findings

1. **`Get-CanonicalReviewPayload` regex broadening**: The header-matching regex was refactored ??BOM handling separated, LF normalization added, and a new `\A`-anchored direct-match path added before the existing `(?m)` embedded-match path. This broadens payload detection to handle more output formats. Non-breaking but worth monitoring during pilot for false positives on unusual model output.

2. **Windows-specific `cmd.exe` wrapper for git**: The diff introduces `& cmd.exe /c "chcp 65001 >nul && <nul git ..."` for git status/diff/rev-parse/branch commands. This is a Windows UTF-8 encoding mitigation unrelated to fallback routing. Could be separated into a dedicated commit for cleaner history.

3. **Missing deterministic probe scripts in diff**: SPEC acceptance criterion AC20 calls for deterministic probes covering scalar compatibility, ordered fallback, semantic terminality, exhaustion, per-attempt timeout semantics, and artifact safety. The test seams (`$_ModelCandidatesOverride`, `$_ReviewCandidatesOverride`) are present and correctly plumb candidate lists, providing the foundation for such probes ??but the probes themselves are not included in this diff. This is a test coverage gap, not a code regression.
