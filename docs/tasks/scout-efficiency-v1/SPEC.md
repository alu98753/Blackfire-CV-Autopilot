# Scout Efficiency v1

Status: Final

## Goal

Make the OpenCode Scout stage a fast, bounded, observable repository-localization step instead of an open-ended codebase audit, while preserving its read-only evidence-provider role and the Draft -> Scout -> Final contract lifecycle.

The default Scout path is optimized for a free/low-cost model: localize the task quickly, surface uncertainty, and stop once there is enough evidence for ChatGPT + user to finalize the spec. Deeper reasoning and broad architecture investigation belong to ChatGPT or Gemini when explicitly escalated.

## Observed problem

Real executions exposed two workflow weaknesses:

1. A simple Scout smoke prompt asking for the primary architecture document expanded into a broader audit than necessary.
2. A real `scout-efficiency-v1` execution using `opencode/big-pickle` exceeded the 8-minute observation budget, remained silent to the user, and produced no canonical `CONTEXT.md` before termination. The observed run started at `2026-09-14 13:43:44` and was terminated at `13:54:09` after about 10 minutes 25 seconds.

This single timed execution proves that the current path can exceed the acceptable interactive latency budget; it does not prove that every Big Pickle execution does so.

The current Scout contract defines what to inspect but has no explicit exploration budget, early-stop rule, output budget, or timeout. The current PowerShell wrapper captures `opencode` output through a blocking `Out-String` pipeline and only writes `CONTEXT.md` after successful completion, so a long-running Scout appears opaque and silent.

## Scope

Primary change surface:

- `.opencode/agents/scout.md`
- `scripts/ai_scout.ps1`
- `docs/architecture/ai_development_workflow.md`
- `docs/tasks/README.md` only if user-facing Scout execution defaults need documentation

A small script-level verification seam/test may be added if needed to verify success, timeout, and failure behavior without invoking a real long-lived model call.

No game/runtime behavior may change.

## Known invariants

1. Scout remains strictly read-only: no repository edits, shell execution, repair subagents, merge actions, or production implementation.
2. Scout remains an evidence provider, not spec owner. It must not promote `SPEC.md` from Draft to Final.
3. `SPEC.md` remains the only normative task contract.
4. Default Scout behavior favors minimal task localization over exhaustive repository audit.
5. Scout may report uncertainty instead of recursively exploring every possibly related subsystem.
6. Successful Scout output still lands at `docs/tasks/<task-id>/CONTEXT.md`.
7. Timeout, process failure, or partial output must never silently replace a previously valid canonical `CONTEXT.md`.
8. Long-running Scout execution must be user-observable from the terminal.
9. The timeout mechanism must terminate only the launched `opencode run` client process and must not kill the persistent `opencode serve` service.
10. Existing callers using `scripts/ai_scout.ps1 -Task <id>` remain valid.
11. Full-suite tests remain user-only.

## Target behavior

### 1. Light-by-default Scout contract

Scout is a task localizer, not a general codebase auditor.

Default behavior:

- begin with `SPEC.md`, `task.json`, declared task scope, and the directly relevant architecture contract;
- inspect only directly necessary neighboring implementation/tests;
- do not start from global runtime entry points unless the task itself concerns bootstrap/runtime ownership;
- stop once the following are sufficiently established:
  - responsibility owner;
  - current control/data path relevant to the task;
  - directly relevant tests or safety mechanisms;
  - smallest plausible change surface;
  - material regression/architecture risks;
  - remaining uncertainty;
- do not traverse sibling subsystems solely because they might be related;
- prefer explicit uncertainty over speculative exploration.

### 2. Exploration/output budget

Default Scout prompt contract:

- inspect at most **10 directly relevant repository files**;
- target report length **<= ~1500 words**;
- when the file budget is reached, stop and report remaining uncertainty instead of expanding scope.

`max_files` is a **soft prompt-enforced budget** in v1 because OpenCode v2.0.3 exposes no native `--max-files` / tool-call cap. The implementation must not pretend this is a hard sandbox guarantee.

### 3. Hard execution timeout

`ai_scout.ps1` must enforce a real wall-clock timeout with a default of **8 minutes / 480 seconds**.

Requirements:

- timeout is enforced by the wrapper, not merely stated in the prompt;
- on timeout, terminate only the launched `opencode run` client process;
- do not terminate the persistent OpenCode service;
- return a clear non-zero failure to the caller;
- do not promote partial output to canonical `CONTEXT.md`;
- support a shorter timeout override/test seam so timeout behavior can be verified in seconds rather than waiting 8 minutes.

The exact public parameter name is implementation detail, but normal `-Task <id>` callers must continue to work unchanged.

### 4. Observable streaming

