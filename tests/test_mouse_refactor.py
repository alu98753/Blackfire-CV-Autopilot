import unittest
from unittest.mock import MagicMock, patch

from actions.mouse import MouseController, SAFE_AREA_CLIENT_POS
from vision.matcher import TemplateMatcher, DEFAULT_MATCH_SCALES


class TestMouseRefactorAndScales(unittest.TestCase):
    def test_default_match_scales_constant(self):
        """驗證 Issue #10：DEFAULT_MATCH_SCALES 具名常數與預設值。"""
        self.assertEqual(DEFAULT_MATCH_SCALES, (1.0, 0.863, 0.75))

    @patch("vision.matcher.cv2.matchTemplate")
    def test_match_all_uses_default_scales_when_none_provided(self, mock_match):
        """驗證 Issue #10：match_all 未傳入 scales 時使用 DEFAULT_MATCH_SCALES。"""
        import numpy as np
        matcher = TemplateMatcher(auto_scale=False)
        dummy_img = MagicMock()
        dummy_img.shape = (1080, 1920, 3)

        dummy_temp = MagicMock()
        dummy_temp.shape = (50, 50, 3)

        with patch.object(matcher, "_load_template", return_value=dummy_temp):
            mock_match.return_value = np.zeros((100, 100), dtype=np.float32)
            results = matcher.match_all(dummy_img, "test_template.png")

        self.assertEqual(results, [])

        # 驗證 _load_template 至少以 DEFAULT_MATCH_SCALES 的第一個 scale 呼叫
        self.assertIn(1.0, DEFAULT_MATCH_SCALES)

    def test_finalize_action_updates_state_and_time(self):
        """驗證 Issue #14：_finalize_action 能正確更新時間戳與重置狀態機 stuck 計數。"""
        mouse = MouseController()
        mock_sm = MagicMock()
        mock_sm.consecutive_stuck_count = 5
        mouse.state_machine = mock_sm

        with patch("actions.mouse.time.time", return_value=12345.67):
            with patch.object(mouse, "move_to_safe_area") as mock_move_safe:
                res = mouse._finalize_action(target_pos=(100, 200), move_safe=True)

        self.assertTrue(res)
        self.assertEqual(mouse.last_target_pos, (100, 200))
        self.assertEqual(mouse.last_action_time, 12345.67)
        self.assertEqual(mock_sm.consecutive_stuck_count, 0)
        mock_move_safe.assert_called_once()

    @patch("actions.mouse.pyautogui.position", return_value=(50, 60))
    def test_finalize_action_fallback_position_and_no_safe_move(self, mock_pos):
        """驗證 Issue #14：未提供 target_pos 時調用 position()，且 move_safe=False 時不移至安全區。"""
        mouse = MouseController()
        with patch.object(mouse, "move_to_safe_area") as mock_move_safe:
            with patch("actions.mouse.time.sleep") as mock_sleep:
                res = mouse._finalize_action(target_pos=None, cooldown=0.3, move_safe=False)

        self.assertTrue(res)
        self.assertEqual(mouse.last_target_pos, (50, 60))
        mock_sleep.assert_called_once_with(0.3)
        mock_move_safe.assert_not_called()

    @patch("actions.mouse.win32gui.PostMessage")
    @patch("actions.mouse.win32api.MAKELONG", return_value=9999)
    def test_move_to_safe_area_backend_mode(self, mock_makelong, mock_post_msg):
        """驗證 Issue #15：後台模式下以純淨 Client (15, 15) 發送 WM_MOUSEMOVE。"""
        mouse = MouseController(backend_mode=True)
        with patch.object(mouse, "get_hwnd", return_value=12345):
            mouse.move_to_safe_area()

        mock_makelong.assert_called_once_with(SAFE_AREA_CLIENT_POS[0], SAFE_AREA_CLIENT_POS[1])
        mock_post_msg.assert_called_once()
        self.assertEqual(mock_post_msg.call_args[0][0], 12345)
        self.assertEqual(mock_post_msg.call_args[0][3], 9999)

    @patch("actions.mouse.pyautogui.moveTo")
    @patch("actions.mouse.win32gui.ClientToScreen", return_value=(115, 215))
    def test_move_to_safe_area_frontend_mode_with_hwnd(self, mock_client_to_screen, mock_move_to):
        """驗證 Issue #15：前台模式下透過 ClientToScreen 轉換 (15, 15) 到實體螢幕座標。"""
        mouse = MouseController(backend_mode=False)
        with patch.object(mouse, "get_hwnd", return_value=12345):
            mouse.move_to_safe_area()

        mock_client_to_screen.assert_called_once_with(12345, SAFE_AREA_CLIENT_POS)
        mock_move_to.assert_called_once_with(115, 215)

    @patch("actions.mouse.pyautogui.moveTo")
    def test_move_to_safe_area_frontend_fallback_last_rect(self, mock_move_to):
        """驗證 Issue #15：前台模式無 HWND 時 fallback 使用 state_machine.last_rect。"""
        mouse = MouseController(backend_mode=False)
        mock_sm = MagicMock()
        mock_sm.last_rect = {"left": 200, "top": 300, "width": 800, "height": 600}
        mouse.state_machine = mock_sm

        with patch.object(mouse, "get_hwnd", return_value=0):
            mouse.move_to_safe_area()

        mock_move_to.assert_called_once_with(200 + SAFE_AREA_CLIENT_POS[0], 300 + SAFE_AREA_CLIENT_POS[1])


if __name__ == "__main__":
    unittest.main()
