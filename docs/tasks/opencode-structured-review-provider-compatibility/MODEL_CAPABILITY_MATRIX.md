# Fresh Phase 1 compatibility matrix

This matrix records only fresh probes made for this task. It does not reproduce classifications from the predecessor task's historical matrix.

| OpenCode | SDK | Provider / model | Reviewer role | Read/search tool call | Successful tool result | Finalization | Structured output | Schema valid | Semantics valid | Classification |
| --- | --- | --- | --- | ---: | ---: | --- | ---: | ---: | ---: | --- |
| `1.18.31` | `1.18.31` | `opencode/big-pickle` | `spec-reviewer` | no | no | voluntary; `stop` | no | no | no | `FAIL_TOOL_CHOICE` |
| `1.18.31` | `1.18.31` | `opencode/mimo-v2.5-free` | `spec-reviewer` | no | no | voluntary; `stop` | no | no | no | `FAIL_TOOL_CHOICE` |

No candidate reached the second-role `regression-reviewer` check because neither first-role probe met the complete lifecycle. The Phase 1 result is `PASS_PROVEN = 0`; no reviewer route is recommended.
