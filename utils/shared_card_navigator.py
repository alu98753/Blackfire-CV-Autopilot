"""Isolated ordered-card navigation state machine.

This module owns navigation evidence and swipe requests only.  It deliberately
does not click cards and is not attached to any production handler in Phase 3.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable

from utils.card_navigator import CardListNavigator
from utils.navigation_catalog import NavigationCatalogEntry


class CardNavigatorState(str, Enum):
    FOUND = "found"
    TRACKING = "tracking"
    RELOCALIZE = "relocalize"
    NEED_RESET_LEFT = "need_reset_left"
    CONTRADICTORY = "contradictory"


class SwipeDirection(str, Enum):
    LEFT = "left"
    RIGHT = "right"


@dataclass(frozen=True)
class PageSwipeRequest:
    """A side-effect-free request for one common page swipe."""

    direction: SwipeDirection

    def execute(self, mouse, rect, *, duration=0.8, inertia=False) -> None:
        """Execute this request through the existing common swipe primitive."""

        if self.direction == SwipeDirection.LEFT:
            CardListNavigator.swipe_left_page(
                mouse, rect, duration=duration, inertia=inertia
            )
        else:
            CardListNavigator.swipe_right_page(
                mouse, rect, duration=duration, inertia=inertia
            )


@dataclass(frozen=True)
class CardNavigationResult:
    state: CardNavigatorState
    target_index: int
    visible_indices: frozenset[int] = frozenset()
    direction: SwipeDirection | None = None
    swipe_request: PageSwipeRequest | None = None
    tracking_misses: int = 0


class SharedCardNavigator:
    """Resolve an ordered card target using bounded visual evidence."""

    def __init__(
        self,
        catalog: Iterable[NavigationCatalogEntry | tuple[int, str, str]],
        target_key: str,
        *,
        threshold: float = 0.75,
        max_tracking_misses: int | None = None,
    ) -> None:
        self.catalog = tuple(
            entry
            if isinstance(entry, NavigationCatalogEntry)
            else NavigationCatalogEntry(*entry)
            for entry in catalog
        )
        matches = [entry for entry in self.catalog if entry.key == target_key]
        if len(matches) != 1:
            raise ValueError(f"target key must identify one catalog entry: {target_key!r}")

        self.target = matches[0]
        self.threshold = float(threshold)
        self.max_tracking_misses = (
            len(self.catalog)
            if max_tracking_misses is None
            else max(1, int(max_tracking_misses))
        )
        self.state: CardNavigatorState | None = None
        self.tracking_misses = 0
        self._tracking_direction: SwipeDirection | None = None
        self._swipe_history: list[SwipeDirection] = []

    @property
    def swipe_history(self) -> tuple[SwipeDirection, ...]:
        """Return requested directions; no synthetic current index is stored."""

        return tuple(self._swipe_history)

    def observe(self, screen_img: Any, matcher) -> CardNavigationResult:
        """Consume one frame of matcher evidence and return a navigation result."""

        if self.state == CardNavigatorState.TRACKING:
            return self._observe_tracking(screen_img, matcher)

        return self._localize(screen_img, matcher)

    def _localize(self, screen_img: Any, matcher) -> CardNavigationResult:
        self.tracking_misses = 0
        self._tracking_direction = None
        target_pos, target_conf = self._match(matcher, screen_img, self.target.template)
        if target_pos is not None and target_conf >= self.threshold:
            self.state = CardNavigatorState.FOUND
            return CardNavigationResult(
                state=self.state,
                target_index=self.target.index,
                visible_indices=frozenset({self.target.index}),
            )

        visible_indices: set[int] = set()
        for entry in self.catalog:
            if entry.key == self.target.key:
                continue
            pos, confidence = self._match(matcher, screen_img, entry.template)
            if pos is not None and confidence >= self.threshold:
                visible_indices.add(entry.index)

        if not visible_indices:
            self.state = CardNavigatorState.NEED_RESET_LEFT
            return self._result(visible_indices=visible_indices)

        lowest = min(visible_indices)
        highest = max(visible_indices)
        if lowest <= self.target.index <= highest:
            self.state = CardNavigatorState.CONTRADICTORY
            return self._result(visible_indices=visible_indices)

        direction = (
            SwipeDirection.LEFT
            if highest < self.target.index
            else SwipeDirection.RIGHT
        )
        self.state = CardNavigatorState.TRACKING
        self._tracking_direction = direction
        self._record_swipe(direction)
        return self._result(
            visible_indices=visible_indices,
            direction=direction,
            swipe_request=PageSwipeRequest(direction),
        )

    def _observe_tracking(self, screen_img: Any, matcher) -> CardNavigationResult:
        pos, confidence = self._match(matcher, screen_img, self.target.template)
        if pos is not None and confidence >= self.threshold:
            self.state = CardNavigatorState.FOUND
            self.tracking_misses = 0
            self._tracking_direction = None
            return self._result(visible_indices={self.target.index})

        self.tracking_misses += 1
        if self.tracking_misses >= self.max_tracking_misses:
            self.state = CardNavigatorState.RELOCALIZE
            self._tracking_direction = None
            return self._result()

        # A miss is evidence that the committed target is not in the current
        # viewport. Repeat the same committed direction; never infer an exact
        # post-swipe index.
        direction = self._tracking_direction
        if direction is None:
            self.state = CardNavigatorState.RELOCALIZE
            return self._result()
        self._record_swipe(direction)
        return self._result(
            direction=direction,
            swipe_request=PageSwipeRequest(direction),
        )

    def _record_swipe(self, direction: SwipeDirection) -> None:
        self._swipe_history.append(direction)

    def _result(
        self,
        *,
        visible_indices: set[int] | frozenset[int] = frozenset(),
        direction: SwipeDirection | None = None,
        swipe_request: PageSwipeRequest | None = None,
    ) -> CardNavigationResult:
        return CardNavigationResult(
            state=self.state or CardNavigatorState.RELOCALIZE,
            target_index=self.target.index,
            visible_indices=frozenset(visible_indices),
            direction=direction,
            swipe_request=swipe_request,
            tracking_misses=self.tracking_misses,
        )

    @staticmethod
    def _match(matcher, screen_img: Any, template: str):
        result = matcher.match(screen_img, template)
        if not isinstance(result, (tuple, list)) or len(result) < 2:
            return None, 0.0
        position, confidence = result[0], result[1]
        try:
            return position, float(confidence)
        except (TypeError, ValueError):
            return position, 0.0
