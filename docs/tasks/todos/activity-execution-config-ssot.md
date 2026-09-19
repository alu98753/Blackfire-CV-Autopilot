# Activity Execution Config SSOT

Status: Future Work

Origin: `navigation-targeted-cv-fast-path` Phase 10 checkpoint discussion.

## Problem

The repository currently has duplicated Activity execution configuration across several historical runtime modes.

Examples in `config/defaults.toml` include:

- `primary_modes.stage` owning Stage execution fields;
- `primary_modes.mix` duplicating Stage and Dungeon execution fields;
- `primary_modes.daily` duplicating Dungeon fields and retaining Stage-related execution fields while also carrying scheduler/fallback policy;
- runtime helpers rebuilding or copying execution config through `setup_stage_config()`, `_apply_tier4_stage_selection()`, `build_tier4_fallback_config()`, quest routes, and hot reload.

This means there is not always one obvious answer to:

> Where is the authoritative execution definition for Stage, Dungeon, Domain, or another Activity?

That ambiguity keeps compatibility branches alive in Navigation because consumers cannot always prove that a supported runtime config has canonical Activity identity.

## Goal

Establish **one execution-config SSOT per Activity** and make higher-level plans/policies compose from those canonical Activity definitions instead of copying their execution fields.

The target ownership model is:

```text
Activity execution config
  owns:
    navigation/templates/buttons
    reset/retry parameters
    activity-specific result/start/explore settings
    canonical target/catalog metadata

Plan / policy config
  owns:
    enable/disable
    selected Activity
    selected target
    fallback/preemption/scheduling policy
```

A policy such as Daily may select "Stage level 6 / first sub-stage", but it must not independently maintain Stage's navigation templates, buttons, or execution contract.

## Required architecture direction

Prefer composition:

```text
Daily/custom policy
      +
selected canonical Activity config
      ↓
build_*_execution_route()
      ↓
runtime execution config
```

The existing Domain Tier-4 assembly is the closest current reference model: the execution route is rooted in the selected canonical Domain config, while Daily contributes only scheduling context and selection policy.

Stage and Dungeon should move toward the same ownership rule.

## Scope

This future task should:

- identify canonical execution-owned fields for Stage, Dungeon, Domain, Lord, Demon Lord, and other Activities as appropriate;
- remove duplicate execution-owned fields from higher-level policy/mode configs where behavior-preserving composition can replace them;
- make route/config builders consume canonical Activity definitions rather than copied parallel definitions;
- define explicit target identity contracts so supported runtime configs always resolve to one canonical Activity target;
- preserve profile override semantics and hot-reload behavior;
- preserve existing runtime behavior while changing config ownership;
- add producer/consumer characterization tests proving official config producers resolve to the same canonical execution definition.

## Important non-goals

Do **not** use this task to rename all runtime concepts to Activity or to introduce `daily/custom/--activity` orchestration.

Specifically, this task should not yet:

- replace `--mode` / `--subflow`;
- introduce an ActivityPlan scheduler;
- merge Town subflows and combat/exploration Activities into one scheduler abstraction;
- change Activity precedence;
- rewrite Handler/FSM ownership;
- redesign Navigation behavior.

Those belong to the separate Activity orchestration consolidation work.

## Relationship to Activity orchestration consolidation

This task is intended to run **before** `activity-plan-mode-consolidation`.

Reason:

Activity orchestration should select and dispatch canonical Activities. If Stage/Dungeon/Domain execution ownership is still duplicated across `stage`, `mix`, and `daily`, the orchestration migration would need temporary precedence rules for deciding which copy is authoritative.

Completing execution-config SSOT first lets the later orchestration task operate on a much smaller contract:

```text
ActivityPlan selects Activity + target
        ↓
canonical Activity execution config
```

rather than also solving config ownership at the same time.

## Relationship to navigation legacy retirement

This task should make later Navigation cleanup easier.

Examples:

- Stage legacy compatibility can be deleted more confidently once every supported Stage execution route has canonical target identity.
- Demon Lord incomplete-catalog compatibility can be reassessed once supported configuration completeness is explicit.
- Navigation should no longer need to infer Activity identity from historical `type="mix"` config shapes.

Do not delete those legacy paths merely because this TODO exists. Delete them only in a later bounded cleanup after the new config contracts are implemented and verified.

## Acceptance direction

A future formal SPEC should require evidence that:

1. each Activity has one authoritative execution definition;
2. higher-level policy configs do not duplicate Activity execution-owned fields;
3. official config producers and hot reload compose from canonical definitions;
4. profile overrides still behave as intended;
5. runtime behavior remains unchanged;
6. no new cross-layer `if mode == ...` compatibility patches are introduced solely to bridge duplicated config ownership.
