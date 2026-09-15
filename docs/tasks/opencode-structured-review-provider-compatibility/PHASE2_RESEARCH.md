# Phase 2 OpenCode Version Research

Date: 2026-09-16

## Purpose

Select the smallest evidence-justified alternate OpenCode runtime to probe after Phase 1 on production-pinned `1.18.31` ended with `PASS_PROVEN = 0`.

This document is research/evidence for the current compatibility task. It does not change the production OpenCode pin and does not authorize paid provider usage.

## Phase 1 facts that drive the search

Fresh post-audit-fix evidence on `1.18.31` showed:

- `opencode/big-pickle` / `spec-reviewer`: no permitted read/search lifecycle, forced `finish = tool-calls`, no structured result;
- `opencode/mimo-v2.5-free` / `spec-reviewer`: lifecycle audit failed while reading session messages with `Expected OutputFormatJsonSchema, got {"type":"json_schema", ...}`;
- therefore `PASS_PROVEN = 0` and no Phase 1 route may be recommended.

The MiMo diagnostic is especially useful because it matches a known upstream OpenCode serialization defect rather than an opaque provider failure.

## Upstream evidence

### 1. Exact `OutputFormatJsonSchema` message-read bug is tracked upstream

OpenCode issue #26929:

- https://github.com/anomalyco/opencode/issues/26929
- reported on `1.14.48`;
- a structured prompt is accepted and the model completes, but `GET /session/:id/message` returns HTTP 400 with `Expected OutputFormatJsonSchema, got {"type":"json_schema", ...}`;
- the reporter identifies the problem as a regression around the May 10-11 2026 releases;
- a user reproducing the same error states that `1.14.41` is the last working version in their environment.

This is the closest public reproduction to the current task's MiMo attempt-006 diagnostic.

### 2. The defect persisted through later 1.x releases

OpenCode issue #40169:

- https://github.com/anomalyco/opencode/issues/40169
- reproduces the same persisted-output-format read failure on `1.17.13`;
- the issue explains the root shape mismatch: a persisted `info.format` comes back as a plain object while the response schema expects a `Schema.Class` instance;
- a follow-up comment reports the same problem on `1.18.21`.

The current task independently reproduces the same class of failure on `1.18.31`.

### 3. A direct upstream fix exists but is not merged

OpenCode PR #37541:

- https://github.com/anomalyco/opencode/pull/37541
- title: `fix(session): encode persisted output formats`;
- status at research time: open / unmerged;
- head SHA: `61e0f0321e34e8134bc27ddf534b75933b9ceb38`;
- changes output format wire schemas from `Schema.Class` to `Schema.Struct` so persisted plain objects can be encoded;
- adds a regression test that persists `text` and `json_schema` formats and reads them through the session-message endpoint.

Because this fix is unmerged, selecting a later 1.x release merely for being newer has no evidence advantage for this bug.

### 4. `1.14.41` has the structured-output mechanism and a matching SDK/runtime pair

The upstream `v1.14.41` source already contains the structured-output contract:

- `format.type = "json_schema"`;
- a synthetic `StructuredOutput` final tool;
- explicit instructions to complete research/tool calls before the final structured result;
- an assistant machine field named `structured`;
- `@opencode-ai/sdk` exposes `createOpencode`, whose server launcher resolves the `opencode` executable from `PATH`.

Therefore `1.14.41` can be tested in a one-shot isolated runtime by installing matching CLI + SDK packages into a temporary package root and prepending that root's `node_modules/.bin` to `PATH`, without touching the globally installed production `1.18.31` executable.

### 5. Newer is not automatically safer for structured output

OpenCode issue #46735 documents current/dev structured-output requests forcing `tool_choice = "required"`, which some newer/thinking models reject. Issue #45953 documents the same provider-compatibility class in the newer session runner. These are separate from the persisted-format codec bug but show that a blind upgrade does not establish the required lifecycle.

The Phase 2 selection should therefore follow concrete compatibility evidence rather than newest-version preference.

## Selected first Phase 2 candidate

Probe exactly:

```text
OpenCode CLI:          1.14.41
@opencode-ai/sdk:      1.14.41
provider/model order:  opencode/big-pickle, then opencode/mimo-v2.5-free
first role:            spec-reviewer
second role:           regression-reviewer only after the exact combination passes spec-reviewer
```

Why `1.14.41` first:

1. it immediately precedes the upstream regression that matches our MiMo diagnostic;
2. upstream user evidence names it as the last working release for the exact message-format failure;
3. it contains the structured-output machinery needed by the qualification contract;
4. matching CLI and SDK versions can be isolated cleanly;
5. it is a much narrower hypothesis test than an uncontrolled version sweep.

This is an evidence-driven downgrade probe, not a recommendation to downgrade production.

## Structured-result compatibility rule

OpenCode's official machine field changed across the versions relevant to this investigation. The compatibility probe may normalize only an official, version-native structured-result field into the task's canonical evidence value:

- current `1.18.x` probe path: `response.data.info.structured_output` as already observed by the current task/predecessor adapter contract;
- `1.14.41` source contract: assistant `info.structured`.

Normalization is allowed only for these official SDK/server machine fields and must still apply the exact same fixed JSON Schema and PASS/BLOCK cross-field checks.

Forbidden substitutes remain forbidden:

- prose or Markdown;
- JSON code fences;
- regex verdict extraction;
- searching earlier/stale messages for a result;
- accepting a diagnostic-agent success as production qualification.

## Required isolation boundary

The `1.14.41` probe must not mutate normal OpenCode installation or state.

Required shape:

1. create/use an ignored task runtime under `.runtime/` or an OS temporary directory;
2. install exact `opencode-ai@1.14.41` and `@opencode-ai/sdk@1.14.41` only into that runtime;
3. prepend only that runtime's `node_modules/.bin` to the child environment `PATH` so the matching SDK launches the matching CLI;
4. prove both CLI and SDK versions in each attempt record before model execution;
5. use `OPENCODE_DB=:memory:` (or an equally isolated task-local state if the older runtime cannot use memory DB safely);
6. disable automatic runtime upgrades through version-supported configuration;
7. keep the repository directory pointed at the actual task worktree so the production reviewer definitions are used;
8. keep attempts bounded and non-interactive;
9. restore caller environment after the probe;
10. never commit the temporary runtime or dependency contents.

The production `scripts/opencode_contract.ps1` pin remains `1.18.31` and is not bypassed for normal Scout/Gate execution.

## Probe stop conditions

For `1.14.41`:

1. run one bounded Big Pickle `spec-reviewer` attempt;
2. if it is not `PASS_PROVEN`, run one bounded MiMo `spec-reviewer` attempt;
3. if either exact combination is `PASS_PROVEN`, immediately run the same version/provider/model with `regression-reviewer`;
4. only a combination that passes both roles becomes a recommended Gate route;
5. if both first-role candidates fail, stop and return evidence to ChatGPT/user before selecting another runtime.

Do not continue into a broad version sweep.

## Secondary research directions if `1.14.41` fails

These are not yet authorized live probes:

- a diagnostic build containing the unmerged PR #37541 fix, solely to separate the session-message codec defect from provider/model behavior; this would not itself be a production-version recommendation;
- a specifically justified later/new major runtime only after checking whether its structured-output/session policy actually implements the required lifecycle.

## Decision

Phase 2 candidate #1 is **OpenCode / SDK 1.14.41 in reversible isolation**.

Production migration remains a separate follow-up decision even if this alternate version becomes `PASS_PROVEN`.
