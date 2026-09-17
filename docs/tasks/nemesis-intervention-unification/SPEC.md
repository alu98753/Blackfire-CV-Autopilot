# Nemesis Intervention Unification

Status: Final

## Goal

Unify known-strong-enemy (`強敵`) intervention and consecutive-defeat-limit handling under the existing `NemesisIntervention` responsibility.

The task supports two policies:

1. **Timed known-nemesis intervention** — pause immediately, notify CLI + Discord, wait a bounded grace period, allow `Shift+C` acknowledgement, and preserve the existing automatic flee fallback only when the grace period expires without acknowledgement.
2. **Indefinite defeat-limit intervention** — when consecutive defeats reach `battle_max_defeat`, replace the current automatic give-up path with an indefinite operator hold for the current bot process/runtime session: no timer, no automatic flee, no automatic give-up, and no in-process timeout/watchdog/recovery/relaunch path may escape the hold without explicit user action.

`NemesisIntervention` remains the class/module concept. Generalization to `BattleIntervention` is deferred.

## Responsibility Boundary

This task owns:

- timed versus indefinite `NemesisIntervention` policy;
- defeat-limit integration before the existing give-up branch;
- `Shift+C` operator-arrival acknowledgement;
- intervention-aware `Ctrl+Space` arbitration;
- Chinese CLI and Discord copy for the two reasons;
- canonical `[nemesis_intervention]` configuration;
- strong-enemy template relocation;
- the minimum in-process runtime/watchdog/relaunch gating needed to preserve intervention holds;
- deterministic tests proving discovered in-process automatic escape paths are suppressed.

This task does not own:

- a general pause/resume redesign;
- Discord transport internals;
- a CV matcher redesign;
- screenshot capture;
- the separate strong-enemy registration workflow;
- English notification copy;
- unrelated battle-stall/recovery behavior outside intervention arbitration;
- process-external Supervisor daily-maintenance restart policy;
- persistence/reconstruction of an intervention across process restart/crash.

## Architecture Contract

### 1. Timed known strong enemy

```text
known strong enemy detected
    -> NemesisIntervention starts TIMED policy
    -> state machine pauses immediately
    -> CLI prints Chinese guidance containing `Shift+C`
    -> Discord sends Chinese guidance containing `Shift+C`
    -> grace timer starts (default 180 s)

        |-- Shift+C before timeout
        |      -> acknowledge user arrival
        |      -> cancel timer
        |      -> enter manual hold
        |      -> remain PAUSED
        |      -> best-effort delete tracked repeated Discord alarms
        |
        `-- grace expires first
               -> existing timeout arbitration wins
               -> existing timeout recovery executes exactly once
               -> existing strong-enemy flee subflow runs
               -> existing timeout notification-history semantics remain
```

### 2. Defeat-limit / possible unregistered strong enemy

At the logical defeat that reaches `battle_max_defeat`:

```text
ResultHandler threshold branch
    -> do NOT click give-up
    -> do NOT enter WAIT_GIVEUP_CONFIRM
    -> record logical defeat count as threshold reached
    -> start NemesisIntervention INDEFINITE policy
    -> pause immediately
    -> CLI prints distinct Chinese warning containing `Shift+C`
    -> Discord sends distinct Chinese warning containing `Shift+C`
    -> create NO timer
    -> remain PAUSED until explicit user action or process replacement
```

The intervention start must not reset `defeat_count`.

### 3. `Shift+C` — Come / user-arrival acknowledgement

`Shift+C` means only:

```text
I am back / acknowledge this intervention
```

It must never implicitly Resume automation.

For either policy:

```text
Shift+C
    -> acknowledge active intervention
    -> cancel timer if one exists
    -> enter/retain manual hold
    -> remain PAUSED
    -> print CLI confirmation that automation remains paused
    -> best-effort remove tracked repeated Discord alarms
