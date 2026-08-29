import unittest
from unittest.mock import MagicMock, patch
import numpy as np
import time

from states.state_machine import GameStateMachine
from states.handlers.lobby import LobbyHandler
from states.handlers.base import BaseStateHandler


class TestBehaviorLobbyStateMachine(unittest.TestCase):
    """
    驗證 LobbyHandler 非阻塞式 (Tick-driven) 開始按鈕點擊與消失確認機制，
    以及 BaseStateHandler / GameStateMachine 的 click_and_wait_until_gone API 規範。
    """

    def setUp(self):
        self.capturer = MagicMock()
        self.matcher = MagicMock()
        self.mouse = MagicMock()
        self.state_machine = GameStateMachine(
            capturer=self.capturer,
            matcher=self.matcher,
            mouse=self.mouse,
            preload_ocr=False
        )
        self.state_machine.config = {
            "type": "stage",
            "lobby_start_btn": "stages/start.png",
            "enable_stage_farming": True
        }
        self.state_machine.current_state = GameStateMachine.STATE_LOBBY
        self.handler = self.state_machine.handlers[GameStateMachine.STATE_LOBBY]
        self.rect = {"left": 100, "top": 100, "width": 800, "height": 600}
        self.dummy_img = np.zeros((600, 800, 3), dtype=np.uint8)

    def test_lobby_first_click_records_time_and_stays_in_lobby(self):
        """
        [Given] 大廳畫面出現 stages/start.png，且尚未點擊過
        [When] 執行 LobbyHandler.handle
        [Then] 應發射點擊，記錄 start_clicked_time，並維持在 STATE_LOBBY（不立即切換至 LOADING）
        """
        self.matcher.match.side_effect = lambda img, template, **kwargs: (
            ((200, 300), 0.95) if template == "stages/start.png" else (None, 0.0)
        )

        self.handler.handle(self.dummy_img, self.rect)

        self.mouse.click.assert_called_once_with(300, 400)
        self.assertIsNotNone(self.handler.start_clicked_time)
        self.assertEqual(self.state_machine.current_state, GameStateMachine.STATE_LOBBY)
        self.assertEqual(self.state_machine.run_count, 0)

    def test_lobby_retry_click_when_button_persists(self):
        """
        [Given] 已點擊過開始按鈕，但按鈕仍在畫面上且已超過補點間隔 (1.0 秒)
        [When] 再次執行 handle
        [Then] 應發起第二次自動補點擊，更新點擊時間戳，並仍維持在 STATE_LOBBY
        """
        self.matcher.match.side_effect = lambda img, template, **kwargs: (
            ((200, 300), 0.95) if template == "stages/start.png" else (None, 0.0)
        )
        self.handler.start_clicked_time = time.time() - 1.5  # 模擬 1.5 秒前已點過

        self.handler.handle(self.dummy_img, self.rect)

        self.mouse.click.assert_called_once_with(300, 400)
        self.assertEqual(self.state_machine.current_state, GameStateMachine.STATE_LOBBY)

    def test_lobby_transitions_to_loading_after_button_disappears(self):
        """
        [Given] 先前已點擊過開始按鈕，當前幀 stages/start.png 已消失 (pos is None)
        [When] 執行 handle
        [Then] 應判定 UI 已吃下指令，累計 run_count，重置內部狀態並轉移至 STATE_LOADING
        """
        self.matcher.match.return_value = (None, 0.0)
        self.handler.start_clicked_time = time.time() - 0.2

        self.handler.handle(self.dummy_img, self.rect)

        self.assertIsNone(self.handler.start_clicked_time)
        self.assertEqual(self.state_machine.run_count, 1)
        self.assertEqual(self.state_machine.current_state, GameStateMachine.STATE_LOADING)

    def test_lobby_direct_battle_feature_transition(self):
        """
        [Given] 畫面直接出現戰鬥特徵 (如 common/auto.png)
        [When] 執行 handle
        [Then] 應重置點擊狀態並直接轉移至 STATE_BATTLE
        """
        self.matcher.match.side_effect = lambda img, template, **kwargs: (
            ((50, 50), 0.9) if template == "common/auto.png" else (None, 0.0)
        )
        self.handler.start_clicked_time = time.time()

        self.handler.handle(self.dummy_img, self.rect)

        self.assertIsNone(self.handler.start_clicked_time)
        self.assertEqual(self.state_machine.current_state, GameStateMachine.STATE_BATTLE)

    @patch("os.path.exists", return_value=True)
    def test_click_and_wait_until_gone_returns_true_on_vanish(self, mock_exists):
        """
        [驗證 API] 當模板在輪詢中成功消失時，click_and_wait_until_gone 應回傳 True
        """
        self.capturer.capture.return_value = self.dummy_img
        # 第一次比對在 (10, 10)，第二次比對消失 (None)
        self.matcher.match.side_effect = [((10, 10), 0.9), (None, 0.0)]

        res = self.handler.click_and_wait_until_gone(
            "dummy.png", 100, 100, self.rect,
            timeout=1.0, check_interval=0.01, post_delay=0.01
        )
        self.assertTrue(res)

    @patch("os.path.exists", return_value=True)
    def test_click_and_wait_until_gone_returns_false_on_timeout(self, mock_exists):
        """
        [驗證 API] 當模板在超時前始終未消失時，click_and_wait_until_gone 應回傳 False
        """
        self.capturer.capture.return_value = self.dummy_img
        self.matcher.match.return_value = ((10, 10), 0.9)

        res = self.handler.click_and_wait_until_gone(
            "dummy.png", 100, 100, self.rect,
            timeout=0.05, check_interval=0.01, post_delay=0.01
        )
        self.assertFalse(res)


if __name__ == "__main__":
    unittest.main()
