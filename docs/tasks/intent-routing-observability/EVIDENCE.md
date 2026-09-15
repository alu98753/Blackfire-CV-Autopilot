# Verification Evidence

Task: intent-routing-observability
Generated: 2026-09-15T11:49:02+08:00
Branch: task-intent-routing-observability
HEAD: 6c17c0d59690c1850fc8643ba39a71afb3f711cd
Base ref: origin/main

## Review verdicts

- Spec reviewer: PASS (blocking=0; type=NORMAL; model=opencode/big-pickle)
- Regression reviewer: PASS (blocking=0; type=NORMAL; model=opencode/big-pickle)

Detailed reports:

- reviews/spec-review.md
- reviews/regression-review.md

## Attempt provenance

- Role: spec-reviewer | Type: NORMAL #1 | Model: opencode/big-pickle | Elapsed: 80.2s | Outcome: VALID_VERDICT | Status: SELECTED
- Role: regression-reviewer | Type: NORMAL #1 | Model: opencode/big-pickle | Elapsed: 119.1s | Outcome: VALID_VERDICT | Status: SELECTED

## Focused tests

- PASS tests/test_behavior_runtime_ports.py (exit=0); local log: .runtime/ai_gate/intent-routing-observability/test-tests_test_behavior_runtime_ports.py.log
- PASS tests/test_behavior_navigation_intent.py (exit=0); local log: .runtime/ai_gate/intent-routing-observability/test-tests_test_behavior_navigation_intent.py.log
- PASS tests/test_behavior_navigation_progress.py (exit=0); local log: .runtime/ai_gate/intent-routing-observability/test-tests_test_behavior_navigation_progress.py.log
- PASS tests/test_behavior_routing_observability.py (exit=0); local log: .runtime/ai_gate/intent-routing-observability/test-tests_test_behavior_routing_observability.py.log

## Full suite

Not run by the AI gate. Repository policy requires the user to run the full suite manually when required.

## Candidate snapshot

Ephemeral status/diff snapshots are stored under .runtime/ai_gate/intent-routing-observability/ and are intentionally git-ignored.