```

The CLI confirmation should tell the operator that, after manual handling is complete, normal resume remains available through `Ctrl+Space`.

If there is no active intervention, `Shift+C` must not create one or alter normal runtime state.

### 4. `Ctrl+Space` arbitration

Existing normal pause/resume ownership remains with the current pause controller/state machine, with this intervention rule:

- **before `Shift+C` acknowledgement:** active intervention blocks `Ctrl+Space` from resuming automation;
- **after `Shift+C` acknowledgement/manual hold:** a later explicit `Ctrl+Space` may end the intervention hold and perform normal user-initiated Resume;
- outside an intervention, current `Ctrl+Space` semantics remain unchanged.

This separates:

```text
Shift+C    = I returned
Ctrl+Space = I finished manual handling; resume automation
```

### 5. Explicit manual restart/exit

`Ctrl+Q` manual fast restart and `Ctrl+Shift+Q` manual exit are explicit user actions. They are not prohibited by the automatic-escape invariant and retain their existing ownership.

## Indefinite-Hold Invariant

> **最大戰敗次數到達後，在目前 bot process / runtime session 仍存續期間，沒有使用者明確動作前，不允許任何 in-process timeout、watchdog、recovery、relaunch、restart、give-up、flee、scheduler 或 state-transition path 自動讓這場戰鬥離開 indefinite pause。**

The same protection applies to the manual-hold phase created when a timed known-nemesis intervention is acknowledged with `Shift+C`.

This is an **in-process / current-session guarantee**, not a durable cross-process guarantee.

The external Supervisor still retains its existing scheduled daily maintenance restart behavior. Therefore this intervention is not guaranteed to survive the daily process replacement. This task intentionally does not modify Supervisor policy or persist intervention state across restart.

Implementation and tests must cover the actual in-process owners discovered by Scout, not just the intervention timer.

### In-process behavior

The normal runtime loop already skips `state_machine.step()` while paused. Existing pause enforcement should remain the primary runtime gate.

The implementation must ensure intervention-owned hold cannot be bypassed by in-process entry points including, where applicable:

- pending Nemesis timeout recovery;
- ResultHandler give-up continuation;
- battle max-duration relaunch;
- battle stall restart/relaunch;
- watchdog popup recovery/relaunch;
- window-loss/capture-failure recovery;
- generic `request_relaunch()`;
- direct battle restart/flee/give-up subflows;
- scheduler/daily-reset state mutation;
- state transitions executed outside the ordinary paused runtime step gate.

Existing guards that already make a path impossible while paused should be preserved and regression-tested rather than duplicated without need.

### Supervisor boundary

`runtime/supervisor.py` remains out of implementation scope for this task.

Required compatibility evidence is only:

- paused runtime continues emitting fresh heartbeat, so a normal intervention pause must not be mistaken for a stale/dead child;
- existing Supervisor scheduled daily maintenance restart remains unchanged and may replace the child even while an intervention hold exists;
- no heartbeat/intervention metadata extension is required by this task;
- whether intervention state should later coordinate with Supervisor restart policy is deferred to backlog observation.

## Lifecycle State Contract

The implementation must model a post-acknowledgement **manual hold** distinctly enough that it cannot be confused with timeout completion or ordinary Resume.

Exact enum/member names are implementation detail, but the lifecycle must distinguish at least:

- waiting for operator with timed policy;
- waiting for operator with indefinite policy;
- acknowledged/manual hold;
- timed out / timeout recovery ownership;
- completed/cleared intervention.

Indefinite policy must not be represented by a huge timeout value. No timer is created for it.

## Notification Contract

Two semantic notification reasons are required:

1. known/configured strong enemy — timed fallback;
2. defeat limit reached / possible unregistered strong enemy — indefinite current-session hold.

Both CLI and Discord copy must explicitly contain:

```text
Shift+C
```

Required meaning:

### Known strong enemy

- a configured strong enemy was detected;
- automation is paused;
- press `Shift+C` when back;
- without acknowledgement within the configured grace period, the existing automatic flee fallback occurs.

### Defeat limit

- consecutive defeat limit was reached;
- an unregistered strong enemy may have been encountered;
- automation will remain paused for the current runtime session until explicit user handling;
- it will not automatically flee/give up through normal in-process recovery paths;
- return to the computer and press `Shift+C`.

The copy must not imply durable persistence across Supervisor process replacement.

Reusable wording/composition belongs in the existing notification i18n/dictionary boundary rather than being hard-coded in `ResultHandler`.

`zh-TW` is required. English wording is deferred.

### Notification cleanup

- while waiting, repeated alarms remain tracked by `NemesisIntervention`;
- `Shift+C` acknowledgement performs existing-style best-effort deletion of all tracked repeated alarm messages;
- a timed intervention that expires without acknowledgement preserves the existing behavior of retaining one successful alarm as history and cleaning up the remainder;
- notification deletion failure must not corrupt intervention state.

## Configuration Contract

Remove the old keys from `[notification]` and remove redundant mode-level copies:

```toml
nemesis_intervention_grace_period_seconds
nemesis_intervention_notification_count
```

Canonical shared configuration becomes:

```toml
[nemesis_intervention]
grace_period_seconds = 180.0
notification_count = 5
```

Rules:

- one unambiguous tracked source for shared defaults;
- handlers/intervention code must read through the repository config boundary, not hard-coded competing literals;
- `battle_max_defeat` remains separate and authoritative for defeat threshold;
- untracked user profile files are not silently rewritten by this task;
- legacy tracked keys cease to be authoritative inputs rather than remaining as hidden fallback sources.

## Defeat Count Contract

The existing ResultHandler threshold check occurs before the final retry increment. The new flow must therefore ensure the logical count reflects that the configured maximum was reached when the intervention starts.

Starting or acknowledging the intervention must not reset the count.

Existing later reset ownership after a genuinely resolved battle/exit remains unchanged unless a minimal adjustment is required to avoid immediate re-trigger after an explicit manual resume.

The implementation must not hide the threshold condition by resetting to zero at intervention entry.

## Strong-Enemy Template Layout

Relocate the existing tracked images to:

```text
templates/nemesis/domain/golden_empire/
  elf_mythril_hag.png
  golden_king.png
  golden_wall_guard_tulan.png
  human_golden_tulakh.png
  undead_altalim.png

