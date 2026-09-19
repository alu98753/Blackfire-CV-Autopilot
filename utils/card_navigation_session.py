"""Verified ownership contract for the shared card-navigation fast path.

This module owns session validity only.  It does not perform CV, swipes, or
card clicks, and is intentionally not wired into production handlers in 9A.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from utils.scene_snapshot import SceneSnapshot, TabId
from utils.scene_types import SceneId
from utils.shared_card_navigator import (
    CardNavigationResult,
    CardNavigatorState,
    SwipeDirection,
)


class CardNavigationOwnershipPhase(str, Enum):
    ACQUIRE = "acquire"
    TRACK = "track"
    INVALIDATED = "invalidated"


class CardNavigationInvalidation(str, Enum):
    MODE_CHANGE = "mode_change"
    TARGET_CHANGE = "target_change"
    CROSS_MODE_ACTION = "cross_mode_action"
    MISS_EXHAUSTION = "miss_exhaustion"
    CONTRADICTORY_LOCALIZATION = "contradictory_localization"
    RESET_RECOVERY = "reset_recovery"
    FOUND = "found"
    LEAVING_SELECTION_SURFACE = "leaving_selection_surface"


_MODE_SCENES = {
    TabId.STAGE: SceneId.STAGE_SELECT,
    TabId.DUNGEON: SceneId.DUNGEON_SELECT,
    TabId.DOMAIN: SceneId.DOMAIN_SELECT,
    TabId.LORD: SceneId.LORD_SELECT,
    TabId.DEMON_LORD: SceneId.DEMON_LORD_SELECT,
}


@dataclass
class VerifiedCardNavigationSession:
    """Single source of truth for verified card-search ownership."""

    mode: TabId
    target_key: str
    target_index: int
    scene_frame_id: int
    phase: CardNavigationOwnershipPhase = CardNavigationOwnershipPhase.ACQUIRE
    direction: SwipeDirection | None = None
    tracking_misses: int = 0
    invalidation: CardNavigationInvalidation | None = None

    @classmethod
    def acquire(
        cls,
        scene: SceneSnapshot,
        *,
        target_key: str,
        target_index: int,
    ) -> "VerifiedCardNavigationSession":
        """Create ownership only from a visually verified mode scene."""

        # The mode is deliberately read from the visual snapshot, not from a
        # requested/configured mode argument.  Exactly one lobby tab must be
        # active and its scene must agree with that tab.
        active_modes = [
            mode
            for mode, scene_id in _MODE_SCENES.items()
            if scene.scene == scene_id and mode in scene.active_tabs
        ]
        if len(active_modes) != 1:
            raise ValueError("scene does not provide unique verified lobby-mode evidence")
        if not target_key:
            raise ValueError("target_key is required")
        if int(target_index) < 1:
            raise ValueError("target_index must be 1-based")
        return cls(
            mode=active_modes[0],
            target_key=target_key,
            target_index=int(target_index),
            scene_frame_id=scene.frame_id,
        )

    @property
    def valid(self) -> bool:
        return self.phase != CardNavigationOwnershipPhase.INVALIDATED

    @property
    def owns_tracking(self) -> bool:
        return self.valid and self.phase == CardNavigationOwnershipPhase.TRACK

    def commit_localization(self, direction: SwipeDirection) -> None:
        """Enter TRACK only after localization commits a real direction."""

        self._require_valid()
        if self.phase != CardNavigationOwnershipPhase.ACQUIRE:
            raise RuntimeError("localization can only be committed from ACQUIRE")
        self.direction = direction
        self.phase = CardNavigationOwnershipPhase.TRACK

    def apply_navigation_result(self, result: CardNavigationResult) -> None:
        """Synchronize ownership with shared-navigator evidence/state."""

        self._require_valid()
        if result.target_index != self.target_index:
            self.invalidate(CardNavigationInvalidation.TARGET_CHANGE)
            return
        if result.state == CardNavigatorState.FOUND:
            self.invalidate(CardNavigationInvalidation.FOUND)
            return
        if result.state == CardNavigatorState.CONTRADICTORY:
            self.invalidate(CardNavigationInvalidation.CONTRADICTORY_LOCALIZATION)
            return
        if result.state == CardNavigatorState.NEED_RESET_LEFT:
            self.invalidate(CardNavigationInvalidation.RESET_RECOVERY)
            return
        if result.state == CardNavigatorState.RELOCALIZE:
            self.invalidate(CardNavigationInvalidation.MISS_EXHAUSTION)
            return
        if result.state != CardNavigatorState.TRACKING or result.direction is None:
            raise ValueError("TRACK requires shared localization direction evidence")
        if self.phase == CardNavigationOwnershipPhase.ACQUIRE:
            self.commit_localization(result.direction)
        elif self.direction != result.direction:
            self.invalidate(CardNavigationInvalidation.CONTRADICTORY_LOCALIZATION)
            return
        self.tracking_misses = max(self.tracking_misses, result.tracking_misses)

    def observe_scene(self, scene: SceneSnapshot) -> bool:
        """Keep ownership only while the same visually verified mode is active."""

        if not self.valid:
            return False
        if scene.scene != _MODE_SCENES[self.mode] or self.mode not in scene.active_tabs:
            self.invalidate(CardNavigationInvalidation.MODE_CHANGE)
            return False
        return True

    def invalidate(self, reason: CardNavigationInvalidation) -> None:
        self.phase = CardNavigationOwnershipPhase.INVALIDATED
        self.direction = None
        self.invalidation = reason

    def invalidate_mode_change(self) -> None:
        self.invalidate(CardNavigationInvalidation.MODE_CHANGE)

    def invalidate_target_change(self) -> None:
        self.invalidate(CardNavigationInvalidation.TARGET_CHANGE)

    def invalidate_cross_mode_action(self) -> None:
        self.invalidate(CardNavigationInvalidation.CROSS_MODE_ACTION)

    def invalidate_miss_exhaustion(self) -> None:
        self.invalidate(CardNavigationInvalidation.MISS_EXHAUSTION)

    def invalidate_reset_recovery(self) -> None:
        self.invalidate(CardNavigationInvalidation.RESET_RECOVERY)

    def invalidate_leaving_selection_surface(self) -> None:
        self.invalidate(CardNavigationInvalidation.LEAVING_SELECTION_SURFACE)

    def _require_valid(self) -> None:
        if not self.valid:
            raise RuntimeError("card-navigation session is invalidated")
