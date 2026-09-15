# Agent Workflow Pilot Retrospective: `intent-routing-observability`

Status: Completed
Author: Antigravity Gemini (Implementation Agent)
Scope: `docs/tasks/agent-workflow-pilot-retrospective-v1/`
Evidence Baseline: `intent-routing-observability` production pilot

---

## 1. Executive Summary

The `intent-routing-observability` task served as the first formal production pilot through the hardened Blackfire AI development workflow:
```text
Task Specification -> OpenCode Scout -> Human/ChatGPT Final SPEC -> Gemini Writer -> Focused Tests -> OpenCode Gate Review -> ChatGPT Semantic Review -> User Merge
```

The product change itself succeeded completely with zero regressions:
- A small immutable structured routing diagnostic contract (`RoutingDiagnostic`, `RoutingInFlightDiagnostic`) was introduced in [`states/navigation_routing.py`](../../../states/navigation_routing.py).
- `resolve_navigation_context()` ordering and pre-observation action snapshots were preserved.
- Free-form runtime logging was cleanly migrated to structured diagnostic sourcing.
- 32 focused tests passed in 0.144s.

However, the pilot revealed friction across the workflow lifecycle:
1. **Task Creation Defect**: The initial `task.json` omitted model configuration, failing Scout before work could begin.
2. **Gate Parser Brittleness**: OpenCode reviewer (`opencode/mimo-v2.5-free`) reached an independent semantic PASS (blocking=0), but wrapped headers in Markdown bold (`**VERDICT: PASS**`), causing regex extraction failure (`PAYLOAD_EXTRACTION_FAILED`) and triggering an infrastructure failure.
3. **Stage Resilience Gap**: Infrastructure failure during spec review prevented regression review from executing.
4. **Evidence Overwrite**: Canonical Gate promotion overwrites `EVIDENCE.md`, erasing failed attempt traces from tracked git history.
5. **No Workflow Script Tests**: Neither `ai_gate.ps1` nor `ai_scout.ps1` has automated regression tests under `tests/`.

---

## 2. Pilot Lifecycle Timeline

The following timeline reconstructs the lifecycle of `intent-routing-observability`. Git commit timestamps provide coarse temporal ordering; direct stopwatch measurements are provided where available.

| Stage | Commit / Event | Timestamp (Coarse Proxy) | Elapsed / Duration | Actor | Outcome / Status | Confidence |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Task Creation** | `87a3298`, `2869a4a` | 2026-09-15 11:13:31 | Coarse | User / ChatGPT | Draft SPEC and initial `task.json` created. | HIGH |
| **2. Initial Scout Failure** | Local execution | ~11:15 - 11:19 | UNKNOWN (unrecorded) | OpenCode Scout | Failed immediately: `task.json` missing `models.scout` field. | HIGH |
| **3. Descriptor Repair** | `e078f8b` | 2026-09-15 11:20:04 | Coarse | User | Added `models.scout` and `models.review` to `task.json`. | HIGH |
| **4. Scout Re-run** | `49291a0` | 2026-09-15 11:25:34 | UNKNOWN (unrecorded) | OpenCode Scout | Generated `CONTEXT.md` mapping architecture boundaries. | MEDIUM |
| **5. Final SPEC & Tests** | `0aebca2`, `fd88356` | 2026-09-15 11:26:28 | Coarse | ChatGPT / User | SPEC promoted to `Status: Final`; focused tests specified. | HIGH |
| **6. Implementation** | Working tree edits | ~11:26 - 11:33 | ~7m (proxy) | Gemini Writer | Implemented diagnostics, updated executor logging, added focused tests in `test_behavior_routing_observability.py`. | HIGH |
| **7. Focused Tests** | Local CLI | 2026-09-15 11:33:25 | 0.144s (measured) | Gemini Writer | 32 tests passed cleanly (unit/behavioral). | HIGH |
| **8. Gate Attempt 1 (Mimo)** | Local `.runtime/...` log (ephemeral) | 2026-09-15 11:36:16 | ~158.6s (local uncommitted log) | OpenCode Mimo | Child process completed normally (exit code 0), but `**VERDICT: PASS**` header caused Gate payload extraction to fail, terminating Gate with Exit 1 (`INFRASTRUCTURE_BLOCKED`). | LOW |
| **9. Degraded Review** | `8975206` | 2026-09-15 11:37:50 | Coarse | Gemini Writer | Created `degraded-gemini-review.md` labeled `NOT_INDEPENDENT`. | HIGH |
| **10. Re-sync & Model Select** | `6c17c0d` | 2026-09-15 11:44:58 | Coarse | User | Merged remote `main`; selected `opencode/big-pickle` for rerun. | HIGH |
| **11. Gate Attempt 2 (BigPickle)** | `74bbbae` | 2026-09-15 11:49:52 | Spec: 80.2s, Regr: 119.1s | OpenCode BigPickle | Spec review: PASS (blocking=0); Regression review: PASS (blocking=0). Exit 0. | HIGH |
| **12. Final Merge** | `0984f5a` | 2026-09-15 11:53:20 | Coarse | User / ChatGPT | Merged into `origin/main` via merge commit. | HIGH |

