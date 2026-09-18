# Nemesis Template Policy Routing

Status: Final

## Goal

Make Nemesis encounter behavior driven by the specific detected template/encounter instead of one mode-level `nemesis_action` switch.

The task also fixes the observed failure mode where configured Nemesis templates may all resolve to missing paths and detection silently produces an empty score summary.

## Problem Evidence

Observed runtime log repeatedly enters Nemesis checking but prints no configured template scores:

```text
🔍 [領域強敵比對 第 1/3 次] 畫面相似度 (門檻 0.75) ➔
```

Current `BattleHandler._check_and_handle_nemesis_encounter()` obtains a non-empty Nemesis template list, but only attempts matching for entries whose `templates/<path>` exists. Therefore a non-empty configured list with zero valid paths becomes a silent no-op.

Current defaults moved Dungeon Nemesis images under `templates/nemesis/dungeon/...`. Profile/local overrides can replace list-valued `nemesis_templates` wholesale, so stale old paths can bypass the new defaults.

Current behavior routing is mode-scoped:

```toml
nemesis_action = "pause" | "flee"
nemesis_templates = [...]
```

This forces all Nemesis encounters in one mode to share one action even when some enemies are manually recoverable and others are known unwinnable.

## Architecture Decision

Nemesis identity is visual evidence. Policy belongs to the detected template, not to the current game mode.

Canonical runtime flow:

```text
battle frame
  -> scan configured Nemesis templates
  -> match specific template
  -> resolve template policy
       |- intervene
       |    -> existing timed NemesisIntervention
       |    -> Shift+C acknowledges arrival
       |    -> Ctrl+Space resumes after manual handling
       |
       |- flee
            -> existing immediate Nemesis flee subflow
```

Defeat-limit fallback remains independent:

```text
no known template match
  -> repeated defeats
  -> battle_max_defeat
  -> existing INDEFINITE intervention
```

## Canonical Configuration Contract

Nemesis routing is globally managed in one place.

```toml
[nemesis]
intervene = [
    "nemesis/dungeon/ice_boss_calvia_body.png",
    "nemesis/domain/golden_empire/golden_king.png"
]

flee = [
    "nemesis/dungeon/dragon_karsos.png",
    "nemesis/dungeon/dragonkin_sakroth.png",
    "nemesis/domain/golden_empire/elf_mythril_hag.png"
]
```

The exact membership of each list is user-configurable. The implementation must not infer policy from folder names or current game mode.

Semantics:

- `nemesis.intervene`: matched template starts the existing timed Nemesis intervention flow.
- `nemesis.flee`: matched template immediately executes the existing Nemesis flee subflow.
- A template must not appear in both lists.
- Dungeon / Golden Empire templates may coexist in the same global lists.
- Runtime scans the union of both lists during the bounded opening Nemesis check and dispatches based on the matched template's configured policy.

## Scope

Expected production surfaces:

- `states/handlers/battle.py`
- `config.py`
- `config/defaults.toml`
- focused Nemesis/config behavior tests

Existing `NemesisIntervention` lifecycle remains the owner of timed/indefinite operator intervention.

## Known Invariants

1. Nemesis matching runs before auto-battle activation.
2. Existing template matcher semantics/threshold remain unchanged unless direct evidence proves the matcher itself is defective.
3. Existing timed intervention semantics from `nemesis-intervention-unification` remain unchanged.
4. Existing defeat-limit INDEFINITE intervention remains unchanged and is not replaced by image routing.
5. Existing Nemesis flee subflow remains the action implementation for `flee`.
6. A configured template has exactly one explicit policy.
7. Runtime must not infer policy from directory/file naming conventions.
8. Runtime must not infer policy from current game mode.
9. Missing configured templates must not silently look like “no Nemesis found.”
10. Supervisor behavior remains out of scope.
11. No new CV model/detector is introduced; this remains template matching.
12. The bounded opening check count remains three unless existing tests require an equivalent preservation mechanism.

## Missing-Template Observability

Required behavior:

- If a configured Nemesis template path does not exist, emit a bounded WARNING containing the missing relative path.
- Do not repeatedly spam the same missing-path warning within the same battle opening check.
- If `nemesis.intervene` + `nemesis.flee` is non-empty but zero configured template files are valid/existing, emit one explicit high-signal diagnostic.
- Do not print an empty score summary that appears to represent a real comparison.
- Runtime remains fail-open for this condition: continue normal battle flow while preserving defeat-limit protection. Do not crash the bot solely because all configured Nemesis files are missing.

## Configuration Validation

The config boundary must reject ambiguous or malformed Nemesis policy configuration.

Required validation:

- `nemesis.intervene` and `nemesis.flee` are lists of non-empty relative template-path strings.
- A template path cannot appear in both lists.
- Unsupported action names are impossible because action is represented by the list key, not arbitrary per-record text.
- Missing files are runtime observability failures, not TOML syntax/config-shape failures.

## Legacy Configuration Migration

The old mode-level routing contract is removed as authoritative behavior:

```toml
nemesis_action = "pause" | "flee"
nemesis_templates = [...]
flee_bosses = [...]
```

Final policy:

- Remove these keys from canonical defaults where they are currently used for Nemesis routing.
- Runtime must not silently fall back to `nemesis_action`, `nemesis_templates`, or `flee_bosses`.
- Stale profile/local overrides containing those keys may remain physically present, but they must not override the new `[nemesis]` policy routing.
- No automatic rewrite of user profile files is required in this task.
- If practical at config load/startup, emit a bounded deprecation WARNING when stale Nemesis legacy keys are present; this is preferred but not required if it would broaden the config layer disproportionately.
- The new global `[nemesis]` table follows normal profile/local deep-merge behavior. Lists replace whole list values when explicitly overridden, consistent with the repository config contract.

## Responsibility Boundary

`BattleHandler` owns encounter detection and dispatch to the already-existing action mechanisms.

It may:

- obtain normalized Nemesis policy config;
- scan configured templates;
- identify the best matching configured template during the bounded opening window;
- route that match to `intervene` or `flee`;
- emit bounded template-path diagnostics.

It must not:

- reimplement `NemesisIntervention`;
- own pause/resume lifecycle state;
- invent a second flee implementation;
- change Supervisor behavior;
- redesign generic matcher semantics.

## Non-Goals

- Redesigning `NemesisIntervention`.
- Changing Shift+C / Ctrl+Space semantics.
- Changing defeat-limit behavior.
- Changing Supervisor/restart behavior.
- Reworking the generic template matcher.
- Adding OCR/object detection/ML classification.
- Inferring behavior from `templates/nemesis/intervene/` or `templates/nemesis/flee/` directory names.
- Broad configuration-system refactor.
- Automatically rewriting user profile TOML files.

## Acceptance Criteria

1. A template listed under `nemesis.intervene` starts the existing timed Nemesis intervention when matched.
2. A template listed under `nemesis.flee` immediately executes the existing Nemesis flee subflow when matched.
3. Dungeon and Golden Empire templates can coexist in the same global policy lists.
4. Two different templates encountered under the same game mode can dispatch to different actions.
5. Mode-level `nemesis_action` is no longer consulted to select behavior.
6. Mode-level `nemesis_templates` / `flee_bosses` are no longer authoritative routing sources.
7. A configured missing template emits an explicit bounded diagnostic with the missing relative path.
8. A non-empty global Nemesis configuration with zero valid template files emits one high-signal diagnostic and continues normal battle flow.
9. Existing valid template scores remain observable during the bounded opening check window.
10. Profile/local override behavior for `[nemesis]` follows repository deep-merge/list-replacement semantics deterministically.
11. Existing timed intervention behavior is regression-preserved.
12. Existing defeat-limit INDEFINITE intervention is regression-preserved.
13. Existing immediate flee behavior is regression-preserved.
14. No Supervisor changes.
15. No generic matcher redesign.

## Required Deterministic Tests

Focused coverage must prove at least:

1. `intervene` template match routes to existing timed intervention.
2. `flee` template match routes to existing immediate flee subflow.
3. Mixed policies work in the same runtime mode.
4. Dungeon and Golden Empire templates can coexist in the same global config.
5. Missing one configured template emits a bounded diagnostic while valid templates are still checked.
6. Zero valid configured templates emits a high-signal diagnostic and does not crash or falsely claim a comparison occurred.
7. Duplicate template across `intervene` and `flee` is rejected by config validation.
8. Stale mode-level `nemesis_action` cannot override new template policy routing.
9. Stale mode-level `nemesis_templates` / `flee_bosses` are not used for routing.
10. Existing timed intervention behavior remains unchanged.
11. Existing defeat-limit INDEFINITE intervention remains unchanged.
12. Existing immediate flee behavior remains unchanged.

## Focused Test Targets

At minimum:

- `tests/test_behavior_dungeon_nemesis.py`
- `tests/test_behavior_golden_empire.py`
- `tests/test_nemesis_intervention.py`
- config-focused tests covering Nemesis policy parsing/validation and override semantics

If implementation introduces a new dedicated config test file, update `task.json`.

## Workflow

This task intentionally uses the user-requested two-agent workflow:

- ChatGPT + user own survey, Final SPEC, semantic/architecture review, and integration.
- Gemini is the sole production implementation writer.
- OpenCode Scout is skipped.
- AI Gate is skipped unless the user later explicitly requests it.

Gemini may begin production implementation now that this SPEC is Final.
