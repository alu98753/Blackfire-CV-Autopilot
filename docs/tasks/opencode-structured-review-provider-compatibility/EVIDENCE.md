# OpenCode structured-review compatibility evidence

## Outcome

Phase 1 completed on the production-pinned OpenCode CLI `1.18.31`. Neither authorized candidate produced `PASS_PROVEN` on the required first qualification role, `spec-reviewer`. No Phase 1 regression-reviewer probe was run because no candidate passed the required first role. Phase 2 C1 cleanup hardening later completed bounded smoke and spec attempts without a qualifying lifecycle; its evidence is recorded below.

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

Attempt 012 was the single fresh C1 Big Pickle regression-reviewer smoke. Attempts 013 and 014 were the frozen Big Pickle and MiMo spec-reviewer sequence after the smoke returned `FAIL_INFRASTRUCTURE`. Each attempt ended at the runner's owned server startup deadline before a provider/model lifecycle, and each post-attempt process check found no `opencode` or Node child process. The records therefore classify infrastructure startup failure rather than a provider/model result. C1 has no qualifying `PASS_PROVEN` route. C2 was not started under the explicit execution limit for this hardening task.

The new records are [attempt 012](attempt-012-c1-big-pickle-regression-smoke.json), [attempt 013](attempt-013-c1-big-pickle-spec-reviewer.json), and [attempt 014](attempt-014-c1-mimo-v2.5-free-spec-reviewer.json).
