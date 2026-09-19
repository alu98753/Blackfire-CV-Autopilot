import unittest

from utils.card_navigation_session import (
    CardNavigationInvalidation,
    CardNavigationOwnershipPhase,
    VerifiedCardNavigationSession,
)
from utils.scene_snapshot import SceneSnapshot, TabId
from utils.scene_types import SceneId
from utils.shared_card_navigator import (
    CardNavigationResult,
    CardNavigatorState,
    SwipeDirection,
)


class TestVerifiedCardNavigationSession(unittest.TestCase):
    def scene(self, mode=TabId.STAGE, frame_id=1):
        scene_id = {
            TabId.STAGE: SceneId.STAGE_SELECT,
            TabId.DUNGEON: SceneId.DUNGEON_SELECT,
            TabId.DOMAIN: SceneId.DOMAIN_SELECT,
            TabId.LORD: SceneId.LORD_SELECT,
            TabId.DEMON_LORD: SceneId.DEMON_LORD_SELECT,
        }[mode]
        return SceneSnapshot(
            frame_id=frame_id,
            captured_at=float(frame_id),
            scene=scene_id,
            active_tabs=frozenset({mode}),
        )

    def acquire(self, mode=TabId.STAGE):
        return VerifiedCardNavigationSession.acquire(
            self.scene(mode), target_key="target", target_index=3
        )

    def tracking_result(self, state=CardNavigatorState.TRACKING, misses=0):
        return CardNavigationResult(
            state=state,
            target_index=3,
            direction=SwipeDirection.LEFT if state == CardNavigatorState.TRACKING else None,
            tracking_misses=misses,
        )

    def test_acquire_to_track_requires_verified_mode_target_and_direction(self):
        session = self.acquire(TabId.LORD)

        self.assertEqual(session.phase, CardNavigationOwnershipPhase.ACQUIRE)
        session.apply_navigation_result(self.tracking_result(misses=1))

        self.assertTrue(session.owns_tracking)
        self.assertEqual(session.mode, TabId.LORD)
        self.assertEqual(session.target_key, "target")
        self.assertEqual(session.target_index, 3)
        self.assertEqual(session.direction, SwipeDirection.LEFT)
        self.assertEqual(session.tracking_misses, 1)

    def test_requested_mode_without_matching_visual_scene_cannot_keep_ownership(self):
        session = self.acquire(TabId.STAGE)

        self.assertFalse(session.observe_scene(self.scene(TabId.DOMAIN)))
        self.assert_invalid(session, CardNavigationInvalidation.MODE_CHANGE)

    def test_scene_without_active_tab_cannot_acquire(self):
        scene = SceneSnapshot(
            frame_id=1,
            captured_at=1.0,
            scene=SceneId.STAGE_SELECT,
            active_tabs=frozenset(),
        )
        with self.assertRaises(ValueError):
            VerifiedCardNavigationSession.acquire(
                scene, target_key="target", target_index=3
            )

    def test_target_change_invalidates(self):
        session = self.acquire()
        session.invalidate_target_change()
        self.assert_invalid(session, CardNavigationInvalidation.TARGET_CHANGE)

    def test_mode_change_invalidates(self):
        session = self.acquire()
        self.assertFalse(session.observe_scene(self.scene(TabId.DOMAIN, 2)))
        self.assert_invalid(session, CardNavigationInvalidation.MODE_CHANGE)

    def test_cross_mode_action_invalidates(self):
        session = self.acquire()
        session.invalidate_cross_mode_action()
        self.assert_invalid(session, CardNavigationInvalidation.CROSS_MODE_ACTION)

    def test_miss_exhaustion_invalidates(self):
        session = self.acquire()
        session.apply_navigation_result(self.tracking_result(misses=1))
        session.apply_navigation_result(
            self.tracking_result(CardNavigatorState.RELOCALIZE, misses=4)
        )
        self.assert_invalid(session, CardNavigationInvalidation.MISS_EXHAUSTION)

    def test_contradictory_localization_invalidates(self):
        session = self.acquire()
        session.apply_navigation_result(
            self.tracking_result(CardNavigatorState.CONTRADICTORY)
        )
        self.assert_invalid(
            session, CardNavigationInvalidation.CONTRADICTORY_LOCALIZATION
        )

    def test_reset_and_recovery_invalidates(self):
        session = self.acquire()
        session.apply_navigation_result(
            self.tracking_result(CardNavigatorState.NEED_RESET_LEFT)
        )
        self.assert_invalid(session, CardNavigationInvalidation.RESET_RECOVERY)

    def test_found_invalidates_and_releases_ownership(self):
        session = self.acquire()
        session.apply_navigation_result(
            self.tracking_result(CardNavigatorState.FOUND)
        )
        self.assert_invalid(session, CardNavigationInvalidation.FOUND)

    def test_leaving_card_selection_surface_invalidates(self):
        session = self.acquire()
        session.invalidate_leaving_selection_surface()
        self.assert_invalid(
            session, CardNavigationInvalidation.LEAVING_SELECTION_SURFACE
        )

    def test_invalidated_session_cannot_reenter_target_only_tracking(self):
        session = self.acquire()
        session.invalidate_mode_change()

        with self.assertRaises(RuntimeError):
            session.commit_localization(SwipeDirection.LEFT)
        with self.assertRaises(RuntimeError):
            session.apply_navigation_result(self.tracking_result())
        self.assertFalse(session.owns_tracking)

    def test_swipe_direction_does_not_create_exact_current_index(self):
        session = self.acquire()
        session.apply_navigation_result(self.tracking_result())

        self.assertFalse(hasattr(session, "current_index"))
        self.assertEqual(session.target_index, 3)
        self.assertEqual(session.direction, SwipeDirection.LEFT)

    def assert_invalid(self, session, reason):
        self.assertFalse(session.valid)
        self.assertFalse(session.owns_tracking)
        self.assertEqual(session.phase, CardNavigationOwnershipPhase.INVALIDATED)
        self.assertEqual(session.invalidation, reason)


if __name__ == "__main__":
    unittest.main()
