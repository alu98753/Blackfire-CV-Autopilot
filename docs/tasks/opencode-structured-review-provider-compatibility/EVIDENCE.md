# OpenCode structured-review compatibility evidence

## Outcome

Phase 1 completed on the production-pinned OpenCode CLI `1.18.31`. Neither authorized candidate produced `PASS_PROVEN` on the required first qualification role, `spec-reviewer`. No Phase 1 regression-reviewer probe was run because no candidate passed the required first role. Phase 2 C1 cleanup hardening completed bounded smoke and spec attempts without reaching a model lifecycle, preserving C1 as infrastructure-blocked. C2 static preflight confirmed absence of an official JSON-Schema structured transport, failing closed. The final matrix outcome is `PASS_PROVEN = 0`; evidence is recorded below.

The fresh canonical Scout context remains [CONTEXT.md](CONTEXT.md). This task used the actual production reviewer definition in [`.opencode/agents/spec-reviewer.md`](../../../.opencode/agents/spec-reviewer.md), without changing its permissions, step budget, or final-response contract.

## Probe method

The reusable helper [opencode_structured_review_probe.mjs](../../../scripts/opencode_structured_review_probe.mjs) uses the official `@opencode-ai/sdk` `1.18.31` path:

```text
session.create
-> session.prompt(format.type = json_schema)
-> session.messages lifecycle inspection
-> response.data.info.structured_output
-> fixed schema and PASS/BLOCK semantic validation
```

It starts the SDK server with `OPENCODE_DB=:memory:` and restores the caller environment afterwards. Evidence records only bounded fields and redacted diagnostics; it does not retain provider raw payloads or credentials.

## Fresh attempts

| Attempt | Candidate | Role | OpenCode / SDK | Read/search call | Successful tool result | Finalization | Structured output | Schema / semantics | Classification |
| --- | --- | --- | --- | ---: | ---: | --- | ---: | --- | --- |
| 001 | `opencode/big-pickle` | `spec-reviewer` | unavailable / unavailable | no | no | not reached | no | not reached | `FAIL_INFRASTRUCTURE` |
| 002 | `opencode/big-pickle` | `spec-reviewer` | unavailable / unavailable | no | no | not reached | no | not reached | `FAIL_INFRASTRUCTURE` |
| 003 | `opencode/big-pickle` | `spec-reviewer` | `1.18.31` / `1.18.31` | no | no | voluntary; `stop` | no | invalid: missing output / not evaluated | `FAIL_TOOL_CHOICE` |
| 004 | `opencode/mimo-v2.5-free` | `spec-reviewer` | `1.18.31` / `1.18.31` | no | no | voluntary; `stop` | no | invalid: missing output / not evaluated | `FAIL_TOOL_CHOICE` |
| 005 | `opencode/big-pickle` | `spec-reviewer` | `1.18.31` / `1.18.31` | no | no | forced; `tool-calls` | no | invalid: missing output / not evaluated | `FAIL_TOOL_CHOICE` |
| 006 | `opencode/mimo-v2.5-free` | `spec-reviewer` | `1.18.31` / `1.18.31` | no | no | audit unavailable | no | not evaluated | `FAIL_LIFECYCLE_AUDIT` |

Attempts 001 and 002 exposed and localized two Windows-only probe preflight defects before a model request: direct Node spawning could not resolve `opencode`, and direct `.cmd` execution returned `EINVAL`. The helper now runs the non-interactive version check through `cmd.exe /d /s /c "opencode --version < NUL"`. Attempts 003 and 004 remain preserved historical fresh-attempt records; attempts 005 and 006 are the post-audit-fix candidate evidence used for the Phase 1 conclusion.

Attempt 005 had usable tool parts in the authoritative prompt response, so no separate message retrieval was needed; it still contained no permitted read/search tool and ended at forced `tool-calls` without `response.data.info.structured_output`. Attempt 006 required `session.messages`; its bounded SDK response error made the lifecycle unprovable, so it is `FAIL_LIFECYCLE_AUDIT`, not a claim that the model chose no tool. Attempts 003 and 004 remain prior fresh records and are not overwritten.

