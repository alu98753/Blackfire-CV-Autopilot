VERDICT: PASS
BLOCKING_FINDINGS: 0

# Spec Review

## Clause coverage

The candidate diff addresses all 14 required behavior sections and 26 acceptance criteria. Material coverage:

- **禮1 Metadata contract**: `Resolve-NormalModelList` / `Resolve-ReviewCandidates` ??scalar/array normalization, blank rejection, CLI override priority. ?n- **禮2 Degraded review**: Gate never invokes Gemini; exits 1 with `MANUAL_DEGRADED_REVIEW_REQUIRED`; outer workflow produces `degraded-gemini-review.md` with required labels. ?n- **禮3 CLI override**: `-Model`/`-ReviewModel` ??single-element candidate list. ?n- **禮4 Fallback eligibility**: All 7 infrastructure failure classifications trigger `continue`; valid PASS/BLOCK are terminal. ?n- **禮5 Gate routing boundary**: Candidate iteration inside per-reviewer foreach; BLOCK is terminal per reviewer; exhaustion exits 1. ?n- **禮6 Timeout per attempt**: Full `ReviewTimeoutSeconds` per candidate; no shared remainder. ?n- **禮7 Scout routing**: Fallback loop with structural `# Scout Context` check; valid report promotes exactly once; all-fail throws. ?n- **禮8 Qualification**: `task.json` arrays reflect actual qualification (BigPickle qualified for Scout only). ?n- **禮10 Exit codes**: 0/1/2 vocabulary preserved; infrastructure exhaustion ??exit 1. ?n- **禮11 Provenance**: Compact records in `EVIDENCE.md` with role/type/index/model/elapsed/outcome/selected. ?n- **禮13 Architecture docs**: Section 10 comprehensively updated with all required semantics. ?n- **禮14 Retrospective**: BACKLOG.md updated with all 9 calibration points under `agent-workflow-pilot-retrospective-v1`. ?n
## Blocking findings

None.

## Advisory findings

1. **Windows-specific git encoding workaround**: `ai_gate.ps1` wraps git commands with `cmd.exe /c "chcp 65001 >nul && <nul git ..."`. This is a platform-specific UTF-8 mitigation unrelated to fallback routing. Not a spec concern but worth noting for cross-platform portability.

2. **`Get-CanonicalReviewPayload` regex broadening**: A new `\A`-anchored direct-match path and LF normalization were added before the existing `(?m)` embedded-match path. This is a non-breaking enhancement that improves robustness but could theoretically surface false positives on unusual model output ??monitor during pilot.

3. **Test evidence gap**: The diff does not include deterministic probe scripts for fallback routing (AC20 requires probes for scalar compatibility, ordered fallback, semantic terminality, exhaustion, unconfirmed termination, and artifact safety). The spec reviewer noted that test seams (`$_ModelCandidatesOverride`, `$_ReviewCandidatesOverride`) are correctly plumbable, providing the foundation for verification scripts to be written separately.

## Test evidence gaps

Present: Test seams (`$_ModelCandidatesOverride`, `$_ReviewCandidatesOverride`, `$_ExecutableOverride`) are correctly added and plumb candidate lists through the routing logic.

Missing: Deterministic probe scripts exercising the full verification matrix (AC20: scalar normalization, ordered fallback, semantic terminality, normal-chain exhaustion, per-attempt timeout semantics, artifact safety, unconfirmed termination). These were flagged by both the spec reviewer and regression reviewer in the diff's review artifacts as absent.
