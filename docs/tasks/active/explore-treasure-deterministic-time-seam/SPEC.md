# explore-treasure-deterministic-time-seam

Status: Draft

## Goal

Reduce deterministic Treasure/Explore test wall-clock time without changing verified production behavior.

This task must keep the existing blocking Treasure control flow and timing values intact. It only makes Treasure elapsed-time and sleep behavior consume the repository's existing clock seam so production continues to use real time through `SystemClock` while tests can use `FakeClock` and advance time instantly.

## Lightweight survey evidence

Current `main` at task creation:

```text
525bb35ad9385efd0a5619429436c4fdff67367a
```

Relevant prior evidence:

- `docs/todos/test_profiling_hotspots_v3.md` recorded Treasure close/terminal waiting as a measured full-suite hotspot (~12.6s in the 2026-09-13 profile).
- `docs/storys/2026-09-13_test_execution_efficiency_and_clock_seam_story.md` established the repository pattern:
  - production -> `SystemClock` -> real time;
  - deterministic tests -> `FakeClock` -> logical time.
- `BaseStateHandler` already provides:
  - `_get_monotonic_time()`;
  - `_sleep()`.
- `tests/support/fake_clock.py` already implements `monotonic()`, `advance()`, and `sleep()`.
- `tests/test_explore_subflow.py` already injects a `FakeClock`, but Treasure production code still calls direct `time.time()` / `time.sleep()`.
- `states/domains/treasure_subflow.py` still has a direct `time.sleep(3.0)`; its actionable Treasure test mocks click/wait behavior but currently has no explicit virtual-time seam for that settle delay.

## Problem boundary

The problem is not that the current Treasure behavior is known to be wrong.

The problem is that deterministic tests still inherit real wall-clock waits from Treasure production code even though the repository already has a clock abstraction designed to avoid that cost.

This task therefore owns **testability of Treasure timing**, not Treasure behavior redesign.

## Scope

Production scope:

- `states/handlers/explore.py`
  - only Treasure-specific timing inside:
    - `_run_treasure_subflow()`;
    - `_wait_for_treasure_terminal()`;
  - replace direct elapsed-time / sleep calls with the existing handler clock seam;
  - preserve the current blocking loop shape and all timing constants.

- `states/domains/treasure_subflow.py`
  - only the Treasure settle delay currently implemented with direct `time.sleep(3.0)`;
  - route it through the existing handler timing seam;
  - preserve the 3.0 second production delay.

Test scope:

- `tests/test_explore_subflow.py`
  - make Treasure tests rely on injected `FakeClock` rather than patching real sleep;
  - preserve existing Treasure click/retry/terminal behavior assertions;
  - add only narrowly necessary deterministic-time coverage.

- `tests/test_domain_common_behavior.py`
  - preserve Treasure evidence semantics;
  - ensure the 3.0 second settle behavior no longer costs real wall-clock time in deterministic tests.

Task artifacts:

- `docs/tasks/active/explore-treasure-deterministic-time-seam/`

## Known invariants

1. Production behavior is already considered valid and must remain behavior-preserving.
2. Production continues to use real time through the existing `SystemClock`.
3. No timeout, retry interval, check interval, settle delay, or post-delay value may be reduced merely to make tests faster.
4. `ExploreHandler._run_treasure_subflow()` remains blocking in this task.
5. `ExploreHandler._wait_for_treasure_terminal()` remains blocking in this task.
6. `DomainTreasureSubflow.handle()` remains blocking in this task.
7. Existing Treasure click order, retry semantics, completion anchors, and failure behavior remain unchanged.
8. Existing `click_and_wait_until_gone()` semantics remain unchanged.
9. Calendar/persistent wall-time semantics are not part of this task; Treasure elapsed durations use monotonic/logical time only.
10. No test-aware production branch, MagicMock detection, or `if TESTING` behavior is permitted.
11. The existing clock abstraction must be reused; do not create a new TimeManager or second clock framework.

## Non-goals

Do not:

- convert Treasure to tick-driven / phase-driven control flow;
- refactor Explore Bless, Relic, Skill, or unrelated dungeon handling;
- change `BaseStateHandler`;
- change `states/state_machine.py`;
- change `runtime/ports.py`;
- change `tests/support/fake_clock.py` unless Scout finds a concrete missing capability required by this exact task;
- change Blood Altar timing;
- change Game Relaunch timing;
- change Navigation, Result, Lord Boss, Domain navigation, OCR, or card navigation;
- remove tests for speed;
- introduce parallel test execution;
- change production CV/template thresholds or Treasure scene semantics.

## Provisional implementation shape

The expected minimal direction is equivalent to:

```text
Explore Treasure:
  time.time()  -> existing monotonic clock seam
  time.sleep() -> existing sleep clock seam

Domain Treasure:
  time.sleep(3.0) -> existing handler sleep clock seam
```

The exact syntax is not normative. Scout must confirm the narrowest safe call sites.

## Provisional acceptance criteria

1. Treasure-specific direct real-time dependency in the scoped `ExploreHandler` methods is removed in favor of the existing clock seam.
2. The Domain Treasure 3.0-second settle delay uses the existing clock seam.
3. With `SystemClock`, production timing values and observable Treasure behavior are unchanged.
4. With `FakeClock`, Treasure deterministic tests complete without waiting for the corresponding real durations.
5. Existing Treasure success, transient-miss, sticky-confirm retry, and terminal-anchor behavior remains covered.
6. Domain Treasure actionable-evidence behavior remains:
   `open -> confirm -> quit`.
7. Domain Treasure scene-evidence-only cases remain zero-click when `open.png` is absent.
8. No production files outside the two scoped Treasure implementation files are modified.
9. No shared timing infrastructure is modified unless Scout proves the task cannot be completed safely without it; such evidence must be reviewed before Final status.
10. Focused tests declared in `task.json` pass.

## Focused verification candidates

Expected focused targets:

```text
tests.test_explore_subflow.TestExploreSubflow.test_run_treasure_subflow_success
tests.test_explore_subflow.TestExploreSubflow.test_run_treasure_subflow_waits_through_transient_misses
tests.test_explore_subflow.TestExploreSubflow.test_run_treasure_subflow_reclicks_confirm_until_disappeared
tests.test_explore_subflow.TestExploreSubflow.test_run_treasure_subflow_accepts_terminal_anchor_without_quit
tests.test_domain_common_behavior.TestDomainCommonBehavior.test_treasure_evidence_scenario_a_open_actionable
tests.test_domain_common_behavior.TestDomainCommonBehavior.test_treasure_evidence_scenario_b_find_treasure_scene_evidence_only
tests.test_domain_common_behavior.TestDomainCommonBehavior.test_treasure_evidence_scenario_c_treasure_card_scene_evidence_only
```

Scout may recommend a smaller or slightly broader focused set if direct Treasure consumers require it.

## Uncertainty for Scout

Scout should answer only the following bounded questions:

1. Are there any Treasure-specific direct `time.time()` / `time.sleep()` calls in the immediate scoped methods that this Draft missed?
2. Can `DomainTreasureSubflow` safely reuse its owning handler's existing `_sleep()` seam without changing ownership or shared infrastructure?
3. Which direct Treasure tests currently incur real wall-clock delay, and which minimal assertions should prove deterministic-time behavior?
4. Is any shared file actually required, or can the task remain confined to the two production files plus direct tests?
5. Are there nearby Treasure behavior invariants that the timing substitution could accidentally alter?

Do not broaden Scout into a general Explore or test-suite audit.
