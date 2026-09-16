# gate-immutable-review-baseline-contract

Status: Draft

Task start base: `main@a537eac18bd177282105d99c0366cfa338d63ca3`

## Goal

Make Gate review input and fallback/test orchestration reproducible and fail-closed after the reviewer-output transport is now reliable.

The primary problem is that a task review must be about the task's own change set, not whatever a moving ref such as `origin/main` happens to mean when Gate eventually runs.

This task also owns the two Gate-orchestration defects explicitly deferred by `gate-reviewer-output-contract-reliability` because they sit at the same trust boundary:

1. malformed/partial adapter output must never permit fallback unless cleanup safety is mechanically proven;
2. focused-test infrastructure failure must not be misreported as a semantic candidate failure.

## Evidence establishing the problem

The predecessor task reached trusted `VALID_BLOCK` results from both independent reviewers, proving the reviewer-output path itself now works. That live run exposed three downstream Gate concerns:

- a regression reviewer saw unrelated Stage 8 / Dungeon 8 changes because review provenance had been contaminated by a moving `origin/main` comparison baseline;
- `Test-Envelope` currently rejects malformed/partial envelopes before Gate can safely reason about `cleanup.safe`, while exit-0 invalid output can still be treated as fallback-eligible;
- focused-test results currently collapse timeout/process failure and ordinary non-zero test failure into the same `testsPassed = false` path, which can turn infrastructure unavailability into `CANDIDATE_BLOCKED`.

The predecessor closure explicitly deferred these concerns to this task.

## Architecture parent

This task is subordinate to `docs/architecture/ai_development_workflow.md` and preserves the existing authority split:

```text
Reviewer      = semantic authority
Adapter       = attempt qualification authority
Gate          = orchestration authority
ChatGPT/human = final semantic safety net
```

This task must strengthen Gate orchestration without moving reviewer semantics or adapter-owned attempt qualification into Gate.

## Known invariants

1. **Immutable task provenance**
   - A review must be reproducible against a specific commit baseline.
   - Moving remote refs must not change the meaning of an already-created task review.
   - Review evidence must state the exact baseline commit actually used.

2. **No review-shopping**
   - Trusted `VALID_PASS` / `VALID_BLOCK` remains terminal for a reviewer role.
   - This task must not add fallback after trusted semantic authority.

3. **Fallback requires proven cleanup safety**
   - Gate may continue to another candidate only when the previous attempt is pre-authority **and** cleanup is affirmatively proven safe.
   - Missing, malformed, unparseable, or ambiguous cleanup evidence must fail closed to `VERIFICATION_UNAVAILABLE` rather than assume safety.

4. **Authority boundaries remain narrow**
   - Gate may validate envelope/process/routing facts.
   - Gate must not re-run adapter schema/semantic qualification, reinterpret reviewer Markdown, or infer reviewer intent.

5. **Infrastructure failure is not semantic BLOCK**
   - Reviewer/test launch failure, timeout, unconfirmed termination, or missing required execution authority maps to verification unavailability, not candidate semantic failure.
   - A focused test that actually runs to completion and exits non-zero may contribute to `CANDIDATE_BLOCKED`.

6. **Canonical artifact safety**
   - Runs that cannot establish trustworthy verification must preserve previously trusted canonical reviews/evidence.
   - Raw diagnostics remain task-namespaced under `.runtime/`.

7. **Multi-worktree safety**
   - No global mutable current-task state.
   - Task identity remains explicit through `-Task` and `docs/tasks/<task-id>/`.

8. **Existing supported reviewer stack remains fixed**
   - OpenCode `1.18.31` and `@opencode-ai/sdk` `1.18.31` remain unchanged.
   - The 480s reviewer / 510s transport / 540s outer timeout hierarchy remains unchanged unless fresh Scout evidence proves a direct conflict with this task.

## Scope

Expected primary surface:

- `scripts/ai_gate.ps1`
- `tests/test_workflow_scripts.py`
- `tests/workflow_scripts/Invoke-WorkflowScriptHarness.ps1`
- `docs/architecture/ai_development_workflow.md`
- `docs/tasks/README.md` if the durable task-baseline descriptor contract must be clarified
- `docs/tasks/gate-immutable-review-baseline-contract/`

Small helpers/fixtures under the existing workflow-test harness are allowed when needed for deterministic proof.

Changes to `scripts/opencode_structured_review.mjs` are not expected. Any need to modify Adapter behavior must be surfaced during Scout/spec finalization rather than assumed.

## Provisional design direction

### A. Immutable review baseline

The durable contract should make the task's comparison base an exact commit identity rather than a moving interpretation.

Provisional preferred form:

