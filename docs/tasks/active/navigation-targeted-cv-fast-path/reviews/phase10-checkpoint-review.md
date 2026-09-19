# Phase 10 Checkpoint Review

Status: PASS

Reviewed branch: `navigation-targeted-cv-fast-path`

Integration target: `main`

## 1. Review question

Can `navigation-targeted-cv-fast-path` close and merge at the current architecture checkpoint without pretending that every historical navigation compatibility path has already been deleted?

**Verdict: YES.**

The task has completed the shared navigation foundation and canonical fixed-target migration. Phase 10 has removed or isolated the duplicate responsibilities that are provably dead under the current config/orchestration contracts. The remaining legacy callers depend on upstream Activity config ownership or orchestration semantics and are intentionally deferred instead of being bridged with additional transitional code.

## 2. Checkpoint achieved

### Shared Navigation Foundation — Complete

The branch provides:

- declarative lobby-tab routing through `NavigationIntentPolicy` / `NavigationTable`;
- Scene-evidence postconditions for tab switches;
- stable ordered navigation catalogs for Stage, Domain, Dungeon, Lord, and Demon Lord;
- one `SharedCardNavigator` target-first / directional / target-only tracking lifecycle;
- `VerifiedCardNavigationSession` as the ownership/invalidity boundary;
- bounded miss exhaustion and relocalization;
- reset-left only as a fallback when useful localization evidence is unavailable.

### Canonical Path Migration — Complete

Canonical supported fixed-target paths use the shared owner:

| Area | Canonical owner | Handoff boundary |
| --- | --- | --- |
| Stage main card | `SharedCardNavigator` | existing main-card click then sub-stage flow |
| Domain main card | `SharedCardNavigator` | existing Domain entry/start/explore |
| Fixed Dungeon | `SharedCardNavigator` + `DungeonCatalog` | existing status/cooldown/locked/click/fight |
| Lord card navigation | `SharedCardNavigator` after business target commitment | existing cooldown/OCR/click/start/fight |
| Demon Lord card navigation | `SharedCardNavigator` for catalog-backed target | existing stone/prepare/start/fight |
| Lobby tab switching | declarative routing | card navigation begins only after visual tab evidence |

Greedy Dungeon is intentionally outside the fixed-target migration boundary because its broad scan still owns target selection before a unique target is committed.

## 3. Phase 10 cleanup achieved

The branch has already removed or isolated the following responsibilities:

- generic `navigation_path` no longer owns canonical normal Stage/Dungeon/Domain lobby-tab switching;
- canonical fixed-target Dungeon has no second independent horizontal-search owner;
- canonical fixed Dungeon resolution is separated from legacy compatibility resolution;
- canonical fixed Dungeon FOUND flows into status/click using the committed target rather than re-entering the legacy resolver;
- Lord shared reset recovery no longer mutates legacy `has_reset_to_left` / `reset_swipe_count` state.

These are bounded responsibility deletions/splits, not whole-function deletion.

## 4. Remaining legacy classification

| Area | Remaining compatibility / old logic | Classification |
| --- | --- | --- |
| Stage | ordinary historical `mix -> Stage` manual main-card search and partial/noncanonical fallback | Deferred behind config/orchestration consolidation |
| Domain | noncanonical identity / primary-alignment compatibility | Deferred behind config SSOT |
| Fixed Dungeon | legacy target resolver compatibility | Deferred behind config SSOT |
| Greedy Dungeon | broad scan, priority, eligibility, cooldown, locked/unavailable target selection | KEEP — distinct responsibility |
| Lord | explicit noncanonical reset/broad-search compatibility | Deferred behind config SSOT |
| Demon Lord | incomplete-catalog `_step_select_boss_card_legacy()` | Deferred until catalog completeness is contractual |
| Cross-mode routing | historical `mix` / cooldown direct Stage/Dungeon tab clicks | Deferred behind Activity orchestration consolidation |

Follow-up dependency:

```text
Activity Execution Config SSOT
        ↓
Activity Plan + Mode Consolidation
        ↓
Navigation Legacy Retirement
```

Tracked documents:

- `docs/tasks/todos/activity-execution-config-ssot.md`
- `docs/tasks/todos/activity-plan-mode-consolidation.md`
- `docs/tasks/todos/navigation-legacy-retirement.md`

## 5. Verification evidence

### Fresh closeout environment

- `ai_gate.ps1`: **unavailable**, explicitly excluded from this closeout.
- GitHub PR CI/checks for the final head: **no workflow runs available**.
- This ChatGPT/GitHub environment cannot execute the repository's canonical Windows/shared-`.venv` focused suite, so this review does **not** claim a fresh task-wide local test rerun.

