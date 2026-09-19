# navigation-targeted-cv-fast-path

Status: Draft

## Goal

Reduce unnecessary CV work specifically inside the `NAVIGATION` state for lobby-mode navigation among:

- `lord`
- `stage`
- `domain`
- `dungeon`
- `demon_lord`

The optimization target is limited to two cases:

1. **cross-mode switching** inside the lobby, such as `domain -> stage`, `stage -> dungeon`, `dungeon -> lord`, etc.;
2. **same-mode horizontal navigation**, such as `stage 2 -> stage 7`, `stage 7 -> stage 2`, `dungeon 2 -> dungeon 7`, etc.

The task is not a general CV optimization. It is a scoped navigation-perception optimization.

## Core contract

Broad CV is permitted for scene/postcondition verification and initial in-mode localization. Once the current mode is scene-confirmed and a same-mode card anchor has been positively observed, navigation may enter a target-tracking fast path that matches only the committed target after each bounded directional swipe.

Cross-mode transitions must invalidate card-position knowledge.

Action history, requested mode, navigation state, or previous mode/card position must never satisfy a scene postcondition.

### Scene remains the only postcondition authority

Example:

```text
Stage active
-> click Dungeon entry
-> Dungeon postcondition is NOT yet satisfied
-> only current-frame Scene evidence may confirm Dungeon active
```

Therefore:

```text
action issued != postcondition satisfied
navigation state != scene truth
requested mode != observed mode
```

A cross-mode switch such as `Stage -> Dungeon` must first be visually confirmed as Dungeon before any Dungeon-local route knowledge may be established.

## Scope

Survey first. No production implementation while this SPEC is Draft.

Primary production/reference surfaces:

- `states/handlers/navigation.py`
- `utils/scene_detector.py`
- `states/navigation_routing.py`
- `utils/card_navigator.py`
- `vision/matcher.py`

Focused tests should be limited to navigation behavior for the five scoped lobby modes and their card/list movement.

### In-scope case A — cross-mode switching

Examples:

```text
domain -> stage
domain -> dungeon
stage -> dungeon
dungeon -> stage
lord -> demon_lord
demon_lord -> domain
```

The important boundary is:

- clicking the target mode/tab is only an action;
- the target mode/tab postcondition must be proven by Scene/current-frame visual evidence;
- horizontal/card position from the previous mode must not be inherited.

Example:

```text
Stage 7 visible
-> click Dungeon
-> screen may happen to show Dungeon 6/7/8
```

This does **not** establish any architectural relationship between Stage 7 and Dungeon 7.

The Dungeon mode must first be visually confirmed, then Dungeon-local position must be acquired from Dungeon evidence.

### In-scope case B — same-mode horizontal navigation

Once all of the following are visually established within the same mode:

1. current mode is confirmed by Scene;
2. a current same-mode anchor/card has been positively observed;
3. committed target is known;

the route may enter a target-tracking fast path.

Example:

```text
Scene = Dungeon
observed anchor = Dungeon 2
target = Dungeon 7

=> direction toward higher index is known
=> after swiping, only Dungeon 7 needs to be matched in steady state
=> unrelated Dungeon cards do not need to be reclassified every cycle
```

Likewise:

```text
Scene = Stage
observed anchor = Stage 7
target = Stage 2

=> direction toward lower index is known
=> steady-state tracking may match only Stage 2
```

This retained knowledge is **same-mode verified route knowledge**, not a navigation-state position prior.

It must not claim an estimated exact intermediate card after a swipe unless that card was actually observed.

## Known invariants

- `NavigationIntentPolicy` remains the owner of intent/routing semantics.
- Scene/perception remains evidence-producing and must not become a second routing-policy owner.
- Scene/current-frame visual evidence is the sole authority for mode/tab postconditions.
- Cross-mode switching invalidates card-position knowledge.
- A previous mode's card/index must never be used as a position prior for another mode.
- A click/action never proves its own postcondition.
- Navigation state never substitutes for scene evidence.
- Initial localization inside a newly confirmed mode may use broad CV.
- After same-mode localization succeeds, steady-state target tracking should prefer only the committed target template.
- Broader CV is allowed again only for bounded fallback/relocalization when target tracking loses confidence or progress.
- Safety/recovery evidence must not be removed merely for speed.
- No blind fixed-coordinate navigation.
- No behavior change to mode selection, task priority, cooldown policy, or recovery semantics.
- Do not optimize or redesign `time.sleep()`, animation waits, debounce, or polling intervals in this task.

## Preliminary evidence from lightweight survey

