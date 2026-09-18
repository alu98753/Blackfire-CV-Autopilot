# domain-lobby-primary-start-boundary

Status: Draft

## Goal

Fix the primary-navigation boundary so a canonical Domain lobby can execute its own `START_PRIMARY` action even when `enable_stage_farming == false`, without weakening card-entry brightness filtering or changing unrelated scheduler behavior.

## Problem Statement

Observed runtime sequence for Golden Empire on 2026-09-18:

- Domain tab/card alignment succeeds and `domains/golden_empire/entry.png` is matched at high confidence.
- Golden Empire entry is clicked.
- A later frame still produces one dark `entry.png` candidate, but brightness filtering rejects it because the relative brightness is below 0.70.
- On the next frame, `common/quit.png` and `domains/common/start_btn.png` are both detected.
- Intent routing resolves `scene=lobby`, `action=start_primary`, `reason=primary_start_ready`.
- State transitions `NAVIGATING -> LOBBY`.
- `LobbyHandler._handle_preconditions()` then evaluates `enable_stage_farming == false` and transitions to `COLLECT_ONLY` before the domain Start action is executed.

Current code therefore allows a legacy stage-specific precondition to override an already-correct generic primary-navigation decision.

The domain configs intentionally normalize `enable_stage_farming` to false because they are not stage-farming modes. That flag must not mean that a Domain lobby is forbidden from starting.

## Evidence Already Surveyed

Current `main` base surveyed: `2c433caa154a458edfac9235f30eff085b86b6f6`.

Relevant findings:

1. `config.py::normalize_config()` only enables `enable_stage_farming` by default for `stage`, `mix`, and `daily`; direct `type="domain"` modes therefore carry `enable_stage_farming == false`.
2. `config/defaults.toml` declares Golden Empire, Abyssbeast Lair, and Coldoath Citadel as `type="domain"`, each with `lobby_start_btn = "domains/common/start_btn.png"`.
3. `states/handlers/lobby.py::_handle_preconditions()` currently performs:

   `if not enable_stage_farming and not is_in_dungeon: -> COLLECT_ONLY`

   without limiting that fallback to a stage-owning route.
4. `states/navigation_routing.py` already resolves the observed Domain lobby to `START_PRIMARY`.
5. `vision/matcher.py` brightness filtering rejects dark candidates after template correlation succeeds. In this incident the dark Golden Empire card appears after an earlier successful click and immediately before the Domain lobby Start button becomes visible.
6. Existing Lobby behavior tests are stage-centric and do not cover `type="domain" + enable_stage_farming=false + domain start button visible`.

## Scope

- Correct the Lobby responsibility boundary so direct Domain routes are allowed to execute their configured `lobby_start_btn` even though stage farming is disabled.
- Preserve existing stage/mix/daily behavior where `enable_stage_farming == false` legitimately controls fallback to `COLLECT_ONLY`.
- Preserve current generic IntentRouting ownership of `START_PRIMARY`.
- Add deterministic regression coverage for direct Domain lobby behavior.
- Verify whether the narrowest correct implementation belongs only in `LobbyHandler._handle_preconditions()` or requires a small policy/helper boundary adjustment.
- Confirm the same fix applies to all canonical direct Domain modes, not only Golden Empire.

## Known Invariants

- `enable_stage_farming` controls ordinary Stage farming. It must not be interpreted as a universal "primary activity disabled" flag.
- A direct `type="domain"` route owns its configured `lobby_start_btn` and must be allowed to start when the lobby scene and start button are visually verified.
- Intent routing remains the generic authority for `START_PRIMARY` once scene evidence is sufficient.
- Legacy preconditions may still preempt primary start for genuinely higher-priority conditions such as bag cleaning or explicit town-subflow ownership.
- Domain navigation/card alignment behavior is preserved.
- Template matching brightness filtering remains enabled for entry/navigation templates unless Scout finds direct causal evidence that it is independently incorrect.
- Scheduler priority and daily-dungeon/domain/stage arbitration are out of scope.
- Behavior-preserving refactor rule applies outside the specific bug.
- Direct Domain behavior should remain generic across Golden Empire, Abyssbeast Lair, and Coldoath Citadel.

## Non-goals

- Lowering or disabling the `brightness_threshold=0.70` for Domain entry templates.
- Treating a single dark template candidate as automatically clickable.
- Reworking Domain card-list alignment.
- Changing Domain template assets.
- Redesigning IntentRouting.
- Changing daily dungeon priority, Tier 4 fallback policy, stamina retreat policy, or collection scheduling.
- Broad Lobby refactoring beyond the ownership boundary required by this bug.
- Fixing unrelated backend/window-coordinate anomalies unless Scout proves they are causal to this exact failure.

## Required Responsibility Boundary

Desired flow:

`Domain card entry -> verified Domain lobby -> IntentRouting START_PRIMARY -> Lobby executes configured domain start button -> loading/battle`

