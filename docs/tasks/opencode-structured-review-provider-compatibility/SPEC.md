# opencode-structured-review-provider-compatibility

Status: Final

## Goal

Identify and prove at least one stable `OpenCode runtime + official client/SDK + provider + model` route that can satisfy Blackfire's machine-readable structured-review lifecycle without weakening Gate semantics:

```text
read/search tool call
-> successful tool result
-> voluntary final assistant turn
-> official structured machine result present
-> fixed JSON Schema valid
-> PASS/BLOCK semantic invariants valid
-> lifecycle audit source trustworthy
-> repeatability confirmed
```

This is a bounded compatibility qualification task, not an open-ended OpenCode history investigation.

Production OpenCode remains pinned to `1.18.31` throughout this task. Any production upgrade/downgrade is a separate follow-up task after a stable route is proven.

## Baseline

The launcher/version prerequisite is complete. Normal Blackfire Scout/Gate execution works on production-pinned OpenCode `1.18.31`, but normal text-verdict success is not structured-output proof.

Phase 1 already re-probed the repaired `1.18.31` baseline:

- `opencode/big-pickle` / `spec-reviewer`: no permitted read/search lifecycle, forced `finish = tool-calls`, no structured result;
- `opencode/mimo-v2.5-free` / `spec-reviewer`: lifecycle audit failed while reading session messages with the upstream-style `Expected OutputFormatJsonSchema, got {"type":"json_schema", ...}` failure.

Therefore:

```text
OpenCode 1.18.31: PASS_PROVEN = 0
```

The existing Phase 1 attempts remain immutable historical/fresh evidence. New Phase 2 taxonomy must not rewrite old classifications.

## Frozen reviewer output contract

The fixed outcome schema is unchanged:

```json
{
  "verdict": "PASS",
  "blocking_findings": 0,
  "report_markdown": "# Review\n..."
}
```

Rules:

- `verdict` is exactly `PASS` or `BLOCK`;
- `blocking_findings` is a non-negative integer;
- `report_markdown` is a string;
- `PASS -> blocking_findings == 0`;
- `BLOCK -> blocking_findings >= 1`;
- no verdict may be reconstructed from Markdown/prose;
- no JSON-fence or regex fallback;
- no stale/earlier-message salvage;
- no diagnostic-agent success may qualify a production route.

## Qualification surface

Qualification uses the actual production reviewer contracts:

- `.opencode/agents/spec-reviewer.md`
- `.opencode/agents/regression-reviewer.md`

Reviewer permissions, step budgets, exploration semantics, prompt/schema, and lifecycle criteria must not be weakened or tuned per runtime/model.

A simplified diagnostic agent is allowed only for failure localization and can never produce route qualification evidence.

## Official structured-result normalization

The task qualifies a semantic capability across OpenCode versions, so version-native official transport differences may be adapted, but only through documented/source-verified official machine fields.

Known mappings already supported by evidence:

- `1.18.x`: `response.data.info.structured_output`;
- `1.14.41`: assistant `info.structured`.

For any other matrix runtime, including `2.0.2`, implementation must first identify the version-native official client/server structured-result surface from that runtime's source/API. If no trustworthy official machine field can be verified, the runtime cannot be qualified by inventing a parser.

Transport adaptation may include official package names, request shape, lifecycle-history API shape, and structured-result field names. It may not change reviewer semantics, prompt/schema, or success criteria.

## Trustworthy lifecycle audit

An attempt cannot be `PASS_PROVEN` unless the audit source is explicitly recorded and trustworthy.

The same-attempt authoritative lifecycle must prove:

1. at least one permitted repository `read` / `glob` / `grep` call occurred;
2. its result completed successfully and returned to the reviewer;
3. the reviewer voluntarily left the tool loop rather than being forced by max-step/step-limit behavior;
4. the final structured machine result belongs to that same authoritative attempt.

A prompt response that itself contains complete typed lifecycle parts may be authoritative. A version-native official session/history/event API may also be authoritative if it returns a complete valid sequence.

Missing, malformed, incomplete, rejected, or reconstructed lifecycle evidence fails closed. Never infer "the model chose no tool" merely because the audit source failed.

## Phase 2 fixed compatibility matrix

The Phase 2 runtime search space is frozen before live probing in:

`docs/tasks/opencode-structured-review-provider-compatibility/PHASE2_COMPATIBILITY_MATRIX.md`

Authorized runtime order is exactly:

```text
C1: OpenCode 1.14.41
    official client: @opencode-ai/sdk@1.14.41

C2: OpenCode 2.0.2
    official CLI/client: @opencode/cli@2.0.2 + @opencode/client@2.0.2
```

Production `1.18.31` is the already-completed control and is not another Phase 2 runtime attempt unless a later implementation defect invalidates its evidence.

Why C1 first:

- upstream issue #26929 reproduces the exact persisted `OutputFormatJsonSchema` read-back error on `1.14.48`;
- a reproducer identifies `1.14.41` as the last working version for that defect;
- `1.14.41` already contains structured-output machinery and an official assistant machine field.

