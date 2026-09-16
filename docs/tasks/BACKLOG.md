# Development Backlog

This file is the canonical entry point for new ideas, future work, bugs that still need investigation, and tasks that are not yet ready for a full `SPEC.md`.

Keep entries concise enough to scan, but preserve architecture intent and dependency order. When an item becomes active development work, promote it into:

```text
docs/tasks/<task-id>/SPEC.md
docs/tasks/<task-id>/task.json
```

Do not duplicate a promoted task here. Replace the backlog item with a link to the active task package or mark its lifecycle state clearly until closeout.

## Backlog

Existing backlog material under `docs/todos/` predates this workflow and remains legacy until touched. New backlog items must be added here, not to `docs/todos/future_work.md` or new files under `docs/todos/`.

### 🔴 Highest priority — paused

#### `gate-immutable-review-baseline-contract`

Status: **Draft task package exists; paused by explicit user decision before Scout / implementation.**

Priority: **P0 / highest current workflow priority when resumed.**

Why it matters:
- make Gate review diffs reproducible against an immutable task baseline instead of a moving `origin/main`;
- prevent unrelated later `main` changes from contaminating reviewer scope;
- make malformed/partial reviewer-attempt fallback fail closed unless cleanup safety is mechanically proven;
- distinguish focused-test infrastructure failure from a real completed test failure.

Existing remote task branch:

```text
task-gate-immutable-review-baseline-contract
```

Resume point:

```text
remote -> local handoff
-> OpenCode Scout
-> ChatGPT + user finalize Draft SPEC
-> implementation
```

Do **not** recreate the task or begin implementation while it remains paused.

# AI workflow roadmap

## North-star architecture

The workflow should reduce human copy/paste and repetitive orchestration without blurring authority boundaries.

```text
Human / ChatGPT
  -> lightweight repository survey
  -> Draft SPEC + task descriptor
  -> OpenCode Scout (read-only evidence)
  -> ChatGPT + user finalize SPEC
  -> Gemini/Antigravity implementation writer
  -> focused tests
  -> OpenCode Gate reviewers (read-only independent evidence)
  -> ChatGPT final semantic / architecture review
  -> user-authorized integration
```

Long-term automation may orchestrate these steps, but orchestration must never silently inherit specification, architecture, implementation, or merge authority.

## Resource / responsibility principles

1. **Contract authority stays explicit**
   - ChatGPT + user own task intent, architecture trade-offs, invariants, scope, and Final SPEC.
   - Scout is an evidence provider, never the spec owner.
   - Gemini/Antigravity remains the production implementation writer in workflow v1.
   - OpenCode Gate reviewers remain independent, read-only blocker detectors.

2. **Repository artifacts are the handoff surface**
   - GitHub-tracked `SPEC.md`, `task.json`, `CONTEXT.md`, reviews, and `EVIDENCE.md` replace manual prompt copying wherever practical.
   - Local/remote worktree state must be made explicit before task commands run.

3. **Automation must degrade safely**
   - Failure of an optional agent/model must not corrupt canonical task artifacts.
   - Model fallback is an infrastructure-reliability mechanism, not semantic review-shopping.
   - Deterministic behavior is preferred for branch/task validation, formatting, state transitions, and safety gates.

4. **Small/local models are semantic compressors, not architecture authorities**
   - Local LLMs may summarize already-grounded evidence under a narrow schema.
   - They must not infer missing product intent, rewrite architecture contracts, claim unverified test results, or invent implementation effects.

5. **Observability before autonomy**
   - Before adding more self-driving workflow behavior, collect enough structured evidence to explain what each agent did, which model ran, why fallback occurred, what artifacts changed, and where human intervention was needed.

## Writer model calibration — measurement track

Purpose: determine which Writer model/effort tier is actually most efficient for this repository using accepted production tasks, rather than routing by intuition or nominal model strength.

