import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import main
from runtime.bootstrap import init_state_machine_system
from cli.arguments import parse_arguments


def args(**overrides):
    values = dict(title="Blackfire Crusade", target=None, profile=None,
                  mode="stage", subflow=None,
                  backend_mode=True, monitor=None, interval=.5)
    values.update(overrides)
    return SimpleNamespace(**values)


class TestRuntimeIOComposition(unittest.TestCase):
    def test_cli_modes(self):
        with patch("sys.argv", ["main.py"]):
            self.assertTrue(parse_arguments().backend_mode)
        with patch("sys.argv", ["main.py", "--foreground"]):
            self.assertFalse(parse_arguments().backend_mode)

    def test_main_uses_composed_capture_for_backend_and_foreground(self):
        for foreground in (False, True):
            selected = args(backend_mode=not foreground)
            composed = MagicMock()
            with patch("main.parse_arguments", return_value=selected), \
                 patch("main.setup_utf8_encoding"), patch("main.select_game_window", return_value=(123, selected.title)), \
                 patch("main.setup_log_level_config"), patch("main.setup_mode_config", return_value={}), \
                 patch("main.setup_equipment_config"), patch("main.get_monitor_index", return_value=2), \
                 patch("runtime.io_adapters.compose_capture", return_value=composed) as compose, \
                 patch("main.SteamGameLauncher") as launcher, patch("main.init_state_machine_system", return_value=MagicMock()), \
                 patch("main.run_main_loop"):
                launcher.return_value.ensure_game_ready.return_value = True
                main.main()
            compose.assert_called_once_with(foreground=foreground, window_title=selected.title, monitor_index=2, hwnd=123)
            self.assertIs(launcher.call_args.kwargs["capturer"], composed)

    def test_bootstrap_passes_composed_pair_to_state_machine(self):
        for foreground in (False, True):
            selected = args(backend_mode=not foreground)
            capture, mouse, machine = MagicMock(), MagicMock(), MagicMock()
            with patch("runtime.io_adapters.compose_io", return_value=(capture, mouse)) as compose, \
                 patch("runtime.bootstrap.GameStateMachine", return_value=machine) as machine_ctor, \
                 patch("runtime.bootstrap.TemplateMatcher"), patch("runtime.bootstrap.DailyManager"), \
                 patch("builtins.print"), \
                 patch("runtime.bootstrap.check_mode_templates", return_value=[]), \
                 patch("runtime.bootstrap.os.path.exists", return_value=True), \
                 patch("runtime.bootstrap.normalize_config", side_effect=lambda value: value), \
                 patch("runtime.bootstrap.get_monitor_index", return_value=2), \
                 patch("runtime.bootstrap.resolve_profile_name", return_value="native"):
                init_state_machine_system(selected, {"name": "Stage", "type": "stage"}, target_hwnd=123)
            compose.assert_called_once_with(foreground=foreground, window_title=selected.title,
                                             hwnd=123, monitor_index=2, human_like=True)
            self.assertIs(machine_ctor.call_args.kwargs["capturer"], capture)
            self.assertIs(machine_ctor.call_args.kwargs["mouse"], mouse)

    def test_missing_templates_precede_io_composition(self):
        selected = args()
        with patch("runtime.bootstrap.check_mode_templates", return_value=["missing.png"]), \
             patch("runtime.io_adapters.compose_io") as compose, \
             patch("builtins.print"), patch("runtime.bootstrap.os.makedirs"):
            with self.assertRaises(SystemExit):
                init_state_machine_system(selected, {"name": "Stage", "type": "stage"})
            compose.assert_not_called()
