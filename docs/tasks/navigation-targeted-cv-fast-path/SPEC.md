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
- This task is about CV work reduction and navigation progress; do not optimize or redesign `time.sleep()` / wait durations in this task.

## Preliminary evidence from lightweight survey

The current `main` at task creation is `2c433caa154a458edfac9235f30eff085b86b6f6`.

Likely hotspots to validate or reject:

1. **Dungeon full-entry scan after target intent is already known**
   - `NavigationHandler` enters the dungeon-select path only after the dungeon tab is observed.
   - It still loops over every configured `dungeon_entries` template and performs `cv2.imread -> resize -> cv2.matchTemplate -> minMaxLoc` each cycle to build `visible_dungeons`.
   - In non-greedy mode, the target dungeon index is already derivable from config/navigation_path before this scan, so scanning every dungeon card may be unnecessary for the common case.

2. **Dungeon relative swipe depends on “any visible dungeon” rather than direct target localization**
   - When the target is not in `visible_dungeons`, current logic chooses the first visible dungeon index and performs a small relative swipe toward the target.
   - Investigate whether, after tab/location lock, a target-specific search plus larger bounded swipe can converge faster without requiring all card identities to be classified every cycle.

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
4. Can non-greedy dungeon navigation safely:
   - derive the target before scanning cards;
   - match only the target card during the steady-state fast path;
   - use a larger bounded directional swipe when the target is absent;
   - periodically or conditionally fall back to anchor/full-card scanning for relocalization?
5. Can the generic reversed `navigation_path` scan be replaced, for committed/known scenes, by a single expected next-edge match without creating a second policy engine?
6. Which existing tests already lock the required behavior, and what focused tests would be needed for match-count/perception-scope behavior?
7. What measurable acceptance criterion should be used (for example matcher-call count per steady-state frame, number of entry templates scanned, or deterministic fake-matcher call assertions) without depending on wall-clock timing?
8. What invalidation/fallback conditions are required so optimization never turns stale location assumptions into blind actions?

## Uncertainty

- Whether greedy dungeon mode can use the same optimization as fixed-target mode is intentionally unresolved; Scout should separate these cases.
- It is not yet established whether template I/O/loading is cached inside `TemplateMatcher` sufficiently to make `cv2.imread` cost secondary; measure/control-flow evidence is needed.
- It is not yet established whether SceneDetector’s global dungeon/result/battle checks are material contributors versus necessary safety cost; Scout must distinguish mandatory safety perception from avoidable target-navigation perception.
- The proper architecture surface may be a committed perception request/profile, a next-edge resolver, or a smaller local optimization in `NavigationHandler`; Scout should provide evidence rather than prematurely choosing one.

