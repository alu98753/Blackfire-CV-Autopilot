# Nemesis Intervention Unification

Status: Draft

## Goal

Unify the existing known-strong-enemy operator intervention flow and the consecutive-defeat-limit flow under the existing `NemesisIntervention` responsibility, while preserving explicit pause ownership and existing battle behavior outside this boundary.

The task must support two distinct policies:

1. **Known strong enemy (`強敵`)**: pause immediately, notify the user, wait a bounded grace period, allow explicit user acknowledgement with `Shift+C`, and retain the existing automatic flee fallback if the user does not return in time.
2. **Defeat-limit strong-enemy candidate**: when consecutive defeats reach `battle_max_defeat`, stop the existing automatic give-up path and instead enter an indefinite intervention pause with no timeout, no automatic flee, and no automatic give-up. This state is intended to let the user return and use the existing external workflow to register a newly discovered strong enemy.

`NemesisIntervention` remains the owner/name for this lifecycle in this task. Generalization to a broader `BattleIntervention` abstraction is explicitly deferred until another battle-interruption use case exists.

## Responsibility Boundary

This task owns:

- extending `NemesisIntervention` to support bounded and indefinite intervention policies;
- integrating the existing consecutive-defeat threshold with the indefinite intervention policy;
- explicit `Shift+C` acknowledgement semantics for an active intervention;
- Chinese CLI and Discord notification wording for the two intervention reasons;
- migration of the shared nemesis-intervention configuration;
- consolidation of strong-enemy template files under one `templates/nemesis/` hierarchy while preserving domain/dungeon applicability;
- gating every automatic timeout/watchdog/recovery/relaunch/give-up path necessary to preserve defeat-limit indefinite pause;
- focused deterministic tests for the above behavior.

This task does not take ownership of:

- general state-machine pause/resume semantics beyond the intervention arbitration required here;
- Discord transport implementation;
- strong-enemy image matching architecture beyond path migration and existing scope selection;
- the external strong-enemy registration workflow;
- unrelated battle-stall/relaunch policy except where it must be suppressed while an indefinite intervention owns the pause.

## Desired Behavior

### 1. Known strong enemy

When an already configured strong-enemy template is detected:

```text
known strong enemy detected
    -> NemesisIntervention starts
    -> automation pauses immediately
    -> CLI prints operator guidance including `Shift+C`
    -> Discord sends operator guidance including `Shift+C`
    -> grace countdown starts (default 180 seconds)

        |-- Shift+C before timeout
        |      -> acknowledge that the user has returned
        |      -> cancel the grace timeout
        |      -> remain PAUSED indefinitely for manual handling
        |
        `-- no Shift+C before timeout
               -> preserve current timeout recovery
               -> execute the existing strong-enemy flee subflow
```

`Shift+C` means **Come / user has returned / acknowledge intervention**. It is not a Resume command.

### 2. Consecutive defeat limit

When consecutive defeats reach the configured `battle_max_defeat` threshold (currently default 30):

```text
defeat_count reaches battle_max_defeat
    -> do NOT enter the existing automatic give-up flow
    -> start defeat-limit NemesisIntervention
    -> automation pauses immediately
    -> CLI prints a distinct Chinese warning including `Shift+C`
    -> Discord sends a distinct Chinese warning including `Shift+C`
    -> no timer is armed
    -> remain PAUSED indefinitely
```

The notification should communicate that the configured consecutive-defeat limit has been reached and that an unregistered strong enemy may have been encountered.

When the user later presses `Shift+C`:

```text
Shift+C
    -> acknowledge that the user has returned
    -> intervention remains PAUSED
    -> no automatic battle action is triggered
