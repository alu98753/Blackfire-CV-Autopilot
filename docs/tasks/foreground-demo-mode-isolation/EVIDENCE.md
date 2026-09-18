# Verification Evidence

Task: 
foreground-demo-mode-isolation
Branch: 
foreground-demo-mode-isolation
HEAD: 
9c5b5ff5cf603c44e73726a85b7080b62b317f00
Base ref: 
origin/main

## Review verdicts

- Spec reviewer: BLOCK (blocking=2)
- Regression reviewer: BLOCK (blocking=2)

## Attempt provenance

- spec-reviewer | model=opencode/big-pickle | classification=VALID_BLOCK | selected=True
- regression-reviewer | model=opencode/big-pickle | classification=VALID_BLOCK | selected=True

## Focused tests

- tests.test_behavior_main_entrypoint: FAIL (exit=1)
- tests.test_screen_capturer_architecture: PASS (exit=0)
- tests.test_mouse_refactor: PASS (exit=0)
- tests.test_mouse_coordinates: PASS (exit=0)

## Full suite

Not run by the AI gate. User must run the repository full suite manually.