```text
task creation records exact base commit SHA
        ↓
Gate validates/resolves that declared baseline
        ↓
status/diff snapshots record exact base SHA + candidate HEAD
        ↓
reviewer prompt receives exact immutable baseline provenance
        ↓
EVIDENCE records the same provenance
```

The implementation must not silently substitute a newer `origin/main` for the task's declared historical base.

Whether the canonical descriptor should make `base_ref` SHA-only or introduce a separate immutable field is intentionally left open until Scout checks compatibility with existing active task packages and workflow scripts.

### B. Cleanup-safe malformed-envelope routing

Gate should separate two questions that are currently coupled:

```text
Can this output provide trusted reviewer authority?
Can this attempt be proven safely cleaned up so fallback may continue?
```

A malformed envelope may have zero reviewer authority. It still must not be treated as fallback-safe unless cleanup safety is independently machine-provable from the supported boundary.

Provisional rule:

```text
fallback allowed
= pre-authority attempt
+ cleanup.safe is explicitly and validly true
+ process termination boundary is otherwise safe
```

Anything weaker fails closed.

### C. Focused-test orchestration classification

Gate should distinguish at least:

```text
test completed, exit 0      -> PASS
test completed, non-zero    -> candidate test failure
timeout / launch failure /
unsafe termination / missing
interpreter authority       -> verification unavailable
```

The exact internal representation is not prescribed yet; the external `0 / 2 / 1` contract must remain coherent.

## Provisional acceptance criteria

1. A deterministic test proves that advancing or changing a symbolic remote ref after task creation cannot change the Gate diff baseline for the task under review.
2. Gate records the exact immutable baseline SHA and candidate HEAD used to build review snapshots/evidence.
3. Reviewer prompt provenance uses the exact immutable baseline actually used by Gate.
4. Gate fails before review execution with a human-actionable diagnostic if the declared immutable baseline cannot be validated/resolved safely.
5. A malformed/partial/unparseable adapter result cannot trigger candidate fallback unless cleanup safety is affirmatively machine-proven.
6. A parseable pre-authority failure with `cleanup.safe == true` may still fall back according to the existing candidate policy.
7. Trusted `VALID_PASS` / `VALID_BLOCK` remains terminal and anti-review-shopping behavior is unchanged.
8. Focused test timeout/process-launch/unsafe-termination failures produce `VERIFICATION_UNAVAILABLE`, not `CANDIDATE_BLOCKED`.
9. A focused test that actually completes with non-zero exit remains eligible to produce `CANDIDATE_BLOCKED`.
10. Infrastructure-unavailable runs preserve existing canonical `reviews/*` and `EVIDENCE.md`.
11. Deterministic workflow tests cover the new baseline, malformed-envelope cleanup, and focused-test classification contracts without live model calls.
12. No game/runtime behavior changes.

## Non-goals

- changing reviewer semantic contracts;
- changing Adapter grounding/schema/cross-field qualification;
- changing OpenCode/SDK/provider versions;
- changing reviewer step budgets or timeout hierarchy;
- implementing resumable verification checkpoints;
- implementing `reviewer-bounded-context-infrastructure`;
- adding a global task registry/current-task marker;
- redesigning Scout;
- running the full product suite by default;
- changing game/runtime code;
- turning Gate into another semantic reviewer.

## Uncertainty to resolve with Scout

1. **Descriptor shape:** should `base_ref` become commit-SHA-only, or should a new immutable `base_sha`/equivalent coexist with a human-readable source ref for compatibility?
2. **Existing task compatibility:** how many active/current task packages still use `origin/main` or another symbolic ref, and what migration behavior is safe?
3. **Baseline validation:** should Gate require the declared commit to be an ancestor of candidate HEAD, or are legitimate task workflows allowed to use another exact comparison commit?
4. **Malformed-envelope cleanup:** what is the smallest Gate-side validation that can prove cleanup safety without duplicating Adapter qualification?
5. **Focused-test failure taxonomy:** which existing `Invoke-BoundedProcess` outcomes need explicit infrastructure classification, and how should interpreter-not-found be represented in evidence?
6. **Snapshot provenance:** whether current `status.txt` / `diff.patch` plus exact SHA metadata are sufficient, or a small versioned snapshot manifest is warranted.

## Scout request

Scout should localize only the evidence needed to finalize these uncertainties:

- current `base_ref` usage and task-package patterns;
- Gate snapshot creation and reviewer prompt provenance;
- envelope validation/fallback control flow;
- focused-test process/result classification;
- deterministic harness seams already available for reproducing the three defects;
- architecture documentation that must be updated if the descriptor/baseline contract changes.

Scout is not asked to design or implement the fix.
