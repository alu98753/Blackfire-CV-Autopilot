"""Behavioral domain tests for logging levels, CLI contracts, and BattleSession telemetry."""

import argparse
import logging
import unittest
from unittest.mock import MagicMock, patch

from config import apply_log_level, get_log_level, get_log_retention_days
from cli.arguments import parse_arguments
from cli.log_setup import init_file_logger, setup_log_level_config
from states.battle_session import BattleSession


class TestBehaviorLogLevelAndCLI(unittest.TestCase):
    """Test suite for log level retrieval, dynamic switching, CLI setup, and stall telemetry."""

    def setUp(self):
        self.original_level = logging.getLogger().level

    def tearDown(self):
        apply_log_level("INFO")

    def test_get_log_level_defaults(self):
        """Default log level should fallback to INFO if not overridden."""
        level = get_log_level()
        self.assertIn(level, ["DEBUG", "INFO", "WARNING", "ERROR"])

    def test_apply_log_level(self):
        """apply_log_level should dynamically adjust the root logger and its handlers."""
        applied = apply_log_level("DEBUG")
        self.assertEqual(applied, "DEBUG")
        self.assertEqual(logging.getLogger().level, logging.DEBUG)

        applied = apply_log_level("WARNING")
        self.assertEqual(applied, "WARNING")
        self.assertEqual(logging.getLogger().level, logging.WARNING)

    def test_cli_argument_log_level_parser(self):
        """CLI parser should correctly parse --log-level argument with case insensitivity."""
        with patch("sys.argv", ["main.py", "--log-level", "debug"]):
            args = parse_arguments()
            self.assertEqual(args.log_level, "DEBUG")

        with patch("sys.argv", ["main.py", "--log-level", "WARNING"]):
            args = parse_arguments()
            self.assertEqual(args.log_level, "WARNING")

    def test_setup_log_level_config_explicit_cli_skips_prompt(self):
        """Explicit --log-level should immediately apply and return without prompting."""
        args = argparse.Namespace(log_level="DEBUG")
        with patch("cli.log_setup.prompt_choice") as mock_prompt:
            chosen = setup_log_level_config(args, is_resume=False)
            self.assertEqual(chosen, "DEBUG")
            self.assertEqual(logging.getLogger().level, logging.DEBUG)
            mock_prompt.assert_not_called()

    def test_setup_log_level_config_resume_skips_prompt(self):
        """Supervisor resume flag should immediately apply profile preference without prompting."""
        args = argparse.Namespace(log_level=None)
        with patch("cli.log_setup.get_log_level", return_value="WARNING"), \
             patch("cli.log_setup.prompt_choice") as mock_prompt:
            chosen = setup_log_level_config(args, is_resume=True)
            self.assertEqual(chosen, "WARNING")
            self.assertEqual(logging.getLogger().level, logging.WARNING)
            mock_prompt.assert_not_called()

    def test_setup_log_level_config_interactive_persists_change(self):
        """Interactive selection should prompt and persist changed preference to profile."""
        args = argparse.Namespace(log_level=None)
        with patch("cli.log_setup.get_log_level", return_value="INFO"), \
             patch("cli.log_setup.prompt_choice", return_value="2"), \
             patch("cli.log_setup.get_active_profile", return_value="native"), \
             patch("cli.log_setup.update_profile_config") as mock_update:
            chosen = setup_log_level_config(args, is_resume=False)
            self.assertEqual(chosen, "DEBUG")
            self.assertEqual(logging.getLogger().level, logging.DEBUG)
            mock_update.assert_called_once_with("native", {"global": {"log_level": "DEBUG"}})

    def test_battle_session_stall_telemetry_and_diff(self):
        """BattleSession should update last_diff and emit debug telemetry during check."""
        session = BattleSession()
        session.begin(now=100.0, entry_state="BATTLE")
        self.assertEqual(session.last_diff, 0)

        with self.assertLogs(level="DEBUG") as cm:
            # 1. First signature observation
            is_stalled = session.is_hp_stalled(current_signature=1800, now=100.0, timeout_seconds=30.0)
            self.assertFalse(is_stalled)
            self.assertEqual(session.last_hp_signature, 1800)
            self.assertEqual(session.last_diff, 0)

            # 2. Minor change (diff = 4 < threshold 25), still stalling
            is_stalled = session.is_hp_stalled(current_signature=1796, now=110.0, timeout_seconds=30.0)
            self.assertFalse(is_stalled)
            self.assertEqual(session.last_diff, 4)

            # Check that DEBUG log was emitted
            debug_logs = [log for log in cm.output if "[BattleStall]" in log]
            self.assertTrue(len(debug_logs) > 0)
            self.assertIn("diff: 4", debug_logs[-1])

            # 3. Timeout reached after 30s with minor change
            is_stalled = session.is_hp_stalled(current_signature=1796, now=130.5, timeout_seconds=30.0)
            self.assertTrue(is_stalled)
            self.assertEqual(session.last_diff, 4)

            # 4. Significant change (diff = 54 >= threshold 25), progress made, stall reset
            is_stalled = session.is_hp_stalled(current_signature=1746, now=131.0, timeout_seconds=30.0)
            self.assertFalse(is_stalled)
            self.assertEqual(session.last_diff, 54)
            self.assertEqual(session.last_hp_signature, 1746)

            # Verify progress telemetry log was emitted
            progress_logs = [log for log in cm.output if "戰鬥推進" in log or "戰鬥進展" in log]
            self.assertTrue(len(progress_logs) > 0)
            self.assertIn("diff=54", progress_logs[-1])

    def test_get_log_retention_days(self):
        """Retention days should default to 7."""
        days = get_log_retention_days()
        self.assertEqual(days, 7)

    def test_init_file_logger_attaches_rotating_handler(self):
        """init_file_logger should create log file and attach TimedRotatingFileHandler."""
        from logging.handlers import TimedRotatingFileHandler
        import shutil
        test_prof = "test_profile_logger"
        try:
            log_path = init_file_logger(test_prof)
            self.assertTrue(log_path.parent.exists())
            self.assertEqual(log_path.name, "app.log")

            root_logger = logging.getLogger()
            rotating_handlers = [
                h for h in root_logger.handlers
                if isinstance(h, TimedRotatingFileHandler) and getattr(h, "_app_log_profile", None) == test_prof
            ]
            self.assertEqual(len(rotating_handlers), 1)
            self.assertEqual(rotating_handlers[0].backupCount, 7)
            self.assertEqual(rotating_handlers[0].when, "MIDNIGHT")

            # Calling it again shouldn't duplicate the handler
            init_file_logger(test_prof)
            rotating_handlers_2 = [
                h for h in root_logger.handlers
                if isinstance(h, TimedRotatingFileHandler) and getattr(h, "_app_log_profile", None) == test_prof
            ]
            self.assertEqual(len(rotating_handlers_2), 1)
        finally:
            root_logger = logging.getLogger()
            for h in list(root_logger.handlers):
                if isinstance(h, TimedRotatingFileHandler) and getattr(h, "_app_log_profile", None) == test_prof:
                    h.close()
                    root_logger.removeHandler(h)
            from config import USER_DATA_DIR
            from pathlib import Path
            test_dir = Path(USER_DATA_DIR) / test_prof
            if test_dir.exists():
                shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
