# Phase 2 OpenCode Version Research

Date: 2026-09-16

## Purpose

Provide the upstream evidence used to freeze the bounded Phase 2 runtime matrix after production-pinned OpenCode `1.18.31` ended with `PASS_PROVEN = 0`.

The authoritative execution order and stop rules are now in:

`docs/tasks/opencode-structured-review-provider-compatibility/PHASE2_COMPATIBILITY_MATRIX.md`

This research document does not authorize additional versions beyond that matrix.

## Phase 1 facts driving runtime selection

Fresh post-audit-fix evidence on `1.18.31` showed:

- Big Pickle / `spec-reviewer`: no permitted read/search lifecycle, forced `finish = tool-calls`, no structured result;
- MiMo / `spec-reviewer`: lifecycle audit failed when the official message-read path rejected persisted `json_schema` format with `Expected OutputFormatJsonSchema, got {"type":"json_schema", ...}`;
- no Phase 1 route became `PASS_PROVEN`.

The MiMo diagnostic closely matches a known upstream OpenCode persisted-output-format serialization defect.

## Evidence for C1: OpenCode 1.14.41

### Exact persisted-format bug

Upstream issue #26929:

- https://github.com/anomalyco/opencode/issues/26929
- reproduces the `Expected OutputFormatJsonSchema` read-back failure on OpenCode `1.14.48`;
- reports that a structured prompt can execute but later session-message retrieval returns HTTP 400;
- identifies the issue as a May 10-11 2026 regression;
- a reproducer states `1.14.41` was the last working version in their environment.

### Persistence through later 1.x

Upstream issue #40169:

- https://github.com/anomalyco/opencode/issues/40169
- reproduces the same stored-format read failure on `1.17.13`;
- attributes it to a persisted plain `info.format` being encoded against a schema expecting a `Schema.Class` instance;
- a follow-up reports the same failure on `1.18.21`.

Blackfire independently observed the same class of failure on `1.18.31`.

### Direct unmerged fix

Upstream PR #37541:

- https://github.com/anomalyco/opencode/pull/37541
- title: `fix(session): encode persisted output formats`;
- open/unmerged at research freeze;
- head SHA: `61e0f0321e34e8134bc27ddf534b75933b9ceb38`;
- changes output format wire schemas from `Schema.Class` to `Schema.Struct` and adds persisted-format endpoint coverage.

Because that fix was not in a released 1.x build, a random later 1.x selection had no evidence advantage for this exact defect.

### Structured-output mechanism exists in 1.14.41

Tagged `v1.14.41` source already contains:

- `format.type = "json_schema"`;
- the synthetic `StructuredOutput` final tool;
- instructions to complete research/tool calls before final structured return;
- an official assistant machine field `structured`;
- `@opencode-ai/sdk` server launch through the `opencode` executable resolved from `PATH`.

This makes exact CLI + SDK `1.14.41` a clean pre-regression hypothesis that can be isolated without touching production `1.18.31`.

## Evidence for C2: OpenCode 2.0.2

C2 is intentionally not another adjacent 1.x release.

Tagged `v2.0.2` source is a major package/session architecture discontinuity:

- repository root version is `2.0.2`;
- the official CLI package is `@opencode/cli@2.0.2` and exposes the `opencode` binary;
- the official client package is `@opencode/client@2.0.2`;
- v2 session/message schemas are represented through the newer public schema packages rather than the same 1.x message-shape implementation;
- current OpenCode SDK documentation still documents JSON-Schema structured output using a `StructuredOutput` mechanism.

This gives C2 high information value if C1 fails: it tests a different major transport/session architecture rather than guessing another nearby release.

C2 is deliberately second because v2 has known independent tool-choice risks:

- issue #37672 documents toolChoice wiring gaps on v2 HEAD;
- issue #45953 documents providers that fail when the runner forces non-`auto` tool choice;
- issue #46735 documents structured output forcing `required` in paths that some newer/thinking models reject.

These do not prove C2 will fail for Big Pickle or MiMo, but they make a newest-version preference unjustified. C2 is a bounded architectural hypothesis, not a default upgrade recommendation.

## Why the matrix stops at two alternate runtimes

The goal is to prove a route, not map every OpenCode release.

The two selected runtimes cover two distinct high-information hypotheses:

1. C1 `1.14.41`: pre-regression stable candidate immediately before the known persisted-format failure window;
2. C2 `2.0.2`: major architecture boundary candidate with version-matched official CLI/client packages.

Adding adjacent 1.x releases would mostly repeat known-bad serialization territory. Adding dev/beta/source builds would change the question from released-route qualification to upstream diagnosis.

Therefore the frozen matrix is exactly C1 then C2. If both are exhausted without a stable route, probing stops and ChatGPT + user choose a new matrix based on the accumulated failure modes.

## Official structured-result compatibility

Version-native official machine fields may be normalized only after static source/API verification for the exact runtime.

Known evidence:

- 1.18.x contract: `response.data.info.structured_output`;
- 1.14.41 contract: assistant `info.structured`.

For 2.0.2, implementation must first identify and test the official client/server structured-result surface from tagged v2.0.2 source/API. If no trustworthy official machine field can be established, the candidate fails closed; prose/Markdown/regex parsing is forbidden.

## Decision

The research phase is closed for this execution cycle.

The only authorized alternate runtime matrix is:

```text
C1: OpenCode / @opencode-ai/sdk 1.14.41
C2: @opencode/cli / @opencode/client 2.0.2
```

All probe ordering, regression smoke, repeatability, taxonomy, isolation, and stop conditions are defined in `PHASE2_COMPATIBILITY_MATRIX.md` and the Final `SPEC.md`.

Production migration remains a separate follow-up task even if either candidate becomes a stable proven route.