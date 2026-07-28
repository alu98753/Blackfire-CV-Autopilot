import unittest
from unittest.mock import MagicMock, patch
import numpy as np
from states.login_flow import _wait_for_town, handle_global_login


class TestLoginFlowPopupDismissal(unittest.TestCase):
    def setUp(self):
        self.mock_machine = MagicMock()
        self.mock_capturer = MagicMock()
        self.mock_mouse = MagicMock()
        self.mock_matcher = MagicMock()

        self.mock_machine.capturer = self.mock_capturer
        self.mock_machine.mouse = self.mock_mouse
        self.mock_machine.matcher = self.mock_matcher

        self.fake_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}

    @patch("os.path.exists", return_value=True)
    def test_wait_for_town_dismisses_welcome_confirm_popup(self, mock_exists):
        """
        測試登入進城時，若畫面出現 common/confirm.png 或 common/ok.png 歡迎彈窗，
        _wait_for_town 能自動點擊關閉彈窗，並於關閉後成功確認 door.png 進城。
        """
        self.mock_capturer.get_window_rect.return_value = self.rect
        self.mock_capturer.capture.return_value = self.fake_img

        match_responses = [
            # 1. 第一輪：比對 confirm.png 成功 (765, 452)
            ((765, 452), 0.95),
            # 2. 第二輪：無彈窗，比對 door.png 成功 (68, 720)
            (None, 0.0), (None, 0.0), (None, 0.0), ((68, 720), 0.95)
        ]
        self.mock_matcher.match.side_effect = match_responses

        with patch("time.sleep", return_value=None):
            _wait_for_town(self.mock_machine, self.rect)

        # 驗證滑鼠是否有觸發點擊彈窗按鈕
        self.mock_mouse.click.assert_called_with(765, 452)


if __name__ == "__main__":
    unittest.main()
