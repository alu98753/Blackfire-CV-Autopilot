"""
Unit and Integration tests for Committed Handler Mislocation Relinquishment Protocol (Slice 3).

Verifies Spec Scenario 4 & Invariant 2:
1. When a committed handler (e.g. ChestHandler) observes physical mislocation
   (e.g. exitfromhouse_and_to_town / goback_town visible, but its own building missing):
   - It performs bounded consecutive confirmation (2 frames).
   - Upon confirmation, it yields/relinquishes physical ownership back to shared
     REACH_TOWN normalization path without mutating the active intent.
   - Strict Invariant 2: MUST NOT defer, pop, or complete the business intent.
2. Full Scenario 4 End-to-End Cycle:
   STATE_CHEST (mislocated in Blood Altar)
   -> Relinquish to STATE_NAVIGATING
   -> REACH_TOWN normalization exits building to Town
   -> Redispatches to STATE_CHEST cleanly.
3. Resilience to perception flicker:
   If own building reappears on frame 2, mislocation_count resets and normal execution resumes.
4. Absence of both own features and exit features falls back to bounded retry/defer.
"""

import unittest
from unittest.mock import MagicMock, patch

import numpy as np

from states.handlers.chest import ChestHandler
from states.navigation_intent import ActionId, IntentId, PostconditionId
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


