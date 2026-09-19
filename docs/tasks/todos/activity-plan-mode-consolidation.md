# Activity Plan + Mode Consolidation

Status: Future Work

Origin: Activity Mode Consolidation architecture proposal and the `navigation-targeted-cv-fast-path` Phase 10 checkpoint discussion.

## Problem

The current runtime has one shared set of underlying handlers and business flows, but its orchestration concepts are historically split:

- `stage`, `dungeon`, `mix`, `collect_only`, Domain modes, and `daily` are exposed as "modes";
- Town/Boss work is often scheduled through `town_subflow_queue`;
- direct development runs use `--subflow`;
- combat/exploration work often switches `self.config` to represent the selected execution route;
- `daily` currently uses `type="mix"` as a compatibility mechanism.

The bottom-level implementations are largely shared, but task selection, naming, CLI entry points, and config/runtime context still express two historical scheduling philosophies.

## Goal

Unify orchestration around:

- **Mode** = how the user constructs an execution plan;
- **ActivityPlan** = enabled Activities plus their target/policy settings;
- **Activity** = one schedulable unit of work;
- **Intent** = the currently committed work unit;
- **Handler/FSM** = local execution after dispatch.

The intended public orchestration modes are:

### `daily`

The repository-defined 24/7 default ActivityPlan using the existing priority, cooldown, defer, and preemption semantics.

### `custom`

A user-defined ActivityPlan that enables/disables Activities and chooses required targets.

`custom` must not introduce a second scheduler. It should use the same selection, priority, intent lifecycle, prerequisite, and dispatch machinery as `daily`.

## Single Activity execution entry

Generalize today's development-only `--subflow` concept into a direct Activity execution entry such as:

```text
--activity dungeon
--activity stage
--activity golden_empire
--activity chest
--activity bag_maintenance
```

This is not a third normal orchestration mode.

Its purpose is development/debug/validation of one Activity while bypassing the global scheduler.

Do not force Stage/Dungeon into the Town-subflow abstraction merely to obtain this entry point.

## Target dependency direction

The target architecture should preserve Greenfield-lite ownership:

```text
User Configuration
  → ActivityPlan
    → Scheduler / Intent Selection
      → Prerequisite Satisfaction
        → Activity Handler / FSM
```

Navigation/Handler layers must not inspect orchestration-mode names to choose a different Activity.

The Scheduler owns selection and eligibility.
Prerequisite/navigation owns reaching the dispatch condition.
Handlers own local execution and completion evidence.

## Existing evidence to preserve

The repository already demonstrates that scheduled and direct execution can share the same underlying implementation:

- Town/bag-maintenance flows use common handlers regardless of whether they were triggered by Daily scheduling or direct subflow execution.
- `bag_maintenance` already behaves like a named macro/composite Activity.
- Precondition contracts such as `REACH_TOWN` already separate business commitment from prerequisite satisfaction.
- Greenfield-lite already defines a single active-intent direction and forbids lower layers from selecting unrelated work.

The consolidation should reuse these existing contracts rather than invent a second workflow engine.

## Prerequisite: Activity execution config SSOT

This work should follow `activity-execution-config-ssot`.

Before changing orchestration semantics, Stage/Dungeon/Domain/etc. should already have canonical execution config ownership.

Otherwise this task would have to solve two independent architecture problems at once:

1. which Activity the scheduler selected;
2. which historical copy of that Activity's config is authoritative.

The desired dependency is:

```text
ActivityPlan selects Activity + target
        ↓
canonical Activity execution config
        ↓
prerequisite satisfaction
        ↓
Handler/FSM
```

This task should consume canonical Activity execution definitions, not create a parallel ownership system.

## Scope

A future formal SPEC should cover:

- define Activity identity and ActivityPlan data/contract;
- make `daily` an official default ActivityPlan;
- add `custom` as a user-composed ActivityPlan using the same scheduler;
- remove `type="mix"` as a long-term orchestration concept once compatibility migration is complete;
- unify Activity selection, priority, cooldown, defer, and preemption ownership;
- generalize direct execution from `--subflow` toward `--activity`;
- preserve `REACH_TOWN` and other prerequisite semantics;
- preserve one active intent / one selection owner;
- migrate incrementally so unconverted handlers continue to work at each slice.

## Non-goals

Do not:

- create a general plugin/workflow framework;
- create a second scheduler for `custom`;
- move Activity selection into Navigation;
- duplicate Activity execution config inside ActivityPlan;
- rename every existing Handler/state merely for terminology consistency;
- rewrite all handlers in one task;
- delete Navigation legacy compatibility until config/orchestration contracts make its callers provably unreachable.

## Relationship to navigation legacy retirement

This consolidation is expected to remove historical orchestration identities that currently keep compatibility navigation alive.

Examples:

- ordinary `mix` Stage fallback should stop looking like a separate execution mode once the scheduler selects the Stage Activity explicitly;
- cooldown/fallback tab-routing code should become policy/selection work above Navigation rather than a second lower-level route owner;
- Navigation should consume an already-selected Activity target rather than infer scheduler intent from `config["type"]`.

After this architecture is implemented, create a bounded Navigation legacy-retirement task to remove compatibility code that is then proven unreachable while preserving all verified behavior.

## Acceptance direction

A future formal SPEC should require:

1. `daily` and `custom` share one scheduler/selection lifecycle;
2. direct `--activity` execution reuses the same Activity handlers without becoming a scheduler mode;
3. `type="mix"` is no longer required as the long-term semantic owner of Daily orchestration;
4. Activity selection happens above Navigation;
5. prerequisite satisfaction preserves the committed Activity intent;
6. no duplicate Activity execution configuration is introduced;
7. legacy paths are removed only after behavior-preserving migration evidence exists.
