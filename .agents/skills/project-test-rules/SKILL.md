---
name: project-test-rules
description: Run and verify this repository's Python tests using the project-standard unittest discovery command.
---

# Project Test Rules

Use the repository's standard test entry point from the project root:

```powershell
.\.venv\Scripts\python -m unittest discover tests
```

Rules:

- Run this command as the default full-suite check.
- If execution is blocked by a missing dependency or environment issue, report the exact error; do not silently substitute another runner.
- When changing runtime behavior, add or update a focused regression test under `tests/`.
- Keep test changes aligned with the existing `unittest` structure.
