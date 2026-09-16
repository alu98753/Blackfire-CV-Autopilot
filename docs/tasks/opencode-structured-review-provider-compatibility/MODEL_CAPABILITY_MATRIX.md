# Fresh Phase 1 compatibility matrix

This matrix records only fresh probes made for this task. It does not reproduce classifications from the predecessor task's historical matrix.

| OpenCode | SDK | Provider / model | Reviewer role | Read/search tool call | Successful tool result | Finalization | Structured output | Schema valid | Semantics valid | Classification |
| --- | --- | --- | --- | ---: | ---: | --- | ---: | ---: | ---: | --- |
| `1.18.31` | `1.18.31` | `opencode/big-pickle` | `spec-reviewer` | no | no | voluntary; `stop` | no | no | no | `FAIL_TOOL_CHOICE` |
| `1.18.31` | `1.18.31` | `opencode/mimo-v2.5-free` | `spec-reviewer` | no | no | voluntary; `stop` | no | no | no | `FAIL_TOOL_CHOICE` |
| `1.18.31` | `1.18.31` | `opencode/big-pickle` | `spec-reviewer` | no | no | forced; `tool-calls` | no | no | no | `FAIL_TOOL_CHOICE` |
| `1.18.31` | `1.18.31` | `opencode/mimo-v2.5-free` | `spec-reviewer` | unproven | unproven | audit failed | no | not evaluated | not evaluated | `FAIL_LIFECYCLE_AUDIT` |

The first two rows are attempts 003 and 004; the latter two are the post-audit-fix attempts 005 and 006. No candidate reached the second-role `regression-reviewer` check because neither first-role probe met the complete lifecycle. The Phase 1 result is `PASS_PROVEN = 0`; no reviewer route is recommended.

## Phase 2 bounded execution

| Candidate | OpenCode | Official client | Provider / model | Reviewer role | Attempt kind | Lifecycle result | Classification |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `C1` | `1.14.41` | `@opencode-ai/sdk@1.14.41` | `opencode/big-pickle` | `regression-reviewer` | smoke | no trustworthy lifecycle | `FAIL_INFRASTRUCTURE` |
| `C1` | `1.14.41` | `@opencode-ai/sdk@1.14.41` | `opencode/big-pickle` | `regression-reviewer` | smoke | owned server startup timeout; cleanup proven | `FAIL_INFRASTRUCTURE` |
| `C1` | `1.14.41` | `@opencode-ai/sdk@1.14.41` | `opencode/big-pickle` | `spec-reviewer` | qualifying | owned server startup timeout; cleanup proven | `FAIL_INFRASTRUCTURE` |
| `C1` | `1.14.41` | `@opencode-ai/sdk@1.14.41` | `opencode/mimo-v2.5-free` | `spec-reviewer` | qualifying | owned server startup timeout; cleanup proven | `FAIL_INFRASTRUCTURE` |
| `C2` | `2.0.2` | `@opencode/client@2.0.2` | `opencode/big-pickle` | `regression-reviewer` | preflight | no official structured-output transport | `FAIL_INFRASTRUCTURE` |

Attempts 007–010 ended before a reviewer lifecycle was available. Attempt 011 reached the host timeout without a bounded result and left isolated child processes that required termination. The matrix stopped for isolation safety; C2 was not started. These records do not establish a provider/model capability result.

After runner hardening, attempts 012–014 each terminated their recorded isolated process tree without an observed orphan process. They still did not reach a reviewer lifecycle because the C1 server did not announce readiness before the owned startup deadline. C1 is preserved as infrastructure-blocked without a provider/model conclusion.

C2 (`2.0.2` with `@opencode/client@2.0.2`) static preflight verified from tagged source and API declarations that `session.prompt` has no JSON-Schema structured-output transport or machine result surface. Under the early fail-closed rule, C2 is classified as `FAIL_INFRASTRUCTURE` (subreason: `STRUCTURED_ADAPTER_UNAVAILABLE`) without live model calls. Both frozen alternate runtimes (C1 and C2) are now exhausted; the matrix outcome is `PASS_PROVEN = 0`.

## Candidate C3 evaluation and qualification outcome

| Candidate | OpenCode | Official client / transport | Provider / model | Reviewer role | Evaluation kind | Transport capability | Formal qualification | Status / Blocker |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `C3` | `1.18.31` | `@opencode-ai/sdk@1.18.31` (SDK v2) | `opencode/big-pickle` | `regression-reviewer` | diagnostic (480s) | PROVEN (HTTP 200, `info.structured`) | NOT PROVEN | Completed with `finish: tool-calls`; `session.messages` is unusable due to the decoder defect |
| `C3` | `1.18.31` | `@opencode-ai/sdk@1.18.31` (SDK v2) | `opencode/mimo-v2.5-free` | `regression-reviewer` | diagnostic (480s) | PROVEN (HTTP 200) | NOT PROVEN | Voluntarily stopped (`finish: stop`), but the model did not invoke StructuredOutput during the full review (`info.structured = undefined`); classifies as `FAIL_STRUCTURED_OUTPUT` |
| `C3` | `1.18.31` | `@opencode-ai/sdk@1.18.31` (SDK v2) | `opencode/big-pickle` | `spec-reviewer` | qualifying (attempt 021) | PROVEN (HTTP 200, `info.structured`) | NOT PROVEN | Authoritative prompt response; model omitted read/glob/grep repository tools; classifies as `FAIL_TOOL_CHOICE` |

- **Transport / Structured-output Capability**: **PROVEN**. Candidate C3 successfully completes JSON-Schema structured transport through official `@opencode-ai/sdk/v2` to `assistant.info.structured` without triggering the Phase 1 OpenAPI prompt crash (both Big Pickle and MiMo successfully returned structured output on the minimal prompt).
- **Lifecycle Audit Surface**: **PROVEN**. Prompt response parts (`promptResult.data.parts`) provide an authoritative, typed lifecycle audit source directly from the prompt response, bypassing the client-side `session.messages` OpenAPI decoder defect.
- **Formal Route Qualification**: **NOT PROVEN (`PASS_PROVEN = 0`)**.
  - On the mandatory first role, `spec-reviewer`, `opencode/big-pickle` directly finalized with structured output without executing any repository exploration tools (`read`, `glob`, `grep`), classifying as `FAIL_TOOL_CHOICE`.
  - On complex review sessions, `opencode/mimo-v2.5-free` voluntarily finalized without emitting structured output (`FAIL_STRUCTURED_OUTPUT`).
- **Matrix Exhaustion & Task Closeout**:
  - `CONTROL` (1.18.31 default): Blocked by client OpenAPI decoder crash on `session.prompt` format schema.
  - `C1` (1.14.41): Blocked at isolated server startup readiness.
  - `C2` (2.0.2): Fails closed due to absence of official JSON-Schema transport in `@opencode/client`.
  - `C3` (1.18.31 + SDK v2): Transport and lifecycle auditing proven; model route qualification failed (`PASS_PROVEN = 0`).
  - The compatibility task is converged and closed without further model or version chasing.