The forbidden flow is:

`Domain lobby -> legacy enable_stage_farming check -> COLLECT_ONLY`

unless an explicit higher-level policy has intentionally converted the machine to a collect-only or non-domain route before entering the Lobby handler.

Prefer the smallest correction that makes the stage-farming fallback stage-specific (or otherwise mode-aware) rather than introducing a Domain-specific special case for Golden Empire.

## Provisional Acceptance Criteria

1. Given a direct `type="domain"` config with `enable_stage_farming == false`, when its configured `lobby_start_btn` is visible in a verified lobby, Lobby handling does not transition to `COLLECT_ONLY` solely because stage farming is disabled.
2. The same scenario executes the existing `START_PRIMARY` path and clicks the configured Domain start button.
3. Golden Empire, Abyssbeast Lair, and Coldoath Citadel inherit the corrected behavior through the generic Domain path; no Golden-Empire-only production branch is introduced.
4. Stage-mode behavior is preserved: when ordinary stage farming is disabled in the contexts that currently use that fallback, the existing `COLLECT_ONLY` behavior remains intact.
5. Existing higher-priority Lobby preconditions (bag cleaning, lord-boss/town-subflow ownership, committed Start action semantics) remain unchanged.
6. Domain entry/card alignment and matcher brightness behavior remain unchanged.
7. Focused regression tests cover at minimum:
   - direct Domain lobby with `enable_stage_farming=false` starts via `domains/common/start_btn.png`;
   - stage fallback semantics still work where applicable;
   - no regression to committed Start retry/disappearance behavior.
8. Existing relevant Lobby/navigation/domain tests pass.

## Secondary Observation — Not Yet In Scope

One runtime line showed:

- matcher center around `(282, 353)`
- logged click around `(283, 1456)`

while an earlier Golden Empire match/click pair was geometrically reasonable and the later Domain lobby was successfully reached.

This suggests a possible window-rect/client-coordinate inconsistency or transient rect race. It is not currently the primary cause of this incident because the Domain lobby and its Start button were subsequently detected.

Scout should inspect this only far enough to determine whether it is causally required for this task. If not causal, record it as a follow-up candidate and do not expand production scope.

## Scout Questions

Scout must verify:

1. Is `LobbyHandler._handle_preconditions()` the only production path that converts a verified direct Domain lobby to `COLLECT_ONLY` because `enable_stage_farming == false`?
2. What exact historical/architectural responsibility is `enable_stage_farming` intended to own?
3. Is the smallest safe fix to gate that fallback by route type, or is there already a canonical helper/policy that should decide whether the current primary route is runnable?
4. Are there any direct Domain tests already exercising Lobby start behavior through another fixture that would constrain the implementation?
5. Does the observed dark `entry.png` candidate represent expected transition residue and therefore validate keeping the brightness filter unchanged?
6. Is the abnormal logged Y click coordinate causal to entering the wrong Lobby state, or an independent diagnostic issue?

Scout is evidence provider only. It must not change Status from Draft or implement production code.

## Expected Focused Tests

Likely focused modules:

- `tests.test_behavior_lobby_state_machine`
- `tests.test_behavior_navigation`
- `tests.test_domain_common_behavior`

Scout may recommend a narrower or additional deterministic test module if repository ownership suggests a better seam.

## Uncertainty

- Whether the correct fix is a one-condition change in `LobbyHandler` or a narrow reuse of an existing primary-route capability/policy helper.
- Whether stage-disabled fallback should be keyed directly by `config["type"] == "stage"` or by a more explicit existing runtime route predicate.
- Whether the anomalous click-coordinate log is entirely independent.

These uncertainties may refine implementation shape after Scout, but must not broaden the task into CV tuning, scheduler redesign, or I/O architecture work without a separate task.


## Additional Runtime Failure — Domain Scene Adoption Without Domain Execution Identity

A second production failure was observed on 2026-09-18 after the bot was physically inside a Domain exploration scene:

```text
成功匹配模板 'domains/common/explore_btn.png' ... 0.9995
全域定位：... 鎖定領地探索狀態 (DOMAIN_EXPLORE)
狀態轉移: UNKNOWN -> DOMAIN_EXPLORE
...
ValueError: 無效的領地運行配置: self.machine.config 缺少必要的 'domain' 識別碼
```

The preceding PyTorch message about quantized APIs being deprecated is only a deprecation warning emitted while EasyOCR/PyTorch is loading. It is not the crash cause.

The actual crash is a scene/execution-context ownership mismatch:

1. `GameStateMachine.detect_current_state()` treats `domains/common/explore_btn.png` as sufficient visual truth for `STATE_DOMAIN_EXPLORE`.
2. Its current condition is effectively unconditional for `explore_btn.png`:

   `if pos and (d_btn.endswith("explore_btn.png") or is_domain_mode):`

   Therefore a physical Domain scene can transition `UNKNOWN -> DOMAIN_EXPLORE` even when the current runtime config is not a Domain config and contains no `domain` identity.