```

The user may then perform the separate existing/manual strong-enemy registration workflow. This task does not capture screenshots or implement that registration flow.

## Hotkey Contract

`Shift+C` is the explicit intervention acknowledgement / `Come` command.

Required semantics:

- it is meaningful only through the intervention/hotkey arbitration boundary established by the implementation;
- for a timed known-strong-enemy intervention, it cancels the countdown and converts the intervention into indefinite manual takeover while remaining paused;
- for a defeat-limit indefinite intervention, it records/acknowledges that the user has returned while remaining paused;
- it must not implicitly call normal Resume;
- normal pause/resume controls retain their existing ownership and semantics outside the intervention behavior required by this task.

The exact current hotkey owner and any collision with existing shortcuts must be established by Scout before Final SPEC.

## Notification Contract

Both intervention reasons must produce user-facing guidance in **both CLI and Discord**.

Both must explicitly mention:

```text
Shift+C
```

so the operator does not need prior knowledge of the acknowledgement control.

The two reasons must be visibly distinguishable in notification text:

- known/configured strong enemy detected;
- consecutive defeat limit reached / possible unregistered strong enemy.

Notification text should use the repository's existing notification dictionary/i18n ownership rather than embedding transport-specific strings in battle/result handlers.

Only Chinese (`zh-TW`) wording is required by this task. English copy is deferred.

## Configuration Migration

Remove the existing nemesis-intervention settings from `[notification]`:

```toml
[notification]
nemesis_intervention_grace_period_seconds = 60.0
nemesis_intervention_notification_count = 5
```

The canonical shared configuration becomes:

```toml
[nemesis_intervention]
grace_period_seconds = 180.0
notification_count = 5
```

The consecutive-defeat indefinite intervention does not use `grace_period_seconds`; it must be represented as a real no-timeout/indefinite policy rather than an arbitrarily large timeout value.

`battle_max_defeat` remains owned by the existing battle/defeat configuration. This task must not duplicate that threshold inside `[nemesis_intervention]`.

Scout must identify any mode-level duplicates or profile/config compatibility implications before Final SPEC. Redundant mode-level nemesis intervention settings should not remain as competing configuration sources unless evidence shows they are intentionally required.

## Strong-Enemy Template Layout

Consolidate the physical strong-enemy templates under:

```text
templates/
└─ nemesis/
   ├─ domain/
   │  └─ golden_empire/
   │     └─ <existing domain strong-enemy images>
   └─ dungeon/
      └─ <existing dungeon strong-enemy images>
