# Scout Efficiency v1

Status: Draft

## Goal

Make the OpenCode Scout stage a fast, bounded, observable repository-localization step instead of an open-ended codebase audit, while preserving its read-only evidence-provider role and the Draft -> Scout -> Final contract lifecycle.

The default Scout path should be appropriate for a free/low-cost model: it should localize the task quickly, surface uncertainty, and stop once there is enough evidence for ChatGPT + user to finalize the spec. Deeper reasoning and broad architecture investigation should remain the responsibility of ChatGPT or Gemini when explicitly escalated.

## Observed problem

Two real executions exposed the same workflow weakness:

1. A simple Scout smoke prompt asking for the primary architecture document expanded into a much broader audit than necessary.
2. `workflow-merge-authority` Scout remained running for roughly 30 minutes without producing `CONTEXT.md`; the user could not observe useful progress because `scripts/ai_scout.ps1` buffers the entire OpenCode output through `Out-String` and writes the context only after process completion.

The current Scout contract defines what to inspect but has no explicit exploration budget, early-stop rule, default depth, output budget, or timeout. The current PowerShell wrapper also provides no useful streaming progress to the user.

## Scope

Primary change surface:

- `.opencode/agents/scout.md`
- `scripts/ai_scout.ps1`
- `docs/architecture/ai_development_workflow.md`
- `docs/tasks/README.md` only if task metadata/schema needs to document Scout execution options

Tests or a small script-level verification seam may be added only if needed to verify timeout/output behavior without running a real long-lived model call.

## Known invariants

1. Scout remains strictly read-only: no repository edits, shell execution, repair subagents, merge actions, or production implementation.
2. Scout remains an evidence provider, not spec owner. It must not promote `SPEC.md` from Draft to Final.
3. `SPEC.md` remains the only normative task contract.
4. Default Scout behavior should favor minimal task localization over exhaustive repository audit.
5. Scout may report uncertainty instead of recursively exploring every possibly related subsystem.
6. Successful Scout output still lands at `docs/tasks/<task-id>/CONTEXT.md`.
7. Partial/timeout output must not silently become authoritative `CONTEXT.md` evidence.
8. User-visible progress must improve: a long-running Scout should not appear as an opaque silent process until completion.
9. The change must not alter game/runtime behavior.
10. Full-suite tests remain user-only and are not required for a workflow/script-only focused verification unless repository closeout policy later requires them.

## Provisional target behavior

### Default Scout mode

Default execution is `light` localization:

- start from `SPEC.md`, `task.json`, declared scope, and directly relevant architecture contracts;
- inspect only directly necessary neighboring implementation/tests;
- do not start from global runtime entry points unless the task itself concerns bootstrap/runtime ownership;
- stop once responsibility owner, current path, relevant tests/safety mechanisms, minimal change surface, material risks, and remaining uncertainty are sufficiently established;
- avoid traversing sibling subsystems solely because they might be related;
- prefer concise evidence over completeness theater.

### Budget

The implementation should support an explicit bounded Scout budget. Provisional defaults:

- mode: `light`
- max files: approximately 10 directly inspected files
- timeout: approximately 8 minutes
- report size: concise enough for fast downstream review, roughly 1200-1800 words maximum

Exact enforcement mechanism is intentionally provisional until Scout/local implementation evidence confirms what OpenCode exposes reliably.

### Observable execution

`ai_scout.ps1` should expose useful live output while the Scout runs rather than buffering everything invisibly until completion.

Preferred semantics:

- user sees OpenCode stdout/stderr progress in the terminal as it arrives;
- output is captured to a temporary file or buffer concurrently;
- only a successful, complete Scout report is promoted to canonical `CONTEXT.md`;
- timeout/non-zero exit clearly reports failure and does not overwrite a previously valid `CONTEXT.md` with partial output;
- temporary output is either cleaned or stored only under ignored runtime state.

### Escalation

If light Scout cannot establish enough evidence, it should return explicit uncertainty / `GO WITH SPEC CHANGES` / `NO-GO` rather than silently becoming a deep audit.

ChatGPT + user may then explicitly choose deeper investigation by ChatGPT/Gemini or a future `deep` Scout mode. Deep mode is not the default.

## Provisional task metadata

If practical, task metadata may gain a small Scout execution section such as:

```json
"scout": {
  "mode": "light",
  "max_files": 10,
  "timeout_minutes": 8
}
```

This shape is provisional. Do not add configuration knobs that cannot be meaningfully enforced or consumed.

Model selection remains separate from execution budget. A free model may remain the default Scout model, but this task should fix the agent/script contract before relying on model replacement as the primary solution.

## Provisional acceptance criteria

1. Scout agent instructions explicitly define light localization, early-stop behavior, and prohibition on unnecessary broad audit.
2. Default Scout execution is bounded by a documented timeout, with a reasonable default near 8 minutes unless implementation evidence supports a better value.
3. A timed-out or failed Scout does not replace canonical `CONTEXT.md` with partial output.
4. A successful Scout still writes a complete `CONTEXT.md` to the canonical task package.
5. The user can observe ongoing Scout output/progress in the terminal while it runs.
6. The script preserves the OpenCode exit result and fails clearly on timeout/non-zero exit.
7. Budget metadata, if added, has one clear canonical schema and does not duplicate model selection semantics.
8. Existing callers using `scripts/ai_scout.ps1 -Task <id>` remain valid with sensible defaults.
9. No production/runtime behavior changes.
10. Focused verification demonstrates at least the success path and timeout/failure safety semantics without requiring a real 30-minute model call.

## Non-goals

- Do not make Scout a second architecture reviewer.
- Do not move spec ownership from ChatGPT + user to OpenCode.
- Do not add autonomous repair loops.
- Do not optimize or redesign `ai_gate.ps1` reviewers in this task unless a shared helper is strictly necessary and behavior-preserving.
- Do not start `intent-routing-observability` here.
- Do not select a permanent paid model/provider architecture.
- Do not add complex telemetry, dashboards, queues, or background services.
- Do not solve latency by simply raising timeouts.

## Uncertainty / Scout questions

Before this spec becomes Final, evidence should answer:

1. What streaming behavior does the installed `opencode run` expose through PowerShell stdout/stderr, and what is the simplest reliable way to tee it to terminal + capture it?
2. What timeout implementation can terminate the child `opencode run` reliably on Windows without killing the persistent `opencode serve` process?
3. Can a practical `max_files` budget be enforced by prompt contract alone, or is only a soft budget realistic with current OpenCode tooling?
4. Does OpenCode emit final Markdown mixed with progress/status output, and if so how should canonical `CONTEXT.md` isolate the report without fragile parsing?
5. Is task-level `scout` metadata needed in v1, or are script defaults + optional command-line overrides simpler and more testable?
6. What focused PowerShell/script tests or mocks already exist nearby, if any, that can verify success/timeout/failure semantics cheaply?
