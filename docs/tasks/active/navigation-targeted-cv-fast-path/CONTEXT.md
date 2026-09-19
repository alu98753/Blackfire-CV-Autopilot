Now let me inspect the core production files in the task scope.
Let me read deeper into the navigation handler, particularly the dungeon detection and card scanning paths.
Let me continue reading the navigation handler to understand the dungeon detection, card scanning, and navigation flow.
Let me find the main navigation handling entry point and the dungeon detection flow.
# Scout Report: navigation-targeted-cv-fast-path

## Statement of Maximum Steps

The maximum exploration budget (8 files) has been reached. I've read the core production and routing files within budget and must now finalize the report without further exploration.


# Scout Context

## Relevant files and symbols

| File | Why it matters |
|------|---------------|
| `docs/tasks/active/navigation-targeted-cv-fast-path/SPEC.md` | Canonical spec defining the fast-path lifecycle: Scene verification ??initial localization ??target-only tracking ??relocalization |
| `docs/tasks/active/navigation-targeted-cv-fast-path/task.json` | Declares scope (7 files) and focused test files |
| `states/handlers/navigation.py` (1355 lines) | Primary production surface; contains `NavigationHandler.handle()`, dungeon full-entry scan (`:800-1042`), card alignment, sub-stage scroll, and all five lobby-mode navigation paths |
---
| `utils/card_navigator.py` (152 lines) | `CardListNavigator` ??provides `swipe_towards_target()`, `align_first_card()`, `reset_to_left()`; no fast-path awareness yet |
| `utils/scene_detector.py` (721 lines) | `SceneDetector` ??scene/postcondition verification; imports from `scene_types` and `scene_snapshot` |
| `states/navigation_routing.py` (395 lines) | `NavigationIntentPolicy`, `resolve_detection_request()`, `resolve_navigation_context()` ??intent/routing ownership; detection request construction with `LobbyTabScope.EXPECTED_TAB` vs `FULL_RELOCALIZE` |
| `vision/matcher.py` (367 lines) | `TemplateMatcher` ??OpenCV template matching with multi-scale, NMS, pyramid precheck, brightness filter |
| `states/handlers/navigation.py:640` | `handle()` entry point ??the main per-frame dispatch |
## Current control flow


1. **Entry**: `NavigationHandler.handle(screen_img, rect)` at line 640
2. **Scene detection**: Calls `resolve_detection_request(machine)` ??builds `SceneDetectionRequest` with `DetectionProfileId` per target tab and `LobbyTabScope.EXPECTED_TAB` or `FULL_RELOCALIZE`
3. **Routing**: `resolve_navigation_context()` ??`NavigationIntentPolicy.resolve(scene, intent)` ??`ActionDecision`
4. **Card alignment**: `_handle_primary_card_alignment()` ??first-card anchor detection using `CardListNavigator.align_first_card()` for stage/dungeon/domain tabs
5. **Dungeon full-entry scan**: Lines ~800-1042 iterate over ALL `dungeon_entries` templates, running per-template `match_current_frame()` to build `visible_dungeons` dict, even when target is already known
6. **Swipe dispatch**: `CardListNavigator.swipe_towards_target(mouse, rect, visible_idx, target_idx)` ??pure mechanical swipe, no fast-path awareness
7. **Post-swipe**: After swipe, the full-entry scan repeats on next frame ??this is the key redundancy the spec targets

**For Stage/Domain/Lord/Demon Lord**: The handler follows analogous patterns using `config.get("stage_templates")`, `config.get("domain_entry_btn")`, etc. Each performs broader-than-necessary CV scans after localization.

## Existing safety mechanisms

- `CardListNavigator.align_first_card()` has bounded attempts (`CARD_RESET_MAX_ATTEMPTS=7`) with explicit EXHAUSTED status
- `resolve_detection_request()` already distinguishes `EXPECTED_TAB` (steady-state, 2 templates) from `FULL_RELOCALIZE` (unknown scene, all tabs) ??this is the detection-level fast path that partially exists
- `NavigationProgress` with `InFlightAction` provides timeout/deadline tracking per action
- Sub-stage scroll has bounded retries (`SUB_STAGE_SCROLL_MAX_ATTEMPTS=5`) and cooldown
- `filter_navigation_path()` already prunes already-active tab navigation entries

## Existing tests

