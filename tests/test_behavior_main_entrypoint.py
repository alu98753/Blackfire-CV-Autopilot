"""Public startup and runtime-loop contracts for the application entry point."""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

import main
from cli.dungeon_setup import setup_dungeon_config
from cli.profile_updates import persist_mode_updates
from cli.prompts import prompt_choice
from cli.stage_setup import setup_stage_config
from runtime.loop import run_main_loop
from utils.keyboard_listener import PauseController


def make_args(**overrides):
    values = {
        "title": "Blackfire Crusade",
        "target": None,
        "profile": None,
        "mode": "stage",
        "subflow": None,
        "backend": True,
        "monitor": None,
        "interval": 0.5,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class TestMainEntrypointBehavior(unittest.TestCase):
    def test_manual_exit_hotkey_requires_target_focus_and_all_three_keys(self):
        pause_controller = PauseController(start_thread=False)
        pause_controller.is_target_window_active = MagicMock(return_value=True)
        with patch("utils.keyboard_listener.ctypes.windll.user32.GetAsyncKeyState", return_value=0x8000):
            pause_controller._poll_once()

        self.assertTrue(pause_controller.check_manual_exit_triggered())
        self.assertFalse(pause_controller.check_manual_exit_triggered())

    def test_prompt_choice_returns_default_for_empty_input_or_terminal_interrupt(self):
        with patch("builtins.input", return_value="   "):
            self.assertEqual(prompt_choice("choice: ", "default"), "default")
        with patch("builtins.input", side_effect=EOFError):
            self.assertEqual(prompt_choice("choice: ", "default"), "default")
        with patch("builtins.input", return_value="six"):
            self.assertEqual(prompt_choice("choice: ", "default"), "six")

    @patch("config.update_profile_config")
    @patch("config.get_active_profile", return_value="sandbox")
    def test_mode_selection_persists_only_changed_values_to_active_profile_mode(
        self, get_active_profile, update_profile_config
    ):
        persist_mode_updates(
            {"_config_mode_key": "daily", "type": "mix"}, {"tier4_sub_stage": "six"}
        )

        get_active_profile.assert_called_once_with()
        update_profile_config.assert_called_once_with(
            "sandbox", {"primary_modes": {"daily": {"tier4_sub_stage": "six"}}}
        )

    @patch("cli.stage_setup.persist_mode_updates")
    @patch("cli.stage_setup.get_stage_configs")
    @patch("cli.stage_setup.os.path.exists", return_value=True)
    @patch("builtins.input")
    def test_explicit_stage_cli_selection_skips_terminal_prompts_and_persists_changed_selection(
        self, terminal_input, _exists, get_stage_configs, persist
    ):
        get_stage_configs.return_value = {
            "6": {
                "name": "Level 6", "entry": "stages/level6.png",
                "sub_stages": {"six": "stages/six_stage.png", "final": "stages/final.png"},
            }
        }
        config = {"type": "stage", "tier4_stage_level": 6, "tier4_sub_stage": "final"}

        setup_stage_config(config, stage_level=6, sub_stage_type="six")

        terminal_input.assert_not_called()
        self.assertEqual(config["stage_target"], "stages/six_stage.png")
        self.assertIn("stages/six_stage.png", config["navigation_path"])
        persist.assert_called_once_with(
            config, {"tier4_stage_level": 6, "tier4_sub_stage": "six"}
        )

    @patch("cli.dungeon_setup.persist_mode_updates")
    @patch("builtins.input", side_effect=["7", "113", "1"])
    def test_greedy_dungeon_deduplicates_targets_and_persists_only_changed_policy(
        self, _input, persist
    ):
        config = {
            "greedy_dungeon": False, "tier4_dungeon_index": 4,
            "greedy_allowed_indices": [0, 1], "bless_mode": "combat",
            "auto_resume_dungeon_on_cd": False,
        }
        args = make_args(blessmode="combat")

        setup_dungeon_config(config, args)

        self.assertTrue(config["greedy_dungeon"])
        self.assertEqual(config["greedy_allowed_indices"], [0, 2])
        self.assertTrue(config["auto_resume_dungeon_on_cd"])
        persist.assert_called_once_with(
            config,
            {
                "greedy_dungeon": True,
                "greedy_allowed_indices": [0, 2],
                "auto_resume_dungeon_on_cd": True,
            },
        )

    @patch("cli.dungeon_setup.persist_mode_updates")
    @patch("builtins.input", side_effect=["2", "3", "2"])
    def test_dungeon_prompt_updates_blessing_and_cooldown_return_policy(self, _input, persist):
        config = {
            "greedy_dungeon": False, "tier4_dungeon_index": 0,
            "greedy_allowed_indices": [0, 1], "bless_mode": "combat",
            "auto_resume_dungeon_on_cd": True,
        }
        args = make_args(blessmode=None)

        setup_dungeon_config(config, args)

        self.assertEqual(config["tier4_dungeon_index"], 1)
        self.assertEqual(config["bless_mode"], "exp")
        self.assertFalse(config["auto_resume_dungeon_on_cd"])
        persist.assert_called_once_with(
            config,
            {
                "tier4_dungeon_index": 1,
                "bless_mode": "exp",
                "auto_resume_dungeon_on_cd": False,
            },
        )

    def test_argument_parser_keeps_optional_activity_flags_unset_without_cli_input(self):
        with patch("sys.argv", ["main.py", "--mode", "daily", "--profile", "sandbox"]):
            args = main.parse_arguments()

        self.assertEqual(args.mode, "daily")
        self.assertEqual(args.profile, "sandbox")
        self.assertIsNone(args.enable_dungeon)
        self.assertIsNone(args.enable_stage_farming)
        self.assertIsNone(args.enable_town_daily)

    def test_argument_parser_accepts_explicit_activity_disable_without_changing_other_policies(self):
        with patch("sys.argv", ["main.py", "--no-dungeon", "--boss"]):
            args = main.parse_arguments()

        self.assertFalse(args.enable_dungeon)
        self.assertTrue(args.enable_lord_boss)
        self.assertIsNone(args.enable_stage_farming)

    def test_argument_parser_accepts_non_interactive_supervisor_restart(self):
        with patch("sys.argv", ["main.py", "--target", "sandbox", "--profile", "sandbox", "--resume"]):
            args = main.parse_arguments()

        self.assertTrue(args.resume)
        self.assertEqual(args.target, "sandbox")

    def test_profile_selection_prefers_explicit_profile_then_target_then_window_title(self):
        self.assertEqual(main.resolve_profile_name(make_args(profile="ACC2"), "[#] Game"), "acc2")
        self.assertEqual(main.resolve_profile_name(make_args(target="sandbox"), "Game"), "sandbox")
        self.assertEqual(main.resolve_profile_name(make_args(), "[#] Blackfire Crusade"), "sandbox")
        self.assertEqual(main.resolve_profile_name(make_args(), "Blackfire Crusade"), "native")

    @patch("main.run_main_loop")
    @patch("main.init_state_machine_system")
    @patch("main.SteamGameLauncher")
    @patch("main.get_monitor_index", return_value=3)
    @patch("main.setup_equipment_config")
    @patch("main.setup_mode_config")
    @patch("config.set_active_profile")
    @patch("main.select_game_window", return_value=(0x123, "[#] Blackfire Crusade"))
    @patch("main.parse_arguments")
    @patch("main.setup_utf8_encoding")
    def test_main_binds_selected_window_profile_before_loading_mode_and_starts_loop(
        self,
        setup_utf8,
        parse_args,
        select_window,
        set_active_profile,
        setup_mode,
        setup_equipment,
        get_monitor,
        launcher_class,
        init_system,
        run_loop,
    ):
        args = make_args()
        config = {"name": "Stage", "type": "stage"}
        machine = MagicMock()
        parse_args.return_value = args
        setup_mode.return_value = config
        launcher_class.return_value.ensure_game_ready.return_value = True
        init_system.return_value = machine

        main.main()

        self.assertEqual(args.title, "[#] Blackfire Crusade")
        set_active_profile.assert_called_once_with("sandbox")
        setup_mode.assert_called_once_with(args)
        setup_equipment.assert_called_once_with(config)
        launcher_class.assert_called_once_with(
            game_title=args.title, backend_mode=True, monitor_index=3, hwnd=0x123
        )
        init_system.assert_called_once_with(args, config, target_hwnd=0x123)
        run_loop.assert_called_once_with(machine, 0.5)
        self.assertIsInstance(machine.incident_session_id, str)
        self.assertTrue(machine.incident_session_id)
        self.assertEqual(
            [setup_utf8.call_args, select_window.call_args, set_active_profile.call_args, setup_mode.call_args],
            [call(), call(target=None, auto_prompt=True), call("sandbox"), call(args)],
        )

    @patch("main.init_state_machine_system")
    @patch("main.SteamGameLauncher")
    @patch("main.setup_equipment_config")
    @patch("main.setup_mode_config", return_value={"name": "Stage", "type": "stage"})
    @patch("config.set_active_profile")
    @patch("main.select_game_window", return_value=(None, "Blackfire Crusade"))
    @patch("main.parse_arguments", return_value=make_args())
    @patch("main.setup_utf8_encoding")
    def test_main_fails_before_state_machine_initialization_when_game_is_not_ready(
        self, _encoding, _arguments, _window, _profile, _mode, _equipment, launcher_class, init_system
    ):
        launcher_class.return_value.ensure_game_ready.return_value = False

        with self.assertRaises(SystemExit) as exited:
            main.main()

        self.assertEqual(exited.exception.code, 1)
        init_system.assert_not_called()

    @patch("runtime.bootstrap.time.sleep")
    @patch("builtins.print")
    @patch("runtime.loop.PauseController")
    @patch("runtime.bootstrap.DailyManager")
    @patch("runtime.bootstrap.GameStateMachine")
    @patch("runtime.bootstrap.MouseController")
    @patch("runtime.bootstrap.TemplateMatcher")
    @patch("runtime.bootstrap.ScreenCapturer")
    @patch("runtime.bootstrap.check_mode_templates", return_value=[])
    @patch("runtime.bootstrap.os.path.exists", return_value=True)
    @patch("runtime.bootstrap.normalize_config", side_effect=lambda config: config)
    @patch("runtime.bootstrap.get_monitor_index", return_value=3)
    def test_initializer_wires_profile_runtime_refresh_and_daily_pipeline(
        self, _monitor, _normalize, _exists, _templates, capturer_class, matcher_class, mouse_class,
        machine_class, daily_manager_class, _pause_controller, _print, _sleep,
    ):
        args = make_args(mode="daily", title="[#] Blackfire Crusade", subflow=None)
        config = {"name": "Daily", "type": "mix", "auto_bread": True, "auto_diamond": True}
        machine = machine_class.return_value
        manager = daily_manager_class.return_value
        manager.load_quest_scheduler.return_value = "scheduler"

        returned = main.init_state_machine_system(args, config, target_hwnd=0x456)

        self.assertIs(returned, machine)
        capturer_class.assert_called_once_with(
            window_title=args.title, backend_mode=True, hwnd=0x456, monitor_index=3
        )
        machine.enable_runtime_config_refresh.assert_called_once_with("daily", config)
        daily_manager_class.assert_called_once_with(profile="sandbox")
        machine.attach_quest_scheduler.assert_called_once_with("scheduler")
        machine.evaluate_and_schedule_daily_pipeline.assert_called_once_with()
        self.assertIs(machine.daily_manager, manager)
        self.assertTrue(machine.enable_bread)

    @patch("runtime.bootstrap.ScreenCapturer")
    @patch("runtime.bootstrap.check_mode_templates", return_value=["stages/missing.png"])
    @patch("runtime.bootstrap.os.makedirs")
    @patch("builtins.print")
    def test_initializer_fails_before_constructing_game_dependencies_when_required_template_is_missing(
        self, _print, _mkdir, _templates, capturer_class
    ):
        args = make_args()
        config = {"name": "Stage", "type": "stage"}

        with self.assertRaises(SystemExit) as exited:
            main.init_state_machine_system(args, config)

        self.assertEqual(exited.exception.code, 1)
        capturer_class.assert_not_called()

    @patch("runtime.loop.time.sleep")
    @patch("builtins.print")
    @patch("runtime.loop.PauseController")
    def test_runtime_loop_refreshes_config_before_each_state_machine_step(
        self, pause_controller_class, _print, sleep
    ):
        state_machine = MagicMock()
        state_machine.is_paused = False
        state_machine.step.side_effect = KeyboardInterrupt
        pause_controller_class.return_value.check_toggle_triggered.return_value = False

        with self.assertRaises(SystemExit):
            run_main_loop(state_machine, interval=0.5)

        self.assertEqual(
            [state_machine.refresh_config_at_safe_point.call_args, state_machine.step.call_args],
            [call(), call()],
        )
        self.assertLess(
            state_machine.mock_calls.index(call.refresh_config_at_safe_point()),
            state_machine.mock_calls.index(call.step()),
        )
