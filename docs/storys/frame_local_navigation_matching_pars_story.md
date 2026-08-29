# Frame-local navigation matching

## Purpose

Reduce navigation latency without allowing a template result from an old game frame
to be used after a scene transition.

## Action

- Treat the configured lobby Start button as a definitive lobby marker after the
  normal lobby anchors are found; record the match in `SceneInfo` and skip tab and
  stage-island fallback scanning.
- Reuse identical detail-page template queries only within one
  `NavigationHandler.handle(screen_img, rect)` call.
- Add regression coverage for the skipped expensive scan, single-frame reuse, and
  a fresh Start check on the following frame.

## Result

The navigation path no longer performs an additional Start match after the scene
detector has already found it. It also avoids duplicate full-screen matches for the
stage-detail label and final-stage button during one navigation tick.

## So What

Large island templates are among the most expensive full-screen OpenCV operations.
Avoiding them on a confirmed lobby frame and avoiding duplicate detail matches lowers
tick latency while keeping click and drag behavior unchanged.

## Influence

The optimization is intentionally frame-local: no coordinates or match result are
stored on the state machine or handler. Every later tick captures and recognizes a
new screenshot, preventing stale results from causing clicks after a transition.
