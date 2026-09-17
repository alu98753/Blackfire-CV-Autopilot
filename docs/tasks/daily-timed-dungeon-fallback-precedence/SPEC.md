# daily-timed-dungeon-fallback-precedence

Status: Final

## Goal

Fix the Daily pipeline scheduling livelock where a ready timed dungeon repeatedly preempts a configured Tier 4 domain/stage fallback, but `evaluate_next_activity()` immediately re-enters that same fallback because pending bounty quests are cooling down.

The intended execution precedence is:

```text
higher-tier runnable Daily work
  > runnable bounty quest
  > ready timed dungeon
  > perpetual Tier 4 fallback (domain/stage)
```

`pending` alone is not execution priority; runnable work is.

## Problem statement

Current behavior can form this loop:

```text
DOMAIN_EXPLORE
  -> has_available_daily_dungeon() == True
  -> exit fallback and re-schedule
  -> evaluate_next_activity()
  -> bounty quests still pending but all cooling
  -> apply_tier4_fallback_config()
  -> return before timed-dungeon selection
  -> DOMAIN_EXPLORE again
  -> repeat forever
```

The bug is not that timed dungeons participate in fallback preemption. Existing code and tests intentionally preserve persistent Daily timed-dungeon policy while the ephemeral runtime route is domain/stage, and already expect a ready timed dungeon to preempt those long-lived fallbacks.

The actual defect is selection asymmetry: fallback relinquishment and central dispatch disagree about the same runnable dungeon candidate.

## Architecture contract

`docs/architecture/project_arch_greenfield_lite_v1.md` remains authoritative:

- `evaluate_next_activity()` owns activity selection / eligibility ordering.
- Navigation executes an already-selected route and must not become a second scheduler.
- Handler FSMs may relinquish an active fallback at an allowed safe point, but must not independently choose the next Daily activity.
- Tier 1 / Tier 1.5 / Tier 2 / Tier 3 precedence remains unchanged.
- Tier 4 is a fallback scheduling bucket, not a statement that every Tier 4 candidate is an unordered peer.

Within Daily Tier 4, distinguish:

```text
Tier 4A: ready timed dungeon
  - cooldown-gated
  - finite/opportunistic
  - enabled by persistent Daily policy

Tier 4B: long-lived fallback
  - domain
  - stage
  - other configured perpetual fallback behavior
```

Required precedence:

```text
Tier 4A > Tier 4B
```

## Preemption-dispatch coherence invariant

If active fallback A relinquishes because runnable candidate X is detected, the next central scheduler evaluation must either:

1. dispatch X, or
2. dispatch another currently-runnable activity with strictly higher precedence than X.

It must not immediately select A again while X remains runnable.

The only valid reasons not to dispatch X are that eligibility changed between observations, a higher-priority runnable activity appeared, or an explicit recovery/safety condition took ownership.

## Required behavior

### Pending but cooling bounty quests

If the quest scheduler still has pending tasks but none is runnable:

- keep the quest scheduler attached;
- retain/arm existing quest preemption semantics;
- continue evaluating lower-priority runnable work;
- do not commit to domain/stage fallback before checking a ready timed dungeon.

### Timed dungeon ready

When all higher-priority activities are currently not runnable and `has_available_daily_dungeon()` is true:

- select the timed dungeon route;
- do not enter domain/stage fallback first;
- preserve the underlying fallback context so normal scheduling can resume afterward.

### No timed dungeon ready

When quests are pending-but-cooling and no enabled timed dungeon is ready:

- enter the configured Tier 4 domain/stage fallback as today;
- preserve existing quest safe-point preemption behavior.

### Higher-priority work becomes runnable

Tier 1, Tier 1.5, Tier 2, and runnable Tier 3 work continue to outrank timed dungeons.

## Authoritative policy source

Timed-dungeon preemption eligibility and timed-dungeon scheduler dispatch eligibility must use the same persistent Daily policy source.

An ephemeral runtime fallback such as:

```text
type = domain
```

or:

```text
type = stage
```

must not hide the persistent Daily values that govern timed dungeons, including:

- `enable_dungeon`
- `greedy_dungeon`
- allowed dungeon indices / selection
- dungeon cooldown state

Do not create a state where preemption says a dungeon is ready while scheduler dispatch says it is unavailable solely because they read different config layers.

## Safe-point semantics

This task does not introduce unsafe mid-battle interruption.

Preserve existing ownership:

- domain may relinquish where its existing handler permits safe exit;
- stage/battle keeps existing Result safe-point semantics;
- committed battle/dungeon workflows retain maintenance ownership until their existing safe point;
- bounty quest preemption after cooldown expiry remains governed by existing safe-point rules.

## Implementation scope

Primary expected change:

- `states/state_machine.py`
  - `evaluate_next_activity()` decision ordering around pending-but-cooling quests and timed-dungeon selection.

Permitted supporting changes when needed for coherence/testability:

- a small scheduling helper local to this responsibility;
- reuse of a common timed-dungeon eligibility predicate;
- bounded logging improvements;
- focused updates to tests;
- clarification of `docs/architecture/project_arch_greenfield_lite_v1.md` section 4.3.1.

Existing `DomainExploreHandler` timed-dungeon preemption behavior should remain unless a focused correction is required. Do not remove timed-dungeon preemption as a workaround.

