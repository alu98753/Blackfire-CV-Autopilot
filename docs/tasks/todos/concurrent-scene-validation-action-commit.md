# Concurrent Scene Validation + Guarded Action Commit

Status: Future Work

Origin: `navigation-targeted-cv-fast-path` Phase 9 final review.

## Problem

Phase 9 intentionally allows a visually verified card-navigation TRACK session to skip repeated broad Scene/tab CV and match only the committed target card.

That optimization is correct for normal bot-owned navigation, but it leaves one deferred robustness case:

- the TRACK session still believes it owns a lobby card-selection surface;
- the user or another external actor manually changes the real game surface without changing the bot's desired mode/config;
- examples include switching to another lobby tab, returning to Town, entering Dungeon Explore / Domain Explore, Battle / Result, or another modal/surface;
- until existing bounded miss invalidation runs, target-only tracking may produce a stale swipe request against the wrong surface.

Existing intent/config/availability preflight guards do not solve this case because their state may remain unchanged while only the real screen changed.

## Goal

Investigate a concurrency-safe perception/action contract that preserves Phase 9's reduced CV cost while preventing stale physical navigation actions after external scene drift.

The preferred model to evaluate is:

```text
                 same Frame N
                /            \
               /              \
      target perception    scene validation
               \              /
                \            /
                 guarded commit
                      |
                 physical action
```

Target perception and Scene validation may run concurrently, but a physical swipe should commit only after the current frame/session evidence authorizes it.

## Candidate contracts

### A. Validate before commit

Run target CV and Scene safety/postcondition validation concurrently for the same captured frame.

A target miss may produce a side-effect-free `SwipeRequest`, but execution waits until validation confirms that:

1. the result still belongs to the current session/frame generation;
2. the previously verified card-selection surface has not been invalidated;
3. desired mode/target identity is still current;
4. no higher-priority safety transition won the frame.

If validation detects Town / another lobby mode / explore / battle / result / incompatible modal evidence, invalidate the TRACK session and discard the pending swipe.

This is the preferred safety model unless later evidence proves speculative actions harmless on every relevant surface.

### B. Speculative action then invalidate

Allow target tracking to execute the swipe immediately while Scene validation runs concurrently, then atomically invalidate the session if Scene evidence contradicts the original postcondition.

This can reduce action latency, but it permits at least one stale physical action because an already executed mouse drag cannot be rolled back.

Use only if the relevant wrong-surface swipe is proven harmless and that weaker contract is explicitly accepted.

## Important invariants

- Config/requested mode may invalidate existing ownership but must never substitute for visual Scene verification.
- Parallelism must not introduce two independent owners of navigation state.
- Results from an older frame/session generation must not commit actions after ownership has changed.
- Scene validation is a postcondition/safety validator, not permission to reconstruct synthetic card position.
- Do not reintroduce repeated full catalog matching during steady TRACK.
- Preserve global popup/safety and battle/result ownership.
- Physical side effects should have one explicit commit point.

## Cases to verify

At minimum, start from a valid Stage/Dungeon/Domain/Lord/Demon-Lord TRACK session and externally move the real UI to:

- another lobby tab;
- Town;
- Dungeon Explore;
- Domain Explore;
- Battle;
- Result;
- preparation/stone/other incompatible modal where applicable.

For each case classify whether current behavior is already protected, the swipe is proven harmless, or action commit requires Scene validation.

## Non-goals

This note does not reopen Phase 9 and is not part of Phase 10 legacy cleanup.

Do not implement concurrency, worker scheduling, locks, frame generations, or Scene-detector restructuring until this future work is promoted into its own formal task and its architecture contract is finalized.
