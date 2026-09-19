# navigation-targeted-cv-fast-path

Status: Draft

## Goal

Reduce navigation latency caused by unnecessary OpenCV/template matching after the active intent, target, and current navigation location/tab are already known.

The desired direction is a targeted perception fast path: once the system has committed to a specific destination and has sufficient scene/tab evidence, perception should prefer the minimum target-specific evidence needed to make forward progress instead of repeatedly performing broad scans.

## Scope

Survey first. No production implementation while this SPEC is Draft.

Primary survey surfaces:
- `states/handlers/navigation.py`
- `utils/scene_detector.py`
- `states/navigation_routing.py`
- `utils/card_navigator.py`
- `vision/matcher.py`
- navigation/dungeon focused tests around target selection and horizontal scrolling

The survey must identify concrete CV hot paths that still run after:
1. the active intent is already committed;
2. the primary target is already known;
3. the expected tab/location has been positively confirmed.

Pay special attention to:
- dungeon card navigation;
- generic reversed `navigation_path` scans;
- SceneDetector checks that may duplicate later handler-level matching;
- repeated full-list matching when only one target template is needed;
- frame-local cache misses caused by the same semantic evidence being queried with different thresholds/options.

## Known invariants

- `NavigationIntentPolicy` remains the owner of intent/routing semantics.
- Scene/perception remains evidence-producing; it must not become a second navigation policy owner.
- Do not remove safety/recovery evidence merely for speed.
- Do not replace objective relocalization with blind coordinate clicking.
- When location/tab evidence becomes uncertain, the system must be able to fall back to broader perception/relocalization.
- Existing behavior for dungeon cooldown/unavailable detection, locked entries, overlays, battle/dungeon-entry transitions, recovery, and state transitions must remain safe.
- A target-specific fast path must have a clear invalidation condition and bounded fallback.
- Cross-mode/tab switching must not inherit a horizontal card-position assumption from the previous mode. For example, Stage 7 -> Dungeon does not imply the Dungeon view is at index 7.
- A mode/tab transition postcondition is satisfied only by current-frame visual evidence. Intent, requested tab, previous route, or prior horizontal index are not sufficient evidence that the new mode/tab is active.
- Target-only steady-state matching is allowed only after two facts have been established by visual evidence within the same mode: (1) the requested mode/tab postcondition is positively confirmed, and (2) the current route/card position has been localized at least once in that mode.
- After same-mode localization succeeds (for example, current dungeon card/index = 2 and fixed target = 7), navigation may retain that route-localization state and stop re-scanning unrelated card identities on every swipe. Subsequent steady-state frames should prefer target-only verification, with broader relocalization only when the retained route state is invalidated or progress becomes contradictory.
- This task is about CV work reduction and navigation progress; do not optimize or redesign `time.sleep()` / wait durations in this task.

## Preliminary evidence from lightweight survey

The current `main` at task creation is `2c433caa154a458edfac9235f30eff085b86b6f6`.

Likely hotspots to validate or reject:

1. **Dungeon full-entry scan after target intent is already known**
   - `NavigationHandler` enters the dungeon-select path only after the dungeon tab is observed.
   - It still loops over every configured `dungeon_entries` template and performs `cv2.imread -> resize -> cv2.matchTemplate -> minMaxLoc` each cycle to build `visible_dungeons`.
   - In non-greedy mode, the target dungeon index is already derivable from config/navigation_path before this scan, so scanning every dungeon card may be unnecessary for the common case.

2. **Dungeon relative swipe depends on repeated broad localization rather than retained same-mode route state**
   - When the target is not in `visible_dungeons`, current logic chooses the first visible dungeon index and performs a relative swipe toward the target.
   - Required semantic boundary: entering Dungeon from Stage/Domain/Lord does not establish Dungeon position. The Dungeon tab postcondition and an initial Dungeon card/index localization must come from current visual evidence.
   - After that one-time same-mode localization succeeds (for example, current Dungeon index = 2, target = 7), investigate retaining the localized route position and using target-only matching on subsequent swipes instead of reclassifying all Dungeon cards every cycle.
   - The fast path must fall back to broader relocalization when target-only progress contradicts the retained route state or reaches a bounded no-progress condition.

