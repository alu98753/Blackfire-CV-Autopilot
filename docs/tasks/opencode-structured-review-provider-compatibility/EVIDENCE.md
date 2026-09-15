# OpenCode structured-review compatibility evidence

## Outcome

Phase 1 completed on the production-pinned OpenCode CLI `1.18.31`. Neither authorized candidate produced `PASS_PROVEN` on the required first qualification role, `spec-reviewer`. The task result is **(c) no authorized viable route proven**. No regression-reviewer probe was run because no candidate passed the required first role, and no Phase 2 version probe was started.

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

Attempts 001 and 002 exposed and localized two Windows-only probe preflight defects before a model request: direct Node spawning could not resolve `opencode`, and direct `.cmd` execution returned `EINVAL`. The helper now runs the non-interactive version check through `cmd.exe /d /s /c "opencode --version < NUL"`. Attempts 003 and 004 are the fresh candidate evidence used for the Phase 1 conclusion.

For attempts 003 and 004, the models reached a completed assistant response (`finish: stop`) but did not perform the prompt-required repository read/search action. The probe deliberately assigns `FAIL_TOOL_CHOICE` before inspecting missing structured output because a schema-valid response without the required lifecycle cannot qualify. Neither attempt produced `response.data.info.structured_output`.

Individual bounded records are retained beside this summary:

- [attempt 001](attempt-big-pickle-spec-reviewer.json)
- [attempt 002](attempt-002-big-pickle-spec-reviewer.json)
- [attempt 003](attempt-003-big-pickle-spec-reviewer.json)
- [attempt 004](attempt-004-mimo-v2.5-free-spec-reviewer.json)

## Historical separation and next dependency

The predecessor matrix at `task-gate-reviewer-output-contract-reliability` was read as historical context only. Its classifications are not copied into this fresh result; the table above contains only attempts made by this task.

The next dependency is a deliberately selected isolated OpenCode version candidate, decided by ChatGPT and the user. That work must retain the same production reviewer contract, model/schema lifecycle, bounded evidence, and isolated state. It must not change the production `1.18.31` pin or normal Gate routing before a candidate passes both reviewer roles.

## Deterministic verification

`cmd.exe /d /s /c "node --test tests\\workflow_scripts\\opencode_structured_review_probe.test.mjs < NUL"` passed with 8 tests. The focused checks cover request construction, fixed schema validation, semantic PASS/BLOCK consistency, missing and malformed output classification, bounded credential redaction, and version/state isolation seams.
