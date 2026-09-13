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
        驗證 ChestHandler committed 後，若畫面為通用建築內部 (exitfromhouse 可見但無寶箱專屬特徵)：
        - 第 1 幀：mislocation_count = 1，回傳 True，不釋放，不 defer，不 pop。
        - 第 2 幀：mislocation_count = 2，主動呼叫 relinquish_subflow_to_navigation，
          轉移至 STATE_NAVIGATING。
        - 核心守護 Invariant 2：current_town_subflow 完好保留，未調用 defer 或 pop！
        """
        self.machine.current_state = self.machine.STATE_CHEST
        self.machine.current_town_subflow = "chest"
        self.machine.town_subflow_queue = ["hero_draw"]
        self.machine.daily_manager = MagicMock()

        # 模擬畫面：未找到寶箱專屬特徵，但找到 exitfromhouse_and_to_town (通用建築內部特徵)
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

        # 斷言：mislocation 計數歸零，點擊進入建築，推進至 VERIFY_ENTRY，未退讓
        self.assertEqual(self.handler.mislocation_count, 0)
        self.assertEqual(self.handler.step_phase, "VERIFY_ENTRY")
        self.assertEqual(self.machine.current_state, self.machine.STATE_CHEST)
        self.mouse.click.assert_called_once_with(300, 400)

        # 第 3 幀：成功進入寶箱內部 (free_treasure.png 可見)
        self.handler.last_action_time = 0.0
        self.matcher.match.side_effect = lambda _s, t, **_kw: (
            ((200, 200), 0.90) if t == "town_building/mysterious_treasure/free_treasure.png" else (None, 0.0)
        )
        with patch("os.path.exists", return_value=True):
            self.handler.handle(self.screen, self.rect)

        self.assertEqual(self.handler.step_phase, "CLICK_FREE_CHEST")
        self.assertEqual(self.machine.current_state, self.machine.STATE_CHEST)

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
        When: Physical screen is observed to be generic building interior (Blood Altar, exitfromhouse visible)
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

        # 1. 模擬畫面處於通用建築內部 (exitfromhouse 可見，無寶箱專屬特徵)
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
        # REACH_TOWN 看到 exitfromhouse (通用建築內部特徵) -> 點擊退場 (IN_PROGRESS)
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

        # 1. 模擬畫面處於通用建築內部 (exitfromhouse 可見)
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

    @patch("states.town_subflow_perception.detect_building_with_red_dot")
    @patch("states.handlers.chest.detect_building_with_red_dot")
    def test_chest_real_path_mislocation_after_entry_click_must_relinquish_without_defer(
        self, mock_chest_detect, mock_prec_detect
    ):
        """
        [真實 Failure A 迴歸驗證]:
        模擬 Chest 從 Town 正常點擊建築入口 -> step_phase 前進 ->
        下一幀實際落入通用建築內部 (如誤入 Blood Altar)。
        
        核心契約與守護 Invariant:
        1. 點擊入口 != 成功進入 Chest。
        2. 若下一幀落入通用建築內部 (exitfromhouse 可見但無 chest dialog)，
           Handler 必須在連續確認後主動 Relinquish 回 STATE_NAVIGATING，
           交由 shared REACH_TOWN 處理。
        3. 嚴格 Invariant 2：物理點偏/錯位絕不得 defer、pop 或 complete 業務 Intent！
        4. 經 shared REACH_TOWN 回城後，同一個 chest intent 重新派發繼續執行。
        """
        self.machine.current_state = self.machine.STATE_CHEST
        self.machine.current_town_subflow = "chest"
        self.machine.daily_manager = MagicMock()

        # Step 1: 在 Town 看到帶紅點的寶箱建築，點擊入口
        mock_chest_detect.return_value = BuildingCheckResult(
            True, True, building_pos=(200, 300), confidence_building=0.9
        )
        self.matcher.match.return_value = (None, 0.0)

        step1_res = self.handler.handle(self.screen, self.rect)
        self.assertTrue(step1_res)
        self.mouse.click.assert_called_with(200, 300)
        # 驗證 phase 精確鎖定在 VERIFY_ENTRY 閘門 (點擊入口 != 成功進入)
        self.assertEqual(self.handler.step_phase, "VERIFY_ENTRY")
        self.assertEqual(self.machine.current_town_subflow, "chest")

        # Step 2: 點擊後下一幀落入通用建築內部 (例如 Blood Altar):
        # exitfromhouse_and_to_town (通用建築內部特徵) 可見，但 chest dialog (free_treasure.png) 不可見
        mock_chest_detect.return_value = BuildingCheckResult(False, False)
        self.matcher.match.side_effect = lambda _s, t, **_kw: (
            ((50, 500), 0.92) if t == "town_building/exitfromhouse_and_to_town.png" else (None, 0.0)
        )

        # 模擬後續影格：Handler 在 foreign building 必須連續確認並 Relinquish，絕不能走入 defer/pop！
        for _ in range(3):
            self.handler.last_action_time = 0.0
            self.handler.handle(self.screen, self.rect)
            if self.machine.current_state == self.machine.STATE_NAVIGATING:
                break

        # 斷言 1: 必須主動 Relinquish 至 STATE_NAVIGATING，並獲取 ownership token
        self.assertEqual(self.machine.current_state, self.machine.STATE_NAVIGATING)
        self.assertTrue(self.machine.town_normalization_pending)

        # 斷言 2: 嚴格守護 Invariant 2：業務 Intent 絕不被懲罰性 defer 或 pop！
        self.assertEqual(self.machine.current_town_subflow, "chest")
        self.machine.daily_manager.defer_subflow.assert_not_called()
        self.machine.daily_manager.record_subflow_completed.assert_not_called()

        # Step 3: shared REACH_TOWN 退出錯誤建築並重新回到 Town
        prec_res = self.machine.handle_town_subflow_precondition(self.screen, self.rect)
        self.assertTrue(prec_res)
        self.mouse.click.assert_called_with(50, 500)

        # Step 4: 回到 Town Ready，重新派發回 STATE_CHEST
        self.matcher.match.side_effect = lambda _s, t, **_kw: (
            ((200, 550), 0.95)
            if t in ("common/door.png", "town_building/arena_of_glory/arena_of_glory.png")
            else (None, 0.0)
        )
        mock_prec_detect.return_value = BuildingCheckResult(
            True, True, building_pos=(200, 300), confidence_building=0.9
        )
        redispatch_res = self.machine.handle_town_subflow_precondition(self.screen, self.rect)
        self.assertTrue(redispatch_res)

        # 斷言 3: 重新派發回 STATE_CHEST，業務 Intent 完好無損，Token 清除
        self.assertEqual(self.machine.current_state, self.machine.STATE_CHEST)
        self.assertEqual(self.machine.current_town_subflow, "chest")
        self.assertFalse(self.machine.town_normalization_pending)
        self.machine.daily_manager.defer_subflow.assert_not_called()

    @patch("states.town_subflow_perception.detect_building_with_red_dot")
    def test_hero_draw_mislocation_in_foreign_building_must_relinquish_without_defer(
        self, mock_prec_detect
    ):
        """
        [HeroDraw 錯位迴歸驗證]:
        驗證 HeroDraw 處於 foreign building 時 (exitfromhouse 可見但無酒館專屬特徵)，
        不得誤認 generic exit 為已在酒館內部；
        必須在連續確認後主動 Relinquish 回 STATE_NAVIGATING，
        嚴格不得懲罰性 defer 業務 Intent！
        """
        self.machine.current_state = self.machine.STATE_HERO_DRAW
        self.machine.current_town_subflow = "hero_draw"
        self.machine.daily_manager = MagicMock()
        hero_handler = self.machine.handlers[self.machine.STATE_HERO_DRAW]

        # 模擬畫面：身處 foreign building (exitfromhouse 可見，但無 recruitment / RECRUITED / Tavern)
        self.matcher.match.side_effect = lambda _s, t, **_kw: (
            ((50, 500), 0.92) if t == "town_building/exitfromhouse_and_to_town.png" else (None, 0.0)
        )

        for _ in range(3):
            hero_handler.last_action_time = 0.0
            hero_handler.handle(self.screen, self.rect)
            if self.machine.current_state == self.machine.STATE_NAVIGATING:
                break

        # 斷言 1: 必須主動 Relinquish 至 STATE_NAVIGATING，並獲取 ownership token
        self.assertEqual(self.machine.current_state, self.machine.STATE_NAVIGATING)
        self.assertTrue(self.machine.town_normalization_pending)

        # 斷言 2: 嚴格守護 Invariant 2：業務 Intent 絕不被懲罰性 defer 或 pop！
        self.assertEqual(self.machine.current_town_subflow, "hero_draw")
        self.machine.daily_manager.defer_subflow.assert_not_called()
        self.machine.daily_manager.record_subflow_completed.assert_not_called()

        # Step 2: shared REACH_TOWN 退出錯誤建築並重新回到 Town
        prec_res = self.machine.handle_town_subflow_precondition(self.screen, self.rect)
        self.assertTrue(prec_res)
        self.mouse.click.assert_called_with(50, 500)

        # Step 3: 回到 Town Ready，重新派發回 STATE_HERO_DRAW
        self.matcher.match.side_effect = lambda _s, t, **_kw: (
            ((200, 550), 0.95)
            if t in ("common/door.png", "town_building/arena_of_glory/arena_of_glory.png")
            else (None, 0.0)
        )
        mock_prec_detect.return_value = BuildingCheckResult(
            True, True, building_pos=(300, 400), confidence_building=0.9
        )
        redispatch_res = self.machine.handle_town_subflow_precondition(self.screen, self.rect)
        self.assertTrue(redispatch_res)

        # 斷言 3: 重新派發回 STATE_HERO_DRAW，業務 Intent 完好無損，Token 清除
        self.assertEqual(self.machine.current_state, self.machine.STATE_HERO_DRAW)
        self.assertEqual(self.machine.current_town_subflow, "hero_draw")
        self.assertFalse(self.machine.town_normalization_pending)
        self.machine.daily_manager.defer_subflow.assert_not_called()

    @patch("states.town_subflow_perception.detect_building_with_red_dot")
    def test_blood_altar_mislocation_in_foreign_building_must_relinquish_without_defer(
        self, mock_prec_detect
    ):
        """
        [BloodAltar 錯位迴歸驗證]:
        驗證 BloodAltar 處於通用建築內部時 (exitfromhouse 可見但無祭壇專屬特徵)，
        不得誤認 generic exit 為已在祭壇內部；
        必須在連續確認後主動 Relinquish 回 STATE_NAVIGATING，
        嚴格不得推進 business phase 並懲罰性 defer/pop 業務 Intent！
        """
        self.machine.current_state = self.machine.STATE_BLOOD_ALTAR
        self.machine.current_town_subflow = "blood_altar"
        self.machine.need_blood_altar = True
        self.machine.daily_manager = MagicMock()
        altar_handler = self.machine.handlers[self.machine.STATE_BLOOD_ALTAR]

        # 模擬畫面：身處通用建築內部 (exitfromhouse 可見，但無 Blood_Altar / Sacrifice / receive_entry)
        self.matcher.match.side_effect = lambda _s, t, **_kw: (
            ((50, 500), 0.92) if t == "town_building/exitfromhouse_and_to_town.png" else (None, 0.0)
        )

        for _ in range(3):
            altar_handler.last_action_time = 0.0
            altar_handler.handle(self.screen, self.rect)
            if self.machine.current_state == self.machine.STATE_NAVIGATING:
                break

        # 斷言 1: 必須主動 Relinquish 至 STATE_NAVIGATING，並獲取 ownership token
        self.assertEqual(self.machine.current_state, self.machine.STATE_NAVIGATING)
        self.assertTrue(self.machine.town_normalization_pending)

        # 斷言 2: 嚴格守護 Invariant 2：業務 Intent 絕不被懲罰性 defer 或 pop！
        self.assertEqual(self.machine.current_town_subflow, "blood_altar")
        self.machine.daily_manager.defer_subflow.assert_not_called()
        self.machine.daily_manager.record_subflow_completed.assert_not_called()

        # Step 2: shared REACH_TOWN 退出錯誤建築並重新回到 Town
        prec_res = self.machine.handle_town_subflow_precondition(self.screen, self.rect)
        self.assertTrue(prec_res)
        self.mouse.click.assert_called_with(50, 500)

        # Step 3: 回到 Town Ready，重新派發回 STATE_BLOOD_ALTAR
        self.matcher.match.side_effect = lambda _s, t, **_kw: (
            ((200, 550), 0.95)
            if t in ("common/door.png", "town_building/arena_of_glory/arena_of_glory.png")
            else (None, 0.0)
        )
        mock_prec_detect.return_value = BuildingCheckResult(
            True, True, building_pos=(350, 450), confidence_building=0.9
        )
        redispatch_res = self.machine.handle_town_subflow_precondition(self.screen, self.rect)
        self.assertTrue(redispatch_res)

        # 斷言 3: 重新派發回 STATE_BLOOD_ALTAR，業務 Intent 完好無損，Token 清除
        self.assertEqual(self.machine.current_state, self.machine.STATE_BLOOD_ALTAR)
        self.assertEqual(self.machine.current_town_subflow, "blood_altar")
        self.assertFalse(self.machine.town_normalization_pending)
        self.machine.daily_manager.defer_subflow.assert_not_called()

    @patch("states.handlers.hero_draw.detect_building_with_red_dot")
    @patch("states.town_subflow_perception.detect_building_with_red_dot")
    @patch("os.path.exists", return_value=True)
    def test_hero_draw_real_path_mislocation_after_entry_click(
        self, mock_exists, mock_prec_detect, mock_hero_detect
    ):
        """
        [HeroDraw 完整真實點擊錯位閉環驗證 (Post-Entry Real Path)]:
        驗證 HeroDraw 從城鎮發起點擊進入 Tavern：
        1. INIT 階段找到 Tavern 且帶紅點，點擊後推進至 ENTERED_TAVERN。
        2. 下一幀實際因點偏落在通用建築內部 (exitfromhouse 可見，但無 free_recruitment / RECRUITED)。
        3. 第一幀判定通用建築內部特徵可見且 own evidence absent -> 進入 suspected mislocation (WAIT)。
        4. 第二幀連續確認成立 -> 輸出 RELINQUISH，交還所有權給 REACH_TOWN。
        5. 嚴格遵守 Invariant 2：不 defer、不 pop、不 mark completed！
        6. shared REACH_TOWN 點擊退出，回到 Town Ready 後乾淨重新派發回 STATE_HERO_DRAW。
        """
        self.machine.current_state = self.machine.STATE_HERO_DRAW
        self.machine.current_town_subflow = "hero_draw"
        self.machine.daily_manager = MagicMock()
        hero_handler = self.machine.handlers[self.machine.STATE_HERO_DRAW]

        # Step 1: 在城鎮發現帶紅點的 Tavern
        mock_hero_detect.return_value = BuildingCheckResult(
            True, True, building_pos=(250, 350), confidence_building=0.92
        )
        self.matcher.match.return_value = (None, 0.0)

        step1_res = hero_handler.handle(self.screen, self.rect)
        self.assertTrue(step1_res)
        self.mouse.click.assert_called_with(250, 350)
        self.assertEqual(hero_handler.step_phase, "ENTERED_TAVERN")
        self.assertEqual(self.machine.current_town_subflow, "hero_draw")

        # Step 2: 點擊後下一幀落入通用建築內部 (例如 Blood Altar)
        # exitfromhouse_and_to_town (通用建築內部特徵) 可見，但 free_recruitment / RECRUITED 均不存在
        mock_hero_detect.return_value = BuildingCheckResult(False, False)
        self.matcher.match.side_effect = lambda _s, t, **_kw: (
            ((50, 500), 0.92) if t == "town_building/exitfromhouse_and_to_town.png" else (None, 0.0)
        )

        for _ in range(3):
            hero_handler.last_action_time = 0.0
            hero_handler.handle(self.screen, self.rect)
            if self.machine.current_state == self.machine.STATE_NAVIGATING:
                break

        # 斷言 1: 必須主動 Relinquish 至 STATE_NAVIGATING，並獲取 ownership token
        self.assertEqual(self.machine.current_state, self.machine.STATE_NAVIGATING)
        self.assertTrue(self.machine.town_normalization_pending)

        # 斷言 2: 嚴格守護 Invariant 2：業務 Intent 絕不被懲罰性 defer 或 pop！
        self.assertEqual(self.machine.current_town_subflow, "hero_draw")
        self.machine.daily_manager.defer_subflow.assert_not_called()
        self.machine.daily_manager.record_subflow_completed.assert_not_called()

        # Step 3: shared REACH_TOWN 退出錯誤建築並重新回到 Town
        prec_res = self.machine.handle_town_subflow_precondition(self.screen, self.rect)
        self.assertTrue(prec_res)
        self.mouse.click.assert_called_with(50, 500)

        # Step 4: 回到 Town Ready，重新派發回 STATE_HERO_DRAW
        self.matcher.match.side_effect = lambda _s, t, **_kw: (
            ((200, 550), 0.95)
            if t in ("common/door.png", "town_building/arena_of_glory/arena_of_glory.png")
            else (None, 0.0)
        )
        mock_prec_detect.return_value = BuildingCheckResult(
            True, True, building_pos=(250, 350), confidence_building=0.9
        )
        redispatch_res = self.machine.handle_town_subflow_precondition(self.screen, self.rect)
        self.assertTrue(redispatch_res)

        # 斷言 3: 重新派發回 STATE_HERO_DRAW，業務 Intent 完好無損，Token 清除
        self.assertEqual(self.machine.current_state, self.machine.STATE_HERO_DRAW)
        self.assertEqual(self.machine.current_town_subflow, "hero_draw")
        self.assertFalse(self.machine.town_normalization_pending)
        self.machine.daily_manager.defer_subflow.assert_not_called()

    @patch("states.town_subflow_perception.detect_building_with_red_dot")
    def test_bag_tidy_mislocation_in_foreign_building_must_relinquish_without_pop(
        self, mock_prec_detect
    ):
        """
        [BagTidy 錯位迴歸驗證 (C1)]:
        驗證 BagTidy 處於通用建築內部時 (exitfromhouse_and_to_town 可見，但無 bag/tidy/door)，
        不得在通用建築內部盲目等待 20 秒超時後 pop_and_next_town_subflow() 消耗業務意圖；
        必須由 MislocationGuard 連續確認 (2 frames) 後主動讓渡實體所有權給 REACH_TOWN！
        嚴格遵守 Invariant 2：業務 Intent 絕不被 pop 或 completed！
        """
        self.machine.current_state = self.machine.STATE_BAG_TIDY
        self.machine.current_town_subflow = "bag_tidy"
        self.machine.need_bag_tidy = True
        self.machine.daily_manager = MagicMock()
        self.machine.pop_and_next_town_subflow = MagicMock(wraps=self.machine.pop_and_next_town_subflow)
        tidy_handler = self.machine.handlers[self.machine.STATE_BAG_TIDY]

        # 模擬畫面：身處通用建築內部 (exitfromhouse 可見，但無 common/door, bag_text, bag, tidy)
        self.matcher.match.side_effect = lambda _s, t, **_kw: (
            ((50, 500), 0.92) if t == "town_building/exitfromhouse_and_to_town.png" else (None, 0.0)
        )

        for _ in range(3):
            tidy_handler.last_action_time = 0.0
            tidy_handler.handle(self.screen, self.rect)
            if self.machine.current_state == self.machine.STATE_NAVIGATING:
                break

        # 斷言 1: 必須主動 Relinquish 至 STATE_NAVIGATING，並獲取 ownership token
        self.assertEqual(self.machine.current_state, self.machine.STATE_NAVIGATING)
        self.assertTrue(self.machine.town_normalization_pending)

        # 斷言 2: 嚴格守護 Invariant 2：業務 Intent 絕不被 pop 或 mark completed！
        self.assertEqual(self.machine.current_town_subflow, "bag_tidy")
        self.machine.pop_and_next_town_subflow.assert_not_called()

        # Step 2: shared REACH_TOWN 退出錯誤建築並重新回到 Town
        prec_res = self.machine.handle_town_subflow_precondition(self.screen, self.rect)
        self.assertTrue(prec_res)
        self.mouse.click.assert_called_with(50, 500)

        # Step 3: 回到 Town Ready，重新派發回 STATE_BAG_TIDY
        self.matcher.match.side_effect = lambda _s, t, **_kw: (
            ((200, 550), 0.95)
            if t in ("common/door.png", "town_building/arena_of_glory/arena_of_glory.png")
            else (None, 0.0)
        )
        mock_prec_detect.return_value = BuildingCheckResult(
            True, True, building_pos=(200, 200), confidence_building=0.9
        )
        redispatch_res = self.machine.handle_town_subflow_precondition(self.screen, self.rect)
        self.assertTrue(redispatch_res)

        # 斷言 3: 重新派發回 STATE_BAG_TIDY，業務 Intent 完好無損，Token 清除
        self.assertEqual(self.machine.current_state, self.machine.STATE_BAG_TIDY)
        self.assertEqual(self.machine.current_town_subflow, "bag_tidy")
        self.assertFalse(self.machine.town_normalization_pending)

    @patch("states.town_subflow_perception.detect_building_with_red_dot")
    def test_bulletin_board_mislocation_in_foreign_building_must_relinquish_without_defer(
        self, mock_prec_detect
    ):
        """
        [BulletinBoard 錯位迴歸驗證 (C2)]:
        驗證 BulletinBoard 處於通用建築內部時 (exitfromhouse 可見，但無 bulletin_board / task / reset / door)，
        不得在通用建築內部盲目重試開窗超時後 defer_subflow() 懲罰業務 Intent；
        必須由 MislocationGuard 連續確認 (2 frames) 後主動讓渡實體所有權給 REACH_TOWN！
        嚴格遵守 Invariant 2：業務 Intent 絕不被 defer、pop 或 mark completed！
        """
        self.machine.current_state = self.machine.STATE_BULLETIN_BOARD
        self.machine.current_town_subflow = "bulletin_board"
        self.machine.need_bulletin_board = True
        self.machine.daily_manager = MagicMock()
        bb_handler = self.machine.handlers[self.machine.STATE_BULLETIN_BOARD]

        # 模擬畫面：身處通用建築內部 (exitfromhouse 可見，但無 common/door, bulletin_board, task, reset)
        self.matcher.match.side_effect = lambda _s, t, **_kw: (
            ((50, 500), 0.92) if t == "town_building/exitfromhouse_and_to_town.png" else (None, 0.0)
        )

        for _ in range(3):
            bb_handler.last_action_time = 0.0
            bb_handler.handle(self.screen, self.rect)
            if self.machine.current_state == self.machine.STATE_NAVIGATING:
                break

        # 斷言 1: 必須主動 Relinquish 至 STATE_NAVIGATING，並獲取 ownership token
        self.assertEqual(self.machine.current_state, self.machine.STATE_NAVIGATING)
        self.assertTrue(self.machine.town_normalization_pending)

        # 斷言 2: 嚴格守護 Invariant 2：業務 Intent 絕不被 defer 或 pop！
        self.assertEqual(self.machine.current_town_subflow, "bulletin_board")
        self.machine.daily_manager.defer_subflow.assert_not_called()
        self.machine.daily_manager.record_subflow_completed.assert_not_called()

        # Step 2: shared REACH_TOWN 退出錯誤建築並重新回到 Town
        prec_res = self.machine.handle_town_subflow_precondition(self.screen, self.rect)
        self.assertTrue(prec_res)
        self.mouse.click.assert_called_with(50, 500)

        # Step 3: 回到 Town Ready，重新派發回 STATE_BULLETIN_BOARD
        self.matcher.match.side_effect = lambda _s, t, **_kw: (
            ((200, 550), 0.95)
            if t in ("common/door.png", "town_building/arena_of_glory/arena_of_glory.png")
            else (None, 0.0)
        )
        mock_prec_detect.return_value = BuildingCheckResult(
            True, True, building_pos=(200, 200), confidence_building=0.9
        )
        redispatch_res = self.machine.handle_town_subflow_precondition(self.screen, self.rect)
        self.assertTrue(redispatch_res)

        # 斷言 3: 重新派發回 STATE_BULLETIN_BOARD，業務 Intent 完好無損，Token 清除
        self.assertEqual(self.machine.current_state, self.machine.STATE_BULLETIN_BOARD)
        self.assertEqual(self.machine.current_town_subflow, "bulletin_board")
        self.assertFalse(self.machine.town_normalization_pending)
        self.machine.daily_manager.defer_subflow.assert_not_called()

    @patch("states.town_subflow_perception.detect_building_with_red_dot")
    def test_jewelry_workshop_mislocation_in_foreign_building_must_relinquish_without_error(
        self, mock_prec_detect
    ):
        """
        [JewelryWorkshop 錯位迴歸驗證 (C3)]:
        驗證 JewelryWorkshop 處於通用建築內部時 (exitfromhouse 可見，但無 sell_out / sell_btn / door / workshop)，
        不得在通用建築內部盲目空轉或觸發 safe recovery / error；
        必須由 MislocationGuard 連續確認 (2 frames) 後主動讓渡實體所有權給 REACH_TOWN！
        嚴格遵守 Invariant 2：業務 Intent 絕不被 defer、pop 或 mark completed！
        """
        self.machine.current_state = self.machine.STATE_JEWELRY_WORKSHOP
        self.machine.current_town_subflow = "jewelry_workshop"
        self.machine.need_jewelry_workshop = True
        self.machine.daily_manager = MagicMock()
        jw_handler = self.machine.handlers[self.machine.STATE_JEWELRY_WORKSHOP]

        # 模擬畫面：身處通用建築內部 (exitfromhouse 可見，但無 sell_out, sell_btn, door, workshop)
        self.matcher.match.side_effect = lambda _s, t, **_kw: (
            ((50, 500), 0.92) if t == "town_building/exitfromhouse_and_to_town.png" else (None, 0.0)
        )

        for _ in range(3):
            jw_handler.last_action_time = 0.0
            jw_handler.handle(self.screen, self.rect)
            if self.machine.current_state == self.machine.STATE_NAVIGATING:
                break

        # 斷言 1: 必須主動 Relinquish 至 STATE_NAVIGATING，並獲取 ownership token
        self.assertEqual(self.machine.current_state, self.machine.STATE_NAVIGATING)
        self.assertTrue(self.machine.town_normalization_pending)

        # 斷言 2: 嚴格守護 Invariant 2：業務 Intent 絕不被 defer、pop 或 mark completed！
        self.assertEqual(self.machine.current_town_subflow, "jewelry_workshop")
        self.machine.daily_manager.defer_subflow.assert_not_called()
        self.machine.daily_manager.record_subflow_completed.assert_not_called()

        # Step 2: shared REACH_TOWN 退出錯誤建築並重新回到 Town
        prec_res = self.machine.handle_town_subflow_precondition(self.screen, self.rect)
        self.assertTrue(prec_res)
        self.mouse.click.assert_called_with(50, 500)

        # Step 3: 回到 Town Ready，重新派發回 STATE_JEWELRY_WORKSHOP
        self.matcher.match.side_effect = lambda _s, t, **_kw: (
            ((200, 550), 0.95)
            if t in ("common/door.png", "town_building/arena_of_glory/arena_of_glory.png")
            else (None, 0.0)
        )
        mock_prec_detect.return_value = BuildingCheckResult(
            True, True, building_pos=(200, 200), confidence_building=0.9
        )
        redispatch_res = self.machine.handle_town_subflow_precondition(self.screen, self.rect)
        self.assertTrue(redispatch_res)

        # 斷言 3: 重新派發回 STATE_JEWELRY_WORKSHOP，業務 Intent 完好無損，Token 清除
        self.assertEqual(self.machine.current_state, self.machine.STATE_JEWELRY_WORKSHOP)
        self.assertEqual(self.machine.current_town_subflow, "jewelry_workshop")
        self.assertFalse(self.machine.town_normalization_pending)
        self.machine.daily_manager.defer_subflow.assert_not_called()


class TestMislocationGuardSemantic(unittest.TestCase):
    """
    MislocationGuard 語意契約單元測試：
    驗證 stateful bounded confirmation guard / debouncer 之狀態機決策轉換：
    1. own=True, generic=True -> RETAIN
    2. generic=True frame1 -> WAIT
    3. generic=True frame2 -> RELINQUISH
    4. generic frame -> own frame -> generic frame -> WAIT (own evidence 重置確認計數)
    5. generic frame -> neither -> generic frame -> WAIT (非連續重置確認計數)
    """

    def setUp(self):
        from states.handler_mislocation_guard import MislocationGuard, MislocationDecision
        self.guard = MislocationGuard(threshold=2)
        self.decision = MislocationDecision

    def test_own_evidence_always_retains_and_resets(self):
        # own=True, generic=True -> RETAIN
        self.assertEqual(self.guard.evaluate(True, True), self.decision.RETAIN)
        self.assertEqual(self.guard.consecutive_count, 0)

        # own=True, generic=False -> RETAIN
        self.assertEqual(self.guard.evaluate(True, False), self.decision.RETAIN)
        self.assertEqual(self.guard.consecutive_count, 0)

    def test_generic_consecutive_confirmation_reaches_relinquish(self):
        # generic=True frame1 -> WAIT
        self.assertEqual(self.guard.evaluate(False, True), self.decision.WAIT)
        self.assertEqual(self.guard.consecutive_count, 1)

        # generic=True frame2 -> RELINQUISH
        self.assertEqual(self.guard.evaluate(False, True), self.decision.RELINQUISH)
        self.assertEqual(self.guard.consecutive_count, 2)

    def test_own_evidence_resets_confirmation_budget(self):
        # generic frame 1 -> WAIT
        self.assertEqual(self.guard.evaluate(False, True), self.decision.WAIT)
        self.assertEqual(self.guard.consecutive_count, 1)

        # own frame -> RETAIN (重置)
        self.assertEqual(self.guard.evaluate(True, False), self.decision.RETAIN)
        self.assertEqual(self.guard.consecutive_count, 0)

        # generic frame -> WAIT (重新從 1 開始)
        self.assertEqual(self.guard.evaluate(False, True), self.decision.WAIT)
        self.assertEqual(self.guard.consecutive_count, 1)

    def test_neither_evidence_resets_consecutive_confirmation(self):
        # generic frame 1 -> WAIT
        self.assertEqual(self.guard.evaluate(False, True), self.decision.WAIT)
        self.assertEqual(self.guard.consecutive_count, 1)

        # neither frame -> WAIT (中斷連續確認)
        self.assertEqual(self.guard.evaluate(False, False), self.decision.WAIT)
        self.assertEqual(self.guard.consecutive_count, 0)

        # generic frame -> WAIT (重新計數)
        self.assertEqual(self.guard.evaluate(False, True), self.decision.WAIT)
        self.assertEqual(self.guard.consecutive_count, 1)


if __name__ == "__main__":
    unittest.main()