```

The expected change is primarily a `git mv` plus configuration/reference migration.

Physical consolidation must **not** flatten applicability semantics. Domain detection must continue to use only the relevant domain templates, and dungeon detection must continue to use only the relevant dungeon templates. The implementation must not respond by matching every strong-enemy image in every mode.

## Known Invariants

1. **最大戰敗次數到達後，在沒有使用者明確動作前，不允許任何 timeout、watchdog 或 recovery path 自動讓這場戰鬥離開永久 pause。**
2. The invariant above includes every discovered path capable of causing battle give-up, flee, state transition, watchdog recovery, game relaunch/restart, timeout recovery, or equivalent automatic escape while defeat-limit indefinite intervention is active.
3. Verification must explicitly enumerate and test the relevant automatic escape paths; testing only `NemesisIntervention`'s own timer is insufficient.
4. `NemesisIntervention` remains the class/module concept for this task; do not rename it to `BattleIntervention`.
5. `Shift+C` acknowledges user return; it does not Resume automation.
6. `Shift+C` acknowledgement leaves both timed-to-manual and already-indefinite intervention flows paused.
7. Known strong-enemy detection without user acknowledgement retains the current automatic flee fallback after the configured grace period.
8. Defeat-limit intervention has no timeout and no automatic flee/give-up fallback.
9. The state machine remains the owner of the actual pause/resume gate.
10. Notification/i18n infrastructure remains the owner of reusable notification wording/transport-facing message composition.
11. `battle_max_defeat` remains the authoritative defeat threshold.
12. Existing strong-enemy mode applicability is preserved after template relocation.
13. No screenshot capture is added.
14. Behavior outside the specified intervention paths remains preserved unless a change is strictly necessary to uphold the permanent-pause invariant.

## Scope

Expected implementation surfaces include, subject to Scout evidence:

- `states/nemesis_intervention.py`;
- `states/handlers/battle.py`;
- `states/handlers/result.py`;
- the current hotkey/pause-control owner;
- `runtime/notification_i18n.py` and existing notification composition surfaces as needed;
- `config/defaults.toml` and any directly affected config resolution code;
- strong-enemy template paths/config references;
- focused tests around intervention lifecycle, defeat handling, hotkey arbitration, and pause escape-path suppression.

Scout should keep this set narrow and identify the actual owners rather than broadening the task speculatively.

## Non-Goals

- No rename/generalization to `BattleIntervention`.
- No screenshot capture for defeat-limit discovery.
- No implementation or redesign of the strong-enemy registration workflow.
- No English notification copy in this task.
- No broad redesign of battle stall, watchdog, recovery, or relaunch architecture; only the minimum gating/arbitration required to uphold indefinite intervention pause.
- No passive mouse/activity detection as a replacement for explicit `Shift+C` acknowledgement.
- No change to the meaning/default ownership of `battle_max_defeat` beyond routing the terminal defeat outcome into indefinite intervention.
- No unrelated state-machine or CV refactor.

## Provisional Acceptance Criteria

1. Default configuration contains exactly the canonical shared section:

   ```toml
   [nemesis_intervention]
   grace_period_seconds = 180.0
   notification_count = 5
   ```

   and the old nemesis-intervention keys are removed from `[notification]`.

2. Redundant/legacy mode-specific configuration sources are either migrated/removed or explicitly justified by Final SPEC after Scout evidence; there is one unambiguous effective source for the shared defaults.

3. Known strong-enemy intervention immediately pauses automation and emits both CLI and Discord guidance that explicitly contains `Shift+C`.

4. Known strong-enemy intervention uses the configured 180-second default grace period.

5. Pressing `Shift+C` during a known-strong-enemy grace period cancels the timeout and leaves automation paused indefinitely; it does not Resume.

6. If no `Shift+C` acknowledgement occurs before the known-strong-enemy grace expires, the existing strong-enemy flee behavior remains intact.

7. Reaching `battle_max_defeat` no longer enters the existing automatic give-up path. It enters a no-timeout indefinite `NemesisIntervention` pause instead.

8. The defeat-limit intervention emits a distinct Chinese CLI warning and a distinct Chinese Discord warning, and both explicitly contain `Shift+C`.

9. Defeat-limit intervention does not arm a timer, invoke flee, invoke give-up, or automatically transition out of the battle.

10. Pressing `Shift+C` during defeat-limit intervention acknowledges user return but leaves automation paused.

11. Scout/implementation verification identifies every relevant automatic escape mechanism reachable while the battle is paused, including at minimum investigation of:
    - Nemesis intervention timeout/recovery;
    - result-handler give-up continuation;
    - battle max-duration handling;
    - battle stall retry/relaunch handling;
    - state/watchdog recovery paths;
    - generic relaunch/restart requests;
    - normal/manual resume arbitration;
    - any main-loop or recovery behavior capable of progressing the battle despite pause.

12. Focused deterministic tests prove that every applicable discovered automatic escape path is blocked/suspended while defeat-limit indefinite intervention owns the pause, until an explicit user action permits later progression.

13. Existing strong-enemy images are relocated under `templates/nemesis/domain/golden_empire/` and `templates/nemesis/dungeon/`, all tracked references are updated, and domain/dungeon matching scope is preserved.

14. No screenshot capture or English translation work is introduced.

15. Existing behavior unrelated to this task continues to pass its relevant focused regression coverage.

## Uncertainty / Scout Questions

Scout must resolve these before Final SPEC:

1. Where is the current authoritative hotkey/pause-control owner, and does `Shift+C` collide with any existing keyboard binding or input path?
2. What is the smallest clean API change to `NemesisIntervention` for timed versus indefinite policy without encoding infinity as a large numeric timeout?
3. What exact semantics should the existing `request_user_resume()`/resume arbitration retain once `Shift+C` is separated from Resume?
4. Which timeout/watchdog/recovery/relaunch/give-up paths can execute or become pending while the state machine is paused, and which must be explicitly gated versus already naturally blocked by the pause gate?
5. Are there additional supervisor/process watchdogs outside the immediate state-machine handlers that could restart or replace the process during an indefinite intervention?
6. How are Discord notification message IDs currently retained/deleted on acknowledgement, and should the retained history semantics differ between timed and indefinite reasons?
7. Which mode/profile configuration files still define legacy `nemesis_intervention_*` keys, and what compatibility behavior is required when removing the old `[notification]` keys?
8. Which tests already cover `NemesisIntervention`, defeat retry/give-up, pause/resume hotkeys, and watchdog/relaunch behavior, and where are the minimal new focused tests best located?

Until these questions are answered with repository evidence, this SPEC remains Draft and production implementation must not begin.