### Why existing focused evidence remains applicable

The final reviewed production implementation anchor is:

`e9cf7e49cfb22b4258783bd058e0f5c44746dcb1`

A GitHub compare from that commit to the closeout head showed **no production or test code changes**. Subsequent changes are documentation/review/future-work artifacts only.

Therefore the implementation under final semantic review is the same production code for which the latest phase evidence was collected.

Recorded evidence includes:

- Phase 10B-2 Dungeon survey focused run: **86 tests, 82 passed, 4 documented pre-existing failures**. The passing evidence covered fixed-target navigation, direction, tracking, status handling, and legacy/greedy boundaries.
- Later Dungeon-focused Phase 10B-4 baseline recorded in SPEC: **94 tests, 90 passed, 4 known pre-existing branch failures**.
- Phase 10B-5 Lord focused result: **36 passed**; semantic review verdict PASS.
- Dedicated regression modules exist for Stage, Domain, fixed Dungeon, Lord, Demon Lord, shared navigator, card-navigation session, catalogs, and declarative routing.

The mode-specific test surfaces explicitly cover:

- target visible -> no reset;
- higher/lower target direction;
- target-only tracking;
- miss-bound relocalization;
- bounded reset fallback;
- target/mode/surface invalidation;
- downstream handoff preservation;
- fixed Dungeon resolver ownership and greedy boundary;
- five-tab declarative routing and postcondition behavior.

## 6. Final semantic / architecture review

### Responsibility boundary — PASS

`SharedCardNavigator` owns only card localization/direction/tracking and returns side-effect requests/results. It does not select Activities, evaluate cooldowns, choose bosses, or own downstream combat.

Mode handlers retain their downstream business logic after FOUND.

### Coupling — PASS

Shared catalog/session/navigation helpers depend on navigation metadata/evidence rather than mode-specific schedulers. Compatibility branches remain isolated instead of being pulled into the shared component.

The remaining `mix` coupling is documented as upstream orchestration debt rather than encoded into a new shared-navigation abstraction.

### State ownership — PASS

- `VerifiedCardNavigationSession` owns verified card-search session validity.
- `SharedCardNavigator` owns navigation-search state.
- `NavigationProgress` owns one in-flight declarative action/postcondition.
- Lord canonical reset attempts are separated from legacy reset bookkeeping.
- Fixed Dungeon canonical committed target identity is not re-resolved through the legacy owner after FOUND.

No new second writer for canonical card-tracking state was found.

### Timing / concurrency — PASS within task scope

This task does not change established sleep/debounce timings. Shared tracking remains sequential and bounded.

External/manual Scene drift during TRACK and generation-aware guarded action commit remain explicitly out of scope and are tracked separately in `concurrent-scene-validation-action-commit.md`.

### Testability — PASS

Shared navigation, session ownership, catalog construction, declarative routing, and each of the five mode integrations have deterministic focused test modules.

Compatibility boundaries such as Greedy Dungeon and incomplete Demon Lord catalogs are directly characterized instead of hidden behind the shared happy path.

### Dead logic — PASS for current checkpoint

Proven-dead duplicate responsibilities were removed/split in Phase 10B-1 through 10B-5.

Remaining old code is not claimed dead. Each retained branch has a documented supported/compatibility/business reason and is assigned to future retirement work.

### Technical debt — ACCEPTED / TRACKED

Known debt is explicit:

- historical `mix` execution identity;
- duplicated Activity execution config ownership;
- noncanonical/incomplete config compatibility;
- remaining direct fallback tab routing;
- overlay semantic debt outside this task;
- external Scene-drift guarded-commit work.

These do not require another compatibility layer inside this navigation task.

### Architecture drift — PASS

The branch moves toward Greenfield-lite invariants:

- selection remains above physical navigation;
- Scene evidence proves navigation postconditions;
- one shared fixed-target card-navigation owner;
- intent/session state survives handler details without making lower layers choose unrelated work.

Stopping here avoids drifting in the opposite direction by teaching shared navigation about historical `mix` orchestration semantics.

## 7. Merge decision

**PASS — merge-ready at the checkpoint boundary.**

The merge means:

> Shared five-mode navigation and canonical fixed-target migration are integrated. Phase 10 cleanup is complete for responsibilities provably dead under current contracts. Remaining compatibility retirement is intentionally deferred behind Activity config SSOT and Activity orchestration consolidation.

The merge does **not** mean:

> every legacy navigation branch in the repository has been deleted.

No blocking semantic/architecture issue was found in the final GitHub review.
