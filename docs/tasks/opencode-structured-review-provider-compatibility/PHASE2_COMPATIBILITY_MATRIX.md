# Phase 2 Compatibility Matrix

Date frozen: 2026-09-16

## Purpose

Freeze the bounded Phase 2 search space before live probing. The task is trying to prove one viable structured-review route, not perform open-ended OpenCode archaeology.

Production OpenCode remains pinned to `1.18.31`. This matrix governs isolated compatibility probing only.

## Fixed runtime matrix

| Order | Runtime | Official client/SDK | Why it is in the matrix | Status before Phase 2 |
| --- | --- | --- | --- | --- |
| Control | OpenCode `1.18.31` | `@opencode-ai/sdk@1.18.31` | Production baseline already re-probed after launcher/local-state repair | Completed: `PASS_PROVEN = 0` |
| C1 | OpenCode `1.14.41` | `@opencode-ai/sdk@1.14.41` | Upstream evidence identifies it as the last working release before the exact persisted `OutputFormatJsonSchema` read-back regression observed by this task; tagged source already contains structured-output machinery | Authorized Phase 2 candidate |
| C2 | OpenCode `2.0.2` | `@opencode/client@2.0.2` with `@opencode/cli@2.0.2` | First frozen current-major candidate after the v2 session/schema architecture discontinuity; official package manifests are version-matched and current OpenCode docs still expose JSON-Schema structured output. Known v2 tool-choice risk is why it is second, not first | Authorized Phase 2 candidate |

No other OpenCode runtime is authorized in this matrix.

The unmerged upstream PR #37541 build is diagnostic-only and is not a route candidate. Dev/beta builds, arbitrary adjacent releases, and paid/authenticated providers are outside this matrix.

## Fixed provider/model order

For every runtime candidate, use the same free/local candidate order:

1. `opencode/big-pickle`
2. `opencode/mimo-v2.5-free`

Do not reorder the models based on intermediate results except that a model that achieves a stable route ends the search immediately.

If a runtime cannot expose one of these model IDs, that attempt is `FAIL_INFRASTRUCTURE`; do not silently substitute a different model.

## Probe invariants across runtime candidates

The qualification prompt, fixed reviewer JSON Schema, semantic invariants, required read/search lifecycle, bounded diagnostics, reviewer files, and route criteria are frozen across C1 and C2.

Only version-native transport adaptation is allowed:

- exact official runtime/client package names and invocation shape;
- exact official machine structured-result field for that runtime;
- exact lifecycle-audit API/response shape for that runtime.

Transport adaptation must never become prose/Markdown/regex fallback or a weaker reviewer contract.

## Attempt-level result taxonomy

Every new Phase 2 live attempt MUST end in exactly one of these classifications:

- `PASS_PROVEN`
- `FAIL_TOOL_CHOICE`
- `FAIL_LIFECYCLE_AUDIT`
- `FAIL_STRUCTURED_OUTPUT`
- `FAIL_SCHEMA`
- `FAIL_SEMANTIC`
- `FAIL_INFRASTRUCTURE`

Use bounded subreason fields for additional detail instead of inventing more top-level classifications.

Classification meaning:

- `FAIL_TOOL_CHOICE`: required repository read/search was never issued, an incompatible tool was chosen instead, or the provider explicitly rejects the tool-choice mode needed by the structured-output path.
- `FAIL_LIFECYCLE_AUDIT`: required tool result did not complete successfully, finalization was forced, or the lifecycle/audit source is missing, malformed, incomplete, or otherwise not trustworthy enough to prove the sequence.
- `FAIL_STRUCTURED_OUTPUT`: the audited lifecycle otherwise completed, but the verified official machine structured-result field is absent or unusable.
- `FAIL_SCHEMA`: structured machine result exists but fails the frozen reviewer JSON Schema.
- `FAIL_SEMANTIC`: schema-valid result violates PASS/BLOCK cross-field invariants.
- `FAIL_INFRASTRUCTURE`: version/client mismatch, runtime startup/install/isolation failure, model/provider unavailable, transport/auth failure, or other failure before a trustworthy reviewer lifecycle can be evaluated.

Historical Phase 1 classifications remain as recorded; this taxonomy governs new Phase 2 attempts and must not rewrite old evidence.

## Trustworthy lifecycle audit requirement

An attempt cannot be `PASS_PROVEN` unless the lifecycle audit source is explicitly recorded and trustworthy.

A trustworthy source must be an authoritative official response/history/event surface for the same attempt and must prove, without inference from missing data:

1. a permitted `read`/`glob`/`grep` call occurred;
2. its result completed successfully and returned to the reviewer;
3. the reviewer left the tool loop voluntarily rather than by max-step/forced finalization;
4. the structured machine result belongs to the same authoritative final attempt.

Examples of potentially trustworthy sources are a prompt response that itself contains complete typed tool lifecycle parts, or a version-native official session/history endpoint that returns a complete schema-valid message/event sequence.

