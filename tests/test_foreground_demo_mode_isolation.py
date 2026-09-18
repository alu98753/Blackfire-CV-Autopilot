import unittest
from unittest.mock import MagicMock, patch

from runtime.io_adapters import (compose_io, BackendScreenCapturer,
    ForegroundScreenCapturer, BackendMouseController, ForegroundMouseController)
from utils.steam_launcher import SteamGameLauncher


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