The task branch was created from main commit:

`2c433caa154a458edfac9235f30eff085b86b6f6`

Current likely hotspot:

### Dungeon full-entry scan

Within `NavigationHandler`, after Dungeon tab evidence is already present, the code may still iterate over all configured `dungeon_entries` and perform per-template OpenCV matching to reconstruct `visible_dungeons`.

For fixed-target navigation, this appears broader than necessary once:

```text
Scene = Dungeon
same-mode anchor observed
target dungeon known
```

The Scout must verify whether equivalent broad behavior also exists for:

- Stage
- Domain
- Lord
- Demon Lord

and distinguish initial localization from steady-state target tracking.

## Required perception lifecycle

The Scout should evaluate the following model:

```text
CROSS-MODE SWITCH
    |
    v
Scene/postcondition verification
    |
    v
INITIAL IN-MODE LOCALIZATION
    broad enough to establish one same-mode anchor
    |
    v
TARGET TRACKING
    committed target only
    + directional swipe
    + target-only CV
    |
    +--> target found -> click
    |
    +--> bounded misses / contradiction / scene lost
             |
             v
        RELOCALIZATION
             |
             +--> broad same-mode CV again
```

### Important boundary

The fast path may retain:

```text
last_verified_anchor = stage_2
target = stage_7
direction = right
```

It must not invent:

```text
after one swipe, current_position = stage_4
```

unless Stage 4 was actually observed.

## Survey questions

Scout should answer only within the scoped five modes and the `NAVIGATION` state:

1. For `lord / stage / domain / dungeon / demon_lord`, what CV runs during cross-mode switching before the target mode Scene postcondition is confirmed?
2. Which of those matches are required to prove the postcondition, and which are redundant?
3. After the target mode is confirmed, how is initial same-mode card/route localization currently performed?
4. For each scoped mode, does the implementation continue scanning multiple cards/templates after a same-mode anchor and committed target are already known?
5. Where can broad card scanning safely stop and target-only matching begin?
6. What state/data should represent the minimal retained same-mode route knowledge without turning navigation state into scene truth?
7. What events must invalidate that retained route knowledge?
8. For same-mode movement such as `2 -> 7` or `7 -> 2`, can the current swipe amplitude be increased while preserving bounded fallback and without requiring intermediate-card classification?
9. What deterministic tests can prove the optimization using matcher-call/template-scope assertions instead of wall-clock timing?
10. Which current code paths violate or duplicate the desired `Scene verification -> localization -> target tracking -> relocalization` lifecycle?

## Provisional acceptance criteria

A Final SPEC should be possible once Scout provides evidence for all of the following:

1. Exact CV call/template sets for cross-mode switching among the five scoped modes.
2. Exact CV call/template sets for initial localization within each relevant mode.
3. Exact broad scans that continue unnecessarily after same-mode localization.
4. A clear rule for entering target-only tracking.
5. A clear rule for invalidating target-only tracking.
6. Cross-mode transitions demonstrably discard previous card-position knowledge.
7. Scene/current-frame evidence remains the sole mode/tab postcondition authority.
8. Same-mode fast path never treats swipe history as proof of exact position.
9. Match-count/template-scope focused tests can verify the reduction deterministically.
10. No changes outside the scoped `NAVIGATION` paths are required to satisfy the task.

## Non-goals

- Any state other than `NAVIGATION`.
- Dungeon exploring/combat logic after entering the dungeon.
- Domain explore logic after entering the domain.
- Battle, result, collection, backpack, town-subflow, login, recovery, or scheduler optimization.
- General SceneDetector optimization outside what is necessary for the five scoped lobby modes.
- General OpenCV/TemplateMatcher performance work.
- Greedy task scheduling or task-priority redesign.
- Cooldown semantics redesign.
- `time.sleep()`, delay, debounce, animation-wait, polling-frequency, or timeout tuning.
- Blind coordinate-based movement.
- Cross-mode position priors.
- Using navigation state or action history as Scene/postcondition evidence.
- Production implementation while this SPEC remains Draft.

## Uncertainty

- The exact broad-scan behavior may differ among Stage, Dungeon, Domain, Lord, and Demon Lord.
- Some modes may already have partial target-specific handling while others may still use generic reversed `navigation_path` scans.
- Swipe amplitude and bounded retry count should not be finalized until Scout identifies the actual UI/card navigation contracts and existing focused tests.
- Greedy Dungeon semantics may require broader perception than fixed-target Dungeon navigation; Scout should report this only where it directly affects the scoped navigation fast path, not expand into scheduler redesign.