---

## 3. Evidence Table

| Item | Quantitative Metric / Artifact Evidence | Data Source | Confidence |
| :--- | :--- | :--- | :--- |
| **Task Descriptor Omission** | `task.json` initially lacked `models` block; fixed in `e078f8b`. | Commit `e078f8b`, `SPEC.md` § Authoritative pilot basis | HIGH |
| **Mimo Gate Duration** | Spec-reviewer attempt 1 ran for ~158.6s before child process exited 0; Gate script exited 1. | Local uncommitted task log `task-819.log`, `.runtime/...` log | LOW |
| **Mimo Semantic Output** | Found 0 blocking findings, concluding with `**VERDICT: PASS**`. | Quoted in tracked `degraded-gemini-review.md` / `spec-reviewer_attempt_1.log` | MEDIUM |
| **Mimo Extraction Failure** | Regex `\AVERDICT:\s*(PASS|BLOCK)` failed due to `**` prefix. | `scripts/ai_gate.ps1` (lines 401, 411, 448), local task log | HIGH |
| **Stage Halt** | Regression reviewer did not run because spec reviewer failed extraction. | Local task log, `ai_gate.ps1` line 480 candidate loop | HIGH |
| **BigPickle Spec Review** | Ran for 80.2s; produced valid canonical header `VERDICT: PASS` (blocking=0). | Canonical `EVIDENCE.md`, `reviews/spec-review.md` | HIGH |
| **BigPickle Regr Review** | Ran for 119.1s; produced valid canonical header `VERDICT: PASS` (blocking=0). | Canonical `EVIDENCE.md`, `reviews/regression-review.md` | HIGH |
| **Focused Test Suite** | 4 files, 32 unit/behavior tests; execution time 0.144s. | CLI output, `EVIDENCE.md` | HIGH |
| **Evidence Overwrite** | Rerun replaced `EVIDENCE.md` and created `reviews/spec-review.md`, wiping failed Attempt 1 traces. | Git status, `EVIDENCE.md` diff | HIGH |
| **Script Test Coverage** | Zero test files for `ai_gate.ps1` or `ai_scout.ps1` found under `tests/`. | `tests/` directory audit, `CONTEXT.md` | HIGH |
| **Scout Timing Data** | Duration of Scout runs on `intent-routing-observability` not recorded. | Missing from `CONTEXT.md` / `EVIDENCE.md` | UNKNOWN |
| **Human Interventions** | 6 manual human touches (task repair, branch sync, rerun, commit message, review handoff, merge). | Shell command logs, Git history | HIGH |

---

## 4. Root Cause vs. Symptom Analysis

