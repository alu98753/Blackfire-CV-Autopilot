# Spec Review

Gate-accepted verdict: BLOCK
Blocking findings: 1

# Spec Review

Maximum steps for this agent were reached; per the step-ceiling constraint, this text response is the terminal deliverable (the StructuredOutput call was unavailable after tool shutdown). The review below is complete and grounded in the snapshots plus repository reads already performed.

## Clause coverage

Reviewed against: `docs/tasks/foreground-demo-mode-isolation/SPEC.md` (Final), `task.json` scope/contracts, `.runtime/ai_gate/foreground-demo-mode-isolation/diff.patch`, and current worktree files. Git grounding: HEAD `ae1916e`, merge-base with `origin/main` = `145522e4` (the task base_sha), current `origin/main` = `2c433caa`.

- **AC1/AC2, composition contract (select once):** `runtime/io_adapters.py` `compose_io`/`compose_capture` are the single family-selection points. `main.py:76-81` launches via `compose_capture`; `runtime/bootstrap.py:153-157` builds the runtime pair via `compose_io`. Fork is resolved exactly once per site from `args.backend_mode`.
- **AC3/AC4, critical invariant (fail-closed, no foreground fallback in backend path):** `BackendScreenCapturer.capture` (io_adapters.py:21-29) returns `None` for full-screen/invalid-HWND/backend failure with no MSS/PIL reachability; `BackendMouseController.click/scroll/drag/move_to_safe_area` (io_adapters.py:69-131) are pure Win32 with `pyautogui` unreachable. `test_foreground_demo_mode_isolation.py` asserts `grab/pil/rect` and pyautogui not called.
- **AC5 (foreground free of backend-selection branches):** `ForegroundScreenCapturer`/`ForegroundMouseController` override all four mode-sensitive methods; `ForegroundScreenCapturer.capture` retains MSS?IL fallback (AC7).
- **AC10 (launcher):** `utils/steam_launcher.py:28-48` ??`mouse`/`backend_mode` removed; missing `capturer` raises `ValueError`, no fallback construction; body uses only injected `capturer` (`get_hwnd`/`get_window_rect`/`ensure_window_on_monitor`). All production call sites (main.py:80, game_relaunch.py:48) and the two lifecycle tests now pass `capturer=`.
- **AC11 (relaunch):** `game_relaunch.py:48-52` passes `capturer=getattr(machine, 'capturer', None)`; `backend_mode`/`mouse` removed; test `test_relaunch_reuses_machine_capture` covers it.
- **AC12:** No new gameplay `backend_mode` I/O-selection branches; remaining `backend_mode` reads are metadata/CLI (`cli/arguments.py:76`, `bootstrap.py:191`, `state_machine.py:1812-1813` quest metadata, `quest_mapper.py:119` config inheritance).
- **AC13-15:** Focused modules `test_runtime_io_composition`, `test_foreground_demo_mode_isolation` are new, non-skipped, deterministic and cover both families plus launcher/relaunch composition; `test_screen_capturer_architecture`/`test_mouse_coordinates` migrated to adapters without `.backend_mode` mutation.
- **AC16:** Default/`--foreground`/`--backend` CLI resolution still asserted in `test_runtime_io_composition.test_cli_modes` and entrypoint tests.

## Blocking findings

### BD-1
Severity: BLOCKING
Contract / invariant: Acceptance criterion 17 ("No unrelated gameplay/CV/scheduling/environment behavior changes") and task.json scope boundaries (baseline `origin/main`)
Location: `config/defaults.toml` (deleted `[primary_modes.abyssbeast_lair]`, `[primary_modes.coldoath_citadel]`); `docs/tasks/generic-domain-catalog-expansion/*` (SPEC/task.json/reviews deleted); `tests/test_domain_common_behavior.py`; `tests/test_behavior_main_entrypoint.py`
Claim: The candidate diff, taken against the comparison baseline `origin/main`, removes the two merged canonical domains and the merged generic-domain task artifacts, reverting domain tests to `abyss_nest`/`frost_citadel` placeholders and re-adding redundant Golden Empire keys. These are out-of-scope, unrelated changes that would regress the merged product.
Evidence: diff.patch lines 1-40 (TOML hunks), 435-883 (deletions of `generic-domain-catalog-expansion` files), 1292-1516 (test reverts). Git grounding: HEAD `ae1916e` has merge-base `145522e4` with `origin/main` `2c433caa`; the merged domain-catalog work exists on main but not on this branch, so the branch predates that merge and the snapshot diffs it against the newer main. `git log` shows two prior gate events (`33d18c4`, `f61aae2` "CANDIDATE_BLOCKED"); `status.txt` is empty. The in-scope I/O-isolation implementation is sound (adapter split, single composition seam, launcher/relaunch ownership stripped, fail-closed preserved), but the branch as presented cannot be integrated into `origin/main` without reverting the canonical Domain catalog ??a direct AC17 violation independent of this task's contract.
Suggested validation: Rebase/merge `origin/main` into the branch, then regenerate the gate diff; confirm only the task-scope files change. Run `tests.test_foreground_demo_mode_isolation`, `tests.test_runtime_io_composition`, and the focused list against the integrated tree.
Confidence: 0.92

## Advisory findings

1. `capture/screen.py:292-319` and `actions/mouse.py:139/220/275/355` retain the mixed-mode base `backend_mode` branches, and base classes remain publicly mutable. SPEC permits a thin facade that does not retain mutable runtime switching; production never constructs these raw, and the adapters override all mode-sensitive methods, so this is a compliance nuance rather than an execution-path violation. Also `scripts/test_single_click.py:38` still constructs raw `MouseController(backend_mode=...)` (dev script, out of scope).
2. `test_mouse_refactor.py:63/76/86` still builds raw `MouseController(backend_mode=True/False)` via constructor arg (mode resolved once, not mutated) ??arguably consistent with AC13's "explicit construction" intent, but it was not migrated to adapters; consider aligning it with the other focused modules.
3. `test_behavior_pause_resume.py:473/485` still mutate `capturer.backend_mode` post-construction; with the adapters the mutation is inert (override ignores it). If pause/resume wiring is touched, per SPEC that file's deterministic targets should be run/migrated.
4. The entrypoint runtime-loop test in this branch drops the `has_pending_timeout_recovery` mock from the merged main version; this belongs to the same stale-base artifact as BD-1, but is secondary to the catalog regression.

## Test evidence gaps

Static grounding covers the adapter split, composition wiring, launcher/relaunch ownership, and fail-closed behavior; execution of the five focused modules through the shared `.venv` remains the outstanding dynamic evidence (this review is read-only). No dynamic run was performed for any module, and the block does not depend on test execution ??it is grounded entirely in the diff-vs-baseline content.

<!-- blackfire-gate-fingerprint: {"schema":1,"role":"spec-reviewer","hash":"272829e22f397403f8bd790ded389f40b34929a59d1db7f15791ac9f1f08b820"} -->
