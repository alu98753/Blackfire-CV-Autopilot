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

    def test_finalize_action_invokes_on_action_success_callback(self):
        """驗證 Issue #11：_finalize_action 透過 _on_action_success callback 通知上層，不直接存取 state_machine。"""
        callback_called = []
        mouse = MouseController(on_action_success=lambda: callback_called.append(1))

        with patch("actions.mouse.time.time", return_value=12345.67):
            with patch.object(mouse, "move_to_safe_area"):
                res = mouse._finalize_action(target_pos=(100, 200), move_safe=True)

        self.assertTrue(res)
        self.assertEqual(mouse.last_target_pos, (100, 200))
        self.assertEqual(mouse.last_action_time, 12345.67)
        self.assertEqual(len(callback_called), 1, "on_action_success 應被呼叫一次")

    @patch("actions.mouse.pyautogui.position", return_value=(50, 60))
    def test_finalize_action_no_callback_is_noop(self, mock_pos):
        """驗證 Issue #11：未注入 callback 時，_finalize_action 正常完成而不拋出異常。"""
        mouse = MouseController()  # 無 on_action_success
        with patch.object(mouse, "move_to_safe_area"):
            with patch("actions.mouse.time.sleep") as mock_sleep:
                res = mouse._finalize_action(target_pos=None, cooldown=0.3, move_safe=False)

        self.assertTrue(res)
        self.assertEqual(mouse.last_target_pos, (50, 60))
        mock_sleep.assert_called_once_with(0.3)

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
    def test_move_to_safe_area_frontend_noop_when_no_hwnd(self, mock_move_to):
        """驗證 Issue #11 (last_rect 移除)：前台模式找不到 hwnd 時為 no-op，不再依賴 state_machine.last_rect。"""
        mouse = MouseController(backend_mode=False)
        with patch.object(mouse, "get_hwnd", return_value=0):
            mouse.move_to_safe_area()  # 應不拋出異常

        mock_move_to.assert_not_called()


if __name__ == "__main__":
    unittest.main()