### 4.1 Gate Payload Extraction Failure
- **Symptom**: `ai_gate.ps1` reported `PAYLOAD_EXTRACTION_FAILED: No valid VERDICT/BLOCKING_FINDINGS header found in final assistant message.` and exited with code 1 (`INFRASTRUCTURE_BLOCKED`).
- **Mechanism**:
  - `ai_gate.ps1` prompt instructs: `The final response MUST begin with: VERDICT: PASS|BLOCK\nBLOCKING_FINDINGS: <count>`.
  - OpenCode model (`opencode/mimo-v2.5-free`) wrote a detailed analytical review and placed the verdict at the end:
    ```markdown
    ---\n\n**VERDICT: PASS**\n**BLOCKING_FINDINGS: 0**
    ```
  - `Get-CanonicalReviewPayload` tried direct match (`\AVERDICT:`) which failed. It then fell back to embedded match (`(?m)^VERDICT:`), which failed because `**` preceded `VERDICT` on that line, meaning the regex never matched and extraction returned empty.
- **Root Cause**: **Contract/parser brittleness**. The parser strictly assumed literal raw text without markdown header tolerance, while the prompt did not forbid markdown styling (bolding), creating a fragility trap for models that format conclusions in markdown.
- **Classification**: `contract/parser brittleness`.

### 4.2 Gate Stage Halting on Reviewer Failure
- **Symptom**: Regression reviewer never ran during Attempt 1, delaying feedback on regression safety.
- **Mechanism**: In `scripts/ai_gate.ps1`, reviewer roles are evaluated in strict sequence: `spec-reviewer` -> `regression-reviewer`. When all normal candidates for `spec-reviewer` fail, the script terminates immediately with `exit 1`.
- **Root Cause**: Strict fail-fast pipeline design without role independence. While a semantic BLOCK legitimately halts downstream stages, an infrastructure extraction failure in an earlier role prevents gathering independent verification evidence from subsequent roles.
- **Classification**: `infrastructure/process failure`.

### 4.3 Task Descriptor Omission
- **Symptom**: Initial `ai_scout.ps1` invocation crashed before analyzing codebase.
- **Mechanism**: `task.json` was authored by human/ChatGPT without a `"models"` block.
- **Root Cause**: Lack of automated schema validation or linting at task authoring time. Human error occurred because `task.json` structure was manually created without preflight syntax or schema verification.
- **Classification**: `avoidable mechanical human friction` + missing guardrail.

### 4.4 Canonical Evidence Overwrite
- **Symptom**: Historical record of Mimo Attempt 1 was erased from `EVIDENCE.md` upon successful Gate completion.
- **Mechanism**: `ai_gate.ps1` generates `EVIDENCE.md` from scratch on successful completion, writing only the selected candidate runs and omitting previous failed attempts from canonical tracking.
- **Root Cause**: Lack of durable attempt history aggregation in the Gate evidence generator.
- **Classification**: `evidence/observability gap`.

---

## 5. Human Intervention Map

During the pilot, human interaction was required at multiple points. These are divided into **Necessary Semantic Control** (required for architecture integrity) and **Avoidable Mechanical Friction** (candidates for automation):

| Intervention Point | Description | Classification | Automation / Guardrail Opportunity |
| :--- | :--- | :--- | :--- |
| **Task Definition** | Authoring task objective, requirements, and invariants in `SPEC.md`. | **Necessary Semantic Control** | None (ChatGPT + User domain). |
| **Model Config Omission** | Authoring `task.json` without `models` block; debugging crash; manual JSON edit. | **Avoidable Mechanical Friction** | Task descriptor schema validation / scaffold helper. |
| **SPEC Finalization** | Reviewing Scout output and finalizing `SPEC.md` to `Status: Final`. | **Necessary Semantic Control** | None (authoritative contract boundary). |
| **Gate Failure Triage** | Reading PowerShell console warning, locating `.runtime/` log, diagnosing bold header. | **Avoidable Mechanical Friction** | Payload normalization / clear extraction diagnostics. |
| **Branch Synchronization** | Manually merging `origin/main` into task branch before rerunning Gate. | **Avoidable Mechanical Friction** | Workflow-level branch sync preflight check. |
| **Manual Rerun Trigger** | Re-executing Gate with `-ReviewModel opencode/big-pickle` override. | **Avoidable Mechanical Friction** | Fallback routing (already qualified) / retry automation. |
| **Commit Message Authoring** | Formatting conventional commit messages with multiline detail. | **Convenience / QoL Friction** | Deterministic commit helper (`ai_commit.ps1`). |
| **Final Merge Authorization** | Verifying evidence and merging task branch to `main`. | **Necessary Semantic Control** | None (User/ChatGPT sole merge authority). |