3. `DomainExploreHandler.handle()` immediately requires:

   `(self.machine.config or {}).get("domain")`

   and raises `ValueError` if it is absent.
4. The state machine therefore has a split contract: global relocalization can adopt Domain scene truth without ensuring that the execution context required by the Domain handler has also been adopted/restored.

This is a deterministic contract mismatch, not a CV false positive in the observed log: `explore_btn.png` matched at 0.9995 and is the canonical Domain exploration feature.

### Relationship To The Original Lobby Bug

The two failures share the same architectural boundary:

- Bug A: a valid Domain primary action is overridden by a legacy stage-specific runtime flag.
- Bug B: a valid Domain physical scene is adopted without a valid Domain execution identity.

Both are cases where **visual/intent truth and runtime execution config are allowed to diverge across a Domain state transition**.

This task therefore owns the narrow Domain runtime handoff boundary needed to keep these truths coherent. It must not broaden into generic state-machine recovery redesign.

### Additional Scope

- Make `UNKNOWN -> DOMAIN_EXPLORE` relocalization safe when the physical Domain scene is visually verified but `self.config` currently lacks `domain`.
- Determine the canonical source from which Domain execution identity should be recovered/adopted, if recovery is valid (for example an already-owned direct Domain `primary_config`, Tier-4 Domain fallback owner, navigation/session context, or another existing explicit owner).
- If no unambiguous Domain identity is owned, fail closed/recover without entering `DomainExploreHandler`; do not invent or guess a specific Domain from the generic `explore_btn.png`.
- Preserve the ability to cold/restart-relocalize into a Domain scene when an unambiguous Domain owner already exists.
- Prevent an unhandled `ValueError`/supervisor restart loop caused solely by scene adoption with missing Domain execution identity.

### Additional Invariants

- Scene truth and execution identity are distinct. Seeing `domains/common/explore_btn.png` proves "physically in a Domain exploration scene"; it does **not** by itself identify which Domain is active.
- `DomainExploreHandler` may require a valid Domain identity; global relocalization must satisfy that precondition before dispatch, or must fail closed before entering the handler.
- Production code must not default an unknown Domain identity to Golden Empire or any other catalog entry.
- A stale/non-Domain `self.config` must not be treated as authoritative merely because it is currently installed if a stronger, explicit runtime owner already exists.
- Conversely, `primary_config` must not be copied blindly unless its ownership semantics prove that it is the correct currently active Domain.
- Supervisor restart must not become the normal recovery mechanism for this deterministic state/config mismatch.

### Additional Provisional Acceptance Criteria

9. When `domains/common/explore_btn.png` is visually verified while `self.config` lacks `domain`, the state machine does not dispatch into `DomainExploreHandler` with an invalid execution config.
10. If an unambiguous existing runtime owner identifies the active Domain, global relocalization restores/adopts a valid Domain execution config before `DOMAIN_EXPLORE` handler execution.
11. If the active Domain identity cannot be determined unambiguously, the bot fails closed through an existing bounded recovery/navigation path rather than guessing a Domain or raising an unhandled `ValueError`.
12. A valid direct Domain config continues to relocalize from `UNKNOWN` to `DOMAIN_EXPLORE` and execute normally.
13. A non-Domain/collect-only config plus a generic Domain exploration visual cannot manufacture a Domain identity from the template alone.
14. Focused tests reproduce the exact contract mismatch: `UNKNOWN + explore_btn visible + config without domain` must not crash on the next handler tick.
15. The PyTorch/EasyOCR deprecation warning is not modified as part of this task unless Scout discovers a separate repository-owned dependency contract requiring action; it is explicitly non-causal to this runtime crash.

### Additional Scout Questions

7. Which code paths can leave the game physically inside Domain exploration while `self.config` is `collect_only`, stage-like, or otherwise lacks `domain`? In particular, determine whether the original Lobby precondition bug can create or contribute to this divergence.
8. What is the canonical existing owner of Domain identity during:
   - direct Domain mode,
   - Tier-4 Domain fallback,
   - temporary Daily/mix preemption,
   - supervisor restart / cold relocalization?
9. Is `primary_config` always safe to use for Domain identity recovery, or can it name a different primary mode while the physical Domain was entered through a temporary route?
10. Should the correction live in global relocalization/adoption, in a shared Domain execution-context resolver, or at another existing explicit ownership boundary?
11. Are there existing tests for `UNKNOWN -> DOMAIN_EXPLORE` that currently assume `explore_btn.png` alone is sufficient regardless of runtime config?
12. Can `DomainExploreHandler`'s current fail-fast validation remain intact after the upstream handoff is fixed? Prefer preserving it as an invariant check rather than weakening it into silent fallback.
