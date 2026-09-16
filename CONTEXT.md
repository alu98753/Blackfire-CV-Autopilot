# Scout Context: watchdog-long-subflow-timeout-200

Status: Draft SPEC reconnaissance only. No production implementation is authorized until the SPEC is promoted to Final.

## Scope and boundary

The task draft asks Scout to inspect the runtime policy and same-state progress reporting, then provide evidence for a later implementation review. This context records repository observations; it does not change watchdog behavior, configuration, tests, or architecture contracts.

## Verified repository observations

### Watchdog configuration

- `states/exceptions/watchdog.py:92-98` classifies `STATE_NAVIGATING` and the existing long-subflow states, then reads `cfg.get("long_subflow_timeout_sec", 90.0)`. The active code path therefore has a literal 90-second fallback.
- `config/exception_features.json:3-5` defines `non_battle_stuck_timeout_sec: 30.0` and `battle_stuck_timeout_sec: 90.0`, but does not define `long_subflow_timeout_sec`.
- `config.py:627-640` supplies a separate `JsonConfigManager` default containing `battle_stuck_timeout_sec: 90.0`, but no `long_subflow_timeout_sec`.
- `utils/config_manager.py:15-44` permits an optional default: when no valid snapshot exists, `snapshot()` returns the supplied default; malformed reloads retain the last valid snapshot. This supports explicit validation/fail-fast only if the exception configuration caller stops supplying an incomplete numeric fallback or validates required keys.
- `battle_stuck_timeout_sec` has no production read found by repository search outside its definition in `config.py` and `config/exception_features.json`. Its remaining references are documentation, task text, and tests. No distinct live responsibility was verified.

### State and progress ownership

- `states/state_machine.py:669-684` defines `GameStateMachine.notify_ui_progress()` as the state-machine progress signal and updates `last_state_change` plus watchdog stuck memory.
- `states/handlers/base.py:46-51` provides the handler wrapper; handlers normally call this wrapper rather than mutating the timer directly.
- Production direct assignments to `last_state_change` found by search are state initialization/transition (`states/state_machine.py:154,512`), watchdog invalid-timestamp repair (`states/exceptions/watchdog.py:42`), relaunch reset (`states/exceptions/subflows/game_relaunch.py:70`), and the canonical progress method (`states/state_machine.py:684`). No second production progress API was found.

### Current `notify_ui_progress()` call sites

Production call-site files found: `states/handlers/bag_cleaning.py`, `backpack_full_sorting.py`, `bag_tidy.py`, `battle.py`, `bulletin_board.py`, `demon_lords.py`, `jewelry_workshop.py`, `lobby.py`, `lord_boss.py`, and `navigation.py`; `states/domains/base_domain.py` forwards progress through its handler. The calls are distributed across item/phase actions and navigation operations, so semantic review should focus on action success rather than merely call frequency.

In `states/handlers/navigation.py`:

- `_handle_primary_card_alignment()` calls `notify_ui_progress()` on `CardAlignmentStatus.RETRYING` after `CardListNavigator.align_first_card(...)` and before its bounded sleep (`:310-345`).
- The dungeon fallback path calls `CardListNavigator.reset_to_left(...)` followed by `notify_ui_progress()` (`:878-887`).
- The greedy dungeon target path calls `CardListNavigator.swipe_towards_target(...)`, records `last_dungeon_scroll_time`, sleeps, and returns without `notify_ui_progress()` (`:1035-1040`). This is the concrete pagination/progress gap described by the draft.

## Existing stale assumptions

- `tests/test_behavior_global_watchdog.py` contains multiple 90/95/91-second assumptions, including long-state threshold and recovery tests (`:41-62`, `:121-169`, `:187-217`).
- `docs/architecture/exception_subsystem_architecture.md:81-89` describes the progress contract but does not state the proposed 200-second configured policy; nearby text still frames the old 30/90-second behavior.
- Additional old-90 references exist in `docs/system_components_index.md`, pause/resume documents, recovery tests, and task-history documents. They require classification during implementation: live contract versus historical/context-only text.

## Proposed smallest implementation surface (for later review)

1. Add the required `long_subflow_timeout_sec` policy to `config/exception_features.json` and establish how missing/malformed required policy is surfaced without a duplicated numeric fallback in `config.py` or `watchdog.py`.
2. Update `ExceptionWatchdog` to consume the canonical key while preserving the existing long-state membership and `COLLECT_ONLY` behavior.
3. Add one canonical progress notification immediately after the known-target dungeon `swipe_towards_target()` dispatch, with focused regression coverage for refresh and genuine no-progress timeout.
4. Update only the architecture contract and focused tests that describe the changed runtime policy; separately classify unrelated historical 90-second prose.

## Open evidence / uncertainty

- The source search establishes current call sites and timer writes, but does not prove every call is semantically valid without reading each handler’s surrounding action result. The later implementation review should inspect only the affected long-running paths.
- The config manager currently retains last-known-good snapshots on reload failure. Whether the desired fail-fast behavior should occur at startup or on every snapshot request remains a design choice for the SPEC owner.
- No remote evidence was available before this context was pushed. Remote evidence must be read after push, as requested.

## Evidence anchors

- `states/exceptions/watchdog.py`
- `config.py`
- `config/exception_features.json`
- `utils/config_manager.py`
- `states/state_machine.py`
- `states/handlers/base.py`
- `states/handlers/navigation.py`
- `tests/test_behavior_global_watchdog.py`
- `docs/architecture/exception_subsystem_architecture.md`