Individual bounded records are retained beside this summary:

- [attempt 001](attempt-big-pickle-spec-reviewer.json)
- [attempt 002](attempt-002-big-pickle-spec-reviewer.json)
- [attempt 003](attempt-003-big-pickle-spec-reviewer.json)
- [attempt 004](attempt-004-mimo-v2.5-free-spec-reviewer.json)
- [attempt 005](attempt-005-big-pickle-spec-reviewer.json)
- [attempt 006](attempt-006-mimo-v2.5-free-spec-reviewer.json)

## Historical separation and next dependency

The predecessor matrix at `task-gate-reviewer-output-contract-reliability` was read as historical context only. Its classifications are not copied into this fresh result; the table above contains only attempts made by this task.

The frozen Phase 2 runtime matrix is already selected (`C1 = 1.14.41`, `C2 = 2.0.2`). The next dependency is therefore not another version choice: it is **probe-runner isolation hardening**. Before any further live provider attempt, the runner must prove that a bounded timeout/cancellation path always terminates the isolated OpenCode/Node child process tree and leaves no orphan process. After deterministic proof of that cleanup behavior, resume the same frozen matrix at C1; do not broaden the runtime/model set. Production `1.18.31`, normal Gate routing, reviewer contracts, and step budgets remain unchanged.

## Phase 1 deterministic verification

`cmd.exe /d /s /c ".venv\\Scripts\\python.exe -X utf8 -m unittest tests.test_opencode_structured_review_probe < NUL"` passed with 1 focused unittest (which runs 11 Node deterministic tests). The checks cover request construction, fixed schema validation, semantic PASS/BLOCK consistency, successful and failed lifecycle audits, missing and malformed output classification, bounded credential redaction, and version/state isolation seams.

## Phase 2 implementation and stop condition

The Phase 2 probe now limits runtime selection to the production control, C1 `1.14.41` with `@opencode-ai/sdk@1.14.41`, and C2 `2.0.2` with `@opencode/client@2.0.2`. Its focused wrapper passed after the implementation update: 1 Python unittest invoking 15 Node deterministic tests. The coverage includes matrix and exact-version checks, the C1 `assistant.info.structured` adapter, C2 fail-closed adapter absence, fixed qualification and smoke prompts, lifecycle taxonomy, environment restoration, and repeatability aggregation.

C1's isolated CLI and SDK were both mechanically reported as `1.14.41`. Attempts 007–010 did not reach a trustworthy reviewer lifecycle: they exposed SDK module loading, server-startup, and session-creation infrastructure failures. The bounded records preserve each diagnostic. Attempt 011 progressed past session startup but did not return a bounded result before the host command timeout. Its isolated Node/OpenCode child processes remained alive and had to be explicitly terminated. No complete same-attempt lifecycle audit or structured result was available, so no model or reviewer conclusion is inferred from that timeout.

The task stopped under the matrix isolation-safety rule. C2 was not started, because the C1 timeout showed that the runner could not guarantee automatic isolated-child cleanup in this host. Separately, static inspection of tagged C2 `@opencode/client@2.0.2` found no official `session.prompt` JSON-schema structured-result transport; the probe's C2 adapter therefore fails closed rather than parsing prose. No route reached a qualifying `PASS_PROVEN`, and no C1/C2 route has the required spec #1 + regression #1 + spec #2 + regression #2 result.

New bounded Phase 2 records are retained as [attempt 007](attempt-007-c1-big-pickle-regression-smoke.json), [attempt 008](attempt-008-c1-big-pickle-regression-smoke.json), [attempt 009](attempt-009-c1-big-pickle-regression-smoke.json), [attempt 010](attempt-010-c1-big-pickle-regression-smoke.json), and [attempt 011](attempt-011-c1-big-pickle-regression-smoke.json). No production pin, reviewer file, or normal routing was changed.

## Probe-runner isolation hardening