- `tests/test_behavior_navigation.py` ??navigation behavior tests
- `tests/test_dungeon_swipe_unit.py` ??unit tests for dungeon swipe mechanics
- `tests/test_behavior_navigation_intent.py` ??intent routing tests
- `tests/test_behavior_navigation_scenarios.py` ??scenario-level navigation tests
- `tests/test_behavior_navigation_progress.py` ??progress/timeout tests (found but not in scope list)

**Not inspected** due to budget; these need review during implementation to verify match-call-count assertion patterns exist or need creation.

## Regression and architecture risks

1. **Dungeon full-entry scan is the primary hotspot**: Lines 800-1042 perform 5-8 template matches per frame against ALL configured `dungeon_entries` even after target is known. This is the highest-value optimization target.
3. **Scene remains postcondition authority**: The routing layer (`resolve_detection_request`) already enforces this via `LobbyTabScope` ??but the fast-path target tracking must not bypass this. Any new fast-path state must be invalidated when scene evidence contradicts.
2. **Cross-mode invalidation**: `_handle_primary_card_alignment()` resets `card_alignment_tab` on target change (`:260-262`), which partially handles cross-mode invalidation, but card-position knowledge in the dungeon scan loop is not explicitly invalidated on mode switch.
4. **Five-mode asymmetry**: Stage uses `stage_templates[]`, dungeon uses `dungeon_entries[]`, domain uses `domain_entry_btn` (single), lord uses `lord_entries[]`, demon_lord uses `demon_lord_entries[]`. The optimization must handle each mode's template structure differently.
5. **Swipe history must not become position proof**: The spec explicitly forbids "after one swipe, current_position = stage_4". `CardListNavigator` is currently stateless ??this is good, but any added fast-path state must preserve this.

## Uncertainty

- **Lord and Demon Lord template structures**: I did not inspect lord_boss.py or demon_lords.py handlers to confirm whether they share the same full-scan pattern as dungeon. The spec lists them as scoped modes but the actual CV call sites need verification within budget was insufficient.
- **Stage template scanning pattern**: The stage path at lines 282-287 reads `config.get("stage_templates", [])` but I could not read deep enough to confirm whether stage performs an analogous full-scan loop. This must be verified.
- **`scene_snapshot.py` and `navigation_intent.py`**: These define `SceneDetectionRequest`, `LobbyTabScope`, `NavigationIntentPolicy` ??I know they exist and import correctly but did not read their internals. The fast-path state lifecycle must integrate with these.
- **Test coverage for match-call-count assertions**: Cannot confirm whether existing tests use template-scope assertions that would validate the optimization deterministically.

## Minimal proposed change surface

1. **`states/handlers/navigation.py`** ??Main change file:
   - Add fast-path state fields to `NavigationHandler.__init__()` (target-only tracking: `target_template`, `fast_path_active`, `fast_path_invalidated`)
   - Modify dungeon/stage/domain/lord/demon_lord scan loops (lines ~800-1042 and equivalents) to short-circuit to target-only match when `fast_path_active` is true
   - Add fast-path invalidation on cross-mode switch, scene contradiction, and bounded miss count
   - Ensure `notify_ui_progress()` continues to be called on each swipe for watchdog health

2. **`utils/card_navigator.py`** ??Possibly add a `target_only_match()` convenience method or keep it stateless and let the handler own fast-path logic

3. **`states/navigation_routing.py`** ??Possibly extend `SceneDetectionRequest` or `resolve_detection_request()` to signal when a fast-path is safe (target tab confirmed + anchor observed)

4. **Test files** ??Add match-call-count assertions proving template scope reduction

## Recommendation

**GO WITH SPEC CHANGES** ??The repository evidence confirms the SPEC's identified hotspot (dungeon full-entry scan at lines 800-1042) and shows analogous patterns likely exist for other modes. The routing layer already provides `EXPECTED_TAB` detection scoping, meaning the detection-level fast path partially exists. The remaining work is (a) adding target-only CV matching within the handler's per-mode scan loops after localization succeeds, and (b) defining invalidation rules. Two spec clarifications are needed before implementation:

1. The SPEC should explicitly name which config keys control the template list per mode (`dungeon_entries`, `stage_templates`, `lord_entries`, `demon_lord_entries`, `domain_entry_btn`) to prevent scope creep during implementation.
2. The SPEC should specify whether the fast-path state lives on `NavigationHandler` instance or on `NavigationProgress`/machine, since lifecycle ownership affects cross-state invalidation.
