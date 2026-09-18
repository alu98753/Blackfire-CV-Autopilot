# Scout Blocker Evidence

Task: `opencode-launcher-version-compatibility`

Status: Canonical Scout blocked before model/provider execution.

## Local execution context

- Worktree branch: `task-opencode-launcher-version-compatibility`
- Synced task HEAD before Scout: `7daa80cc4a544e6ed12c2db5d038dc8bafb9b1a1`
- Previously verified installed OpenCode version: `1.18.31`
- `opencode run --help` for that runtime does not advertise `--standalone`; it does advertise `--pure` as `run without external plugins`.

## Canonical Scout attempt

Command executed from the task worktree:

```powershell
cmd.exe /d /s /c "powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\ai_scout.ps1 -Task opencode-launcher-version-compatibility < NUL"
```

Observed behavior:

1. Candidate `opencode/mimo-v2.5-free` caused OpenCode to print `opencode run [message..]` help and exited non-zero with code 1 in approximately 5.1 seconds.
2. Candidate `opencode/big-pickle` produced the same CLI help/exit behavior and exited non-zero with code 1 in approximately 4.1 seconds.
3. Scout provenance classified both attempts as `NON_ZERO_EXIT`.
4. No candidate was selected.
5. `scripts/ai_scout.ps1` failed closed with: `All configured Scout candidate models failed infrastructurally. Canonical CONTEXT.md left untouched.`
6. The failure occurred at the OpenCode CLI invocation layer before there is evidence of either configured model/provider performing inference.

## Interpretation

This failure is launcher/runtime compatibility evidence, not provider/model compatibility evidence.

The production Scout path currently constructs an invocation containing `opencode run --standalone ...`. OpenCode 1.18.31 rejects that command shape before model execution. Therefore these two failed attempts MUST NOT be counted as MiMo or Big Pickle provider compatibility failures.

`CONTEXT.md` remains intentionally absent/untouched. This task must preserve the self-hosting blocker instead of silently bypassing canonical Scout.

## Guardrails pending SPEC convergence

- Do not replace `--standalone` with `--pure` solely because `--pure` is accepted by the CLI; semantic equivalence has not been established.
- Do not remove `--standalone` from tracked workflow code while the SPEC is Draft.
- Do not upgrade/downgrade OpenCode globally as an untracked workaround.
- Do not run Gate for this Draft task.
- Do not treat this canonical Scout failure as provider qualification evidence.

## Evidence still needed

Scout/Final-SPEC convergence must resolve:

- the repository-authoritative supported OpenCode version policy;
- whether required process isolation is already supplied by the PowerShell child-process wrapper independently of an OpenCode-specific flag;
- whether any OpenCode release actually supports `run --standalone`, and if so what that flag means;
- the smallest deterministic parser-level compatibility test for the real production launcher;
- bootstrap behavior for installed-version mismatch and deterministic installation of the supported version.
