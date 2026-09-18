import unittest
from unittest.mock import MagicMock, patch

from runtime.io_adapters import (compose_io, BackendScreenCapturer,
    ForegroundScreenCapturer, BackendMouseController, ForegroundMouseController)
from utils.steam_launcher import SteamGameLauncher
import runtime.io_adapters as adapters


class TestForegroundDemoModeIsolation(unittest.TestCase):
    def test_composition_selects_fixed_adapter_families(self):
        with patch('capture.screen.mss.MSS'):
            capture, mouse = compose_io(foreground=False, window_title='x')
            self.assertIsInstance(capture, BackendScreenCapturer)
            self.assertIsInstance(mouse, BackendMouseController)
            capture, mouse = compose_io(foreground=True, window_title='x')
            self.assertIsInstance(capture, ForegroundScreenCapturer)
            self.assertIsInstance(mouse, ForegroundMouseController)

    def test_launcher_requires_injected_capture_and_has_no_mode_owner(self):
        capture = MagicMock()
        launcher = SteamGameLauncher(capturer=capture, game_title='x')
        self.assertIs(launcher.capturer, capture)
        self.assertFalse(hasattr(launcher, 'backend_mode'))
        self.assertFalse(hasattr(launcher, 'mouse'))

    def test_backend_capture_is_fail_closed_without_foreground_calls(self):
        capture = BackendScreenCapturer(window_title='x', hwnd=123)
        capture._capture_backend = MagicMock(return_value=None)
        with patch.object(capture, 'get_hwnd', return_value=123), patch.object(capture, 'get_window_rect') as rect:
            with patch.object(capture.sct, 'grab') as grab, patch('PIL.ImageGrab.grab') as pil:
                self.assertIsNone(capture.capture()); grab.assert_not_called(); pil.assert_not_called(); rect.assert_not_called()

    def test_foreground_capture_uses_pil_after_mss_failure(self):
        capture = ForegroundScreenCapturer(window_title='x')
        capture.get_window_rect = MagicMock(return_value={'left': 1, 'top': 2, 'width': 3, 'height': 4})
        capture.sct.grab = MagicMock(side_effect=RuntimeError('mss'))
        import numpy as np
        with patch('PIL.ImageGrab.grab', return_value=np.zeros((2,2,3), dtype='uint8')):
            self.assertIsNotNone(capture.capture())

    def test_backend_input_never_calls_pyautogui(self):
        mouse = BackendMouseController(window_title='x', hwnd=123)
        with patch.object(mouse, 'get_hwnd', return_value=123), patch.object(mouse, '_screen_to_client', return_value=(10, 20)), patch.object(mouse, '_draw_debug_click'), patch.object(mouse, '_finalize_action', return_value=True), patch.object(adapters.win32gui, 'PostMessage'), patch.object(adapters.win32gui, 'SendMessage'), patch.object(adapters.win32gui, 'GetClientRect', return_value=(0, 0, 100, 100)), patch.object(adapters.win32gui, 'ClientToScreen', return_value=(10, 20)), patch.object(adapters.pyautogui, 'moveTo') as move, patch.object(adapters.pyautogui, 'mouseDown') as down, patch.object(adapters.pyautogui, 'scroll') as scroll, patch.object(adapters.pyautogui, 'dragTo') as drag:
            self.assertTrue(mouse.click(10, 20)); self.assertTrue(mouse.scroll(1)); self.assertTrue(mouse.drag(1, 2, 3, 4, duration=.1)); mouse.move_to_safe_area()
            move.assert_not_called(); down.assert_not_called(); scroll.assert_not_called(); drag.assert_not_called()

    def test_foreground_input_uses_pyautogui(self):
        mouse = ForegroundMouseController(window_title='x')
        with patch.object(mouse, 'get_hwnd', return_value=None), patch.object(mouse, '_finalize_action', return_value=True), patch.object(adapters.pyautogui, 'moveTo'), patch.object(adapters.pyautogui, 'mouseDown'), patch.object(adapters.pyautogui, 'mouseUp'), patch.object(adapters.pyautogui, 'scroll') as scroll, patch.object(adapters.pyautogui, 'dragTo'):
            self.assertTrue(mouse.click(1, 2)); self.assertTrue(mouse.scroll(1)); self.assertTrue(mouse.drag(1, 2, 3, 4)); mouse.move_to_safe_area(); scroll.assert_called_once_with(1)

    def test_backend_drag_preserves_timing_and_release_sequence(self):
        mouse = BackendMouseController(window_title='x', hwnd=123)
        sleeps = []
        with patch.object(mouse, 'get_hwnd', return_value=123), \
             patch.object(mouse, '_screen_to_client', side_effect=[(10, 20), (30, 40)]), \
             patch.object(mouse, '_finalize_action', return_value=True) as finalize, \
             patch.object(adapters.win32gui, 'SendMessage') as send, \
             patch.object(adapters.win32api, 'MAKELONG', side_effect=lambda x, y: (x, y)), \
             patch.object(adapters.time, 'sleep', side_effect=lambda value: sleeps.append(value)):
            self.assertTrue(mouse.drag(1, 2, 3, 4, duration=.1, inertia=False))
        messages = [call.args[1] for call in send.call_args_list]
        self.assertEqual(messages[0:2], [adapters.win32con.WM_MOUSEMOVE, adapters.win32con.WM_LBUTTONDOWN])
        self.assertEqual(messages[-2:], [adapters.win32con.WM_MOUSEMOVE, adapters.win32con.WM_LBUTTONUP])
        self.assertIn(.03, sleeps)
        self.assertIn(.05, sleeps)
        self.assertIn(.15, sleeps)
        self.assertIn(.02, sleeps)
        finalize.assert_called_once_with(cooldown=.3, move_safe=True)

    @patch('states.exceptions.subflows.game_relaunch.terminate_game_process')
    @patch('states.exceptions.subflows.game_relaunch.time.sleep')
    @patch('states.exceptions.subflows.game_relaunch.SteamGameLauncher')
    def test_relaunch_reuses_machine_capture(self, launcher_type, sleep, terminate):
        machine = MagicMock()
        machine.window_title = 'x'; machine.capturer = MagicMock()
        machine.capturer.get_hwnd.return_value = 123
        machine.is_sandbox = False; machine.matcher = MagicMock()
        machine.exception_watchdog = MagicMock()
        launcher_type.return_value.ensure_game_ready.return_value = True
        machine.STATE_UNKNOWN = 'unknown'
        from states.exceptions.subflows.game_relaunch import GameRelaunchSubflow
        GameRelaunchSubflow().execute(machine, 'test')
        self.assertIs(launcher_type.call_args.kwargs['capturer'], machine.capturer)
        self.assertNotIn('backend_mode', launcher_type.call_args.kwargs)

    @patch('states.exceptions.subflows.game_relaunch.SteamGameLauncher')
    def test_relaunch_missing_capture_fails_before_launcher(self, launcher_type):
        machine = MagicMock(capturer=None)
        machine.window_title = 'x'
        from states.exceptions.subflows.game_relaunch import GameRelaunchSubflow
        with self.assertRaisesRegex(RuntimeError, 'machine.capturer'):
            GameRelaunchSubflow().execute(machine, 'missing')
        launcher_type.assert_not_called()
