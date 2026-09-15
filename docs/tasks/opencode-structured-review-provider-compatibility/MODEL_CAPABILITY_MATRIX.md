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