---

## 6. KEEP / CHANGE / MEASURE MORE / DEFER Decisions

### 6.1 Gate Payload Robustness
- **Decision**: **CHANGE** (Schedule narrow follow-up task).
- **Rationale**: HIGH confidence. Mimo produced an accurate, high-quality review with 0 blocking findings, but failed solely due to Markdown bold syntax (`**VERDICT: PASS**`). Normalizing markdown-wrapped headers (`**`, `#`, leading/trailing whitespace) eliminates a proven failure mode without weakening semantic rigor.

### 6.2 Gate Stage Sequencing Resilience
- **Decision**: **DEFER** (Keep current fail-fast behavior for now).
- **Rationale**: MEDIUM confidence. While running the regression reviewer despite spec-reviewer infrastructure failure could provide additional diagnostic data, the primary problem in the pilot was payload extraction. Fixing payload robustness addresses the root cause of the early exit. Changing Gate sequencing adds pipeline complexity and potential artifact promotion ambiguity.

### 6.3 Task Descriptor / Schema Validation
- **Decision**: **CHANGE** (Schedule narrow linting/validation task).
- **Rationale**: HIGH confidence. A simple JSON schema validator or preflight check in `ai_scout.ps1` / `ai_gate.ps1` would have prevented the initial Scout failure immediately with an actionable error message (`task.json missing required 'models' object`).

### 6.4 Model Routing, Timeout, and Step Budgets
- **Decision**: **MEASURE MORE**.
- **Rationale**: LOW to MEDIUM confidence. BigPickle succeeded in ~80.2s and ~119.1s (HIGH confidence, canonical `EVIDENCE.md`), while Mimo ran for ~158.6s (LOW confidence, local ephemeral log). However, this constitutes exactly one data point. The current 480s timeout policy and model fallback ordering must not be prematurely optimized based on a single pilot.

### 6.5 Workflow Evidence Retention
- **Decision**: **CHANGE** (Incorporate attempt history preservation into follow-up).
- **Rationale**: HIGH confidence. Overwriting `EVIDENCE.md` destroyed the primary provenance record of Attempt 1, forcing this retrospective to rely on secondary text quotes. Preserving previous attempt summaries in `EVIDENCE.md` ensures full auditability.

### 6.6 Workflow-Script Regression Testing
- **Decision**: **CHANGE** (Prerequisite for future script changes).
- **Rationale**: HIGH confidence. `ai_gate.ps1` is 890 lines of complex process, regex, and state logic with zero automated regression tests in `tests/`. Modifying extraction regexes without a test harness risks silent regressions. A dedicated unit/integration test harness for PowerShell workflow scripts is a required prerequisite.

### 6.7 Semantic Commit Agent
- **Decision**: **KEEP DEFERRED** (Prioritize reliability over convenience).
- **Rationale**: HIGH confidence. Commit authoring was a minor convenience friction during the pilot; it never blocked task completion or caused infrastructure failure. Core reliability and parser robustness take strict precedence over commit automation.

### 6.8 Workflow Interruptibility
- **Decision**: **DEFER** (Maintain v2 positioning).
- **Rationale**: MEDIUM confidence. Interruption did not surface as a blocker during this pilot. Process bounding and kill confirmation worked as designed.

---

## 7. Prioritized Follow-Up Tasks

