# reviewer-bounded-context-infrastructure

Status: Draft

## Goal

Design a deterministic, bounded reviewer-context infrastructure that supplies high-value repository evidence before an OpenCode reviewer begins semantic reasoning, so review latency, token use, and model-owned repository exploration are reduced without weakening review independence or semantic judgment.

The intended responsibility split is:

```text
deterministic evidence discovery / packaging
                ↓
        bounded context pack
                ↓
read-only reviewer semantic judgment
                ↓
optional bounded targeted verification
                ↓
structured review verdict
```

The task must first survey current leading code-agent / code-review context architectures and repository-retrieval techniques before selecting an implementation design.

## Observed problem

The completed `opencode-structured-review-provider-compatibility` task established that the structured transport itself is no longer the primary blocker. The verified baseline is documented in [`docs/architecture/opencode_structured_review_baseline.md`](../../architecture/opencode_structured_review_baseline.md).

Key evidence:

- OpenCode `1.18.31` + `@opencode-ai/sdk@1.18.31` official v2 transport + `opencode/big-pickle` successfully completed JSON-Schema structured transport through OpenCode `StructuredOutput`, returned HTTP 200, and exposed a schema-valid object at `promptResult.data.info.structured`.
- The same task proved `promptResult.data.parts` can provide a trustworthy typed same-attempt lifecycle audit surface.
- A real Big Pickle regression-review diagnostic consumed roughly 229 seconds and about 61k total tokens while performing broad repository exploration.
- A fresh Big Pickle `spec-reviewer` qualification emitted a valid structured review without invoking the required repository `read` / `glob` / `grep`, producing `FAIL_TOOL_CHOICE`.
- MiMo showed a different reliability failure on a full review: it voluntarily stopped without emitting the required structured output.

These results indicate that model-owned context acquisition / repository exploration is a major remaining source of latency and instability.

## Known invariants

1. **OpenCode compatibility baseline is frozen unless new evidence requires reopening it.**
   - Production remains pinned to OpenCode `1.18.31`.
   - Structured-review infrastructure should build on `@opencode-ai/sdk@1.18.31` official v2 capability when structured transport is needed.
   - Do not resume adjacent-version guessing or provider/version churn merely to solve context acquisition.

2. **Deterministic infra owns evidence discovery; reviewer owns semantic judgment.**
   - Context selection, provenance, bounded packaging, stable ordering, and mechanical repository facts may be deterministic.
   - The context builder must not decide PASS/BLOCK, reinterpret task intent, or silently change architecture policy.

3. **Reviewer independence remains explicit.**
   - OpenCode reviewers remain read-only blocker detectors.
   - A prebuilt context pack must not become a substitute for reviewer reasoning.
   - Reviewer should retain a bounded targeted verification path when supplied evidence is insufficient or suspicious.

4. **Canonical task artifacts remain authoritative.**
   - Final `SPEC.md` defines completion semantics.
   - `task.json`, `CONTEXT.md`, diff/status snapshots, architecture contracts, tests, and generated context artifacts are evidence, not alternative specifications.

5. **Context must be bounded and provenance-preserving.**
   - Any truncation or omission policy must be deterministic and visible.
   - The pack must identify base/head/diff identity and where each included fact came from.
   - Missing evidence must never be silently interpreted as proof that no relevant path exists.

6. **Fail closed on stale or ambiguous repository state.**
   - Wrong branch, detached task state, stale base/head, malformed pack, or unprovable provenance must not produce a trusted review input.

7. **Behavior-preserving workflow change by default.**
   - This task changes AI-review infrastructure, not game runtime behavior.
   - Existing production reviewer semantic boundaries are preserved unless the Final SPEC explicitly authorizes a reviewer-contract change.

## Initial scope

### Research / architecture survey

Survey current leading approaches for minimizing code-agent review context while maintaining retrieval quality and low latency. The survey should distinguish documented architecture from inference and should prioritize current official documentation, papers, and source code where available.

Candidate areas to compare include, without presupposing the final design:

- deterministic diff-first context selection;
- changed-symbol extraction and symbol-level neighborhood expansion;
- direct caller / callee and reference discovery;
- test-to-symbol / symbol-to-test linkage;
- architecture-contract selection;
- repository maps / structural summaries;
- AST / tree-sitter based extraction;
- language-server / SCIP / LSIF style code intelligence;
- lexical search (`rg` / grep) and hybrid lexical + structural retrieval;
- embeddings / semantic RAG only where evidence shows clear benefit;
- incremental indexing and cache invalidation;
- change-impact analysis;
- bounded evidence ranking / truncation;
- reviewer targeted verification after pre-supplied evidence.