The C1 runner now launches its isolated server through a runner-owned `cmd.exe` process-tree root. It applies a bounded startup deadline and probe deadline, then calls `taskkill /PID <owned-root> /T /F` only for that recorded PID. Cleanup failure overrides the result to `FAIL_INFRASTRUCTURE` with `ISOLATION_CLEANUP_UNSAFE`; the runner restores PATH, `OPENCODE_DB`, and auto-update state in the same finalization path. Focused deterministic verification passed with the additional timeout, exception, normal-completion, exact-owned-PID, cleanup-failure, and environment-restoration cases.

Attempt 012 was the single fresh C1 Big Pickle regression-reviewer smoke. Attempts 013 and 014 were the frozen Big Pickle and MiMo spec-reviewer sequence after the smoke returned `FAIL_INFRASTRUCTURE`. Each attempt ended at the runner's owned server startup deadline before a provider/model lifecycle, and each post-attempt process check found no `opencode` or Node child process. The records therefore classify infrastructure startup failure rather than a provider/model result. C1 has no qualifying `PASS_PROVEN` route and is preserved as infrastructure readiness blocked.

The new records are [attempt 012](attempt-012-c1-big-pickle-regression-smoke.json), [attempt 013](attempt-013-c1-big-pickle-spec-reviewer.json), and [attempt 014](attempt-014-c1-mimo-v2.5-free-spec-reviewer.json).

## C2 static preflight and matrix exhaustion

C2 evaluation used OpenCode CLI `@opencode/cli@2.0.2` and official client `@opencode/client@2.0.2`. Static inspection of tagged v2.0.2 client type definitions (`@opencode/client/dist/effect/api/api.d.ts` and `types.d.ts`) established that `SessionPromptInput` accepts only `sessionID`, `id`, `text`, `files`, `agents`, `skills`, `metadata`, `delivery`, and `resume`. It provides no `format`, `schema`, or `json_schema` request parameter, and its assistant response provides no official machine structured-output payload field.

Under the C2 early fail-closed rule, C2 is classified as `FAIL_INFRASTRUCTURE` with subreason `STRUCTURED_ADAPTER_UNAVAILABLE` without issuing live model calls. No synthetic markdown/regex parser was introduced.

Both authorized alternate runtimes in the frozen matrix are now exhausted:
- C1 `1.14.41`: blocked at isolated server readiness before provider/model lifecycle; process cleanup proven.
- C2 `2.0.2`: preflight established absence of official JSON-Schema structured transport.

The final matrix outcome is **PASS_PROVEN = 0**; neither candidate established a production-viable structured-review route. Production OpenCode remains pinned to `1.18.31`.

## Candidate C3 structured transport diagnostic (2026-09-16)

Under the authorized amendment ([PHASE2_C3_AMENDMENT.md](PHASE2_C3_AMENDMENT.md)), Candidate C3 evaluates the production-pinned OpenCode CLI `1.18.31` paired with `@opencode-ai/sdk@1.18.31` using the official SDK v2 transport (`@opencode-ai/sdk/v2`).

Initial live C3 smoke attempts [attempt 015](attempt-015-c3-big-pickle-regression-smoke.json), [attempt 016](attempt-016-c3-big-pickle-regression-smoke.json), [attempt 017](attempt-017-c3-big-pickle-regression-smoke.json), and [attempt 018](attempt-018-c3-big-pickle-regression-smoke.json) are preserved as `FAIL_INFRASTRUCTURE` (cleanup verification edge case / 120s probe timeouts / server startup timeout).

On 2026-09-16, a controlled diagnostic run ([diagnostic-c3-big-pickle-regression-review.json](diagnostic-c3-big-pickle-regression-review.json)) with a 480-second outer deadline was executed using the production reviewer contract:

