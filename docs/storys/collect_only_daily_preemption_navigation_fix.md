# PARS Story: Fix COLLECT_ONLY Daily Quest Wake-Up Navigation Stall

## Purpose
The daily quest scheduler could correctly detect that a higher-priority quest had become ready while the machine was idling in `COLLECT_ONLY`, but the wake-up path stopped after mutating scheduling state. That left the machine visually and logically parked in idle mode, so it never crossed the shared navigation boundary that actually starts moving toward the target activity.

This fix was needed to restore the intended contract: when a daily quest unfreezes during `COLLECT_ONLY`, the machine should wake once, leave idle safely, and let the central navigation path consume the pending preemption and apply the quest-specific config.

## Action
The `CollectOnlyHandler` wake-up branch was changed to stop calling `check_and_advance_quest_target()` directly. Instead, it now uses `poll_daily_quest_preemption()` and, when a ready quest is detected, transitions the machine to `STATE_NAVIGATING`.

That keeps the responsibility split clean:

1. `COLLECT_ONLY` only decides whether the machine should wake up.
2. `NAVIGATING` remains the single safe boundary that consumes pending quest preemption.
3. Quest-specific config is applied exactly where actual navigation can begin, instead of being applied repeatedly while still idling.

A regression test was also added to verify that a ready daily quest wakes the machine out of `COLLECT_ONLY`, lands in `NAVIGATING`, clears the pending latch, exits Tier 4 fallback config, and enables the quest activity config needed for execution.

## Result
The stall is removed. When a daily quest becomes ready during `COLLECT_ONLY`, the machine now advances into the shared navigation flow instead of looping in idle state and relying on the watchdog to recover.

The regression is covered by `tests/test_behavior_daily_preemption.py`, so the wake-up path is now locked as an externally verified behavior rather than an implicit implementation detail.

## So What
This change closes an important scheduler-state-machine seam. The bug was not that readiness detection failed; it was that readiness was consumed at the wrong place. By routing wake-up through `NAVIGATING`, the state machine now preserves a single transition boundary for task preemption and reduces the chance of future "config changed but state did not move" bugs.

It also keeps `COLLECT_ONLY` lightweight and predictable, which matters because it is one of the states most vulnerable to silent loops and watchdog-driven recovery.

## Influence
- Behavior fixed in [CollectOnlyHandler](../../states/handlers/collect_only.py)
- Regression coverage added in [test_behavior_daily_preemption.py](../../tests/test_behavior_daily_preemption.py)
- Related orchestration continues to rely on [GameStateMachine](../../states/state_machine.py)
