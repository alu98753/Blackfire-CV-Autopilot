import time
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

from states.state_machine import GameStateMachine


class TestBehaviorLobbyStateMachine(unittest.TestCase):
    def setUp(self):
        self.capturer = MagicMock()
        self.matcher = MagicMock()
        self.mouse = MagicMock()
        self.state_machine = GameStateMachine(
            capturer=self.capturer,
            matcher=self.matcher,
            mouse=self.mouse,
            preload_ocr=False,
        )
        self.state_machine.config = {
            "type": "stage",
            "lobby_start_btn": "stages/start.png",
            "enable_stage_farming": True,
        }
        self.state_machine.current_state = GameStateMachine.STATE_LOBBY
        self.state_machine.notify_ui_progress = MagicMock()
        self.handler = self.state_machine.handlers[GameStateMachine.STATE_LOBBY]
        self.rect = {"left": 100, "top": 100, "width": 800, "height": 600}
        self.dummy_img = np.zeros((600, 800, 3), dtype=np.uint8)

    def _match_start_button_only(self):
        self.matcher.match.side_effect = lambda image, template, **kwargs: (
            ((200, 300), 0.95) if template == "stages/start.png" else (None, 0.0)
        )

    def test_first_click_stays_in_lobby_without_resetting_watchdog(self):
        self._match_start_button_only()

        self.handler.handle(self.dummy_img, self.rect)

        self.mouse.click.assert_called_once_with(300, 400)
        self.assertIsNotNone(self.handler.start_first_click_time)
        self.assertEqual(self.handler.start_first_click_time, self.handler.last_start_click_time)
        self.assertEqual(self.state_machine.current_state, GameStateMachine.STATE_LOBBY)
        self.assertEqual(self.state_machine.run_count, 0)
        self.state_machine.notify_ui_progress.assert_not_called()

    def test_retry_uses_last_click_time_without_resetting_watchdog(self):
        self._match_start_button_only()
        self.handler.start_first_click_time = time.time() - 1.5
        self.handler.last_start_click_time = time.time() - 1.5

        self.handler.handle(self.dummy_img, self.rect)

        self.mouse.click.assert_called_once_with(300, 400)
        self.assertEqual(self.state_machine.current_state, GameStateMachine.STATE_LOBBY)
        self.state_machine.notify_ui_progress.assert_not_called()

    def test_disappearance_transitions_to_loading_and_reports_real_progress(self):
        self.matcher.match.return_value = (None, 0.0)
        self.handler.start_first_click_time = time.time() - 0.2
        self.handler.last_start_click_time = time.time() - 0.2

        self.handler.handle(self.dummy_img, self.rect)

        self.assertIsNone(self.handler.start_first_click_time)
        self.assertIsNone(self.handler.last_start_click_time)
        self.assertEqual(self.state_machine.run_count, 1)
        self.assertEqual(self.state_machine.current_state, GameStateMachine.STATE_LOADING)
        self.state_machine.notify_ui_progress.assert_called_once()

    def test_due_bread_collection_does_not_preempt_committed_start(self):
        self.matcher.match.return_value = (None, 0.0)
        self.handler.start_first_click_time = time.time() - 0.2
        self.handler.last_start_click_time = time.time() - 0.2
        self.state_machine.enable_bread = True
        self.state_machine.need_bread_collection = True

        self.handler.handle(self.dummy_img, self.rect)

        self.assertEqual(self.state_machine.current_state, GameStateMachine.STATE_LOADING)
        self.assertTrue(self.state_machine.need_bread_collection)
        self.state_machine.notify_ui_progress.assert_called_once()

    def test_due_bread_collection_can_preempt_before_start_is_committed(self):
        self._match_start_button_only()
        self.state_machine.enable_bread = True
        self.state_machine.need_bread_collection = True

        self.handler.handle(self.dummy_img, self.rect)

        self.assertEqual(self.state_machine.current_state, GameStateMachine.STATE_NAVIGATING)
        self.mouse.click.assert_not_called()

    def test_total_timeout_resets_tracking_without_another_click(self):
        self._match_start_button_only()
        self.handler.start_first_click_time = time.time() - 5.1
        self.handler.last_start_click_time = time.time() - 1.1

        self.handler.handle(self.dummy_img, self.rect)

        self.mouse.click.assert_not_called()
        self.assertIsNone(self.handler.start_first_click_time)
        self.assertIsNone(self.handler.last_start_click_time)
        self.state_machine.notify_ui_progress.assert_not_called()

    def test_direct_battle_feature_transitions_to_battle(self):
        self.matcher.match.side_effect = lambda image, template, **kwargs: (
            ((50, 50), 0.9) if template == "common/auto.png" else (None, 0.0)
        )
        self.handler.start_first_click_time = time.time()
        self.handler.last_start_click_time = time.time()

        self.handler.handle(self.dummy_img, self.rect)

        self.assertIsNone(self.handler.start_first_click_time)
        self.assertIsNone(self.handler.last_start_click_time)
        self.assertEqual(self.state_machine.current_state, GameStateMachine.STATE_BATTLE)

    @patch("os.path.exists", return_value=True)
    def test_click_and_wait_until_gone_returns_true_on_vanish(self, mock_exists):
        self.capturer.capture.return_value = self.dummy_img
        self.matcher.match.side_effect = [((10, 10), 0.9), (None, 0.0)]

        result = self.handler.click_and_wait_until_gone(
            "dummy.png", 100, 100, self.rect,
            timeout=1.0, check_interval=0.01, post_delay=0.01,
        )

        self.assertTrue(result)

    @patch("os.path.exists", return_value=True)
    def test_click_and_wait_until_gone_returns_false_on_timeout(self, mock_exists):
        self.capturer.capture.return_value = self.dummy_img
        self.matcher.match.return_value = ((10, 10), 0.9)

        result = self.handler.click_and_wait_until_gone(
            "dummy.png", 100, 100, self.rect,
            timeout=0.05, check_interval=0.01, post_delay=0.01,
        )

        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
