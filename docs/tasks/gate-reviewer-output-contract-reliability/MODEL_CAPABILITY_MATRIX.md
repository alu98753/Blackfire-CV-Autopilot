# OpenCode Reviewer Model Capability Matrix

Diagnostic census for pinned OpenCode 1.18.31. The local selectable set was
enumerated with `opencode models opencode --verbose` under
`OPENCODE_DB=:memory:`. Metadata capability flags are taken from the pinned
runtime model catalog; a missing `structured_output` flag is not treated as
support.

| Candidate | Local status | Tool call | Structured output metadata | Free | Live probe | Finish | Structured output returned | Classification | Evidence |
| --- | --- | ---: | ---: | ---: | --- | --- | ---: | --- | --- |
| `opencode/big-pickle` | active | true | missing | yes | existing | `tool-calls` | no | `FAIL_FINALIZATION` | Repeated Gate runs ended without a final structured response. |
| `opencode/ling-3.0-flash-fin-free` | active | true | false/missing | yes | not run | n/a | n/a | `METADATA_REJECTED` | Not eligible for probe. |
| `opencode/mimo-v2.5-free` | active | true | missing | yes | existing | `tool-calls` | no | `FAIL_FINALIZATION` | Bounded adapter probe ended with `finish: "tool-calls"`. |
| `opencode/muse-spark-1.2-contributor-free` | active | true | true | yes | 1 probe | n/a; HTTP 400 | no | `FAIL_TOOL_CHOICE` | Provider returned: only `"auto"` is supported for `tool_choice`. |
| `opencode/muse-spark-1.3-contributor-free` | active | true | true | yes | existing | n/a; HTTP 400 | no | `FAIL_TOOL_CHOICE` | Provider rejects the tool-choice mode used by the structured flow. |
| `opencode/nemotron-3-ultra-free` | active | true | missing | yes | not run | n/a | n/a | `METADATA_REJECTED` | Not eligible for probe. |
| `opencode/nemotron-3.5-lightning-free` | active | true | true | yes | existing | n/a; fetch failure | no | `FAIL_TRANSPORT` | Session prompt failed after approximately 312 seconds; retain as currently unreliable, not permanently incapable. |
| `opencode/qwen3-coder-next` | not locally selectable | unknown | unknown | unknown | not run | n/a | n/a | `NOT_LOCALLY_AVAILABLE` | Not present in the current local `opencode` model listing. |
| `opencode/kimi-k2.5` | not locally selectable | unknown | unknown | unknown | not run | n/a | n/a | `NOT_LOCALLY_AVAILABLE` | Not present in the current local `opencode` model listing. |
| `opencode/kimi-k3` | not locally selectable | unknown | unknown | unknown | not run | n/a | n/a | `NOT_LOCALLY_AVAILABLE` | Not present in the current local `opencode` model listing. |
| `opencode/minimax-m2.5-free` | not locally selectable | unknown | unknown | unknown | not run | n/a | n/a | `NOT_LOCALLY_AVAILABLE` | Not present in the current local `opencode` model listing. |
| `opencode/glm-5.3-flash` | not locally selectable | unknown | unknown | unknown | not run | n/a | n/a | `NOT_LOCALLY_AVAILABLE` | Not present in the current local `opencode` model listing. |

## Permission A/B probe

Model: `opencode/mimo-v2.5-free`

| Group | Reviewer permissions | Result |
| --- | --- | --- |
| A | Current `spec-reviewer` permissions with wildcard `"*"` deny | `finish="tool-calls"`; `structured_output` missing |
| B | Temporary otherwise-identical reviewer agent with explicit `StructuredOutput` allow added after the wildcard deny | `finish="tool-calls"`; `structured_output` missing |

Both groups used the identical model, prompt, JSON schema, required read/tool
interaction, structured adapter, and `OPENCODE_DB=:memory:` isolation. Neither
group produced an HTTP/API error. Explicitly allowing `StructuredOutput` did
not change the result; the wildcard-deny permission hypothesis is therefore
not supported as the root cause of the MiMo finalization failure.

## Proven viable Gate reviewers

None. No currently tested OpenCode 1.18.31 candidate satisfies the complete
Gate contract: tool call, successful tool return, voluntary final assistant
turn, and valid JSON-Schema `structured_output`.

## Known incompatible reviewers

- `big-pickle` and `mimo-v2.5-free`: finalization failure; both ended at
  `finish: "tool-calls"` without structured output.
- `muse-spark-1.2-contributor-free` and `muse-spark-1.3-contributor-free`:
  provider tool-choice incompatibility (HTTP 400; only `auto` is supported).
- `nemotron-3.5-lightning-free`: current live transport/fetch instability
  during `session.prompt`; this is not classified as permanent incapability.

## Unprobed potentially viable reviewers

No locally selectable candidate remained both metadata-eligible and untested.
The requested Qwen3-Coder-Next, Kimi K2.5/K3, MiniMax M2.5, and GLM-5.3-Flash
identifiers were not present in the current local OpenCode selectable list.
They were not probed because availability through this pinned installation
was not established and no paid API usage was authorized.

## Routing recommendation

No safe routing currently exists. Do not modify `models.review` based on this
census. The next action should be one of:

- evaluate an authenticated/paid structured-output-capable provider;
- test a newer OpenCode version in a separate compatibility task; or
- remain infrastructure-blocked until a candidate passes this complete probe.

Historical free-form Gate PASS results are recorded only as historical
evidence elsewhere and do not prove this JSON-Schema contract.

## Current task status

- Project-side structured reviewer transport and validation implementation is complete enough for compatibility testing.
- No tested OpenCode 1.18.31 reviewer candidate has achieved `PASS_PROVEN`.
- There is currently no safe `models.review` routing.
- Final acceptance requiring a fresh independent real Gate PASS remains unmet.
- The task is blocked by OpenCode/provider/model structured-review compatibility.
- Production workflow semantics must not be weakened to work around this.
- This branch must not be merged as a completed task until a `PASS_PROVEN` reviewer route exists.

## Follow-up dependency

Proposed follow-up task: `opencode-structured-review-provider-compatibility`

Its responsibility is to identify a proven combination of OpenCode version,
provider, model, and structured-output/tool-call behavior that successfully
completes:

```text
tool call
-> tool result
-> final assistant turn
-> valid JSON-Schema structured_output
```
