---
name: debug-artifact-management
description: Maintain centralized debug image artifacts for this project. Use when adding, changing, reviewing, or refactoring diagnostic screenshots, OCR visualizations, grid overlays, `debug_*.png` output, or debug image tools.
---

# Debug Artifact Management

Route every runtime diagnostic PNG through `utils.debug_artifacts`. Debug images are disposable artifacts and must be written under `scratch/debug/`, never the repository root.

## Workflow

1. Search for direct image writes (`cv2.imwrite`, `PIL.Image.save`) and output names matching `debug_*.png`.
2. Use `write_debug_image("debug_<purpose>.png", image)` for runtime output. Do not create directories or concatenate debug paths in handlers, states, actions, or OCR modules.
3. Preserve meaningful filenames. Use a timestamp or bounded counter only when successive artifacts must be retained.
4. Let the centralized writer handle directory creation, path validation, write failures, and logging. Debug-output failures must not interrupt a game flow.
5. For standalone tools, default diagnostic output to the managed directory; allow an explicitly supplied output directory only when the tool requires it.

## Constraints

- Use a basename matching `debug_*.png`; never pass an absolute or nested path to the runtime writer.
- Keep drawing and annotation logic in the domain component and file persistence in `utils.debug_artifacts`.
- Do not add root-level ignore entries or manually delete existing debug artifacts as part of a code change.
- Add or update behavioral tests for the managed output path and automatic directory creation.
- Before handoff, search for direct runtime writes that can still create root-level `debug_*.png` files and run focused tests.