## Known invariants

- Central scheduler owns activity selection.
- Navigation must not query Daily managers / quest schedulers to choose work.
- A higher-tier activity blocks lower tiers only when it is currently runnable under existing eligibility rules.
- Pending-but-cooling bounty work remains pending and armed for future preemption, but must not suppress currently-runnable lower-priority work.
- `has_available_daily_dungeon()` remains valid while the active runtime route is domain/stage.
- `enable_dungeon = false` must strictly disable timed-dungeon dispatch and preemption.
- Behavior-preserving semantics outside this scheduling correction are required.

## Acceptance criteria

1. Daily active + pending bounty quest + no runnable bounty quest + ready timed dungeon + `tier4_mode=domain` selects the timed dungeon directly rather than re-entering domain.
2. The same scenario with `tier4_mode=stage` selects the timed dungeon rather than retrying/re-entering stage.
3. Pending bounty quests + all cooling + no ready timed dungeon still enters the configured Tier 4 fallback.
4. A runnable bounty quest still outranks a ready timed dungeon.
5. Runnable Tier 1 / Tier 1.5 / Tier 2 activity still outranks a ready timed dungeon.
6. `enable_dungeon=false` prevents both timed-dungeon preemption and timed-dungeon dispatch.
7. If a timed dungeon becomes ready while domain/stage fallback is already running, the fallback relinquishes only at its existing safe boundary; the following central schedule selects that dungeon or a newly-runnable higher-priority activity.
8. The same continuously-runnable dungeon candidate cannot cause `domain -> exit -> domain -> exit` or equivalent stage livelock.
9. Quest cooldown expiry during dungeon/fallback execution still uses existing quest safe-point preemption.
10. Timed-dungeon preemption and dispatch resolve eligibility from a coherent Daily policy source.
11. No new task-selection responsibility is added to Navigation.
12. Existing timed-dungeon/domain/stage behavior tests remain green unless a test encoded the defective early-fallback ordering; any such change must be explicitly justified.

## Required focused regression tests

Add exact combined regressions for at least:

```text
Daily active
+ pending quest
+ no runnable quest
+ ready timed dungeon
+ tier4_mode=domain
=> dungeon selected
```

and the stage equivalent.

Preserve coverage for existing behaviors including:

- ready timed dungeon preempts domain route;
- Tier 4 stage with dungeon enabled exits at the existing safe point when a timed dungeon becomes ready;
- Tier 4 stage with dungeon disabled continues normal stage behavior;
- pending-but-cooling quests with no ready dungeon still use Tier 4 fallback;
- runnable quest outranks timed dungeon.

Likely focused suites include:

- `tests/test_behavior_daily_tier4.py`
- `tests/test_daily_pipeline_orchestration.py`
- `tests/test_behavior_daily_preemption.py`

Use the smallest additional tests necessary to prove the decision-order contract.

## Architecture documentation requirement

Update `docs/architecture/project_arch_greenfield_lite_v1.md` section 4.3.1 to clarify that Tier 4 is a common fallback bucket while Daily scheduling still has an internal readiness precedence:

```text
ready cooldown-gated timed dungeon > perpetual domain/stage fallback
```

This clarification must not elevate timed dungeons above runnable Tier 1-3 activities.

## Non-goals

- Do not remove `has_available_daily_dungeon()` from fallback preemption.
- Do not make dungeon/domain/stage fully unordered peers.
- Do not rewrite the Daily scheduler.
- Do not introduce a generic planner, workflow DSL, priority queue, or second scheduling owner.
- Do not redesign QuestScheduler lifecycle.
- Do not change dungeon cooldown calculation.
- Do not change domain/stage gameplay mechanics.
- Do not change battle safe-point semantics.
- Do not perform broad `GameStateMachine` refactoring unrelated to this bug.

## Explicit behavior correction

Before:

```text
quest pending but cooling
+ timed dungeon ready
=> fallback domain/stage
=> immediate timed-dungeon preemption
=> same fallback again
=> livelock
```

After:

```text
quest pending but cooling
+ timed dungeon ready
=> timed dungeon

quest later becomes runnable
=> existing safe-point quest preemption

no timed dungeon ready
=> configured domain/stage fallback
```

## Evidence used to finalize without Scout

The user explicitly authorized this task to skip the formal OpenCode Scout if the repository evidence was sufficient.

Finalization is based on direct inspection of latest `main` at task creation plus the prior incident trace, specifically:

- `project_arch_greenfield_lite_v1.md` centralized scheduler ownership and Tier hierarchy;
- `GameStateMachine.has_available_daily_dungeon()` and `has_pending_daily_activity()`;
- `GameStateMachine.evaluate_next_activity()` where pending-but-cooling quests currently return to fallback before the timed-dungeon branch;
- `DomainExploreHandler` fallback relinquishment behavior;
- existing tests in `test_behavior_daily_tier4.py` that explicitly expect ready timed dungeons to preempt domain/stage fallback.

No unresolved architecture question remains that requires an additional Scout pass before implementation.

## Uncertainty

Low.

Implementation must still verify the exact local control flow and test fixtures before editing, especially whether a small reorder is sufficient or whether a tiny helper is preferable to prevent duplicated eligibility checks. That is an implementation detail, not an unresolved product/architecture decision.