class TestHandlerMislocationRelinquish(unittest.TestCase):
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
        self.machine.config = {"type": "chest", "name": "Chest"}
        self.machine.primary_config = self.machine.config.copy()
        self.screen = np.zeros((600, 800, 3), dtype=np.uint8)
        self.rect = {"left": 0, "top": 0, "width": 800, "height": 600}
        self.handler = ChestHandler(self.machine)

    @patch("states.handlers.chest.detect_building_with_red_dot")
    def test_chest_handler_relinquishes_after_consecutive_mislocation_frames(self, mock_detect):
        """
        驗證 ChestHandler committed 後，若畫面為非自身房間 (exitfromhouse 可見但無寶箱)：
        - 第 1 幀：mislocation_count = 1，回傳 True，不釋放，不 defer，不 pop。
        - 第 2 幀：mislocation_count = 2，主動呼叫 relinquish_subflow_to_navigation，
          轉移至 STATE_NAVIGATING。
        - 核心守護 Invariant 2：current_town_subflow 完好保留，未調用 defer 或 pop！
        """
        self.machine.current_state = self.machine.STATE_CHEST
        self.machine.current_town_subflow = "chest"
        self.machine.town_subflow_queue = ["hero_draw"]
        self.machine.daily_manager = MagicMock()

        # 模擬畫面：未找到寶箱建築，但找到 exitfromhouse_and_to_town
        mock_detect.return_value = BuildingCheckResult(False, False)

        def match(_screen, template, **_kw):
            if template == "town_building/exitfromhouse_and_to_town.png":
                return (50, 500), 0.92
            return None, 0.0

        self.matcher.match.side_effect = match

        # 第 1 幀：防抖確認中
        res1 = self.handler.handle(self.screen, self.rect)
        self.assertTrue(res1)
        self.assertEqual(self.handler.mislocation_count, 1)
        self.assertEqual(self.machine.current_state, self.machine.STATE_CHEST)
        self.assertEqual(self.machine.current_town_subflow, "chest")
        self.assertEqual(self.machine.town_subflow_queue, ["hero_draw"])
        self.machine.daily_manager.defer_subflow.assert_not_called()
        self.machine.daily_manager.record_subflow_completed.assert_not_called()

        # 第 2 幀：連續確認成立，觸發 Relinquish
        self.handler.last_action_time = 0.0  # 推進冷卻
        res2 = self.handler.handle(self.screen, self.rect)
        self.assertTrue(res2)
        # 實體所有權已轉移至 STATE_NAVIGATING
        self.assertEqual(self.machine.current_state, self.machine.STATE_NAVIGATING)
        # 嚴格守護 Invariant 2：業務 Intent 絕不變異！
        self.assertEqual(self.machine.current_town_subflow, "chest")
        self.assertEqual(self.machine.town_subflow_queue, ["hero_draw"])
        self.machine.daily_manager.defer_subflow.assert_not_called()
        self.machine.daily_manager.record_subflow_completed.assert_not_called()

    @patch("states.handlers.chest.detect_building_with_red_dot")
    def test_chest_handler_relinquishes_when_in_lobby(self, mock_detect):
        """驗證若 committed 後誤入大廳 (goback_town 可見)，同樣連續 2 幀後 Relinquish 回城。"""
        self.machine.current_state = self.machine.STATE_CHEST
        self.machine.current_town_subflow = "chest"
        self.machine.daily_manager = MagicMock()
        mock_detect.return_value = BuildingCheckResult(False, False)

        def match(_screen, template, **_kw):
            if template == "goback_town.png":
                return (40, 50), 0.88
            return None, 0.0

        self.matcher.match.side_effect = match

        # 第 1 幀
        self.handler.handle(self.screen, self.rect)
        self.assertEqual(self.handler.mislocation_count, 1)
        self.assertEqual(self.machine.current_state, self.machine.STATE_CHEST)

        # 第 2 幀
        self.handler.last_action_time = 0.0
        self.handler.handle(self.screen, self.rect)
        self.assertEqual(self.machine.current_state, self.machine.STATE_NAVIGATING)
        self.assertEqual(self.machine.current_town_subflow, "chest")
        self.machine.daily_manager.defer_subflow.assert_not_called()

    @patch("states.handlers.chest.detect_building_with_red_dot")
    def test_perception_flicker_recovers_without_relinquish(self, mock_detect):
        """
        驗證感知防抖韌性：
        第 1 幀誤判/閃爍未見寶箱 (mislocation_count=1)；
        第 2 幀自身寶箱特徵恢復可見，mislocation_count 歸零並正常進入建築，不退讓！
        """
        self.machine.current_state = self.machine.STATE_CHEST
        self.machine.current_town_subflow = "chest"

        # 第 1 幀：閃爍未見寶箱
        mock_detect.return_value = BuildingCheckResult(False, False)
        self.matcher.match.side_effect = lambda _s, t, **_kw: (
            ((50, 500), 0.92) if t == "town_building/exitfromhouse_and_to_town.png" else (None, 0.0)
        )
        self.handler.handle(self.screen, self.rect)
        self.assertEqual(self.handler.mislocation_count, 1)
        self.assertEqual(self.machine.current_state, self.machine.STATE_CHEST)

        # 第 2 幀：寶箱特徵恢復且帶紅點
        self.handler.last_action_time = 0.0
        mock_detect.return_value = BuildingCheckResult(
            True, True, building_pos=(300, 400), confidence_building=0.9
        )
        with patch("os.path.exists", return_value=True):
            self.handler.handle(self.screen, self.rect)

        # 斷言：mislocation 計數歸零，推進至 CLICK_FREE_CHEST，未退讓
        self.assertEqual(self.handler.mislocation_count, 0)
        self.assertEqual(self.handler.step_phase, "CLICK_FREE_CHEST")
        self.assertEqual(self.machine.current_state, self.machine.STATE_CHEST)
        self.mouse.click.assert_called_once_with(300, 400)

    @patch("states.handlers.chest.detect_building_with_red_dot")
    def test_no_own_feature_and_no_exit_falls_back_to_bounded_defer(self, mock_detect):
        """驗證若自身特徵遺失且無 exit/goback (如黑屏或未知場景)，維持原有的 5 幀 defer 機制。"""
        self.machine.current_state = self.machine.STATE_CHEST
        self.machine.current_town_subflow = "chest"
        self.machine.daily_manager = MagicMock()
        mock_detect.return_value = BuildingCheckResult(False, False)
        self.matcher.match.return_value = (None, 0.0)

        for _ in range(4):
            self.handler.last_action_time = 0.0
            self.handler.handle(self.screen, self.rect)
            self.assertEqual(self.handler.mislocation_count, 0)
            self.machine.daily_manager.defer_subflow.assert_not_called()

        # 第 5 幀耗盡
        self.handler.last_action_time = 0.0
        self.handler.handle(self.screen, self.rect)
        self.machine.daily_manager.defer_subflow.assert_called_once_with("chest", 180)

    @patch("states.town_subflow_perception.detect_building_with_red_dot")
    @patch("states.handlers.chest.detect_building_with_red_dot")
    def test_scenario_4_full_end_to_end_cycle(self, mock_chest_detect, mock_prec_detect):
        """
        [Spec Scenario 4 Full Acceptance Test]:
        Given: Subflow A (Chest) is committed (current_state == STATE_CHEST)
        When: Physical screen is observed to be an unrelated TOWN_BUILDING (Blood Altar, exitfromhouse visible)
        Then:
          1. ChestHandler yields ownership without calling defer_subflow or mutating intent.
          2. System transitions to STATE_NAVIGATING.
          3. REACH_TOWN normalization exits building to TOWN.
          4. ChestHandler is resumed / redispatched from TOWN.
        """
        self.machine.handlers[self.machine.STATE_CHEST] = self.handler
        self.machine.start_subflow_queue(["chest", "hero_draw"])
        self.machine.daily_manager = MagicMock()

        # 模擬已完成 dispatch，處於 STATE_CHEST
        self.machine.transition_to(self.machine.STATE_CHEST)
        self.assertEqual(self.machine.current_state, self.machine.STATE_CHEST)
        self.assertEqual(self.machine.current_town_subflow, "chest")

        # 1. 模擬畫面處於血之祭壇內部 (exitfromhouse 可見，無寶箱)
        mock_chest_detect.return_value = BuildingCheckResult(False, False)

        def match_blood_altar(_screen, template, **_kw):
            if template == "town_building/exitfromhouse_and_to_town.png":
                return (50, 500), 0.92
            return None, 0.0

        self.matcher.match.side_effect = match_blood_altar

        # 幀 1: ChestHandler 偵測到 mislocation (1/2)
        h1 = self.machine.handlers[self.machine.STATE_CHEST].handle(self.screen, self.rect)
        self.assertTrue(h1)
        self.assertEqual(self.machine.current_state, self.machine.STATE_CHEST)

        # 幀 2: ChestHandler 連續確認 (2/2) -> 主動 Relinquish 實體所有權至 STATE_NAVIGATING！
        self.handler.last_action_time = 0.0
        h2 = self.machine.handlers[self.machine.STATE_CHEST].handle(self.screen, self.rect)
        self.assertTrue(h2)
        self.assertEqual(self.machine.current_state, self.machine.STATE_NAVIGATING)
        self.assertEqual(self.machine.current_town_subflow, "chest")
        self.assertTrue(self.machine.town_normalization_pending)
        self.machine.daily_manager.defer_subflow.assert_not_called()

        # 幀 3: 主迴圈執行 handle_town_subflow_precondition (在 STATE_NAVIGATING)
        # REACH_TOWN 看到 exitfromhouse -> 點擊退場 (IN_PROGRESS)
        prec1 = self.machine.handle_town_subflow_precondition(self.screen, self.rect)
        self.assertTrue(prec1)
        self.mouse.click.assert_called_with(50, 500)
        self.assertEqual(
            self.machine.navigation_progress.in_flight.action_id,
            ActionId.EXIT_BUILDING_TO_TOWN,
        )

        # 幀 4: 退場後畫面抵達城鎮 (door.png + arena_of_glory.png + 寶箱建築帶紅點)
        def match_town_ready(_screen, template, **_kw):
            if template in ("common/door.png", "town_building/arena_of_glory/arena_of_glory.png"):
                return (200, 550), 0.95
            return None, 0.0

        self.matcher.match.side_effect = match_town_ready
        mock_prec_detect.return_value = BuildingCheckResult(
            True, True, building_pos=(300, 400), confidence_building=0.9
        )

        prec2 = self.machine.handle_town_subflow_precondition(self.screen, self.rect)
        self.assertTrue(prec2)

        # 斷言：城鎮 Precondition 通過，寶箱子流程被重新派發，token 已清除！
        self.assertEqual(self.machine.current_state, self.machine.STATE_CHEST)
        self.assertEqual(self.machine.current_town_subflow, "chest")
        self.assertEqual(self.machine.town_subflow_queue, ["hero_draw"])
        self.assertFalse(self.machine.town_normalization_pending)
        self.machine.daily_manager.defer_subflow.assert_not_called()
        self.machine.daily_manager.record_subflow_completed.assert_not_called()

    @patch("states.town_subflow_perception.detect_building_with_red_dot")
    @patch("states.handlers.chest.detect_building_with_red_dot")
    def test_diamond_collection_must_not_preempt_relinquished_normalization(
        self, mock_chest_detect, mock_prec_detect
    ):
        """
        [Mandatory Regression / Guaranteed Ownership Handoff Verification]:
        Given:
          Chest committed (current_state == STATE_CHEST, current_town_subflow == 'chest')
          + physical scene = other Town building (exitfromhouse visible)
          + need_diamond_collection = True (待領鑽石)
        When:
          Chest relinquishes (after 2-frame confirmation)
        Then:
          1. current_town_subflow remains 'chest' (Intent preserved).
          2. town_normalization_pending is True (Explicit ownership token set).
          3. REACH_TOWN normalization owns the next physical action:
             Diamond collection MUST NOT preempt! (_should_skip_handle returns False).
          4. Physical normalization exits building (EXIT_BUILDING_TO_TOWN).
          5. Town ready achieved -> redispatch Chest -> town_normalization_pending cleared.
        """
        self.machine.handlers[self.machine.STATE_CHEST] = self.handler
        self.machine.start_subflow_queue(["chest"])
        self.machine.daily_manager = MagicMock()
        self.machine.need_diamond_collection = True

        self.machine.transition_to(self.machine.STATE_CHEST)
        self.assertEqual(self.machine.current_state, self.machine.STATE_CHEST)
        self.assertEqual(self.machine.current_town_subflow, "chest")

        # 1. 模擬畫面處於其他建築 (exitfromhouse 可見)
        mock_chest_detect.return_value = BuildingCheckResult(False, False)
        self.matcher.match.side_effect = lambda _s, t, **_kw: (
            ((50, 500), 0.92) if t == "town_building/exitfromhouse_and_to_town.png" else (None, 0.0)
        )

        # 幀 1: 防抖
        self.handler.handle(self.screen, self.rect)
        # 幀 2: Relinquish!
        self.handler.last_action_time = 0.0
        self.handler.handle(self.screen, self.rect)

        # 驗證 Relinquish 結果與 Ownership Token
        self.assertEqual(self.machine.current_state, self.machine.STATE_NAVIGATING)
        self.assertEqual(self.machine.current_town_subflow, "chest")
        self.assertTrue(self.machine.town_normalization_pending)

        # 幀 3: 在 STATE_NAVIGATING 下，雖然 need_diamond_collection = True，
        # 但 TownSubflowPreconditionController 憑藉 town_normalization_pending 取得實體優先權！
        # 絕不被 diamond collection 擋掉 (不得 skip)！
        prec_handled = self.machine.handle_town_subflow_precondition(self.screen, self.rect)
        self.assertTrue(prec_handled)
        self.mouse.click.assert_called_with(50, 500)
        self.assertEqual(
            self.machine.navigation_progress.in_flight.action_id,
            ActionId.EXIT_BUILDING_TO_TOWN,
        )

        # 幀 4: 抵達城鎮 Ready，完成歸一化並重新派發 Chest
        self.matcher.match.side_effect = lambda _s, t, **_kw: (
            ((200, 550), 0.95)
            if t in ("common/door.png", "town_building/arena_of_glory/arena_of_glory.png")
            else (None, 0.0)
        )
        mock_prec_detect.return_value = BuildingCheckResult(
            True, True, building_pos=(300, 400), confidence_building=0.9
        )
        redispatch_handled = self.machine.handle_town_subflow_precondition(self.screen, self.rect)
        self.assertTrue(redispatch_handled)

        # 斷言：順利重回 STATE_CHEST，且 ownership token 已清除！
        self.assertEqual(self.machine.current_state, self.machine.STATE_CHEST)
        self.assertEqual(self.machine.current_town_subflow, "chest")
        self.assertFalse(self.machine.town_normalization_pending)
        self.machine.daily_manager.defer_subflow.assert_not_called()


if __name__ == "__main__":
    unittest.main()
