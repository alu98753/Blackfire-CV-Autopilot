import unittest
from unittest.mock import MagicMock, patch

import numpy as np

from states.navigation_intent import ActionId, IntentId, PostconditionId
from states.navigation_table import NavigationGoal, NavigationTable
from states.state_machine import GameStateMachine
from utils.scene_snapshot import ElementId, ElementMatch, SceneId, SceneSnapshot
from utils.town_building_detector import BuildingCheckResult


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class TownSubflowPreconditionTestCase(unittest.TestCase):
    def setUp(self):
        self.matcher = MagicMock()
        self.matcher.templates_dir = "templates"
        self.mouse = MagicMock()
        self.clock = FakeClock()
        self.machine = GameStateMachine(
            capturer=MagicMock(),
            matcher=self.matcher,
            mouse=self.mouse,
            preload_ocr=False,
            clock=self.clock,
        )
        self.machine.config = {"type": "daily", "name": "Daily"}
        self.machine.primary_config = self.machine.config.copy()
        self.screen = np.zeros((600, 800, 3), dtype=np.uint8)
        self.rect = {"left": 10, "top": 20, "width": 800, "height": 600}

    def test_queue_latches_head_without_dispatch_before_scene_evidence(self):
        original_config = self.machine.config.copy()

        self.machine.start_subflow_queue(["chest", "hero_draw"])

        self.assertEqual(self.machine.current_town_subflow, "chest")
        self.assertEqual(self.machine.town_subflow_queue, ["hero_draw"])
        self.assertEqual(self.machine.current_state, self.machine.STATE_UNKNOWN)
        self.assertEqual(self.machine.config, original_config)

    def test_five_town_tasks_share_reach_town_goal(self):
        from states.town_subflow_navigation import TOWN_SUBFLOW_SPECS

        expected = {
            "chest",
            "hero_draw",
            "blood_altar",
            "bulletin_board",
            "jewelry_workshop",
        }
        self.assertTrue(expected.issubset(TOWN_SUBFLOW_SPECS))
        self.assertEqual(
            {TOWN_SUBFLOW_SPECS[key].navigation_goal for key in expected},
            {NavigationGoal.REACH_TOWN},
        )

    def test_goal_table_is_task_agnostic(self):
        snapshot = SceneSnapshot(
            frame_id=1,
            captured_at=1.0,
            scene=SceneId.LOBBY,
            elements={
                ElementId.GOBACK_TOWN: ElementMatch(
                    100, 200, 0.9, "goback_town.png"
                )
            },
        )

        edge = NavigationTable().next_goal_edge(
            snapshot, NavigationGoal.REACH_TOWN
        )

        self.assertEqual(edge.action, ActionId.RETURN_TOWN)
        self.assertEqual(edge.postcondition, PostconditionId.TOWN)

    @patch("states.town_subflow_perception.detect_building_with_red_dot")
    def test_overlay_quit_precedes_building_exit(self, mock_building):
        self.machine.start_subflow_queue(["chest"])
        self.machine.current_state = self.machine.STATE_NAVIGATING
        mock_building.return_value = BuildingCheckResult(False, False)

        def match(_screen, template, **_kwargs):
            matches = {
                "common/quit.png": ((300, 100), 0.95),
                "town_building/exitfromhouse_and_to_town.png": ((50, 500), 0.92),
            }
            return matches.get(template, (None, 0.0))

        self.matcher.match.side_effect = match

        handled = self.machine.handle_town_subflow_precondition(
            self.screen, self.rect
        )

        self.assertTrue(handled)
        self.mouse.click.assert_called_once_with(310, 120)
        action = self.machine.navigation_progress.in_flight
        self.assertEqual(action.intent_id, IntentId.TOWN_SUBFLOW)
        self.assertEqual(action.action_id, ActionId.DISMISS_OVERLAY)
        self.assertEqual(action.expected, PostconditionId.OVERLAY_CLOSED)

    @patch("states.town_subflow_perception.detect_building_with_red_dot")
    def test_registered_confirm_overlay_precedes_navigation(self, mock_building):
        self.machine.start_subflow_queue(["chest"])
        self.machine.current_state = self.machine.STATE_NAVIGATING
        mock_building.return_value = BuildingCheckResult(False, False)

        def match(_screen, template, **_kwargs):
            matches = {
                "common/ok.png": ((300, 100), 0.95),
                "goback_town.png": ((50, 500), 0.92),
            }
            return matches.get(template, (None, 0.0))

        self.matcher.match.side_effect = match

        handled = self.machine.handle_town_subflow_precondition(
            self.screen, self.rect
        )

        self.assertTrue(handled)
        self.mouse.click.assert_called_once_with(310, 120)
        self.assertEqual(
            self.machine.navigation_progress.in_flight.action_id,
            ActionId.DISMISS_OVERLAY,
        )

    @patch("states.town_subflow_perception.detect_building_with_red_dot")
    def test_building_uses_exit_house_after_overlay_is_absent(self, mock_building):
        self.machine.start_subflow_queue(["hero_draw"])
        self.machine.current_state = self.machine.STATE_NAVIGATING
        mock_building.return_value = BuildingCheckResult(False, False)

        def match(_screen, template, **_kwargs):
            if template == "town_building/exitfromhouse_and_to_town.png":
                return (50, 500), 0.92
            return None, 0.0

        self.matcher.match.side_effect = match

        handled = self.machine.handle_town_subflow_precondition(
            self.screen, self.rect
        )

        self.assertTrue(handled)
        self.mouse.click.assert_called_once_with(60, 520)
        action = self.machine.navigation_progress.in_flight
        self.assertEqual(action.action_id, ActionId.EXIT_BUILDING_TO_TOWN)
        self.assertEqual(action.expected, PostconditionId.TOWN)

    def test_domain_exits_to_lobby_before_returning_to_town(self):
        self.machine.start_subflow_queue(["chest"])
        self.machine.current_state = self.machine.STATE_NAVIGATING
        self.matcher.match.side_effect = lambda _img, name, **_kw: (
            ((600, 500), 0.93)
            if name == "domains/common/exit_to_lobby.png"
            else (None, 0.0)
        )

        handled = self.machine.handle_town_subflow_precondition(
            self.screen, self.rect
        )

        self.assertTrue(handled)
        self.mouse.click.assert_called_once_with(610, 520)
        action = self.machine.navigation_progress.in_flight
        self.assertEqual(action.action_id, ActionId.EXIT_DOMAIN_TO_LOBBY)
        self.assertEqual(action.expected, PostconditionId.LOBBY)

    @patch("states.town_subflow_perception.detect_building_with_red_dot")
    def test_chest_dispatches_only_after_town_entry_and_red_dot(self, mock_building):
        self.machine.start_subflow_queue(["chest", "hero_draw"])
        self.machine.current_state = self.machine.STATE_NAVIGATING
        self.matcher.match.side_effect = lambda _img, name, **_kw: (
            ((200, 550), 0.95)
            if name == "common/door.png"
            else (None, 0.0)
        )
        mock_building.return_value = BuildingCheckResult(
            True, True, building_pos=(250, 300), confidence_building=0.9
        )

        handled = self.machine.handle_town_subflow_precondition(
            self.screen, self.rect
        )

        self.assertTrue(handled)
        self.assertEqual(self.machine.current_state, self.machine.STATE_CHEST)
        self.assertEqual(self.machine.current_town_subflow, "chest")
        self.assertEqual(self.machine.town_subflow_queue, ["hero_draw"])
        self.assertEqual(self.machine.config["type"], "chest")
        self.mouse.click.assert_not_called()

    def test_dungeon_exploring_keeps_owning_the_workflow(self):
        self.machine.start_subflow_queue(["chest"])
        self.machine.current_state = self.machine.STATE_DUNGEON_EXPLORING
        self.machine.is_in_dungeon = True
        self.matcher.match.return_value = ((300, 100), 0.95)

        handled = self.machine.handle_town_subflow_precondition(
            self.screen, self.rect
        )

        self.assertFalse(handled)
        self.assertEqual(
            self.machine.current_state, self.machine.STATE_DUNGEON_EXPLORING
        )
        self.assertEqual(self.machine.current_town_subflow, "chest")
        self.mouse.click.assert_not_called()

    def test_unknown_dungeon_evidence_wins_over_quit_overlay(self):
        self.machine.start_subflow_queue(["chest"])
        self.machine.config = {
            "type": "dungeon",
            "name": "Dungeon",
            "explore_priorities": [],
        }

        def match(_screen, template, **_kwargs):
            if template == "dungeons/dungeon_fight.png":
                return (400, 300), 0.96
            if template == "common/quit.png":
                return (300, 100), 0.95
            return None, 0.0

        self.matcher.match.side_effect = match

        handled = self.machine.handle_town_subflow_precondition(
            self.screen, self.rect
        )

        self.assertFalse(handled)
        self.mouse.click.assert_not_called()

    def test_battle_keeps_owning_frame_until_result_boundary(self):
        self.machine.start_subflow_queue(["chest"])
        self.machine.current_state = self.machine.STATE_BATTLE
        self.matcher.match.return_value = ((300, 100), 0.95)

        handled = self.machine.handle_town_subflow_precondition(
            self.screen, self.rect
        )

        self.assertFalse(handled)
        self.assertEqual(self.machine.current_state, self.machine.STATE_BATTLE)
        self.mouse.click.assert_not_called()

    @patch("states.town_subflow_perception.detect_building_with_red_dot")
    def test_missing_red_dot_completes_subflow_without_defer(self, mock_building):
        self.machine.daily_manager = MagicMock()
        self.machine.start_subflow_queue(["chest", "hero_draw"])
        self.machine.current_state = self.machine.STATE_NAVIGATING
        self.matcher.match.side_effect = lambda _img, name, **_kw: (
            ((200, 550), 0.95)
            if name == "common/door.png"
            else (None, 0.0)
        )
        mock_building.return_value = BuildingCheckResult(
            True, False, building_pos=(250, 300), confidence_building=0.9
        )

        handled = self.machine.handle_town_subflow_precondition(
            self.screen, self.rect
        )

        self.assertTrue(handled)
        self.machine.daily_manager.record_subflow_completed.assert_called_once_with(
            "chest"
        )
        self.machine.daily_manager.defer_subflow.assert_not_called()
        self.assertEqual(self.machine.current_town_subflow, "hero_draw")

    @patch("states.town_subflow_perception.detect_building_with_red_dot")
    def test_missing_town_entry_is_bounded_and_deferred(self, mock_building):
        self.machine.daily_manager = MagicMock()
        self.machine.start_subflow_queue(["chest", "hero_draw"])
        self.machine.current_state = self.machine.STATE_NAVIGATING
        self.matcher.match.side_effect = lambda _img, name, **_kw: (
            ((200, 550), 0.95)
            if name == "common/door.png"
            else (None, 0.0)
        )
        mock_building.return_value = BuildingCheckResult(False, False)

        for _ in range(4):
            self.assertTrue(
                self.machine.handle_town_subflow_precondition(
                    self.screen, self.rect
                )
            )
        self.machine.daily_manager.defer_subflow.assert_not_called()

        self.assertTrue(
            self.machine.handle_town_subflow_precondition(self.screen, self.rect)
        )

        self.machine.daily_manager.defer_subflow.assert_called_once_with(
            "chest", 180
        )
        self.assertEqual(self.machine.current_town_subflow, "hero_draw")

    @patch("states.town_subflow_perception.detect_building_with_red_dot")
    def test_bulletin_board_completes_when_building_is_visible_without_red_dot(
        self, mock_building
    ):
        self.machine.daily_manager = MagicMock()
        self.machine.start_subflow_queue(["bulletin_board"])
        self.machine.current_state = self.machine.STATE_NAVIGATING
        self.matcher.match.side_effect = lambda _img, name, **_kw: (
            ((200, 550), 0.95)
            if name == "common/door.png"
            else (None, 0.0)
        )
        mock_building.return_value = BuildingCheckResult(
            True, False, building_pos=(250, 300), confidence_building=0.9
        )

        handled = self.machine.handle_town_subflow_precondition(
            self.screen, self.rect
        )

        self.assertTrue(handled)
        self.machine.daily_manager.record_subflow_completed.assert_called_once_with(
            "bulletin_board"
        )
        self.machine.daily_manager.defer_subflow.assert_not_called()
        self.assertNotEqual(
            self.machine.current_state, self.machine.STATE_BULLETIN_BOARD
        )

    @patch("states.town_subflow_perception.detect_building_with_red_dot")
    def test_bulletin_board_dispatches_when_building_has_red_dot(
        self, mock_building
    ):
        self.machine.daily_manager = MagicMock()
        self.machine.start_subflow_queue(["bulletin_board"])
        self.machine.current_state = self.machine.STATE_NAVIGATING
        self.matcher.match.side_effect = lambda _img, name, **_kw: (
            ((200, 550), 0.95)
            if name == "common/door.png"
            else (None, 0.0)
        )
        mock_building.return_value = BuildingCheckResult(
            True, True, building_pos=(250, 300), confidence_building=0.9, confidence_red_dot=0.9
        )

        handled = self.machine.handle_town_subflow_precondition(
            self.screen, self.rect
        )

        self.assertTrue(handled)
        self.assertEqual(
            self.machine.current_state, self.machine.STATE_BULLETIN_BOARD
        )

    def test_next_town_subflow_restores_navigation_identity_before_dispatch(self):
        self.machine.primary_config = {"type": "daily", "name": "Daily"}
        self.machine.start_subflow_queue(["chest", "hero_draw"])
        self.machine.current_state = self.machine.STATE_CHEST
        self.machine.config = {"type": "chest", "name": "Chest"}

        self.machine.pop_and_next_town_subflow()

        self.assertEqual(self.machine.current_town_subflow, "hero_draw")
        self.assertEqual(self.machine.current_state, self.machine.STATE_NAVIGATING)
        self.assertEqual(self.machine.config, self.machine.primary_config)

    def test_dispatched_hero_handler_does_not_reclaim_lobby_navigation(self):
        self.machine.current_town_subflow = "hero_draw"
        self.machine.current_state = self.machine.STATE_HERO_DRAW
        self.machine.config = {"type": "hero_draw", "name": "Hero"}
        handler = self.machine.handlers[self.machine.STATE_HERO_DRAW]

        self.matcher.match.side_effect = lambda _img, name, **_kw: (
            ((100, 200), 0.95)
            if name == "goback_town.png"
            else (None, 0.0)
        )

        handler.handle(self.screen, self.rect)

        self.mouse.click.assert_not_called()

    @patch("states.state_machine.os.path.exists", return_value=True)
    def test_task_complete_popup_preempts_town_return(self, _mock_exists):
        self.machine.start_subflow_queue(["chest"])
        self.machine.current_state = self.machine.STATE_NAVIGATING
        self.machine.capturer.get_window_rect.return_value = self.rect
        self.machine.capturer.capture.return_value = self.screen

        def match(_img, template, **_kwargs):
            if template == "task_complete.png":
                return (300, 100), 0.95
            if template == "goback_town.png":
                return (100, 200), 0.95
            return None, 0.0

        self.matcher.match.side_effect = match
        with (
            patch.object(self.machine.exception_watchdog, "check", return_value=False),
            patch.object(self.machine, "_run_task_complete_subflow") as task_flow,
        ):
            self.machine.step()

        task_flow.assert_called_once_with(self.rect)
        self.mouse.click.assert_not_called()

    def test_repeated_navigation_timeout_defers_instead_of_clicking_forever(self):
        self.machine.daily_manager = MagicMock()
        self.machine.start_subflow_queue(["chest"])
        self.machine.current_state = self.machine.STATE_NAVIGATING
        self.matcher.match.side_effect = lambda _img, name, **_kw: (
            ((50, 500), 0.92)
            if name == "town_building/exitfromhouse_and_to_town.png"
            else (None, 0.0)
        )

        max_attempts = self.machine.navigation_progress.settings.action_max_attempts
        timeout = self.machine.navigation_progress.settings.action_timeout_seconds
        self.assertTrue(
            self.machine.handle_town_subflow_precondition(self.screen, self.rect)
        )
        for _ in range(max_attempts):
            self.clock.advance(timeout + 0.1)
            self.machine.handle_town_subflow_precondition(self.screen, self.rect)

        self.machine.daily_manager.defer_subflow.assert_called_once_with(
            "chest", 180
        )
        self.assertIsNone(self.machine.current_town_subflow)
        self.assertEqual(self.mouse.click.call_count, max_attempts)

    def test_unknown_state_relocalizes_result_before_town_navigation(self):
        self.machine.start_subflow_queue(["chest"])

        def match(_screen, template, **_kwargs):
            if template == "common/continue.png":
                return (300, 450), 0.94
            return None, 0.0

        self.matcher.match.side_effect = match

        with patch("states.state_machine.os.path.exists", return_value=True):
            self.machine.detect_current_state(self.screen, self.rect)

        self.assertEqual(self.machine.current_state, self.machine.STATE_RESULT)