Relevant leading systems / research may include code-review agents, coding agents, repository-map approaches, code intelligence platforms, SWE-bench style agents, and production context-engineering systems. Exact systems must be selected during the survey based on current evidence rather than this Draft naming a winner in advance.

### Repository integration survey

Locate the smallest integration seams around:

- `scripts/ai_gate.ps1`;
- `.opencode/agents/spec-reviewer.md`;
- `.opencode/agents/regression-reviewer.md`;
- existing Gate status/diff snapshots;
- task artifacts (`SPEC.md`, `task.json`, `CONTEXT.md`, `EVIDENCE.md`);
- structured review probe evidence where useful;
- focused-test declarations;
- architecture documents and task scope.

### Candidate artifact

Evaluate a bounded `Review Context Pack` (name provisional) that may contain mechanically derived evidence such as:

```text
task identity / base / head
Final SPEC references
changed files and bounded diff hunks
changed symbols
high-confidence direct references / callers / callees
focused and directly related tests
material architecture contracts
provenance for every section
explicit truncation / uncertainty metadata
```

The Final SPEC must decide the exact schema and collection algorithm only after research and Scout evidence.

## Non-goals

- Do not change OpenCode versions/providers as part of this task unless a newly discovered concrete blocker invalidates the verified baseline.
- Do not make Gemini/Antigravity or the context builder a semantic Gate authority.
- Do not eliminate reviewer read/search capability merely to force deterministic behavior.
- Do not build a full repository embedding/vector database unless the architecture survey demonstrates that simpler deterministic/static techniques are insufficient.
- Do not require exhaustive whole-repository traversal for every review.
- Do not optimize solely for one diagnostic task at the expense of reusable workflow boundaries.
- Do not alter game runtime behavior.
- Do not begin production implementation while this SPEC remains Draft.

## Provisional acceptance criteria

1. A sourced architecture survey compares leading context-acquisition/retrieval patterns on at least:
   - retrieval quality / evidence coverage;
   - latency;
   - context/token cost;
   - determinism / reproducibility;
   - freshness / incremental-update cost;
   - provenance / auditability;
   - implementation complexity for this repository.

2. The design chooses the simplest architecture justified by evidence rather than defaulting to embeddings or a full code graph.

3. The proposed context artifact is bounded, deterministic for the same repository state, and records base/head plus evidence provenance.

4. The design preserves the separation:

```text
context infra -> evidence
reviewer -> semantic verdict
```

5. Reviewers retain a bounded targeted verification path for evidence gaps rather than being forced to trust the pack blindly.

6. The Final SPEC defines measurable benchmark methodology for before/after review latency, model token/context consumption where observable, number of reviewer tool calls, and review correctness/regression findings on representative tasks. Exact performance thresholds remain open until the initial measurements and architecture survey are complete.

7. Deterministic tests cover selection/truncation/provenance/staleness behavior without live model calls.

8. Any reviewer prompt or Gate-contract change is explicit, test-covered, and does not silently weaken PASS/BLOCK semantics.

## Uncertainty / open questions

- What is the minimum useful evidence neighborhood for `spec-reviewer` versus `regression-reviewer`?
- Can diff + symbol references + directly linked tests cover most reviews without a persistent semantic index?
- Which languages/files in this repository justify AST/LSP/SCIP support versus lexical search?
- Is a repository map useful as a fallback or does it add avoidable context noise?
- Should architecture-document selection be rule-based from task scope, changed paths, explicit references, or a small hybrid ranker?
- How should large diffs be deterministically chunked/ranked?
- What should be cached across reviews, and what exact repository identity invalidates the cache?
- After a context pack exists, should formal reviewer qualification still require a repository read/search call, or should the contract instead require evidence-pack provenance plus optional targeted verification? This is a policy decision for Final SPEC, not an implementation shortcut.
- What benchmark tasks provide enough variety to detect context omission without making evaluation expensive?

## First-phase stop condition

Before Scout or production implementation, ChatGPT should complete a current external architecture survey plus a lightweight repository survey, write the findings into tracked task evidence, and refine this Draft only enough to establish a credible architecture hypothesis and Scout questions. Do not prematurely finalize the implementation design from this Draft alone.