Canonical measurement log: [`WRITER_MODEL_BENCHMARK.md`](WRITER_MODEL_BENCHMARK.md).

Policy:
- ChatGPT maintains the compact log from Writer closeout reports plus tracked Gate/final-review evidence.
- Missing timing is recorded as `unknown`; models must not estimate values they cannot observe.
- Compare total time, implementation time, verification time, iteration count, and accepted outcome.
- Do not promote a model-routing rule from one or two anecdotes. Collect at least 5-10 representative completed Writer tasks before changing the default Writer tier or designing dynamic routing.
- This is a measurement track, not a new authority layer: Final SPEC still defines the work, Gate remains independent, and ChatGPT/user own final routing policy.

## Completed foundation

- `scout-efficiency-v1` — merged.
- `ai-gate-execution-resilience` — merged.
- AI workflow roadmap planning — merged via PR #5.
- `agent-role-contract-hardening-v1-1` — completed and merged.
- `agent-model-fallback-routing-v1-1` — completed and merged.
  - Ordered role-specific normal-model fallback exists for infrastructure failures.
  - Normal semantic PASS/BLOCK remains terminal; no review-shopping.
  - Gate no longer silently appends an undeclared degraded reviewer path when configured normal candidates are exhausted.
- `intent-routing-observability` — completed and merged.
  - First production pilot for hardened workflow.
  - Implemented structured routing diagnostics, preserved pre-observation in-flight action evidence, and migrated runtime logging.
  - Provided direct production evidence for pilot retrospective.

## Active

### 4. `agent-workflow-pilot-retrospective-v1`

Status: active documentation task (finalizing retrospective and backlog).

Goal: use actual production evidence from `intent-routing-observability` to decide what automation and fixes should be added next.

Key evidence-backed conclusions:
- Gate parser brittleness: strict regex failed on semantically valid Markdown bold headers (`**VERDICT: PASS**`), triggering avoidable infrastructure failure.
- Test protection gap: `ai_gate.ps1` and `ai_scout.ps1` lack automated regression tests.
- Task schema gap: initial `task.json` omitted required `models` block, causing Scout crash.
- Model calibration: single pilot is insufficient for global model order or timeout changes (MEASURE MORE).
- Semantic commit agent: keep deferred (convenience friction does not block throughput; reliability takes precedence).

## Prioritized Next (Workflow v1.2 Reliability & Safety)

### 5. `workflow-script-testing-harness`

Priority: P0 (Prerequisite before modifying workflow scripts).

Goal:
- Provide an automated test harness for `scripts/ai_gate.ps1` and `scripts/ai_scout.ps1` without requiring live AI model invocations.
- Exercise `Get-CanonicalReviewPayload`, `Test-ReviewVerdictStructure`, `Resolve-ReviewCandidates`, timeout bounding, and kill-confirmation seams.
- Prevent regressions during subsequent parser and validation refactoring.

### 6. `gate-payload-robustness-v1`

Priority: P1 (Core Reliability).

Goal:
- Update `Get-CanonicalReviewPayload` and `Test-ReviewVerdictStructure` in `scripts/ai_gate.ps1` to tolerate common Markdown formatting (bolding `**`, headings `#`, backticks) on the `VERDICT` header while maintaining strict semantic rejection of ambiguous or multiple verdicts.
- Preserve attempt history and previous candidate results in `EVIDENCE.md` to prevent canonical evidence overwrite upon rerun.

### 7. `task-descriptor-schema-linting`

Priority: P2 (Developer Experience & Safety).

Goal:
- Add preflight schema validation for `task.json` in `scripts/ai_scout.ps1` and `scripts/ai_gate.ps1`.
- Fail fast with human-actionable error messages if required keys (`id`, `base_ref`, `scope`, `models.scout`, `models.review`) are missing or malformed before executing external processes.

## Planned Future Work (Workflow v2)

### 8. `semantic-commit-agent-v1`

Priority: Deferred candidate. Do not start until P0/P1 reliability tasks and further pilot measurements are complete.

