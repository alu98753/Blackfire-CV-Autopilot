import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from states.state_machine import GameStateMachine
from states.handlers.result import ResultHandler
from tests.support.fake_clock import FakeClock

class TestBehaviorResultTickDriven(unittest.TestCase):
    def setUp(self):
        self.mock_capturer = MagicMock()
        self.mock_matcher = MagicMock()
        self.mock_mouse = MagicMock()
        self.clock = FakeClock(now=1000.0)

        self.sm = GameStateMachine(
            capturer=self.mock_capturer,
            matcher=self.mock_matcher,
            mouse=self.mock_mouse,
            preload_ocr=False
        )
        self.sm.clock = self.clock
        self.sm.config = {"type": "dungeon", "current_dungeon_index": 1, "battle_max_defeat": 3}
        self.sm.current_dungeon_index = 1
        self.sm.is_in_dungeon = True
        self.sm.defeat_count = 2  # 累計達 (max_defeat - 1)，下一次觸發放棄

        self.handler = ResultHandler(self.sm)
        self.fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}

    @patch("os.path.exists", return_value=True)
    def test_scenario_1_init_delay_multi_tick_stability(self, _mock_exists):
        """
        情境 1: INIT_DELAY 多 tick 驗證
        連續多幀呼叫不重設 timestamp，1.5 秒前維持等待，滿 1.5 秒自動轉入 CONTINUE_LOOP。
        """
        self.mock_matcher.match.return_value = (None, 0.0)

        # Tick 1: 進入結算，初始化時間戳
        self.handler.handle(self.fake_img, self.rect)
        self.assertEqual(self.handler.subflow_step, "INIT_DELAY")
        initial_ts = self.handler.init_delay_start_time
        self.assertIsNotNone(initial_ts)

        # Tick 2 (前進 0.8s，未滿 1.5s): 維持 INIT_DELAY，且時間戳未被重設/覆蓋
        self.clock.advance(0.8)
        self.handler.handle(self.fake_img, self.rect)
        self.assertEqual(self.handler.subflow_step, "INIT_DELAY")
        self.assertEqual(self.handler.init_delay_start_time, initial_ts)

        # Tick 3 (再前進 0.8s，總計 1.6s >= 1.5s): 轉入 CONTINUE_LOOP，清除時間戳
        self.clock.advance(0.8)
        self.handler.handle(self.fake_img, self.rect)
        self.assertEqual(self.handler.subflow_step, "CONTINUE_LOOP")
        self.assertIsNone(self.handler.init_delay_start_time)

    @patch("os.path.exists", return_value=True)
    def test_scenario_2_giveup_click_prevents_duplicate_clicks_and_waits_confirm(self, _mock_exists):
        """
        情境 2: Giveup 點擊防重發與等待
        點擊 giveup 後、confirm 尚未出現前，不得重複點擊，不得切換狀態。
        """
        # 跳過 INIT_DELAY
        self.handler.subflow_step = "CONTINUE_LOOP"

        def mock_match(img, temp, **kw):
            if temp == "defeat.png":
                return ((100, 100), 0.90)
            if temp == "defeat_giveup.png":
                return ((500, 500), 0.90)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = mock_match

        # Tick 1: 發現戰敗超限，點擊 defeat_giveup.png，切換至 WAIT_GIVEUP_CONFIRM
        self.handler.handle(self.fake_img, self.rect)
        self.assertEqual(self.handler.subflow_step, "WAIT_GIVEUP_CONFIRM")
        self.assertEqual(self.mock_mouse.click.call_count, 1)
        self.assertIsNotNone(self.handler.giveup_confirm_start_time)

        # Tick 2 (前進 1.0s，confirm 尚未出現): 維持等待，絕不重複點擊，絕不切換狀態
        self.clock.advance(1.0)
        self.handler.handle(self.fake_img, self.rect)
        self.assertEqual(self.handler.subflow_step, "WAIT_GIVEUP_CONFIRM")
        self.assertEqual(self.mock_mouse.click.call_count, 1)  # 仍然是 1 次
        self.assertEqual(self.sm.current_state, "UNKNOWN")  # 狀態機未被提前切換

    @patch("os.path.exists", return_value=True)
    def test_scenario_3_confirm_click_transitions_to_wait_exit_without_early_completion(self, _mock_exists):
        """
        情境 3: Confirm 點擊與防早熟
        Confirm 出現時僅點擊一次，進入 WAIT_GIVEUP_EXIT，仍不得立即宣告 exit success。
        """
        self.handler.subflow_step = "WAIT_GIVEUP_CONFIRM"
        self.handler.giveup_confirm_start_time = self.clock.monotonic()

        def mock_match(img, temp, **kw):
            if temp == "common/confirm.png":
                return ((600, 600), 0.90)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = mock_match

        # Tick 1: 發現 confirm 按鈕，點擊確認，切換至 WAIT_GIVEUP_EXIT
        self.handler.handle(self.fake_img, self.rect)
        self.assertEqual(self.handler.subflow_step, "WAIT_GIVEUP_EXIT")
        self.assertEqual(self.mock_mouse.click.call_count, 1)
        self.assertIsNotNone(self.handler.giveup_exit_start_time)

        # 斷言：此時絕對尚未提交結算 side effects！
        self.assertEqual(self.sm.defeat_count, 2)
        self.assertTrue(self.sm.is_in_dungeon)
        self.assertEqual(self.sm.dungeon_cooldowns[1], 0.0)
        self.assertEqual(self.sm.current_state, "UNKNOWN")

    @patch("os.path.exists", return_value=True)
    def test_scenario_4_positive_exit_evidence_commits_side_effects(self, _mock_exists):
        """
        情境 4: 正向退出證據與 Side Effect Commit
        僅當退出正向場景證據（大廳/城鎮/領地等）成立時，方提交 cooldown、清空 defeat_count 並切換狀態。
        """
        self.handler.subflow_step = "WAIT_GIVEUP_EXIT"
        self.handler.giveup_exit_start_time = self.clock.monotonic()
        self.handler.giveup_is_dungeon = True

        def mock_match(img, temp, **kw):
            # 偵測到大門/準備大廳特徵
            if temp == "common/select_stage.png":
                return ((100, 100), 0.90)
            return (None, 0.0)

        self.mock_matcher.match.side_effect = mock_match

        # Tick 1: 偵測到大門正向場景特徵，正式提交完成 side effects
        self.handler.handle(self.fake_img, self.rect)

        # 斷言：正向特徵成立，合法提交 Side Effects
        self.assertEqual(self.sm.defeat_count, 0)
        self.assertFalse(self.sm.is_in_dungeon)
        self.assertGreater(self.sm.dungeon_cooldowns[1], 0.0)
        self.assertEqual(self.sm.current_state, self.sm.STATE_NAVIGATING)
        self.assertEqual(self.handler.subflow_step, "INIT_DELAY")

    @patch("os.path.exists", return_value=True)
    def test_scenario_5_timeout_triggers_recovery_without_committing_success_side_effects(self, _mock_exists):
        """
        情境 5: 超時安全防護
        Confirm 或 Exit 超時時，絕對不得以 success side effects（設定 cooldown、重置 defeat）收尾。
        """
        # 測試 5.1: WAIT_GIVEUP_CONFIRM 5 秒超時
        self.handler.subflow_step = "WAIT_GIVEUP_CONFIRM"
        self.handler.giveup_confirm_start_time = self.clock.monotonic()
        self.handler.giveup_is_dungeon = True
        self.mock_matcher.match.return_value = (None, 0.0)

        # 前進 5.1s 觸發超時
        self.clock.advance(5.1)
        self.handler.handle(self.fake_img, self.rect)

        # 斷言：超時觸發 UNKNOWN 重定位，🚫 絕不提交 cooldown，絕不重置 defeat_count
        self.assertEqual(self.sm.current_state, self.sm.STATE_UNKNOWN)
        self.assertEqual(self.sm.defeat_count, 2)
        self.assertTrue(self.sm.is_in_dungeon)
        self.assertEqual(self.sm.dungeon_cooldowns[1], 0.0)

        # 測試 5.2: WAIT_GIVEUP_EXIT 5 秒超時
        self.handler.subflow_step = "WAIT_GIVEUP_EXIT"
        self.handler.giveup_exit_start_time = self.clock.monotonic()
        self.clock.advance(5.1)
        self.handler.handle(self.fake_img, self.rect)

        # 斷言：Exit 超時同樣不提交成功 side effects
        self.assertEqual(self.sm.current_state, self.sm.STATE_UNKNOWN)
        self.assertEqual(self.sm.defeat_count, 2)
        self.assertEqual(self.sm.dungeon_cooldowns[1], 0.0)

if __name__ == "__main__":
    unittest.main()