While Scout runs, output emitted by the child process must be visible to the user in the terminal instead of being fully buffered until exit.

The implementation should use one coherent child-process ownership mechanism for:

- obtaining the launched client PID/process handle;
- observing stdout/stderr as they arrive;
- enforcing timeout;
- collecting candidate output;
- reading the final exit code.

Prefer `System.Diagnostics.Process` or an equivalently robust mechanism if needed to satisfy all of the above together. Do not keep a simple streaming pipeline if it makes reliable timeout/process ownership ambiguous.

### 5. Candidate output and canonical promotion

Candidate output must be staged outside the canonical task artifact, preferably under ignored runtime state such as:

```text
.runtime/ai_scout/<task-id>/
```

Canonical promotion rules:

- only a successful process exit may promote candidate output to `docs/tasks/<task-id>/CONTEXT.md`;
- candidate output must be non-empty and contain the expected Scout report structure sufficiently to reject obvious empty/broken output;
- timeout/non-zero exit must leave any previously valid `CONTEXT.md` untouched;
- partial/debug output may remain only under ignored runtime state or be cleaned up;
- avoid fragile parsing that depends on undocumented OpenCode presentation strings.

If stdout/stderr need separate handling to keep diagnostics visible without contaminating canonical Markdown, the implementation may separate them, but must verify actual local behavior rather than assume which stream OpenCode uses for progress.

### 6. Escalation policy

If light Scout cannot establish enough evidence, it returns explicit uncertainty and `GO WITH SPEC CHANGES` or `NO-GO` rather than silently deepening into a broad audit.

ChatGPT + user may then assign deeper investigation to ChatGPT/Gemini. A configurable `deep` Scout mode is explicitly **not part of v1**.

### 7. Configuration policy

Do **not** add `task.json.scout` execution-budget schema in v1.

Rationale:

- timeout can have a sensible script default plus an optional override;
- file/report budgets are prompt-level soft constraints;
- adding per-task metadata now would create configuration surface before there is evidence that tasks need different Scout budgets.

Model selection remains under the existing `models.scout` field and is separate from Scout execution policy.

## Acceptance criteria

1. `.opencode/agents/scout.md` explicitly defines light localization, early-stop behavior, <=10 directly relevant files, concise output, and uncertainty instead of broad speculative traversal.
2. Scout report target is concise (approximately <=1500 words) and still contains enough evidence for Draft -> Final spec convergence.
3. `ai_scout.ps1` enforces a default hard timeout of 480 seconds while preserving the existing `-Task <id>` invocation.
4. Timeout terminates only the launched `opencode run` client and returns a clear failure without killing the persistent OpenCode server.
5. The user can observe child output in the terminal during execution as it is emitted.
6. Successful output is staged and promoted to `docs/tasks/<task-id>/CONTEXT.md` only after successful completion and minimal structural/non-empty validation.
7. Timeout and non-zero exit never overwrite a previously valid canonical `CONTEXT.md` with partial output.
8. The script preserves/returns the child process failure result clearly enough for local automation to detect failure.
9. No `task.json.scout` schema or configurable deep mode is introduced in v1.
10. Focused verification demonstrates at least:
    - successful child completion + canonical promotion;
    - timeout + client-only termination + no canonical overwrite;
    - non-zero child exit + no canonical overwrite;
    - visible streaming behavior through a short deterministic probe or test seam.
11. Verification must not require a real 8-minute model call or full test suite.
12. No production/game behavior changes.

## Non-goals

- Do not make Scout a second architecture reviewer.
- Do not move spec ownership from ChatGPT + user to OpenCode.
- Do not add autonomous repair loops.
- Do not optimize or redesign `ai_gate.ps1` reviewers in this task unless a shared helper is strictly necessary and behavior-preserving.
- Do not start `intent-routing-observability` here.
- Do not select a permanent paid model/provider architecture.
- Do not add complex telemetry, dashboards, queues, or background services.
- Do not solve latency by simply raising timeouts.
- Do not add a configurable `deep` Scout mode in v1.
- Do not add per-task Scout budget configuration in v1.

## Evidence basis / remaining uncertainty

Confirmed locally:

- at least one real Big Pickle Scout execution exceeded the 8-minute observation budget;
- current wrapper produced no user-visible terminal streaming during that run;
- no canonical `CONTEXT.md` existed before termination;
- terminating the client process did not kill the persistent OpenCode service;
- OpenCode v2.0.3 exposes no native max-files/tool-call cap, so file budget is prompt-soft in v1.

Still to be verified during implementation/focused testing:

- exact stdout vs stderr behavior of the installed OpenCode CLI under the new process wrapper;
- the smallest robust Windows invocation/quoting mechanism for the installed `opencode` command shim;
- minimal structural validation that rejects broken/empty candidate output without brittle parsing.