#### Problem

Current commits are partly dependent on whichever agent/person happens to write the message. The same repository change may therefore produce a terse manual message or a richer AI-generated message even though task intent already exists in tracked artifacts.

The objective is **not** to let another agent reason about architecture. The objective is to deterministically convert grounded repository evidence into consistent semantic Git metadata.

#### Architectural role

`Semantic Commit Agent` is a **read-only semantic compressor**.

Authoritative inputs:

```text
staged diff
+ active task Final SPEC
+ task.json
+ CONTEXT.md when relevant
+ current lifecycle phase
+ optionally recent accepted commit examples
```

Bounded semantic output:

```json
{
  "type": "feat|fix|refactor|test|docs|chore",
  "scope": "routing",
  "summary": "add structured intent routing diagnostics",
  "behavior_change": false,
  "effects": [
    "expose routing decision evidence from NavigationRoutingContext",
    "preserve pre-observation in-flight action evidence"
  ]
}
```

A deterministic formatter, not the model, converts the validated schema into the final commit message.

#### Responsibility boundary

Allowed:
- summarize the staged diff;
- classify conventional-commit type/scope;
- correlate an actual change with already-declared Final SPEC intent;
- produce concise semantic effects;
- identify lifecycle phase from canonical tracked artifacts.

Forbidden:
- modify production files or task artifacts;
- stage additional files;
- infer or alter architecture decisions;
- infer roadmap intent not present in canonical artifacts;
- describe planned-but-unimplemented work as completed;
- claim tests/Gate passed without corresponding evidence;
- push, merge, delete branches, or modify `main`;
- make implementation or review decisions.

#### v0 — deterministic commit helper

Proposed entry point:

```powershell
.\scripts\ai_commit.ps1 -Task <task-id>
```

No LLM dependency.

Responsibilities:
- validate current worktree/branch/task relationship;
- fail on detached/wrong-task state rather than guessing;
- inspect only staged changes (`git diff --cached`);
- detect lifecycle artifact category where deterministic;
- enforce project commit formatting;
- show a preview before commit;
- optionally accept a human one-line semantic summary;
- never stage/push automatically unless a future explicit contract authorizes it.

Purpose: establish a trustworthy deterministic shell before adding model inference.

#### v1 — local semantic commit generation

Add optional local inference through an interchangeable local provider (for example Ollama/llama.cpp-compatible execution; provider choice is implementation detail, not architecture contract).

Initial target class: small instruct model roughly in the 1.5B-4B range, benchmarked on this repository rather than assumed sufficient.

Model task is deliberately narrow:
- read bounded staged diff + task contract snippets;
- emit schema-constrained JSON;
- no free-form command execution;
- no repository writes.

Safety requirements:
- strict JSON/schema validation;
- bounded diff/context size and deterministic truncation policy;
- reject hallucinated files/symbols/effects not grounded in the staged diff;
- reject unsupported `tests_passed`, Gate, behavior-change, or completion claims;
- display generated commit message before execution initially;
- record model/provider provenance only if useful, without polluting normal commit subjects.

Fallback invariant:

```text
local model unavailable / invalid output
        -> deterministic v0 path
        -> commit workflow remains usable
```

The local model must never become a single point of failure for Git operations.

#### v2 — lifecycle-aware semantic commits

After v1 evidence demonstrates adequate grounding, map canonical lifecycle stages into consistent commit semantics, for example:

```text
Draft SPEC        -> docs(task): draft ...
Scout evidence    -> docs(task): add scout context
Final SPEC        -> docs(task): finalize ...
Implementation    -> feat/fix/refactor(...): ...
Focused tests     -> test(...): ...
Gate remediation  -> fix(...): address gate finding ...
Evidence closeout -> docs(task): record verification evidence
```

The resulting Git history should act as a compact workflow execution trace, but task state continues to come from canonical task artifacts rather than being reconstructed from commit text.