### Task 1: `workflow-script-testing-harness` (P0 - Prerequisite)
- **Problem Statement**: `scripts/ai_gate.ps1` and `scripts/ai_scout.ps1` lack automated test coverage. Any edits to regexes, fallback logic, or process handling carry high regression risk.
- **Responsibility Boundary**: Create a lightweight, isolated PowerShell test suite (e.g. `tests/test_workflow_scripts.ps1` or Pester-compatible) that exercises `Get-CanonicalReviewPayload`, `Test-ReviewVerdictStructure`, `Resolve-ReviewCandidates`, and timeout/kill seams without invoking live AI models.
- **Evidence & Confidence**: HIGH (Scout confirmed 0 test files for scripts).
- **Separation Justification**: Testing infrastructure must exist before modifying script production logic.

### Task 2: `gate-payload-robustness-v1` (P1 - Core Reliability)
- **Problem Statement**: Strict regex parsing rejects semantically valid reviews that use Markdown formatting (bold, headings, backticks) on the `VERDICT` header.
- **Responsibility Boundary**: Update `Get-CanonicalReviewPayload` and `Test-ReviewVerdictStructure` in `scripts/ai_gate.ps1` to tolerate common markdown wrapping (e.g. `**VERDICT: PASS**`, `# VERDICT: PASS`) while preserving strict semantic rejection of ambiguous or multiple verdicts. Preserve attempt history in `EVIDENCE.md`.
- **Evidence & Confidence**: HIGH for mechanism failure (tracked `degraded-gemini-review.md`), LOW for exact duration (~158.6s from local log).
- **Separation Justification**: Strictly targets the parser and evidence persistence; does not alter model routing, timeouts, or task schemas.

### Task 3: `task-descriptor-schema-linting` (P2 - Developer Experience & Safety)
- **Problem Statement**: Missing fields in `task.json` (such as `models`) cause scripts to fail with unhelpful stack traces during execution.
- **Responsibility Boundary**: Implement a preflight validation function in `scripts/ai_scout.ps1` and `scripts/ai_gate.ps1` (or a dedicated schema validator) that asserts required fields (`id`, `base_ref`, `scope`, `models.scout`, `models.review`) before launching any child processes.
- **Evidence & Confidence**: HIGH (Pilot crashed at inception due to missing `models`).
- **Separation Justification**: Standalone validation layer; does not touch parser or execution runtime.

---

## 8. Explicit Requirements for Future Tasks

### 8.1 Semantic Commit Agent: Explicit Decision
- **Decision**: **KEEP DEFERRED**.
- **Evidence**: In the pilot, manual commit messages took negligible time (~1 minute) compared to diagnosing the Gate parser failure and performing branch re-sync. Building an LLM-based commit summarizer addresses quality-of-life convenience, not workflow throughput or reliability. It remains deferred until P0/P1 reliability tasks are completed.

### 8.2 Workflow Interruptibility: Concrete Requirements
For future implementation of `workflow-interruptibility-v2`:
1. **Cancellation Grace Period**: When a user cancels a running Scout or Gate operation, `ai_gate.ps1` must enforce immediate process kill confirmation for child OpenCode processes before exiting.
2. **Artifact Invalidation**: If an in-flight Gate attempt is interrupted mid-execution, `.runtime/` candidate files must be cleanly deleted or marked `INTERRUPTED`; canonical `reviews/` and `EVIDENCE.md` must not be partially promoted.
3. **Resumption Boundary**: Resuming an interrupted workflow must always start from the boundary of the last uncompleted role, rather than resuming halfway through a process invocation.

---

## 9. Recommended Roadmap Ordering

```text
Current Pilot Closeout (agent-workflow-pilot-retrospective-v1)
  │
  ▼
[P0] workflow-script-testing-harness
  │  (Build automated tests for ai_gate.ps1 & ai_scout.ps1)
  ▼
[P1] gate-payload-robustness-v1
  │  (Markdown-tolerant header parsing & durable evidence retention)
  ▼
[P2] task-descriptor-schema-linting
  │  (Preflight schema & field validation for task.json)
  ▼
[Measure More] Production Pilot 2 (Second real feature task)
  │  (Collect broader timing, fallback, and step-budget data)
  ▼
[Deferred] semantic-commit-agent-v1 & workflow-interruptibility-v2
```