templates/nemesis/dungeon/
  dragon_karsos.png
  dragonkin_sakroth.png
  ice_boss_calvia_body.png
```

Requirements:

- use path/reference migration (`git mv` semantics) rather than matcher redesign;
- update config, tests, and documentation references;
- domain matching continues to use only the relevant domain list;
- dungeon matching continues to use only the relevant dungeon list;
- a cross-mode test fixture may reference a template for regression purposes, but production applicability must not be flattened.

## Expected Implementation Surfaces

Evidence indicates the implementation may need to touch:

- `states/nemesis_intervention.py`
- `states/handlers/battle.py`
- `states/handlers/result.py`
- `states/state_machine.py`
- `runtime/loop.py`
- `utils/keyboard_listener.py`
- `runtime/notification_i18n.py`
- `config.py` / config accessors only as needed for the new section
- `config/defaults.toml`
- existing Nemesis template references and files
- focused tests listed in `task.json`

`runtime/heartbeat.py` and `runtime/supervisor.py` are observation/regression boundaries only unless implementation evidence shows an existing in-process regression; they are not planned production-change surfaces for this task.

Do not broaden this into a generic recovery framework.

## Non-Goals

- No rename to `BattleIntervention`.
- No screenshot capture.
- No strong-enemy registration implementation.
- No English notification copy.
- No passive mouse/activity acknowledgement.
- No general CV matcher redesign.
- No automatic migration/mutation of untracked profile files.
- No Supervisor daily-restart deferral.
- No Supervisor crash-recovery redesign.
- No durable persistence/reconstruction of an intervention across process replacement.
- No unrelated state-machine/recovery refactor.

## Acceptance Criteria

1. `NemesisIntervention` supports a real timed policy and a real no-timer indefinite policy.
2. Canonical defaults are exactly represented under `[nemesis_intervention]` with `grace_period_seconds = 180.0` and `notification_count = 5`; old `[notification]` keys and redundant tracked mode-level copies are removed as authoritative sources.
3. Known strong-enemy detection pauses immediately and emits Chinese CLI + Discord guidance containing `Shift+C`.
4. Known strong-enemy default grace period is 180 seconds and default notification count is 5.
5. Known strong-enemy timeout without acknowledgement preserves the existing flee subflow exactly once.
6. `Shift+C` before timeout cancels the timer, acknowledges user arrival, cleans tracked repeated alarms best-effort, and leaves automation paused.
7. While an intervention is still waiting for `Shift+C`, `Ctrl+Space` cannot resume automation.
8. After `Shift+C`, a later explicit `Ctrl+Space` may clear the manual hold and resume normal automation.
9. Reaching `battle_max_defeat` no longer clicks give-up or enters the give-up continuation; it enters indefinite Nemesis intervention before those mutations.
10. Defeat-limit intervention creates no timer, invokes no flee/give-up fallback, preserves the logical threshold count, and emits distinct Chinese CLI + Discord guidance containing `Shift+C`.
11. `Shift+C` during defeat-limit intervention leaves automation paused for the current runtime session/manual handling period.
12. Automatic in-process escape paths identified by Scout cannot bypass intervention-owned hold. Required coverage includes battle timeout, stall/restart/relaunch, watchdog/recovery, generic relaunch, result give-up continuation, and state/scheduler paths that could otherwise progress the battle.
13. Paused intervention continues producing fresh heartbeat and does not trigger stale-heartbeat recovery merely because automation is paused.
14. Existing Supervisor daily maintenance restart behavior remains unchanged and is explicitly outside the guarantee of this task.
15. Explicit `Ctrl+Q` manual restart and `Ctrl+Shift+Q` manual exit remain available as user-authorized actions.
16. All eight existing strong-enemy images are moved under the new `templates/nemesis/domain/golden_empire/` and `templates/nemesis/dungeon/` layout; tracked config/test/doc references are updated and production applicability remains scoped.
17. Existing notification cleanup race/idempotence behavior remains deterministic; ACK/timeout has one winner and no double flee/resume occurs.
18. No screenshot capture, English-copy work, passive activity detection, Supervisor redesign, or broad battle/recovery refactor is introduced.
19. Focused deterministic tests in `task.json` pass before review; any new focused test file introduced must also be added to `task.json`.

## Verification Matrix

At minimum prove:

### Timed

- known nemesis -> pause;
- default 180 s / count 5;
- CLI contains `Shift+C`;
- Discord contains `Shift+C`;
- timeout -> existing flee once;
- `Shift+C` -> timer cancelled, alarms cleaned best-effort, still paused;
- no flee after ACK;
- repeated `Shift+C` is idempotent;
- ACK/timeout race has one deterministic winner.

### Indefinite

- final defeat reaches configured threshold and logical count reflects it;
- threshold -> indefinite intervention before give-up mutation;
- no timer;
- no give-up/flee;
- CLI + Discord contain `Shift+C`;
- `Shift+C` -> manual hold, still paused;
- pre-ACK `Ctrl+Space` blocked;
- post-ACK `Ctrl+Space` explicitly resumes;
- battle timeout/stall/restart/relaunch cannot escape automatically inside the process;
- watchdog/recovery/generic relaunch cannot escape automatically inside the process;
- scheduler/state transitions do not progress while hold is active;
- paused runtime keeps heartbeat fresh;
- no requirement that intervention survive scheduled Supervisor daily restart or another process replacement.

### Configuration/templates

- canonical new section only;
- old tracked keys absent as sources;
- `battle_max_defeat` remains separate;
- all template paths migrated;
- domain/dungeon production scopes preserved.

## Scout Provenance

Canonical OpenCode Scout failed infrastructurally and left canonical context untouched. The user explicitly authorized a one-time Gemini/Antigravity read-only fallback. Its findings were recorded in `docs/tasks/nemesis-intervention-unification/CONTEXT.md` and cross-checked before this SPEC was finalized. Supervisor daily restart was deliberately classified as a process-lifetime boundary/non-goal after review: the task guarantees intervention hold behavior only within the current bot process/runtime session.
