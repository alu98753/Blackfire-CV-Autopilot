"""
Unit and Integration tests for Town-Requiring Consumer Integration & Login Boundary Regression (Slice 4).

Verifies Spec Section 6 (Slice 4) and Section 7 Acceptance Scenarios:
1. Scenario 1: Login Mislocation with Town Consumer
   - Login satisfies WORLD_READY only; does not act as a town navigator.
   - When a town consumer (e.g. Chest) is pending, shared REACH_TOWN normalization
     exits the building, establishes Town readiness, and dispatches the workflow.
2. Scenario 2: Login / Relaunch in Dungeon (Negative Boundary Protection)
   - Login completes in dungeon; satisfies WORLD_READY with is_in_dungeon=True.
   - System MUST NOT force REACH_TOWN; dungeon continuation is strictly preserved.
3. Scenario 5: Already in Town (Zero Redundancy)
   - When screen is already verified SceneId.TOWN with clear anchor, REACH_TOWN issues
     zero extra clicks and immediately dispatches the business workflow.
"""

import unittest
from unittest.mock import MagicMock, patch

import numpy as np

from states.login_flow import _wait_for_town
from states.navigation_intent import ActionId, IntentId, PostconditionId
from states.reach_town_normalization import (
    NormalizationResult,
    ReachTownNormalizationController,
)
from states.state_machine import GameStateMachine
from utils.scene_catalog import SceneCatalog
from utils.scene_detector import SceneDetector, SceneInfo, SceneType
from utils.scene_snapshot import ElementId, ElementMatch, SceneId, SceneSnapshot
from utils.town_building_detector import BuildingCheckResult


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class TestLoginAndTownBoundaryRegression(unittest.TestCase):
    def setUp(self):
        self.capturer = MagicMock()
        self.matcher = MagicMock()
        self.matcher.templates_dir = "templates"
        self.mouse = MagicMock()
        self.clock = FakeClock()
        self.machine = GameStateMachine(
            capturer=self.capturer,
            matcher=self.matcher,
            mouse=self.mouse,
            preload_ocr=False,
            clock=self.clock,
        )
        self.machine.config = {"type": "daily", "name": "Daily"}
        self.machine.primary_config = self.machine.config.copy()
        self.screen = np.zeros((600, 800, 3), dtype=np.uint8)
        self.rect = {"left": 0, "top": 0, "width": 800, "height": 600}
        self.capturer.get_window_rect.return_value = self.rect
        self.capturer.capture.return_value = self.screen

    @patch("states.town_subflow_perception.detect_building_with_red_dot")
    @patch("utils.scene_detector.SceneDetector.detect")
    def test_scenario_1_login_mislocation_with_town_consumer(
        self, mock_scene_detect, mock_building_detect
    ):
        """
        [Spec Scenario 1 Verification]:
        Given: Login flow completes and observes a valid known-world scene, but physical scene is TOWN_BUILDING.
        And: The next intended workflow requires TOWN (e.g. Chest).
        Then:
          1. Login satisfies WORLD_READY only (does not force town navigation inside login_flow).
          2. Before the Town-dependent workflow executes, shared REACH_TOWN normalization exits the building,
             verifies SceneId.TOWN, and then executes the original intended workflow.
        """
        # 1. 模擬登入完成：全域感知識別為 TOWN_BUILDING (KNOWN_WORLD_SCENE 成立)
        mock_scene_detect.return_value = SceneInfo(
            scene_type=SceneType.TOWN_BUILDING,
            is_town=False,
            is_lobby=False,
            is_in_dungeon=False,
        )
        self.matcher.match.return_value = (None, 0.0)

        with patch("states.login_flow.time.sleep"):
            login_success = _wait_for_town(self.machine, self.rect)

        # 斷言 1: Login 流程成功，滿足 WORLD_READY
        self.assertTrue(login_success)
        self.assertFalse(self.machine.is_in_dungeon)

        # 2. 設定下一個 Intent 為需要城鎮的 Chest 子流程
        self.machine.start_subflow_queue(["chest"])
        self.machine.current_state = self.machine.STATE_NAVIGATING
        self.assertEqual(self.machine.current_town_subflow, "chest")

        # 3. 模擬當前畫面為 TOWN_BUILDING (exitfromhouse_and_to_town 可見)
        def match_building(_screen, template, **_kw):
            if template == "town_building/exitfromhouse_and_to_town.png":
                return (60, 520), 0.92
            return None, 0.0

        self.matcher.match.side_effect = match_building

        # 執行 Precondition: shared REACH_TOWN normalization 點擊離開建築
        handled_step1 = self.machine.handle_town_subflow_precondition(self.screen, self.rect)
        self.assertTrue(handled_step1)
        self.mouse.click.assert_called_with(60, 520)
        self.assertEqual(
            self.machine.navigation_progress.in_flight.action_id,
            ActionId.EXIT_BUILDING_TO_TOWN,
        )
        # 業務 Intent 完好保留在 chest，未提前派發或丟棄
        self.assertEqual(self.machine.current_town_subflow, "chest")
        self.assertEqual(self.machine.current_state, self.machine.STATE_NAVIGATING)

        # 4. 退出建築後畫面抵達城鎮 (door.png + arena_of_glory.png + 寶箱建築帶紅點)
        def match_town(_screen, template, **_kw):
            if template in ("common/door.png", "town_building/arena_of_glory/arena_of_glory.png"):
                return (200, 550), 0.95
            return None, 0.0

        self.matcher.match.side_effect = match_town
        mock_building_detect.return_value = BuildingCheckResult(
            True, True, building_pos=(250, 350), confidence_building=0.9
        )

        handled_step2 = self.machine.handle_town_subflow_precondition(self.screen, self.rect)
        self.assertTrue(handled_step2)

        # 斷言 2: 抵達城鎮且驗證 Ready 後，順利派發至 STATE_CHEST！
        self.assertEqual(self.machine.current_state, self.machine.STATE_CHEST)
        self.assertEqual(self.machine.current_town_subflow, "chest")

    @patch("utils.scene_detector.SceneDetector.detect")
    def test_scenario_2_login_relaunch_in_dungeon_negative_boundary_protection(
        self, mock_scene_detect
    ):
        """
        [Spec Scenario 2 Verification]:
        Given: Login or relaunch completes
        When: Physical scene is observed to be IN_DUNGEON
        Then:
          1. WORLD_READY is satisfied
          2. System MUST NOT force REACH_TOWN
          3. Existing dungeon recovery / continuation behavior is strictly preserved.
        """
        # 模擬登入完成，全域感知識別身處地下城
        mock_scene_detect.return_value = SceneInfo(
            scene_type=SceneType.IN_DUNGEON,
            is_town=False,
            is_lobby=False,
            is_in_dungeon=True,
        )
        self.matcher.match.return_value = (None, 0.0)

        with patch("states.login_flow.time.sleep"):
            login_success = _wait_for_town(self.machine, self.rect)

        # 斷言 1: Login 成功，WORLD_READY 滿足，且標記 is_in_dungeon = True
        self.assertTrue(login_success)
        self.assertTrue(self.machine.is_in_dungeon)

        # 模擬 detect_current_state 定位為 STATE_DUNGEON_EXPLORING
        self.machine.current_state = self.machine.STATE_DUNGEON_EXPLORING

        # 模擬隊列中有城鎮任務
        self.machine.start_subflow_queue(["chest"])
        self.machine.current_state = self.machine.STATE_DUNGEON_EXPLORING

        # 執行 Precondition 檢查
        handled = self.machine.handle_town_subflow_precondition(self.screen, self.rect)

        # 斷言 2: 系統絕不強迫觸發 REACH_TOWN，讓渡給地下城狀態！
        self.assertFalse(handled)
        self.assertEqual(self.machine.current_state, self.machine.STATE_DUNGEON_EXPLORING)
        self.mouse.click.assert_not_called()

    @patch("states.town_subflow_perception.detect_building_with_red_dot")
    def test_scenario_5_already_in_town_zero_redundant_clicks(
        self, mock_building_detect
    ):
        """
        [Spec Scenario 5 Verification]:
        Given: A workflow requiring TOWN starts (e.g. chest subflow queue)
        When: Physical screen is already SceneId.TOWN (common/door.png + arena_of_glory.png visible)
        Then:
          1. REACH_TOWN normalization policy issues zero extra clicks (mouse.click NOT called for navigation).
          2. Immediately dispatches / continues the target workflow.
        """
        self.machine.start_subflow_queue(["chest"])
        self.machine.current_state = self.machine.STATE_NAVIGATING
        self.machine.daily_manager = MagicMock()

        # 畫面物理狀態已完全在城鎮且 Ready
        def match_town_ready(_screen, template, **_kw):
            if template in ("common/door.png", "town_building/arena_of_glory/arena_of_glory.png"):
                return (200, 550), 0.95
            return None, 0.0

        self.matcher.match.side_effect = match_town_ready
        mock_building_detect.return_value = BuildingCheckResult(
            True, True, building_pos=(250, 350), confidence_building=0.9
        )

        handled = self.machine.handle_town_subflow_precondition(self.screen, self.rect)

        self.assertTrue(handled)
        # 斷言 1: 零多餘點擊！完全沒有發起任何導航點擊
        self.mouse.click.assert_not_called()
        # 斷言 2: 立即派發目標子流程
        self.assertEqual(self.machine.current_state, self.machine.STATE_CHEST)
        self.assertEqual(self.machine.current_town_subflow, "chest")


if __name__ == "__main__":
    unittest.main()
