# OpenCode Structured Review Compatibility Baseline

Status: Verified baseline
Date: 2026-09-16

## Purpose

This document preserves the durable compatibility result from `opencode-structured-review-provider-compatibility` so future implementation and review work does not reopen version/provider exploration without a concrete new reason.

## Verified structured-review transport

The following exact stack has been live-tested successfully on Windows:

```text
OpenCode 1.18.31
+ @opencode-ai/sdk 1.18.31 / official v2 transport
+ opencode/big-pickle
        ↓
JSON-Schema request
        ↓
OpenCode StructuredOutput tool
        ↓
HTTP 200
        ↓
promptResult.data.info.structured
        ↓
valid structured object
```

The structured object uses the project review contract:

```json
{
  "verdict": "PASS | BLOCK",
  "blocking_findings": 0,
  "report_markdown": "..."
}
```

Evidence:
- [`EVIDENCE.md`](../tasks/opencode-structured-review-provider-compatibility/EVIDENCE.md)
- [`MODEL_CAPABILITY_MATRIX.md`](../tasks/opencode-structured-review-provider-compatibility/MODEL_CAPABILITY_MATRIX.md)
- [`attempt-021-c3-big-pickle-spec-reviewer.json`](../tasks/opencode-structured-review-provider-compatibility/attempt-021-c3-big-pickle-spec-reviewer.json)
- [`diagnostic-c3-spec-reviewer-lifecycle.json`](../tasks/opencode-structured-review-provider-compatibility/diagnostic-c3-spec-reviewer-lifecycle.json)
- [`diagnostic-c3-big-pickle-regression-review.json`](../tasks/opencode-structured-review-provider-compatibility/diagnostic-c3-big-pickle-regression-review.json)

## Lifecycle audit baseline

For the SDK v2 route, `promptResult.data.parts` is a verified typed same-attempt lifecycle surface. Tool parts use `part.tool` and `part.state.status`; completed tool settlement is observable as `state.status == "completed"`. The prompt response can therefore be audited directly without requiring `client.session.messages` when it contains a complete typed lifecycle.

`client.session.messages` remains affected by the `OutputFormatJsonSchema` decoder defect for this route and must not be treated as the preferred lifecycle source when the prompt response is already authoritative.

## Qualification result

Transport compatibility is **PROVEN**, but the current free-model reviewer route is **NOT formally qualified** (`PASS_PROVEN = 0`):

- `opencode/big-pickle` on `spec-reviewer` can emit valid structured output without executing the required repository `read` / `glob` / `grep`, producing `FAIL_TOOL_CHOICE`.
- `opencode/mimo-v2.5-free` demonstrated structured-output capability on minimal prompts but omitted `StructuredOutput` on a full complex review, producing `FAIL_STRUCTURED_OUTPUT`.

This is a reviewer/context-acquisition reliability limitation, not evidence that the verified SDK v2 structured transport is broken.

## Version policy

Production OpenCode remains pinned to **1.18.31**.

Do **not** resume adjacent-version guessing or migrate OpenCode solely to solve the already-verified structured transport problem. A version change requires a new concrete incompatibility, security/maintenance requirement, or an explicitly approved task with fresh evidence that the current baseline no longer satisfies the needed contract.

Future reviewer infrastructure should build on this verified baseline first. The next architectural problem is reducing model-owned repository discovery while preserving bounded independent verification and semantic review authority.