3. **Generic reversed navigation-path matching after scene/tab evidence is already available**
   - Later in `NavigationHandler.handle()`, `filtered_nav_path` is scanned in reverse and each candidate template is matched until one succeeds.
   - Survey whether committed intent + confirmed current scene can select a single expected next edge/template instead of probing several historical path elements.

4. **SceneDetector plus handler-level duplicate perception**
   - `SceneDetector.detect()` already performs global safety/scene checks and expected-tab fast-path matching.
   - The same frame then enters additional handler-level matches for domain explore, target/card alignment, card scans, door/overlay checks, stage labels/targets, and generic nav path.
   - Identify duplicated semantic evidence where the detector result can be reused rather than independently re-matched.

5. **Expected-tab fast path is scoped only to tab resolution, not downstream navigation evidence**
   - `resolve_detection_request()` already emits `EXPECTED_TAB` when a route is committed.
   - `SceneDetector` limits tab matching in that case, but downstream target/card selection still often uses broad matching.
   - Survey whether this existing request/context should carry enough information to enable a downstream “committed target perception profile”.

## Non-goals

- No `time.sleep()`, delay, debounce, cooldown, animation-wait, or polling-interval tuning in this task.
- No change to task priority, intent precedence, scheduler behavior, dungeon cooldown policy, greedy-vs-fixed target semantics, or recovery semantics.
- No blind fixed-coordinate navigation.
- No wholesale replacement of OpenCV or TemplateMatcher.
- No broad codebase CV micro-optimization unrelated to navigation after target commitment.
- No production implementation while SPEC is Draft.

## Provisional acceptance criteria

Scout should produce evidence sufficient to finalize a narrowly scoped optimization task by answering:

1. What are the top 3-5 CV-heavy navigation paths that still run after intent/target/location are committed?
2. For each, exactly which templates are matched, how many may be matched per frame/tick, and which results are actually needed for the next action?
3. Which matches are safety/relocalization evidence that must remain broad, versus target-progress evidence that can become narrow?
4. Can non-greedy dungeon navigation safely implement a two-phase perception model:
   - **acquisition/relocalization phase**: after entering Dungeon, first prove the Dungeon tab postcondition from current-frame visual evidence and localize the current Dungeon card/index without assuming any position inherited from Stage/Domain/Lord;
   - **steady-state route phase**: once current Dungeon index and fixed target are known in the same mode, retain that route-localization state, match only the target card on subsequent swipes, and avoid re-scanning unrelated Dungeon identities;
   - use bounded directional swipes derived from the retained same-mode route relation (current index vs target index);
   - conditionally return to broader card/anchor scanning only when the retained route state is invalidated, target-only progress stalls, contradictory evidence appears, or mode/tab postcondition is lost?
5. Can the generic reversed `navigation_path` scan be replaced, for committed/known scenes, by a single expected next-edge match without creating a second policy engine?
6. Which existing tests already lock the required behavior, and what focused tests would be needed for match-count/perception-scope behavior?
7. What measurable acceptance criterion should be used (for example matcher-call count per steady-state frame, number of entry templates scanned, or deterministic fake-matcher call assertions) without depending on wall-clock timing?
8. What invalidation/fallback conditions are required so optimization never turns stale location assumptions into blind actions?

## Uncertainty

- Whether greedy dungeon mode can use the same optimization as fixed-target mode is intentionally unresolved; Scout should separate these cases.
- It is not yet established whether template I/O/loading is cached inside `TemplateMatcher` sufficiently to make `cv2.imread` cost secondary; measure/control-flow evidence is needed.
- It is not yet established whether SceneDetector’s global dungeon/result/battle checks are material contributors versus necessary safety cost; Scout must distinguish mandatory safety perception from avoidable target-navigation perception.
- The proper architecture surface may be a committed perception request/profile, a next-edge resolver, retained same-mode route-localization state, or a smaller local optimization in `NavigationHandler`; Scout should provide evidence rather than prematurely choosing one.
- The task explicitly rejects cross-mode horizontal position priors as an optimization premise. Any retained position state must be scoped to a visually confirmed mode and invalidated when leaving that mode unless fresh evidence re-establishes it.