#### Evaluation criteria

Before wider adoption, benchmark against real task commits:
- semantic correctness;
- hallucination rate;
- percentage requiring human edit;
- latency on the user's local machine;
- context/token requirements;
- robustness on docs-only vs implementation vs mixed commits;
- behavior-change classification accuracy;
- deterministic fallback success.

A larger model is justified only if evidence shows small-model error rate defeats the convenience benefit.

### 9. `workflow-interruptibility-v2`

Interruptibility remains deferred to v2; reliability P0/P1/P2 work comes first.

Goal:
- safe `Pause -> Amend -> Resume` semantics for long-running workflow stages;
- material contract changes invalidate downstream evidence as appropriate;
- no live prompt/message injection into an already-running generation;
- no partial canonical artifact promotion;
- preserve clear ownership of which stage must rerun after a contract change.

Open questions to settle in SPEC:
- what constitutes a material vs non-material amendment;
- artifact invalidation graph;
- cancellation semantics for local model processes;
- whether reviewer attempts are resumable or must restart from clean input;
- how worktree/branch state is recovered after interruption.

### 10. `workflow-orchestrator-v2`

Deferred until reliability, retrospective, and interruptibility contracts are proven.

Target experience:

```text
start task
  -> create/sync branch + task package
  -> Scout
  -> wait for contract owner Finalization
  -> writer handoff
  -> focused tests
  -> Gate
  -> semantic commit assistance
  -> final review handoff
  -> user-authorized integration
```

The orchestrator owns **sequencing**, not task semantics.

Hard boundaries:
- cannot promote Draft SPEC to Final;
- cannot reinterpret blocking reviewer evidence;
- cannot silently repair production code through an unowned writer role;
- cannot merge without explicit integration authority;
- must stop on ambiguous repository/worktree state rather than guessing;
- every automated transition should leave enough evidence to explain why it occurred.

## Deferred candidates after V2 evidence

Not scheduled until production evidence justifies them:

- workflow/status dashboard derived from canonical task artifacts;
- autonomous repair/retry loops;
- parallel or multi-model reviewer voting/racing;
- dynamic local/cloud model routing based on measured cost/latency/quality; only after the Writer benchmark has enough representative samples;
- automatic commit grouping/splitting suggestions;
- richer execution telemetry and per-agent performance history;
- near-autonomous task orchestration beyond sequencing.

## Explicit non-goal for the roadmap

The roadmap does **not** aim to create a swarm of agents that independently reinterpret the codebase. The desired system is a contract-driven development pipeline in which increasingly more mechanical coordination is automated while semantic authority remains deliberately narrow and auditable.

## Verified compatibility baseline — OpenCode structured review (2026-09-16)

The compatibility task `opencode-structured-review-provider-compatibility` established a durable baseline for future reviewer infrastructure work:

```text
OpenCode 1.18.31
+ @opencode-ai/sdk 1.18.31 / official v2 transport
+ opencode/big-pickle
        ↓
JSON-Schema request
        ↓
OpenCode StructuredOutput tool
        ↓
HTTP 200
        ↓
promptResult.data.info.structured
        ↓
valid structured object
```

Evidence and the version policy are preserved in [`docs/architecture/opencode_structured_review_baseline.md`](../architecture/opencode_structured_review_baseline.md).

Roadmap policy:
- Structured transport compatibility for this exact stack is **PROVEN**.
- Formal reviewer-route qualification remains **NOT PROVEN** because the current bottleneck is model-owned repository discovery / structured-finalization behavior, not the verified SDK v2 transport.
- Production OpenCode remains pinned to **1.18.31**.
- Do not resume adjacent-version guessing or change OpenCode solely to solve structured transport unless a new concrete incompatibility, maintenance/security requirement, or explicitly approved task invalidates this baseline.
- Future reviewer work should first improve bounded context acquisition and reviewer evidence supply while preserving independent semantic judgment.
