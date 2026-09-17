# Spec Review

Gate-accepted verdict: PASS
Blocking findings: 0

# Spec Review

## Clause coverage

Reviewed Final SPEC (§1–§9, AC1–20, non-goals) against `scripts/ai_gate.ps1` (current HEAD, 444 lines), `tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1`, the frozen `.runtime` snapshots, and `git diff origin/main`.

**§1 Reviewer fan-out — conformant.** Both `NEEDS_RUN` slots are launched to `RUNNING` in a first pass before the polling loop starts, so execution overlaps. Each slot owns its own `Process`, `Stopwatch`, async stdout/stderr drains, `Agent_N.log` naming, `candidate_<file>.md` staging path, model-candidate index, and terminal result. Sibling state is never mutated by the other slot (`$slot.*` only). Harness `'Gate parallel reviewers overlap execution'` proves real overlap via start/sibling markers in `fake-reviewer.py`, independent of LLM timing (AC1–2).

**§2 Deterministic fan-in — conformant.** No third judge. `while ($true)` loop exits only when `$runningCount -eq 0` (all required stages terminal) before any aggregate classification (AC6). Exit mapping preserved: any `FAILED` slot → exit 1 before tests/evidence (AC17); `-not $testsPassed` or any `BLOCK` → exit 2; else exit 0. Infrastructure failure remains fail-closed (`INFRASTRUCTURE_FAILED` / unsafe-cleanup / unsafe-kill / catastrophic paths), and fallback only continues on non-trusted, non-catastrophic attempts (no review-shopping).

**§3/§4 Fingerprint & travel — conformant.** `Get-ReviewFingerprint` composes role-specific SHA-256 over: role, SPEC.md content, `status.txt`, `diff.patch`, `base_ref`, `.opencode/agents/<role>.md` contract, generated prompt text, candidate model order, arguments overrides, and (regression only) sorted task scope. Embedded as `<!-- blackfire-gate-fingerprint: {"schema":1,...} -->` in the promoted canonical review, so fresh-clone reuse does not depend on `.runtime/` state (AC19 contract text in `ai_development_workflow.md` matches the emitted format). Not a whole-tree hash; no database created.

**§5 Reuse/invalidation — conformant.** `Test-CanonicalReviewReuse` returns stale (`$null`) for: missing artifact, missing/unparsable `schema=1` fingerprint, role/hash mismatch, missing/invalid `Gate-accepted verdict: PASS|BLOCK` line, or inconsistent `Blocking findings` count. Historical artifacts without fingerprints need no migration (stale-once). Harness proves: immediate second run reuses both (no invocation marker increment), partial resume reuses one and reruns the other, SPEC change / args (contract/config) change / reversed model order / malformed fingerprint / malformed review all rerun (AC8–14).

**§6 Partial resume — conformant.** Reuse is per-role; a `VERIFICATION_UNAVAILABLE` run (one slot failed) exits 1 and does not promote `EVIDENCE.md` or touch `EVIDENCE.md` backups; the surviving sibling's valid review is promoted to canonical and reused on the next identical-input run (harness `'Gate partial resume reuses surviving sibling and reruns failed reviewer'`). `EVIDENCE.md` is only regenerated/promoted when every required reviewer stage resolves.

**§7 ForceRefresh — conformant.** `[switch]$ForceRefresh` sets reuse to `$null` for both reviewers regardless of cache validity, and does nothing else (no implementation/dependency/branch side effects). Harness `'Gate ForceRefresh bypasses cache and reruns both reviewers'`.

**§8 Artifact safety — conformant.** Stale `candidate_*.md` are deleted at invocation start (harness `'Gate clears stale candidate evidence before reviewer phase'`); candidate paths are role-distinct; promotion occurs only after trusted envelope (`cleanup.safe=$true`, `VALID_PASS/BLOCK`, structured present); per-target backup + rollback on `_FailPromotionOnTarget`; failed-slot runs never overwrite the failed reviewer's canonical artifact.

**§9 / AC18 / AC20 — conformant by inspection.** No caching for tests/other stages; existing harness contracts (exit-code probes 0/1/2/7, bounded timeout, scout version rejection, catastrophic-failure fallback-stop, promotion rollback) are preserved. Diff touches only scripts/docs/tests — no production/game runtime change.

## Blocking findings

None.

## Advisory findings

1. **Out-of-scope-worktree-change invalidation is broader than SPEC §4's "unrelated repository changes should not invalidate" phrasing.** The fingerprint hashes `status.txt`/`diff.patch`, which reflect the full worktree diff vs `base_ref` (only `reviews/`, `EVIDENCE.md`, `CONTEXT.md`, `.runtime` excluded). A genuinely unrelated local modification invalidates both reviewers. This is defensible because §4 mandates "implementation/review snapshot identity used by Gate" and the diff snapshot is exactly that identity, and the original CONTEXT test-plan case ("unrelated file outside scope hits cache") was not carried into the Final SPEC's harness. No focused test covers out-of-scope-change cache hits.
2. **Sibling review promotion on partial (exit 1) runs differs from the Scout CONTEXT recommendation (stage-only, canonical untouched), though the Final SPEC §6/§8 permits it** — only `EVIDENCE.md` promotion is forbidden on unavailable verification, and the harness explicitly asserts the promoted-then-reused behavior. Noted as a deliberate design decision; flag for the human final review.
3. **Reuse parser edge case:** `(?m)^Gate-accepted verdict:` / `^Blocking findings:` are line-anchored; a report body that quoted those exact strings at line starts could confuse reuse validation. Low likelihood; non-blocking.
4. **Test matrix gap:** no focused case for the both-`FAILED` cell (both reviewers infrastructure-failed → exit 1, canonical untouched). The code path is identical to the covered single-FAILED path.

## Test evidence gaps

Focused evidence is present for overlap, fan-in matrix (PASS/PASS=0, each BLOCK=2, one infra-fail=1), partial resume, immediate rerun reuse, stable-checkout reuse, model-order/SPEC/contract/config/malformed-fingerprint/malformed-review invalidation, ForceRefresh, stale-candidate cleanup, and rollback. Not run here (read-only review; no execution permitted); the harness must be executed by the user/implementation reviewer to confirm the asserted cases pass on this machine. Both-infrastructure-failed cell and out-of-scope-change cache-hit are untested by design.

<!-- blackfire-gate-fingerprint: {"schema":1,"role":"spec-reviewer","hash":"fb39d5535f184aeaa521774787f50462d44312a40ce7afbf75acdfe3efb3eb26"} -->
