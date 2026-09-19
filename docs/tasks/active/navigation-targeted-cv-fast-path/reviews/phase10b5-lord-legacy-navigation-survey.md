# Phase 10B-5 — Lord legacy reset/search/swipe ownership survey

Production anchor: `d33227ca074ebca04a6d1e4336ff323e8b1cbee5`

## Scope

Bounded Phase 10 survey of `states/handlers/lord_boss.py` only around:

- shared Lord card navigation ownership;
- legacy `has_reset_to_left` / `reset_swipe_count` bookkeeping;
- first-card alignment;
- candidate-card scanning;
- direct horizontal swipe reachability.

This survey does **not** change Lord availability policy, cooldown OCR/update semantics, candidate priority, card click, start/fight verification, result handling, or daily bookkeeping.

## Current ownership graph

```text
supported fresh Lord selection
  -> _handle_lord_shared_navigation()
     -> policy commits one available target
     -> SharedCardNavigator localizes/tracks
     -> optional NEED_RESET_LEFT recovery via align_first_card()
     -> FOUND
  -> existing single-target OCR/click/start/fight owner

legacy/non-canonical path
  -> old first-card alignment block
  -> broad avail_bosses scan
  -> direct swipe_left_page()
```

For a fresh supported configuration, `HANDLED` returns before the old alignment/search block and `FOUND` sets a handoff that restricts downstream scanning to the committed target. Therefore the old reset/search/swipe block is not the normal owner on initial canonical entry.

## Proven ownership leak

The shared recovery path currently writes legacy state:

- on shared `NEED_RESET_LEFT`, `lord_card_reset_attempts` is mirrored into `reset_swipe_count`;
- on successful shared first-card alignment, `has_reset_to_left = True`.

The shared entry point also contains this compatibility guard:

```python
if (
    self.has_reset_to_left
    and self.lord_card_navigator is None
    and self.lord_navigation_target is None
):
    return None
```

That means a canonical shared session can manufacture the exact sentinel that later disables shared ownership.

One concrete reachable shape is:

```text
shared localization has no evidence
-> shared NEED_RESET_LEFT
-> first-card alignment succeeds
-> has_reset_to_left becomes True
-> later target/session is cleared
   (for example after target cooldown/availability invalidation)
-> next selection frame sees has_reset_to_left=True with no shared target/session
-> _handle_lord_shared_navigation() returns None
-> old broad candidate scan / direct left-swipe algorithm owns navigation again
```

This is a Phase 10 ownership leak. The shared recovery mechanism is valid; writing the legacy sentinel/counter from the shared path is not required for the shared navigator to continue.

## Safe cleanup slice

### REMOVE from canonical shared ownership

1. Do not seed `lord_card_reset_attempts` from legacy `reset_swipe_count` when committing a new shared target.
2. Do not mirror shared reset attempts back into legacy `reset_swipe_count`.
3. Do not set legacy `has_reset_to_left` when shared `NEED_RESET_LEFT` alignment succeeds.

After this split:

- `lord_card_reset_attempts` belongs to shared navigation recovery.
- `has_reset_to_left` and `reset_swipe_count` remain legacy compatibility bookkeeping only.
- A canonical session that clears/recommits a target after shared recovery re-enters shared navigation rather than falling into the old scan/swipe path.

### KEEP

- Shared `NEED_RESET_LEFT -> CardListNavigator.align_first_card()` recovery.
- The existing target-selection order over `avail_bosses`.
- Target-first/shared catalog localization and target-only tracking.
- Post-`FOUND` single-target match, confidence protection, cooldown OCR, DailyManager cooldown update, card click, start/fight verification.
- The legacy guard and old reset/search/swipe path for an already-established legacy/non-canonical compatibility session unless a stronger repository contract later proves that compatibility path dead.

## Why the whole legacy block is not deleted here

Repository configuration currently deep-merges profile overrides into `subflow_configs` without a Lord-specific structural completeness validator. Canonical defaults declare all three manager-backed Lord bosses, but the repository does not yet provide a fail-fast contract strong enough to classify every malformed/non-canonical Lord configuration as unsupported.

Therefore Phase 10B-5 should remove only the canonical ownership leak. It should not silently turn this bounded cleanup into a Lord configuration-contract redesign.

## Tests required for implementation

Add the smallest characterization/regression coverage that proves the ownership split:

1. **Shared recovery does not create legacy state**
   - drive shared `NEED_RESET_LEFT`;
   - after `ALIGNED`, assert shared bookkeeping is reset appropriately;
   - assert `has_reset_to_left` and `reset_swipe_count` were not mutated by the shared path.

2. **Stale legacy flag cannot be produced by canonical shared recovery**
   - a supported catalog target that requires shared reset/relocalization must remain shared-owned after the recovery.

3. **Target/session clear after shared recovery re-enters shared navigation**
   - simulate the supported target being cleared after shared recovery;
   - the next supported target selection must return `FOUND` or `HANDLED` from the shared path, not `None`.

4. **Legacy compatibility stays characterized**
   - an explicitly pre-established legacy session (`has_reset_to_left=True`, no shared navigator/target) may still bypass shared navigation;
   - this test is compatibility evidence, not a canonical normal-path expectation.

5. Existing downstream Lord tests must continue to prove:
   - candidate priority/selection;
   - cooldown OCR/update;
   - visible card click;
   - start/fight verification;
   - relaunch bound for alignment failure.

Tests that currently set `has_reset_to_left=True` merely to bypass navigation for business-policy setup should be rewritten so they do not accidentally define legacy physical navigation as the canonical contract. Where the test is intentionally about compatibility, say so explicitly.

## Expected production delta

The intended production patch should be very small and local to `LordBossHandler`:

- decouple `lord_card_reset_attempts` from `reset_swipe_count`;
- stop shared navigation from setting `has_reset_to_left`;
- keep the legacy block intact behind its existing compatibility state;
- do not alter timing constants, swipe geometry, OCR, DailyManager, target priority, or combat flow.

If implementation requires changing those business responsibilities, stop: the patch has exceeded Phase 10B-5 scope.

## Phase 10B-5 survey verdict

- Canonical duplicate reset/search/swipe owner: **reachable only because shared recovery writes legacy bookkeeping**.
- Safe cleanup: **decouple shared recovery state from legacy reset/search state**.
- Whole legacy block deletion: **not proven safe in this phase**.
- Business/downstream changes: **none allowed**.