Why C2 second:

- it is a major session/schema architecture discontinuity rather than another guessed adjacent 1.x release;
- its tagged source identifies version-matched official `@opencode/cli` and `@opencode/client` packages;
- current OpenCode documentation still exposes JSON-Schema structured output;
- v2 also has known tool-choice compatibility risks, so it is deliberately second rather than preferred merely because it is newer.

No other runtime is authorized in this matrix. The unmerged upstream PR #37541, dev/beta/nightly builds, adjacent 1.x releases, later 2.x releases, and paid/authenticated providers require a new explicit matrix decision after current evidence is exhausted.

## Fixed provider/model order

For each authorized runtime:

1. `opencode/big-pickle`
2. `opencode/mimo-v2.5-free`

Do not silently substitute another provider/model if one is unavailable. Runtime/model unavailability is evidence, not permission to broaden the search.

## Phase 2 attempt taxonomy

Every new Phase 2 live attempt must end in exactly one of these top-level classifications:

- `PASS_PROVEN`
- `FAIL_TOOL_CHOICE`
- `FAIL_LIFECYCLE_AUDIT`
- `FAIL_STRUCTURED_OUTPUT`
- `FAIL_SCHEMA`
- `FAIL_SEMANTIC`
- `FAIL_INFRASTRUCTURE`

Use bounded `subreason` / diagnostic fields for detail rather than creating more top-level classes.

Classification rules:

- `FAIL_TOOL_CHOICE`: required read/search was never issued, an incompatible tool path was chosen, or the provider rejects the tool-choice mode required by the structured-output path.
- `FAIL_LIFECYCLE_AUDIT`: required tool result did not complete successfully, finalization was forced, or the authoritative lifecycle source is missing/untrusted/unusable.
- `FAIL_STRUCTURED_OUTPUT`: audited lifecycle otherwise completed, but the verified official structured machine field is absent or unusable.
- `FAIL_SCHEMA`: official structured result exists but violates the frozen schema.
- `FAIL_SEMANTIC`: schema-valid result violates PASS/BLOCK cross-field invariants.
- `FAIL_INFRASTRUCTURE`: runtime/client mismatch, install/startup/state isolation failure, model/provider unavailable, transport/auth failure, or another failure before trustworthy reviewer lifecycle evaluation.

## Early regression-reviewer smoke

Do not wait until a full spec-reviewer success to discover a role-specific transport/config incompatibility.

Before full spec-reviewer qualification for each runtime, run exactly one bounded diagnostic-only `regression-reviewer` smoke using `opencode/big-pickle`.

The smoke must:

- load the actual production regression reviewer contract;
- use the same official structured-output transport and frozen output schema;
- require one repository read/search lifecycle;
- use one fixed minimal smoke prompt shared unchanged across C1 and C2;
- use the same audit/classification rules;
- remain non-qualifying: smoke success never counts toward route repeatability.

Smoke failure does not automatically skip the required spec-reviewer matrix attempts because a second model may still provide a viable full route.

## Full candidate execution algorithm

For C1, then C2:

1. run the fixed Big Pickle regression-reviewer smoke;
2. run Big Pickle `spec-reviewer` full probe;
3. if Big Pickle spec fails, run MiMo `spec-reviewer` full probe;
4. when a model gets spec `PASS_PROVEN`, run one full `regression-reviewer` probe using the exact same runtime + official client + provider + model;
5. if full regression fails, reject that route and continue the frozen matrix;
6. if both roles pass once, run the repeatability confirmation below;
7. if repeatability fails, do not add an ad-hoc retry; continue the frozen matrix.

All full probes use the same qualification prompt, output schema, reviewer files, lifecycle criteria, and isolation rules across runtime candidates.

## Repeatability requirement

A single successful attempt is not enough to declare a production-capable route.

After one full success on both roles for the exact same combination, rerun the exact pair once:

```text
spec-reviewer #1       PASS_PROVEN
regression-reviewer #1 PASS_PROVEN
spec-reviewer #2       PASS_PROVEN
regression-reviewer #2 PASS_PROVEN
```

The early regression smoke does not count.

Only after all four qualifying attempts pass under the same runtime/client/provider/model/prompt/schema/isolation/audit contract may the task announce:

```text
PASS_PROVEN: OpenCode X + provider/model
```

If either confirmation attempt fails, the route is not repeatable. Preserve the failing attempt and continue the matrix without an extra retry.

## Isolation requirements

Every alternate runtime probe must be reversible and isolated from production state.

Required behavior:

- use an ignored `.runtime/` subtree or OS temporary directory;
- install exact version-matched official runtime/client packages only there;
- never replace or mutate the global/production OpenCode installation;
- mechanically verify runtime and official client versions before each live attempt;
- point the repository/session directory at the actual Blackfire task worktree so the real reviewer definitions are used;
- use `OPENCODE_DB=:memory:` where safely supported, otherwise an explicitly task-local isolated state path;
- never fall back to the user's normal OpenCode database;
- disable candidate auto-update where supported;
- restore PATH/environment after each probe;
- keep all commands non-interactive;
- never commit temporary dependency contents, credentials, local state, or raw provider dumps.

