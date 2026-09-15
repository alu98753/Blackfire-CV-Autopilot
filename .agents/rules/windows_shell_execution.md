# Windows Shell & Tool Execution Policy

Environment: Windows.

For non-interactive shell/tool execution, always invoke commands through
`cmd.exe /d /s /c` so the command processor terminates cleanly and Antigravity
receives process completion/EOF reliably.

## Rules
- Prefer: `cmd.exe /d /s /c "<command>"`
- Commands must be non-interactive.
- Do not use `cmd /k` for agent tool execution.
- If a child CLI might wait on stdin, redirect stdin from NUL:
  `cmd.exe /d /s /c "<command> < NUL"`
- For PowerShell commands, wrap PowerShell inside `cmd.exe /c`, for example:
  `cmd.exe /d /s /c "powershell.exe -NoProfile -ExecutionPolicy Bypass -Command \"<powershell command>\" < NUL"`
- Preserve the current repository working directory. Do not cd to the user home directory.
- For OpenCode automation, prefer `--standalone` unless the task explicitly requires the shared OpenCode service.
- Never start an interactive shell or command that waits for user input from an agent tool call.