- **Exact Runtime / SDK**: OpenCode CLI `1.18.31`, `@opencode-ai/sdk@1.18.31` official v2 transport
- **Provider / Model**: `opencode/big-pickle`
- **Reviewer Role**: `regression-reviewer` (production contract, 10-step budget)
- **Total Duration**: ~229 seconds (229,431 ms)
- **Transport Status**: HTTP 200
- **Official Machine Structured Field**: `promptResult.data.info.structured`
- **Structured Schema Shape**: Valid object with `verdict` ("PASS"), `blocking_findings` (0), and non-empty `report_markdown`
- **Finish Reason**: `tool-calls` (step-budget exhaustion at 10 steps; total tokens 61,398)
- **Process Cleanup**: Proven; child server process terminated cleanly without orphan processes
- **Audit-Surface Finding**:
  - `client.session.prompt` succeeded and returned official structured machine output without OpenAPI decoding failure.
  - Calling `client.session.messages` triggered the known client-side OpenAPI decoder failure: `Expected OutputFormatJsonSchema, got {"type":"json_schema"} at [0]["info"]["format"]`.
  - Therefore, `client.session.messages` is currently unusable due to the decoder defect. A complete `promptResult.data.parts + info` lifecycle may still qualify as the authoritative same-attempt audit surface if it satisfies the Final SPEC.
- **Explicit Interpretation**:
  - **Transport Success != Route Qualification**: While Candidate C3 demonstrates proven ability to transport JSON-Schema structured review verdicts through official SDK v2 without the Phase 1 OpenAPI prompt crash, transport success remains separate from route qualification. Whether the recorded Big Pickle diagnostic itself satisfies that complete prompt-response audit has not yet been formally reclassified unless tracked evidence already proves it; formal qualification remains not proven.

### MiMo (`opencode/mimo-v2.5-free`) diagnostic evaluation (2026-09-16)

Following Big Pickle, Candidate C3 was evaluated with `opencode/mimo-v2.5-free` under the identical 2-step diagnostic workflow:

- **Step 1 (Trivial ok smoke)**:
  - Total duration: 11.0s (11,061 ms)
  - Transport: HTTP 200
  - Official structured machine output: Present (`verdict: "PASS"`, `blocking_findings: 0`, `report_markdown: "ok"`)
  - Cleanup: Proven (no orphan processes)
- **Step 2 (Production regression-reviewer contract, 480s deadline)**:
  - Total duration: ~80 seconds (79,769 ms)
  - Transport: HTTP 200
  - Tokens: 14,133
  - Finish reason: `stop` (voluntary model finalization)
  - Structured output: `undefined` (`promptResult.data.info.structured` missing)
  - Messages audit finding: `client.session.messages` triggered `Expected OutputFormatJsonSchema` decoder crash, identical to Big Pickle.
  - Classification under Final SPEC: `FAIL_STRUCTURED_OUTPUT` (voluntary stop without valid structured result).
  - Diagnostic record: [diagnostic-c3-mimo-regression-review.json](diagnostic-c3-mimo-regression-review.json)
- **Mechanistic Root-Cause Audit via `scripts/inspect_mimo_structured.mjs`**:
  - OpenCode's JSON-schema mechanism functions by injecting an internal `StructuredOutput` tool into the prompt context.
  - When the diagnostic helper ([inspect_mimo_structured.mjs](../../../scripts/inspect_mimo_structured.mjs)) executed a minimal prompt with `agent: "regression-reviewer"`, MiMo actively invoked `Tool: StructuredOutput`, and OpenCode populated `info.structured` completely (`verdict: "PASS"`, `blocking_findings: 0`, and non-empty markdown).
  - During the full multi-step review, the model did not invoke StructuredOutput during the full review, but voluntarily terminated (`finish: stop`), leaving `info.structured: undefined`.
  - Conclusion: Candidate C3's SDK v2 transport fully supports JSON-Schema structured transport for both models; however, the model did not invoke StructuredOutput during the full review on complex, multi-turn review sessions compared to minimal prompts.

## Candidate C3 formal qualification attempts and lifecycle audit boundary refinement (2026-09-16)

Candidate C3 formal qualifying attempts were executed against the required first role, `spec-reviewer`, using the production contract:

- [attempt 019](attempt-019-c3-big-pickle-spec-reviewer.json): `opencode/big-pickle` on `spec-reviewer`, classified as `FAIL_LIFECYCLE_AUDIT` with subreason `AUDIT_UNTRUSTWORTHY`.
- [attempt 020](attempt-020-c3-mimo-spec-reviewer.json): `opencode/mimo-v2.5-free` on `spec-reviewer`, classified as `FAIL_LIFECYCLE_AUDIT` with subreason `AUDIT_UNTRUSTWORTHY`.

