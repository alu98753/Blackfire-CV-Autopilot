# Verification Evidence

Task: 
foreground-demo-mode-isolation
Branch: 
foreground-demo-mode-isolation
HEAD: 
48df20fdc6cc57f86f8773200ad46f608e5ca45a
Base ref: 
origin/main

## Review verdicts

- Spec reviewer: PASS (blocking=0)
- Regression reviewer: BLOCK (blocking=2)

## Attempt provenance

- spec-reviewer | model=opencode/big-pickle | classification=VALID_PASS | selected=True
- regression-reviewer | model=opencode/big-pickle | classification=VALID_BLOCK | selected=True

## Focused tests

- tests.test_runtime_io_composition: PASS (exit=0)
- tests.test_screen_capturer_architecture: PASS (exit=0)
- tests.test_mouse_refactor: PASS (exit=0)
- tests.test_mouse_coordinates: PASS (exit=0)
- tests.test_foreground_demo_mode_isolation: PASS (exit=0)

## Full suite

Not run by the AI gate. User must run the repository full suite manually.