If the audit endpoint fails, returns an unusable shape, or requires reconstructing the lifecycle from missing/stale messages, the attempt is `FAIL_LIFECYCLE_AUDIT`.

## Early regression-reviewer smoke

Do not wait until a full spec-reviewer success to discover that a runtime cannot load or execute the regression reviewer at all.

Before the full spec-reviewer candidate sequence for each runtime, run exactly one bounded, diagnostic-only regression-reviewer smoke using `opencode/big-pickle`.

The smoke MUST:

- use the actual production `regression-reviewer` agent definition;
- use the same official structured-output transport and the same frozen output schema;
- require one repository read/search tool lifecycle;
- use a fixed minimal smoke prompt shared unchanged across all runtime candidates;
- record the same audit source and classification taxonomy;
- remain non-qualifying: a smoke success does not count toward route repeatability or authorize a route.

The smoke is an early incompatibility detector only. Its failure does not skip the required spec-reviewer matrix attempts, because another model may still satisfy the full route.

## Full candidate execution order

For each runtime C1 then C2:

1. run the fixed regression-reviewer smoke with Big Pickle;
2. run Big Pickle `spec-reviewer` full probe;
3. if Big Pickle spec fails, run MiMo `spec-reviewer` full probe;
4. when a model gets spec `PASS_PROVEN`, run one full `regression-reviewer` probe using the exact same runtime + official client + provider + model;
5. if full regression fails, that route is rejected and the matrix continues with the next model/runtime;
6. if both roles pass once, perform the repeatability confirmation below before stopping.

Do not change prompt, schema, step budget, reviewer semantics, or lifecycle criteria between C1 and C2.

## Repeatability requirement

A single lucky success is not a stable Gate route.

After the same runtime + official client + provider + model has one full `PASS_PROVEN` on both roles, rerun the exact pair once:

- second `spec-reviewer` full probe;
- second `regression-reviewer` full probe.

The route is stable only when all four qualifying attempts are `PASS_PROVEN`:

```text
spec #1 PASS_PROVEN
regression #1 PASS_PROVEN
spec #2 PASS_PROVEN
regression #2 PASS_PROVEN
```

All four must use the same version pair, provider/model, reviewer files, prompt/schema, isolation design, lifecycle rules, and trustworthy audit requirements.

The early regression smoke never counts toward these four attempts.

If either confirmation attempt fails, do not add an ad-hoc retry. The route is not repeatable; record the failure and continue the frozen matrix.

The public route declaration `PASS_PROVEN: OpenCode X + provider/model` is reserved for a combination that passes both roles and this repeatability requirement.

## Isolation requirements

Every alternate runtime must be reversible and isolated from production OpenCode state:

- install exact runtime/client versions only under ignored `.runtime/` or an OS temporary directory;
- never change the global OpenCode executable/package;
- never change the production `scripts/opencode_contract.ps1` pin;
- prove runtime and official client package versions mechanically before each attempt;
- use memory/task-local state only; never reuse the user's normal OpenCode database;
- restore PATH/environment after each attempt;
- disable automatic update where the candidate runtime supports it;
- never commit dependency contents, credentials, raw provider payload dumps, or temporary state.

## Matrix stop rules

The search is closed over the frozen matrix.

Stop immediately and return to ChatGPT/user when any one of these becomes true:

1. a stable route is proven by both roles twice each; or
2. C1 and C2 are exhausted without a stable route; or
3. a safety/isolation defect makes continued probing risk production state; or
4. the next required probe would incur paid/API cost without explicit user authorization.

When C1 and C2 are exhausted, do NOT automatically test:

- 1.14.40/1.14.42/other adjacent releases;
- another 1.x release;
- a newer 2.x release that appeared after this matrix freeze;
- dev/beta/nightly builds;
- PR #37541 or another source build;
- another provider/model.

Those require a new explicit matrix decision by ChatGPT + user based on the completed evidence.

## Research basis for candidate ordering

C1 is first because upstream issue #26929 reproduces the same `Expected OutputFormatJsonSchema` failure on 1.14.48 and a reproducer identifies 1.14.41 as the last working version for that defect. Issue #40169 shows the same persisted-format failure later in 1.x, including 1.18.x. PR #37541 proposes a direct encoding fix but remains unmerged.

C2 is second because v2 is an architectural discontinuity rather than another arbitrary adjacent 1.x release. The v2.0.2 source identifies version-matched `@opencode/cli@2.0.2` and `@opencode/client@2.0.2`. Current OpenCode SDK documentation still documents JSON-Schema structured output, while upstream v2 issues also warn that tool-choice behavior remains a real compatibility risk. This makes 2.0.2 a bounded high-information second hypothesis, not a newest-version preference.

## Frozen decision

Phase 2 runtime search space is exactly:

```text
C1: 1.14.41
C2: 2.0.2
```

Production `1.18.31` remains untouched. A production upgrade/downgrade is a separate follow-up task only after a stable route is proven.