class TownSubflowResultBoundaryTestCase(unittest.TestCase):
    def setUp(self):
        self.matcher = MagicMock()
        self.matcher.templates_dir = "templates"
        self.mouse = MagicMock()
        self.machine = GameStateMachine(
            capturer=MagicMock(),
            matcher=self.matcher,
            mouse=self.mouse,
            preload_ocr=False,
        )
        self.machine.config = {
            "type": "stage",
            "name": "Stage",
            "battle_max_defeat": 3,
        }
        self.screen = np.zeros((600, 800, 3), dtype=np.uint8)
        self.rect = {"left": 0, "top": 0, "width": 800, "height": 600}

    @patch("states.handlers.result.os.path.exists", return_value=True)
    def test_normal_result_exits_for_pending_town_subflow(self, _mock_exists):
        self.machine.start_subflow_queue(["chest"])
        self.machine.current_state = self.machine.STATE_RESULT
        handler = self.machine.handlers[self.machine.STATE_RESULT]
        handler.subflow_step = "FINAL_MATCH"

        def match(_screen, template, **_kwargs):
            if template == "exit_battle.png":
                return (100, 200), 0.95
            if template == "stages/retry.png":
                return (300, 200), 0.95
            return None, 0.0

        self.matcher.match.side_effect = match
        handler.click_and_wait_until_gone = MagicMock()

        handler.handle(self.screen, self.rect)

        handler.click_and_wait_until_gone.assert_called_once()
        self.assertEqual(
            handler.click_and_wait_until_gone.call_args.args[0],
            "exit_battle.png",
        )

    @patch("states.handlers.result.os.path.exists", return_value=True)
    def test_dungeon_result_is_not_forced_to_exit(self, _mock_exists):
        self.machine.start_subflow_queue(["chest"])
        self.machine.current_state = self.machine.STATE_RESULT
        self.machine.is_in_dungeon = True
        self.machine.config = {
            "type": "dungeon",
            "name": "Dungeon",
            "battle_max_defeat": 3,
        }
        handler = self.machine.handlers[self.machine.STATE_RESULT]
        handler.subflow_step = "FINAL_MATCH"

        def match(_screen, template, **_kwargs):
            if template == "exit_battle.png":
                return (100, 200), 0.95
            if template == "stages/retry.png":
                return (300, 200), 0.95
            return None, 0.0

        self.matcher.match.side_effect = match
        handler.click_and_wait_until_gone = MagicMock()

        handler.handle(self.screen, self.rect)

        handler.click_and_wait_until_gone.assert_called_once()
        self.assertEqual(
            handler.click_and_wait_until_gone.call_args.args[0],
            "stages/retry.png",
        )


if __name__ == "__main__":
    unittest.main()
