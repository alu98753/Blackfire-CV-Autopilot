import unittest
from unittest.mock import patch, MagicMock
from utils.sandbox_manager import SandboxManager
from states.exceptions.subflows.game_relaunch import GameRelaunchSubflow


class TestSandboxManager(unittest.TestCase):
    def setUp(self):
        self.manager = SandboxManager(start_exe=r"C:\Program Files\Sandboxie-Plus\Start.exe", box_name="TestBox")

    def test_is_sandbox_title(self):
        self.assertTrue(SandboxManager.is_sandbox_title("[#] Blackfire Crusade [#]"))
        self.assertTrue(SandboxManager.is_sandbox_title("[#] Some Game [#]"))
        self.assertFalse(SandboxManager.is_sandbox_title("Blackfire Crusade"))
        self.assertFalse(SandboxManager.is_sandbox_title(None))

    @patch("os.path.exists", return_value=True)
    def test_get_start_exe_configured(self, _mock_exists):
        self.assertEqual(self.manager.get_start_exe(), r"C:\Program Files\Sandboxie-Plus\Start.exe")

    @patch("subprocess.Popen")
    @patch("os.path.exists", side_effect=lambda p: True if "Start.exe" in p else False)
    def test_launch_steam_game_fallback_url(self, _mock_exists, mock_popen):
        success = self.manager.launch_steam_game(app_id="1765770", box_name="TestBox")
        self.assertTrue(success)
        mock_popen.assert_called_once()
        cmd = mock_popen.call_args[0][0]
        self.assertIn("/box:TestBox", cmd)
        self.assertIn("steam://rungameid/1765770", cmd)

    @patch("subprocess.Popen")
    @patch("os.path.exists", return_value=True)
    def test_launch_steam_game_direct_exe(self, _mock_exists, mock_popen):
        success = self.manager.launch_steam_game(app_id="1765770", box_name="TestBox")
        self.assertTrue(success)
        mock_popen.assert_called_once()
        cmd = mock_popen.call_args[0][0]
        self.assertIn("/box:TestBox", cmd)
        self.assertIn("Blackfire Crusade.exe", cmd[2])

    @patch("subprocess.run")
    @patch("os.path.exists", return_value=True)
    def test_terminate_box_success(self, _mock_exists, mock_run):
        success = self.manager.terminate_box(box_name="TestBox")
        self.assertTrue(success)
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        self.assertIn("/box:TestBox", cmd)
        self.assertIn("/terminate", cmd)


class TestGameRelaunchSubflowSandboxAware(unittest.TestCase):
    def setUp(self):
        self.subflow = GameRelaunchSubflow()
        self.mock_machine = MagicMock()
        self.mock_machine.window_title = "[#] Blackfire Crusade [#]"
        self.mock_machine.is_sandbox = True
        self.mock_machine.STATE_UNKNOWN = "STATE_UNKNOWN"

    @patch("utils.steam_launcher.SteamGameLauncher.ensure_game_ready", return_value=True)
    @patch("subprocess.run")
    @patch("win32gui.FindWindow", side_effect=[0x9999, 0])
    @patch("win32gui.IsWindow", return_value=True)
    @patch("win32process.GetWindowThreadProcessId", return_value=(0, 10452))
    def test_execute_sandbox_kills_only_target_pid_preserving_steam(
        self, _mock_thread_pid, _mock_is_window, _mock_find_window, mock_run, _mock_ensure
    ):
        result = self.subflow.execute(self.mock_machine, reason="test_sandbox_crash")
        self.assertTrue(result)
        mock_run.assert_called_once()
        self.assertIn("10452", mock_run.call_args[0][0])
        self.mock_machine.transition_to.assert_called_once_with("STATE_UNKNOWN")


if __name__ == "__main__":
    unittest.main()
