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

        # 第 1 幀：防抖確認中，吞下幀不提前結案
        self.assertTrue(
            self.machine.handle_town_subflow_precondition(self.screen, self.rect)
        )
        self.machine.daily_manager.record_subflow_completed.assert_not_called()
        self.assertEqual(self.machine.current_town_subflow, "chest")

        # 第 2 幀：連續確認無紅點達標，標記完成並前進下一任務
        self.assertTrue(
            self.machine.handle_town_subflow_precondition(self.screen, self.rect)
        )
        self.machine.daily_manager.record_subflow_completed.assert_called_once_with(
            "chest"
        )
        self.machine.daily_manager.defer_subflow.assert_not_called()
        self.assertEqual(self.machine.current_town_subflow, "hero_draw")

    @patch("states.town_subflow_perception.detect_building_with_red_dot")
    def test_missing_red_dot_resets_debounce_if_red_dot_appears(self, mock_building):
        self.machine.daily_manager = MagicMock()
        self.machine.start_subflow_queue(["chest"])
        self.machine.current_state = self.machine.STATE_NAVIGATING
        self.matcher.match.side_effect = lambda _img, name, **_kw: (
            ((200, 550), 0.95)
            if name == "common/door.png"
            else (None, 0.0)
        )
        # 第 1 幀：看見建築但無紅點
        mock_building.return_value = BuildingCheckResult(
            True, False, building_pos=(250, 300), confidence_building=0.9
        )
        self.assertTrue(
            self.machine.handle_town_subflow_precondition(self.screen, self.rect)
        )
        self.machine.daily_manager.record_subflow_completed.assert_not_called()

        # 第 2 幀：紅點出現！防抖計數重置，立即派發進入 chest 子流程
        mock_building.return_value = BuildingCheckResult(
            True, True, building_pos=(250, 300), confidence_building=0.9, confidence_red_dot=0.95
        )
        self.assertTrue(
            self.machine.handle_town_subflow_precondition(self.screen, self.rect)
        )
        self.machine.daily_manager.record_subflow_completed.assert_not_called()
        self.assertEqual(self.machine.current_state, self.machine.STATE_CHEST)

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

        # 第 1 幀防抖
        self.assertTrue(
            self.machine.handle_town_subflow_precondition(self.screen, self.rect)
        )
        self.machine.daily_manager.record_subflow_completed.assert_not_called()

        # 第 2 幀確認完成
        self.assertTrue(
            self.machine.handle_town_subflow_precondition(self.screen, self.rect)
        )

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
        self.clock = FakeClock()
        self.machine = GameStateMachine(
            capturer=MagicMock(),
            matcher=self.matcher,
            mouse=self.mouse,
            preload_ocr=False,
            clock=self.clock,
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

    def test_town_anchors_exclude_exit_battle_false_positive(self):
        """驗證當畫面存在城鎮大門時，排斥 exit_battle (0.8038) 誤匹配，正確識別為 TOWN"""
        perception = self.machine.town_subflow_precondition.perception

        def match(_screen, template, threshold=0.8, **_kwargs):
            if template == "common/door.png":
                return (68, 719), 0.9543
            if template == "diamond.png":
                return (1107, 52), 0.9750
            if template == "exit_battle.png":
                # 模擬背景暗處誤匹配
                return (1115, 764), 0.8038 if threshold <= 0.8038 else 0.0
            return None, 0.0

        self.matcher.match.side_effect = match
        snapshot = perception.observe(self.screen, "chest")
        self.assertEqual(snapshot.scene, SceneId.TOWN)

    def test_activity_scheduler_does_not_fall_back_to_collect_only_when_town_subflow_pending(self):
        """驗證當有待辦城鎮子流程時，調度器不會穿透進入 COLLECT_ONLY 兜底待機"""
        self.machine.start_subflow_queue(["hero_draw"])
        self.machine.current_state = self.machine.STATE_NAVIGATING
        # 模擬所有週期性活動 (Boss, Dungeon) 均在冷卻中
        self.machine.daily_manager = MagicMock()
        self.machine.daily_manager.get_pending_town_subflows.return_value = []
        self.machine.get_available_selected_lord_bosses = MagicMock(return_value=[])
        self.machine.has_available_dungeon = MagicMock(return_value=False)

        scheduled = self.machine.evaluate_next_activity()
        self.assertTrue(scheduled)
        self.assertNotEqual(self.machine.current_state, self.machine.STATE_COLLECT_ONLY)

    def test_collect_only_daily_reset_resumes_navigating_with_primary_config(self):
        """驗證 08:05 跨日重置時，CollectOnlyHandler 正確還原 primary_config 並切換至 NAVIGATING"""
        self.machine.current_state = self.machine.STATE_COLLECT_ONLY
        self.machine.pending_daily_reset_exit = True
        self.machine.stamina_retreat_start_time = 12345.0
        self.machine.primary_config = {"type": "daily", "name": "Daily"}
        self.machine.config = {"type": "collect_only", "name": "Collect"}

        handler = self.machine.handlers[self.machine.STATE_COLLECT_ONLY]
        handler.handle(self.screen, self.rect)

        self.assertFalse(self.machine.pending_daily_reset_exit)
        self.assertIsNone(self.machine.stamina_retreat_start_time)
        self.assertEqual(self.machine.config.get("type"), "daily")
        self.assertEqual(self.machine.current_state, self.machine.STATE_NAVIGATING)

    def test_collect_only_boss_wake_guarded_by_pending_town_subflow(self):
        """驗證待辦城鎮任務存在時，Boss 冷卻結束不會抹殺城鎮佇列"""
        self.machine.current_state = self.machine.STATE_COLLECT_ONLY
        self.machine.start_subflow_queue(["blood_altar"])
        self.machine.daily_manager = MagicMock()
        self.machine.get_available_selected_lord_bosses = MagicMock(return_value=["lord_spider"])
        self.machine.config = {"type": "collect_only", "name": "Collect"}
        self.matcher.match.return_value = (None, 0.0)

        handler = self.machine.handlers[self.machine.STATE_COLLECT_ONLY]
        handler.handle(self.screen, self.rect)

        # 佇列頭部應保持為 blood_altar，未被 lord_boss 覆蓋
        self.assertEqual(self.machine.current_town_subflow, "blood_altar")

    def test_deferred_bread_collection_does_not_block_town_precondition(self):
        """驗證領體力進入 DEFER 退避期間，不視為 pending，不阻塞城鎮前置條件"""
        controller = self.machine.town_subflow_precondition
        self.machine.enable_bread = True
        self.machine.need_bread_collection = True

        # 未被 defer 時，_collection_pending 應為 True
        self.assertTrue(controller._collection_pending())

        # 模擬領體力 defer
        self.machine.navigation_progress.defer(IntentId.COLLECT_BREAD, self.clock.monotonic())

        # 處於 defer 期間，_collection_pending 應為 False
        self.assertFalse(controller._collection_pending())

    def test_bread_collection_handler_clears_flag_on_timeout_defer(self):
        """驗證 BreadCollectionHandler 在連續 3 幀未見元素逾時退避時，清除 need_bread_collection"""
        self.machine.current_state = self.machine.STATE_BREAD_COLLECTION
        self.machine.enable_bread = True
        self.machine.need_bread_collection = True
        self.machine.bread_window_opened = True
        self.matcher.match.return_value = (None, 0.0)

        handler = self.machine.handlers[self.machine.STATE_BREAD_COLLECTION]

        # 前 2 幀：累計未發現次數
        handler.handle(self.screen, self.rect)
        handler.handle(self.screen, self.rect)
        self.assertTrue(self.machine.need_bread_collection)

        # 第 3 幀：觸發逾時退避
        handler.handle(self.screen, self.rect)
        self.assertFalse(self.machine.need_bread_collection)
        self.assertFalse(self.machine.bread_window_opened)
        self.assertTrue(self.machine.navigation_progress.is_deferred(IntentId.COLLECT_BREAD, self.clock.monotonic()))

    def test_diamond_collection_handler_clears_flag_on_timeout_defer(self):
        """驗證 DiamondCollectionHandler 在連續 3 幀未見元素逾時退避時，清除 need_diamond_collection"""
        self.machine.current_state = self.machine.STATE_DIAMOND_COLLECTION
        self.machine.need_diamond_collection = True
        self.machine.diamond_window_opened = True
        self.matcher.match.return_value = (None, 0.0)

        handler = self.machine.handlers[self.machine.STATE_DIAMOND_COLLECTION]

        # 前 2 幀
        handler.handle(self.screen, self.rect)
        handler.handle(self.screen, self.rect)
        self.assertTrue(self.machine.need_diamond_collection)

        # 第 3 幀：觸發逾時退避
        handler.handle(self.screen, self.rect)
        self.assertFalse(self.machine.need_diamond_collection)
        self.assertFalse(self.machine.diamond_window_opened)
        self.assertTrue(self.machine.navigation_progress.is_deferred(IntentId.COLLECT_DIAMOND, self.clock.monotonic()))


if __name__ == "__main__":
    unittest.main()

