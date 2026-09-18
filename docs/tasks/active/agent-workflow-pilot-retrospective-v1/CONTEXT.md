Now let me inspect the key scoped files to understand the current state of the evidence and contracts:
Now let me inspect the key scripts and check for pilot artifacts from `intent-routing-observability`:
Now let me check the existing pilot task's evidence and reviews, plus look for tests:
## Maximum Steps Reached

I've reached the tool invocation limit. I have gathered sufficient evidence from 7 files to produce the scout report. Here it is:

---

# Scout Context


1. **`docs/tasks/agent-workflow-pilot-retrospective-v1/SPEC.md`** ??The Draft SPEC for the retrospective task itself. Defines scope, invariants, non-goals, acceptance criteria, and expected outputs (RETROSPECTIVE.md + BACKLOG.md update). Authoritative for desired behavior.

2. **`docs/tasks/agent-workflow-pilot-retrospective-v1/task.json`** ??Task descriptor. Scope covers the task package, BACKLOG.md, architecture workflow doc, ai_scout.ps1, ai_gate.ps1, and tests/.

## Relevant files and symbols
3. **`scripts/ai_gate.ps1`** (889 lines) ??The Gate orchestration script. Key symbols: `Get-CanonicalReviewPayload` (line 384), `Test-ReviewVerdictStructure` (line 438), candidate loop (line 480), promotion logic (line 803), `Resolve-ReviewCandidates` (line 50). This is the central artifact for the Markdown-bold failure mode and infrastructure-failure sequencing analysis.

4. **`scripts/ai_scout.ps1`** (412 lines) ??Scout orchestration. `Resolve-NormalModelList` (line 40), `Invoke-ScoutProcessAttempt` (line 113). Relevant for model routing/fallback analysis.
5. **`docs/tasks/intent-routing-observability/EVIDENCE.md`** ??The pilot's successful Gate evidence. Records BigPickle spec-review 80.2s PASS, regression-review 119.1s PASS, 4 focused tests all PASS. **Does NOT record the earlier failed Mimo attempt** ??it was overwritten by the successful run.


6. **`docs/tasks/intent-routing-observability/reviews/degraded-gemini-review.md`** ??Degraded review artifact. Documents the Mimo bold-markdown incident explicitly: `**VERDICT: PASS**` failed regex `\AVERDICT:\s*(PASS|BLOCK)` ??`PAYLOAD_EXTRACTION_FAILED` ??`MANUAL_DEGRADED_REVIEW_REQUIRED`. Contains the full failed reviewer output inline.

