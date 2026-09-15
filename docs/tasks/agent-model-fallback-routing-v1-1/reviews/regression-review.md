VERDICT: PASS
BLOCKING_FINDINGS: 0

# Regression Review

## Behavior-preservation assessment

All existing single-model behaviors are preserved: when a scalar string is provided for `models.scout` or `models.review` (or via CLI `-Model`/`-ReviewModel`), it is normalized to a one-element candidate list and processed identically to the prior single-invocation path. The inline process lifecycle in Scout is refactored into `Invoke-ScoutProcessAttempt` but retains identical process-start, streaming, timeout/kill-confirmation, and cleanup semantics. Gate continues to reuse `Invoke-BoundedProcess` unchanged. Exit code vocabulary (0/1/2), transactional promotion/rollback, `--standalone` isolation, working directory, closed stdin, and kill confirmation are all preserved. The only behavioral delta is intentional: eligible infrastructure failures now trigger a fallback to the next candidate rather than immediately aborting.

## Blocking findings

None.

## Advisory findings

1. **Windows-specific `cmd.exe` wrapper for git**: The diff introduces `& cmd.exe /c "chcp 65001 >nul && <nul git ..."` for git status/diff/rev-parse/branch commands in ai_gate.ps1. This is a Windows-encoding mitigation. It is not a regression risk but is worth noting that this change is unrelated to fallback routing and could be separated into a dedicated commit for cleaner history.

2. **Scout `Invoke-ScoutProcessAttempt` always streams to console**: Unlike Gate's `Invoke-BoundedProcess` which has a `-StreamToConsole` switch, Scout's helper always writes to console. This matches the prior behavior (Scout always streamed) and is not a regression, but diverges architecturally from Gate's pattern.

3. **`Get-CanonicalReviewPayload` regex change**: The header-matching regex was modified (BOM handling separated, LF normalization added, and a new `\A`-anchored direct-match path added before the existing `(?m)` embedded-match path). This broadens payload detection to handle more output formats. It is a non-breaking enhancement but could surface false positives on unusual model output — monitor during pilot.
