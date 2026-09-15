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

## Completed foundation

- `scout-efficiency-v1` — merged.
- `ai-gate-execution-resilience` — merged.
- AI workflow roadmap planning — merged via PR #5.
- `agent-role-contract-hardening-v1-1` — completed and merged.
- `agent-model-fallback-routing-v1-1` — completed and merged.
  - Ordered role-specific normal-model fallback exists for infrastructure failures.
  - Normal semantic PASS/BLOCK remains terminal; no review-shopping.
  - Gate no longer silently appends an undeclared degraded reviewer path when configured normal candidates are exhausted.

## Active

### 3. `intent-routing-observability`

Status: active production pilot.

Purpose:
- first production task run through the hardened Spec -> Scout -> Writer -> Gate -> Final Review workflow;
- add structured intent/in-flight routing evidence while preserving navigation behavior;
- use the task as workflow evidence, not merely as a product feature.

Pilot evidence worth retaining for the retrospective:
- handoff friction and manual steps;
- Scout/Gate attempt count and elapsed time;
- model fallback frequency;
- branch/worktree synchronization problems;
- task descriptor/schema mistakes;
- amount of human prompt rewriting required;
- whether reviewer findings were actionable vs speculative;
- whether final Git history communicates task lifecycle clearly.

Current task remains higher priority than starting any roadmap item below.

## Planned next

### 4. `agent-workflow-pilot-retrospective-v1`

Depends on successful closeout of `intent-routing-observability`.

Goal: use actual production evidence to decide what automation should be added next instead of extrapolating from toy runs.

Analyze:
- end-to-end elapsed time by lifecycle stage;
- local -> remote and remote -> local handoff failures;
- model attempt elapsed time, timeout rate, fallback rate, and which candidates actually recover infrastructure failure;
- Gate evidence quality and false/blocking findings;
- human interventions, copy/paste, manual commit writing, branch switching, artifact repair, and reruns;
- current 480s timeout policy and model-specific step budgets;
- task descriptor/schema drift and whether stronger validation is required;
- whether commits themselves form a readable lifecycle trace.

Expected output:
- evidence-backed priority ordering for workflow v1.2/v2;
- calibrated model routing/timeouts/steps;
- explicit decision on whether Semantic Commit Agent should be promoted immediately or remain deferred;
- interruptibility requirements for v2.

Optimization order remains:

```text
reliability
-> production pilot
-> evidence collection
-> calibration
-> convenience automation
-> higher autonomy
```

### 5. `semantic-commit-agent-v1`

Priority: P1 candidate after pilot retrospective. Do not start before task 4 unless manual commit friction proves materially blocking.

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

### 6. `workflow-interruptibility-v2`

Depends on task 4 evidence; ordering relative to Semantic Commit Agent may be swapped by the retrospective if interruption pain is materially higher than commit friction.

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

### 7. `workflow-orchestrator-v2`

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
- automatic task schema validation/linting if retrospective shows recurrent descriptor drift;
- autonomous repair/retry loops;
- parallel or multi-model reviewer voting/racing;
- dynamic local/cloud model routing based on measured cost/latency/quality;
- automatic commit grouping/splitting suggestions;
- richer execution telemetry and per-agent performance history;
- near-autonomous task orchestration beyond sequencing.

## Explicit non-goal for the roadmap

The roadmap does **not** aim to create a swarm of agents that independently reinterpret the codebase. The desired system is a contract-driven development pipeline in which increasingly more mechanical coordination is automated while semantic authority remains deliberately narrow and auditable.
