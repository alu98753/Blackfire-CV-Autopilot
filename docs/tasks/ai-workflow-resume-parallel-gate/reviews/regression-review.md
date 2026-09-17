# Regression Review

Gate-accepted verdict: PASS
Blocking findings: 0

# Regression Review

## Behavior-preservation assessment

The diff rewrites `scripts/ai_gate.ps1` from a sequential reviewer loop into a dual-slot parallel coordinator with fingerprint-gated reviewer reuse and `-ForceRefresh`. Verified against current repo state:

- **Frozen snapshot contract preserved**: `status.txt`/`diff.patch` are generated once before both reviewer slots launch; both reviewers read the same files. Snapshot generation now excludes `.runtime`, task `reviews/`, `EVIDENCE.md`, `CONTEXT.md` via `:!` pathspecs (correctly passed as separate argv words through the unquoted `cmd /c` string), which is required for cross-run fingerprint stability.
- **Exit semantics preserved**: `0=PASS` / `2=CANDIDATE_BLOCKED` / `1=VERIFICATION_UNAVAILABLE` mapping is retained; fan-in is deterministic boolean aggregation (`$blocked` from `Verdict` of both slots + `$testsPassed`), no third judge.
- **Fail-closed infra handling preserved**: timeout/unsafe-kill/catastrophic/corrupt-envelope paths classify as `INFRASTRUCTURE_FAILED` and terminate the slot; any slot `FAILED` → exit 1 before tests/evidence.
- **Fallback semantics preserved**: per-slot candidate loops with identical classification ladder; unsafe cleanup and unsafe kill still stop fallback.
- **Focused-test behavior unchanged**: same unsafe-target guard, interpreter-not-found exit 1, per-test timeout via `Invoke-BoundedProcess`.
- **Fingerprint inputs are responsibility-aware**: role, `SPEC.md` SHA, status/diff snapshot SHA, `baseRef`, `.opencode/agents/<role>.md` contract SHA (files confirmed present on disk and tracked), prompt text SHA, model list, per-role args override, and `scope` for regression-reviewer. Unrelated repo changes do not invalidate (only `.`-scoped status/diff under excludes are hashed).
- **Reuse validation is strict**: missing/unparsable fingerprint, missing/`UNKNOWN` verdict line, or PASS-with-findings/BLOCK-without-findings all degrade to a fresh run. Historical artifacts without fingerprint comments are treated stale-once.
- **Documented contract change (intentional, test-covered)**: the old "canonical artifacts untouched on unavailable" behavior is replaced by per-slot promotion of a trusted sibling during a partial-infra failure (SPEC §6, AC 16; harness `Gate sibling artifact survives infrastructure failure` and `Gate partial resume...` assert the new canonical+EVIDENCE semantics).
- **Adapter/resilience contracts untouched**: `opencode_structured_review.mjs`, `opencode_contract.ps1`, `node_workflow_contract.ps1` are not modified; `Invoke-BoundedProcess` retains its pipe-drain-before-wait-on-exit logic; slot process handling preserves `taskkill /T /F` tree kill and per-slot stopwatch isolation (no shared `$attempts`/`$unavailable` mutable state between reviewers; candidate paths and log names are role-partitioned).

## Blocking findings

None

## Advisory findings

1. **Phase E prose contraction in `docs/architecture/ai_development_workflow.md`**: the new exit-code list (`0/2/1`) was inserted where the sentence "Candidate changes/evidence are pushed. ChatGPT performs final semantic/architecture review. Integration requires explicit user authorization." previously stood under "### Phase E — Final review, integration, cleanup". The exit-code meanings belong in the Gate section, and the final human-review/integration-authorization contract now relies on the top-of-document workflow diagram surviving. Verify the Phase E section still names ChatGPT final review and user-authorized integration; otherwise the canonical doc loses a workflow-ownership statement.
2. **Infra-failure messaging drift**: gate still prints "Canonical artifacts were left untouched for failed reviewer(s)" on exit 1, but a trusted sibling review is now promoted during partial-infra runs. Wording is now only accurate per-slot; consider aligning the message with the new per-slot promotion contract.
3. **`Ledger/evidence` promotion atomicity changed structurally**: reviews are promoted inline per slot (with per-file backup/rollback) and `EVIDENCE.md` is promoted separately afterwards; the old all-or-nothing three-file transactional promotion is gone. This is spec-conformant and tested via `_FailPromotionOnTarget`, but a simulated `evidence` failure after both reviews promote leaves new reviews plus old evidence (recovered only by the next successful run).
4. **`New-Invocation` override change**: with `_ReviewerExecutableOverride`, override args now always get `--agent` prepended (unless already present), changing fake/real reviewer argv shape vs the old code; harness fixtures were updated to match, but any external override contract relying on the previous bare-argv shape would be affected.
5. **Harness cleanup scope**: `Reset-DisposableGateState` deletes non-(`.py/.cmd/.ps1`) files under the shared helper dir and also removes `.invocations.txt` counters; subsequent counting assertions depend on run ordering inside the single harness process. Isolation between concurrent harness runs is not guaranteed, but each harness invocation starts with a fresh gate fixture.

## Confidence

- Reviewer fan-out/isolation and fingerprint logic: high (code + harness assertions cross-checked).
- `.opencode/agents/*.md` presence confirmed via directory listing (glob tool ignores dot-dirs); contract-hash element is therefore live, not a constant empty string.
- Phase E doc finding is advisory-only: the workflow diagram (untouched by the diff) retains `ChatGPT final semantic review → User-authorized integration`.

<!-- blackfire-gate-fingerprint: {"schema":1,"role":"regression-reviewer","hash":"eb11a06add8ff96d435080409131ec28f8f3759816a062e29c903312ec5115d0"} -->
