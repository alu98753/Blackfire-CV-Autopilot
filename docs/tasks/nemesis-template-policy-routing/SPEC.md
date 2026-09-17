# Nemesis Template Policy Routing

Status: Draft

## Goal

Make Nemesis encounter behavior driven by the specific detected template/encounter instead of one mode-level `nemesis_action` switch.

The task also fixes the observed failure mode where configured Nemesis templates may all resolve to missing paths and detection silently produces an empty score summary.

## Problem Evidence

Observed runtime log repeatedly enters Nemesis checking but prints no configured template scores:

```text
🔍 [領域強敵比對 第 1/3 次] 畫面相似度 (門檻 0.75) ➔
```

Current `BattleHandler._check_and_handle_nemesis_encounter()` obtains a non-empty `nemesis_templates` list, but only attempts matching for entries whose `templates/<path>` exists. Therefore a non-empty configured list with zero valid paths becomes a silent no-op.

Current defaults moved Dungeon Nemesis images under `templates/nemesis/dungeon/...`. Profile/local overrides can replace list-valued `nemesis_templates` wholesale, so stale old paths can bypass the new defaults.

Current behavior routing is mode-scoped:

```toml
nemesis_action = "pause" | "flee"
nemesis_templates = [...]
```

This forces all Nemesis encounters in one mode to share one action even when some enemies are manually recoverable and others are known unwinnable.

## Architecture Decision

Nemesis identity is visual evidence. Policy belongs to the detected encounter/template, not to the current game mode.

Target model:

```text
battle frame
  -> Nemesis template match
  -> matched encounter
  -> encounter policy
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

## Scope

Expected production surfaces:

- `states/handlers/battle.py`
- `config.py`
- `config/defaults.toml`
- focused Nemesis/config behavior tests
- profile/config migration compatibility only where required by the Final contract

Existing `NemesisIntervention` lifecycle remains the owner of timed/indefinite operator intervention.

## Proposed Configuration Contract

Prefer explicit encounter records rather than deriving behavior from folder names.

Provisional shape:

```toml
[[nemesis.encounters]]
template = "nemesis/dungeon/ice_boss_calvia_body.png"
action = "intervene"

[[nemesis.encounters]]
template = "nemesis/dungeon/dragon_karsos.png"
action = "flee"

[[nemesis.encounters]]
template = "nemesis/dungeon/dragonkin_sakroth.png"
action = "flee"
```

Allowed actions for v1:

- `intervene`: use the existing timed Nemesis intervention flow.
- `flee`: immediately execute the existing Nemesis flee subflow.

The exact grouping/location of this table in `defaults.toml` may be refined before Final, but the behavior must be encounter/template-level rather than mode-level.

## Known Invariants

1. Nemesis matching runs before auto-battle activation.
2. Existing template matcher semantics/threshold remain unchanged unless evidence proves they are the defect.
3. Existing timed intervention semantics from `nemesis-intervention-unification` remain unchanged.
4. Existing defeat-limit INDEFINITE intervention remains unchanged and is not replaced by image routing.
5. Existing Nemesis flee subflow remains the action implementation for `flee`.
6. A detected encounter has exactly one explicit policy.
7. Runtime must not infer policy from directory/file naming conventions.
8. Missing configured templates must not silently look like “no Nemesis found.”
9. Supervisor behavior remains out of scope.
10. No new CV model/detector is introduced; this remains template matching.

## Missing-Template Observability

The current silent behavior is unacceptable.

Required provisional behavior:

- If a configured Nemesis template path does not exist, emit a bounded WARNING containing the missing relative path.
- If a configured encounter set is non-empty but zero configured templates are valid/existing, emit an explicit high-signal diagnostic.
- Do not print an empty score summary that appears to represent a real comparison.
- Exact fail-open vs fail-closed runtime behavior for “zero valid templates” is an explicit Final-SPEC decision. Current preference: fail visibly without crashing the whole bot, while preserving defeat-limit protection.

## Legacy Configuration / Migration

Provisional intent:

- Remove mode-level `nemesis_action` as the authoritative routing source.
- Remove mode-level `nemesis_templates` as the authoritative policy source once encounter routing is adopted.
- Do not silently retain hidden legacy fallbacks that can reintroduce stale template paths.
- User/profile overrides must have a clear migration behavior; list replacement semantics in `_deep_merge()` are part of the bug surface and must be tested.
- Whether old keys fail-fast, warn-and-ignore, or receive one explicit compatibility migration is unresolved until Final.

## Non-Goals

- Redesigning `NemesisIntervention`.
- Changing Shift+C / Ctrl+Space semantics.
- Changing defeat-limit behavior.
- Changing Supervisor/restart behavior.
- Reworking the generic template matcher.
- Adding OCR/object detection/ML classification.
- Inferring behavior from `templates/nemesis/intervene/` or `templates/nemesis/flee/` directory names.
- Broad configuration-system refactor.

## Provisional Acceptance Criteria

1. A Dungeon encounter configured with `action = "intervene"` starts the existing timed Nemesis intervention when its image matches.
2. A Dungeon encounter configured with `action = "flee"` immediately executes the existing Nemesis flee subflow when its image matches.
3. Domain and Dungeon encounters can independently assign different actions per template.
4. Mode-level `nemesis_action` is no longer needed to select behavior.
5. A configured missing template emits an explicit diagnostic with the missing path.
6. A non-empty configured encounter set with zero valid template files cannot silently log an empty “score summary.”
7. Existing-template scores remain observable during the bounded 3-check opening window.
8. Profile/local override behavior cannot silently resurrect stale pre-migration paths without a diagnostic.
9. Existing timed intervention behavior is regression-preserved.
10. Existing defeat-limit INDEFINITE intervention is regression-preserved.
11. Existing immediate flee behavior is regression-preserved.
12. No Supervisor changes.
13. Focused deterministic tests cover:
    - per-template intervene routing;
    - per-template flee routing;
    - mixed policies in the same mode;
    - missing one configured template;
    - zero valid configured templates;
    - stale profile/list override behavior;
    - no fallback to removed mode-level `nemesis_action`;
    - no regression to defeat-limit intervention.

## Uncertainty To Resolve Before Final

1. Exact canonical TOML location/schema:
   - global `[[nemesis.encounters]]`, or
   - mode-local encounter records with policy per item.
2. Exact backward-compatibility behavior for old `nemesis_action` / `nemesis_templates` profile overrides.
3. Whether “configured encounters exist but zero template files exist” should:
   - warn and continue with defeat-limit fallback, or
   - fail-fast at config/startup validation.
4. Which current Dungeon Nemesis image(s) should default to `intervene` vs `flee`; user intent/config will determine defaults rather than code inference.

## Workflow Note

This task intentionally uses a two-party implementation workflow requested by the user:

- ChatGPT + user own survey/spec/review/integration.
- Gemini is the production implementation writer after `Status: Final`.
- OpenCode Scout and AI Gate are intentionally skipped for this task unless the user later requests them.
