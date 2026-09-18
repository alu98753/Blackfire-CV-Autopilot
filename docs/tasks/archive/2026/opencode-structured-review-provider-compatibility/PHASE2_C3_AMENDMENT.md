# Phase 2 C3 Compatibility Amendment

Date: 2026-09-16
Status: Authorized continuation

## Why this amendment exists

The original frozen matrix (Control / C1 / C2) is exhausted, but follow-up upstream inspection found a materially different official transport surface that was not represented in that matrix:

- the released `@opencode-ai/sdk@1.18.31` package itself exports an official `./v2` client/server surface;
- its generated v2 types include `OutputFormatJsonSchema`, `UserMessage.format`, `StructuredOutputError`, and `AssistantMessage.structured`;
- its v2 server helper still launches the same `opencode serve` executable from PATH;
- therefore this is not a new OpenCode runtime version and does not require changing the production `1.18.31` pin.

This is a new transport hypothesis, not an open-ended version search.

## Survey evidence

At upstream tag `v1.18.31`, `packages/sdk/js/package.json` exports:

```text
./v2
./v2/client
./v2/server
./v2/types
```

The same tagged generated v2 types define:

```text
OutputFormatJsonSchema {
  type: "json_schema"
  schema: JsonSchema
  retryCount?: number
}

UserMessage.format?: OutputFormat
AssistantMessage.structured?: unknown
```

The tagged v2 server helper launches `opencode serve` and supports bounded startup timeout / AbortSignal. The tagged v2 client is an official generated client over the server API.

By contrast, the experimental `@opencode/client@2.0.2` / `@opencode/cli@2.0.2` line examined as C2 exposes a different session API whose `session.prompt` request does not carry the required JSON-Schema format field. C2 remains correctly fail-closed for that exact route.

## C3 candidate

Authorize exactly one additional matrix candidate:

```text
C3 runtime:          OpenCode CLI 1.18.31
C3 SDK package:      @opencode-ai/sdk@1.18.31
C3 transport:        official SDK v2 exports only
                     (@opencode-ai/sdk/v2 and/or its documented v2 client/server exports)
provider/model order:
  1. opencode/big-pickle
  2. opencode/mimo-v2.5-free
```

C3 is deliberately the same released production runtime, but a different official client/transport path from the Phase 1 control.

## Hypothesis

Phase 1 used the legacy 1.18.31 SDK surface and encountered the persisted `OutputFormatJsonSchema` session-message codec failure. C3 tests whether the official generated v2 transport can carry the same JSON-Schema request/result and audit lifecycle without that legacy decoder failure.

This is only a hypothesis until proven by deterministic adapter checks and live evidence.

## Invariants

All existing qualification invariants remain unchanged:

```text
read/search
-> successful tool result
-> voluntary finalization
-> official structured result present
-> schema valid
-> semantic invariant valid
-> trustworthy same-attempt lifecycle audit
-> repeatability confirmed
```

No Markdown/prose/regex/fenced-JSON fallback is authorized.

Production pin, normal Scout/Gate routing, reviewer contracts, prompt/schema, provider/model order, seven-result taxonomy, process isolation rules, and 4/4 repeatability requirement remain unchanged.

## C3 preflight requirements

Before any live provider request:

1. mechanically prove CLI `1.18.31` and SDK package `1.18.31`;
2. use the official SDK v2 export path, not the legacy Phase 1 client;
3. prove from installed/tagged API that the request accepts JSON-Schema format and that the official response/message schema exposes a machine structured-result field;
4. identify an authoritative v2 lifecycle source capable of proving tool call, successful tool settlement, finalization, and same-attempt structured result;
5. reuse the already-hardened runner-owned Windows process-tree cleanup;
6. add deterministic tests for the C3 adapter and for fail-closed lifecycle audit behavior.

If any required official surface cannot be established, classify C3 `FAIL_INFRASTRUCTURE` and stop without inventing a parser.

## C3 execution order

If deterministic preflight passes:

1. Big Pickle `regression-reviewer` smoke;
2. Big Pickle `spec-reviewer` qualification;
3. MiMo `spec-reviewer` only if Big Pickle spec is not `PASS_PROVEN`;
4. for any spec-pass route, same exact combination on full `regression-reviewer`;
5. if both roles pass once, run spec + regression confirmation once each.

Stable route still requires:

```text
spec #1 PASS_PROVEN
regression #1 PASS_PROVEN
spec #2 PASS_PROVEN
regression #2 PASS_PROVEN
```

No ad-hoc retry beyond this contract.

## Stop rule after C3

Stop when either:

- C3 proves a stable 4/4 route; or
- C3 is exhausted / fails closed.

Do not automatically add another version, dev build, PR build, provider, or model. Further expansion requires another explicit ChatGPT + user matrix decision.

## Production migration boundary

Even if C3 succeeds, this task does not change normal Gate routing. A separate follow-up task must decide whether production Gate should migrate from the legacy SDK surface to the official SDK v2 transport.