7. **`docs/tasks/BACKLOG.md`** (337 lines) ??Canonical roadmap. `intent-routing-observability` is "active"; retrospective is "planned next" (#4). Contains deferred candidates (schema validation, commit agent) that the retrospective must evaluate for promotion.

## Current control flow

**This task produces documentation, not code.** There is no implementation control flow to trace. The task's output path is:

1. Scout (this pass) ??produces CONTEXT.md
2. ChatGPT + user finalize SPEC.md to Status: Final
3. Writer produces `docs/tasks/agent-workflow-pilot-retrospective-v1/RETROSPECTIVE.md`
4. After approval, updates `docs/tasks/BACKLOG.md`

The retrospective itself analyzes the control flow of `ai_gate.ps1` and `ai_scout.ps1` as evidence subjects. Key Gate flow: candidate loop iterates normal models ??structured JSON extraction ??`Get-CanonicalReviewPayload` (strict regex at line 401: `\AVERDICT:\s*(PASS|BLOCK)\nBLOCKING_FINDINGS:\s*(\d+)`) ??`Test-ReviewVerdictStructure` (line 448: same `\A` anchor). If all candidates fail infrastructurally, Gate exits 1 and emits `MANUAL_DEGRADED_REVIEW_REQUIRED`.

**Critical regex detail**: `Get-CanonicalReviewPayload` has a two-tier extraction ??direct match (line 401, prefers `\A` start) and embedded fallback (line 411, finds VERDICT anywhere). However, `Test-ReviewVerdictStructure` (line 448) then re-validates with `\A` anchor on the extracted payload. This means the embedded fallback extracts the payload starting at VERDICT, but bold-wrapped output like `**VERDICT: PASS**` would still fail because `**` precedes `VERDICT` even after substring extraction. This is the exact failure mechanism.
## Existing safety mechanisms

- **Task descriptor validation**: Both scripts validate task.json existence, id-match, and models field presence (gate line 41, scout line 36). No schema-level validation exists beyond id-matching.
- **Bounded process execution**: `Invoke-BoundedProcess` (gate line 124) enforces 480s default timeout per reviewer with kill-confirmation.
- **Atomic promotion with rollback**: Gate lines 821-879 backup canonical artifacts before promotion and roll back on failure.

- **Infrastructure-failure gating**: Exit code 1 (INFRASTRUCTURE_BLOCKED) preserves canonical artifacts untouched; exit code 2 (CANDIDATE_BLOCKED) promotes blocking evidence.
- **Degraded review labeling contract**: architecture workflow doc (line 311) mandates `DEGRADED`, `LOW_EVIDENCE`, `NOT_INDEPENDENT` labels.
- **No test coverage**: Zero test files exist for `ai_gate.ps1` or `ai_scout.ps1` in the `tests/` directory. The gate script has internal test seams (`_ReviewerExecutableOverride`, etc.) but no test harness files were found.

## Existing tests

No test files matching `*gate*` or `*scout*` exist under `tests/`. The pilot's focused tests were product tests (`test_behavior_*.py`), not workflow-script tests. The gate's internal test seams (parameter overrides at lines 14-22) suggest tests were designed for but not yet created or are stored elsewhere not yet located within budget.

## Regression and architecture risks

- **Evidence overwrite**: The successful Gate run overwrites `EVIDENCE.md` and `reviews/*` from the failed attempt. The first-failed Mimo attempt's provenance is only preserved in `.runtime/` (gitignored) and in the degraded-gemini-review's prose. The retrospective must reconstruct the failed attempt from secondary evidence.
- **Scope creep risk**: The retrospective task must not implement fixes. BACKLOG.md already contains detailed proposals (semantic-commit-agent v0/v1/v2) that could be mistaken for implementation authorization.
- **No script tests**: Any workflow improvement task (payload normalization, stage resilience) currently lacks regression protection. This is a gap the retrospective should note.
- **Single-pilot limitation**: All evidence comes from one production task. Model timeout/calibration recommendations should be marked MEASURE MORE, not policy changes.

## Uncertainty

1. **First-failed Gate attempt logs**: The `.runtime/ai_gate/intent-routing-observability/` directory (gitignored) likely contains `candidate_spec-reviewer_attempt_1.log` with the raw Mimo output. Cannot confirm from tracked files whether this log was committed or is purely local.
3. **Initial task.json omission details**: The SPEC mentions the initial task.json omitted `models` configuration. Whether this was `intent-routing-observability`'s original task.json or a separate incident is not fully resolved from files reached.
4. **Commit history timestamps**: Git commit timestamps could provide lifecycle timing for Scout, writer, handoff, and rerun stages, but were not inspected within budget. This is a key evidence source for the retrospective timeline reconstruction.
5. **`.runtime` remote unavailability**: Whether `.runtime/` content is intentionally local-only and whether any CI or remote artifact preserved the failed Gate attempt is unknown.
2. **Scout timing for the pilot**: No Scout elapsed time or attempt provenance for the `intent-routing-observability` Scout pass is recorded in any tracked artifact. Must be treated as missing evidence.

6. **Backlog update timing**: The SPEC requires BACKLOG.md update only after Final SPEC and approved retrospective. Current BACKLOG.md item #3 still shows `intent-routing-observability` as "active" ??whether it should transition to "completed" before or after the retrospective is a governance question.
This task produces documentation only:
- **Create**: `docs/tasks/agent-workflow-pilot-retrospective-v1/RETROSPECTIVE.md`
- **Update**: `docs/tasks/BACKLOG.md` (lifecycle status + roadmap reprioritization)

- **No script, test, or production code changes**

## Recommendation

**GO WITH SPEC CHANGES**

The Draft SPEC is well-structured and comprehensive. However, two clarifications are needed:
## Minimal proposed change surface

1. **Evidence source for failed Gate attempt**: The SPEC assumes the first-failed Mimo attempt can be reconstructed, but `EVIDENCE.md` only records the successful run. The SPEC should explicitly authorize reconstruction from `.runtime/` logs (if committed), `degraded-gemini-review.md` inline quotes, and commit history ??or explicitly declare that attempt as "reconstructed from secondary evidence" with appropriate confidence labels.

2. **Missing Scout evidence**: The SPEC's acceptance criteria (item 5) require Scout/writer timing to be "recorded as missing evidence rather than invented," but no current artifact provides this. The SPEC should explicitly instruct the retrospective author to check git commit timestamps as a proxy for stage timing where direct measurements are absent.

The task scope, invariants, non-goals, and acceptance criteria are otherwise clear, well-bounded, and appropriate for a documentation-only retrospective. No implementation risk exists; the primary risk is evidence completeness.