Production `scripts/opencode_contract.ps1` remains authoritative for normal Scout/Gate and stays pinned to `1.18.31`.

## Phase 2 matrix stop rules

Stop immediately and return evidence to ChatGPT/user when any of these is true:

1. one stable route passes both reviewer roles twice each;
2. C1 and C2 are exhausted without a stable route;
3. continued probing would risk production state/isolation;
4. the next action would incur paid/API cost without explicit user authorization.

When C1 and C2 are exhausted, do not automatically test another version, source PR, dev build, model, or provider. A new matrix decision is required.

## Scope

In scope:

- maintain one bounded official structured-output compatibility probe;
- add version-native adapters only where required by C1/C2 official client surfaces;
- deterministic tests for matrix selection, package/runtime matching, lifecycle audit, structured-result normalization, taxonomy, isolation, and environment restoration;
- execute the frozen matrix under the actual production reviewer contracts;
- preserve bounded per-attempt evidence and update the compatibility matrix/evidence summary;
- recommend a future Gate route only after both roles and repeatability are proven.

Allowed change surfaces:

- `docs/tasks/opencode-structured-review-provider-compatibility/`
- `scripts/opencode_structured_review_probe.mjs` and minimal helper code
- `tests/workflow_scripts/` and the existing focused Python wrapper
- `.opencode/` only for diagnostic configuration when genuinely necessary; production reviewer semantics must not change
- package metadata only where needed for existing repository probe tooling; alternate runtime dependency contents stay local/ignored
- architecture docs only if a durable qualification rule must be documented.

## Non-goals

- fixing OpenCode upstream inside Blackfire;
- changing production OpenCode pin;
- changing normal Gate routing;
- changing reviewer step budgets/timeouts to manufacture success;
- changing prompt/schema per runtime or model;
- Markdown/prose/regex verdict fallback;
- broad provider/version benchmarking;
- automatic dev/beta/source-build probing;
- paid probes without explicit authorization;
- production/game behavior changes;
- merging/closing the blocked predecessor task inside this task.

## Deterministic verification requirements

Before live Phase 2 attempts, focused offline tests must cover at least:

- frozen matrix/runtime selection and rejection of unlisted versions;
- exact official runtime/client version matching;
- fixed prompt/schema construction;
- both production reviewer roles being discoverable/loadable under the candidate adapter;
- structured-result normalization for each implemented runtime adapter;
- no prose/Markdown/regex fallback;
- lifecycle audit trustworthy/untrustworthy cases;
- new Phase 2 taxonomy mapping;
- isolation and caller PATH/environment restoration;
- repeatability aggregation logic;
- preservation of the existing 1.18.31 path.

Live provider calls are evidence runs, not deterministic unit tests.

## Required evidence

Every fresh Phase 2 attempt must record:

- matrix candidate ID (`C1`/`C2`);
- exact CLI/runtime version;
- exact official client/SDK package + version;
- provider/model;
- reviewer role and whether attempt is `smoke`, `qualifying`, or `confirmation`;
- isolation method;
- lifecycle-audit source and whether it is trustworthy;
- required read/search occurrence;
- successful tool result;
- voluntary vs forced finalization and finish reason;
- exact official structured machine field used;
- structured result presence;
- schema validation;
- semantic validation;
- exact top-level classification;
- bounded/redacted diagnostic + subreason on failure.

Historical attempts are never overwritten.

## Acceptance criteria

1. Phase 1 `1.18.31` evidence remains preserved as `PASS_PROVEN = 0`.
2. Phase 2 uses the pre-frozen C1/C2 matrix and does not select versions reactively after each failure.
3. The exact same full spec-reviewer probe contract is applied across matrix runtimes, with only official version-native transport adaptation.
4. Each runtime receives the fixed early regression-reviewer compatibility smoke before full spec qualification.
5. New attempts use only the frozen seven-result taxonomy.
6. Attempt `PASS_PROVEN` requires required read/search, successful result, voluntary finalization, official structured result, valid schema, valid semantics, and trustworthy same-attempt lifecycle audit.
7. A public route-level `PASS_PROVEN: OpenCode X + provider/model` is declared only after the exact same combination passes both reviewer roles twice each.
8. Matrix exhaustion stops the task; no open-ended version/provider search occurs.
9. No paid probe executes without explicit user authorization.
10. No production pin/routing/reviewer semantics are changed.
11. No secrets, temporary runtimes, or unbounded raw provider data are committed.
12. Focused deterministic tests pass.
13. If a stable alternate route is proven, production migration is proposed as a separate follow-up task rather than performed here.

## Workflow state

This SPEC remains `Status: Final`.

The next local step is to synchronize this Final SPEC and `PHASE2_COMPATIBILITY_MATRIX.md`, then have the implementation writer update only the bounded probe/test/evidence surface needed for the frozen Phase 2 matrix. Do not begin live C1/C2 probes until the deterministic matrix/adapter/repeatability tests pass.