# Writer Model Benchmark

Purpose: collect small, comparable measurements from completed Writer tasks so model routing is based on observed task throughput and acceptance quality rather than intuition alone.

This is telemetry, not a task contract. ChatGPT maintains the table from Writer closeout reports plus tracked Gate/final-review evidence.

Rules:
- record real completed task runs only;
- use `unknown` when a model/tool cannot provide a value; never infer missing timing;
- durations are approximate and may overlap when the Writer cannot separate phases cleanly;
- `Outcome` is finalized by ChatGPT from tracked Gate evidence and final semantic review, not self-declared by the Writer;
- do not change routing policy from one sample; accumulate at least 5-10 representative tasks first.

| Task | Model | Total | Impl | Verify | Iterations | Outcome |
|---|---|---:|---:|---:|---|---|
| `gate-payload-robustness-v1` | Luna Light | ~49m26s | ~43m07s | ~6m | multiple | Harness 21/21; Gate PASS; final review pending scope cleanup |

## Writer closeout report

Every Writer should end with this exact compact block. Unknown values must be written as `unknown` rather than guessed.

```text
WRITER_BENCHMARK
Task: <task-id>
Model: <model + effort, if known>
Total: <duration or unknown>
Implementation: <duration to implementation commit or unknown>
Verification: <duration or unknown>
Iterations: <count / multiple / unknown>
Harness: <pass summary / N/A / unknown>
Gate: <PASS / BLOCK / INFRA_BLOCKED / not run>
Implementation commit: <sha or unknown>
Final artifacts commit: <sha / N/A / unknown>
END_WRITER_BENCHMARK
```

ChatGPT derives the final `Outcome` after reviewing GitHub evidence.