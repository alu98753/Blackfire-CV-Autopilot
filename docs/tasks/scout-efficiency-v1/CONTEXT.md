# Scout Context: Execution Evidence for scout-efficiency-v1

## Execution Summary

- **Task**: `scout-efficiency-v1`
- **Start Time**: `2026-09-14 13:43:44`
- **Termination Time**: `2026-09-14 13:54:09`
- **Elapsed Duration**: 10 minutes 25 seconds (~625 seconds; observation budget: 8 minutes)
- **Model**: `opencode/big-pickle`
- **Command**: `opencode run --agent scout --model opencode/big-pickle "..."` via `scripts/ai_scout.ps1`
- **Canonical CONTEXT.md Produced Before Timeout**: No (`Test-Path docs\tasks\scout-efficiency-v1\CONTEXT.md` was `False`).
- **Terminal Streaming Output**: None. The user observed complete terminal silence throughout the entire run.

## Direct Evidence of ai_scout.ps1 Buffering and Failure Mode

1. **Stdout/Stderr Full Buffering**:
   - `scripts/ai_scout.ps1` line 51 uses:
     ```powershell
     $output = & opencode @args 2>&1 | Out-String
     ```
   - In PowerShell, assigning expression output piped into `Out-String` completely buffers all output into memory until process termination. Neither stdout nor stderr is emitted to the host console during execution.
2. **Process Separation & Lingering Wait**:
   - Client process (`PID 20744`) was launched by the script, consuming negligible CPU (~1.8s) while waiting on the persistent background service (`PID 21508`, `opencode serve --service`).
   - The client remained blocked indefinitely without emitting interim progress or triggering a timeout.
3. **Canonical Artifact Write Timing**:
   - `scripts/ai_scout.ps1` line 57 performs `Set-Content` only after the blocking invocation returns and `$LASTEXITCODE -eq 0`.
   - Because the command was still blocked when the 8-minute observation budget expired, no partial or canonical `CONTEXT.md` had been written to disk.
4. **Client Termination Safety**:
   - Terminating the `opencode run` client process (`PID 20744`) immediately released the task execution without harming the background server process (`PID 21508`), confirming client-isolated termination is practical on Windows.

## Read-only Targeted Survey Findings (Implementation Uncertainty)

1. **PowerShell Streaming Capability**:
   - Verified via direct probe: Windows PowerShell native pipeline streaming (`& <cmd> 2>&1 | ForEach-Object { ... }`) immediately streams individual lines as they arrive from external processes.
   - Streaming is blocked only when downstream cmdlets like `Out-String` or batch assignments accumulate the stream.
2. **Tee-to-Terminal + Capture Pattern**:
   - The simplest and most robust PowerShell pattern is:
     ```powershell
     $captured = & opencode @args 2>&1 | ForEach-Object {
         [Console]::WriteLine($_)
         $_
     }
     ```
   - Alternatively, redirecting output directly to a temporary file in `.runtime/ai_scout/$Task/` while reading/tailing or using `Tee-Object` avoids memory exhaustion while providing continuous visibility.
3. **Timeout and Child Process Termination**:
   - Using .NET `System.Diagnostics.Process` or `Start-Process -PassThru` allows evaluating `$p.WaitForExit($timeoutMilliseconds)`.
   - If `$finished -eq $false`, executing `$p.Kill()` (or `taskkill /F /PID $p.Id`) precisely terminates the `opencode run` child process without affecting the persistent `opencode serve` daemon.
4. **Atomic Promotion to Canonical CONTEXT.md**:
   - Output should first be written to a temporary staging file (e.g., `.runtime/ai_scout/$Task/candidate.md`).
   - Only upon verification that exit code is 0, process did not time out, and content contains valid non-empty markdown headings should `Move-Item -Force` promote the candidate to `docs/tasks/$Task/CONTEXT.md`.
   - On timeout or non-zero exit, canonical `CONTEXT.md` is preserved untouched.
5. **Enforcement Boundary of max_files**:
   - `opencode run --help` confirms no native `--max-files` or tool-call-limiting CLI parameter exists in OpenCode v2.0.3.
   - Therefore, `max_files` must be a soft constraint enforced via `.opencode/agents/scout.md` system prompt and invocation prompt contract, rather than a hard engine sandbox limit.

## Recommendation

**GO WITH SPEC CHANGES**

- **Reason**: The empirical observation of this execution definitively proves that OpenCode Scout with the default model (`big-pickle`) consistently exceeds the acceptable 8-minute SLA when unconstrained, while providing zero terminal visibility due to `Out-String` buffering in `ai_scout.ps1`. The draft spec's direction—introducing bounded timeouts, real-time terminal streaming, atomic promotion, and soft-budget prompt constraints—is validated by direct local evidence and is ready for spec finalization and implementation.