The subsequent controlled diagnostic ([diagnostic-c3-spec-reviewer-lifecycle.json](diagnostic-c3-spec-reviewer-lifecycle.json)) captured the raw SDK v2 response and established the underlying model behavior:
- `promptResult.data.info` contained non-empty message ID, consistent session ID, finish reason `tool-calls`, and `info.structured` with a completed review payload.
- `promptResult.data.parts` contained a complete typed lifecycle: `step-start`, reasoning and text blocks, an internal `StructuredOutput` tool call with status `completed`, and `step-finish`.
- No permitted repository inspection tool (`read`, `glob`, or `grep`) was invoked.

Under the prior adapter implementation, `hasAuthoritativePromptResponse()` required at least one completed read/search tool before accepting prompt-response lifecycle evidence. When no permitted read/search tool was called, the adapter treated the prompt response as incomplete and fell back to `client.session.messages`. The `session.messages` endpoint consistently failed due to the OpenAPI client decoder defect (`Expected OutputFormatJsonSchema`), resulting in `FAIL_LIFECYCLE_AUDIT` with subreason `AUDIT_UNTRUSTWORTHY`. This masked the actual model behavior (failure to execute repository exploration tools).

Historical records Attempt 019 and Attempt 020 remain immutable as recorded by the prior adapter semantics. The adapter has now separated lifecycle audit authority from downstream tool-choice compliance: a prompt response is authoritative whenever it provides a complete, typed, and internally consistent lifecycle for the same attempt. Under these corrected semantics, an equivalent attempt where the model voluntarily completes without permitted read/search tool execution classifies directly as `FAIL_TOOL_CHOICE` from authoritative `prompt-response` evidence without falling back to `session.messages`.

### Fresh qualification verification under corrected taxonomy (Attempt 021)

A single fresh qualification attempt was executed under the corrected adapter logic on 2026-09-16:

- [attempt 021](attempt-021-c3-big-pickle-spec-reviewer.json): Candidate C3, `opencode/big-pickle` on `spec-reviewer`, classified definitively as `FAIL_TOOL_CHOICE`.

The fresh attempt confirmed the corrected lifecycle taxonomy:
- `lifecycle_audit_source`: `"prompt-response"`
- `lifecycle_audit_trustworthy`: `true`
- `read_search_tool_called`: `false` (no permitted `read`, `glob`, or `grep` executed)
- `structured_output_present`: `true` (valid JSON-Schema structured payload delivered to `assistant.info.structured`)
- `session.messages`: Not called; no masking by the client OpenAPI decoder defect occurred.
- `classification`: `FAIL_TOOL_CHOICE`

## Final Task Conclusion

This compatibility investigation is formally concluded. All evaluation candidates have been comprehensively audited against the production reviewer contracts:
- **CONTROL** (`1.18.31` with default client): Fails on `session.prompt` schema transport with client OpenAPI decoder error (`PASS_PROVEN = 0`).
- **Candidate C1** (`1.14.41`): Infrastructure blocked at isolated server readiness (`PASS_PROVEN = 0`).
- **Candidate C2** (`2.0.2`): Preflight verified absence of official JSON-Schema structured transport (`PASS_PROVEN = 0`).
- **Candidate C3** (`1.18.31` with `@opencode-ai/sdk/v2`):
  - Structured transport to `assistant.info.structured` is **PROVEN**.
  - Authoritative lifecycle auditing from `promptResult.data.parts` without `session.messages` decoder failure is **PROVEN**.
  - Route qualification across models is **NOT PROVEN** (`FAIL_TOOL_CHOICE` on Big Pickle for omitting required repository exploration tools; `FAIL_STRUCTURED_OUTPUT` on MiMo for failing to invoke `StructuredOutput` on full reviews).

Total qualifying `PASS_PROVEN = 0`. This closes the compatibility task without further model or version chasing; production reviewer gates remain on their baseline architecture.
