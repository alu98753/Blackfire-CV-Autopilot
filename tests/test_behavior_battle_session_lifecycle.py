"""Behavioral coverage for battle timeout ownership and relaunch recovery."""

import unittest
from unittest.mock import MagicMock, patch

from states.handlers.battle import BattleHandler
from states.state_machine import GameStateMachine


class FakeClock:
    def __init__(self, now=0.0):
        self.now = now

    def monotonic(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class TestBattleSessionLifecycle(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock(now=10_000.0)
        self.process_port = MagicMock()
        self.machine = GameStateMachine(
            capturer=MagicMock(),
            matcher=MagicMock(),
            mouse=MagicMock(),
            preload_ocr=False,
            clock=self.clock,
            process_port=self.process_port,
        )
        self.machine.matcher.match.return_value = (None, 0.0)
        self.machine.config = {
            "type": "stage",
            "result_buttons": [],
            "dungeon_battle_results": [],
        }

    @patch("states.handlers.battle.os.path.exists", return_value=False)
    @patch("states.handlers.battle.time.sleep")
    def test_relocated_battle_starts_a_new_timeout_window(self, _sleep, _exists):
        """A recovered auto.png observation cannot inherit a previous battle age."""
        self.machine.battle_start_time = self.clock.monotonic() - 25_697.9

        self.machine.transition_to(self.machine.STATE_BATTLE)
        BattleHandler(self.machine).handle(MagicMock(), {"left": 0, "top": 0})

        self.assertEqual(self.machine.battle_elapsed_seconds(), 0.0)
        self.process_port.relaunch.assert_not_called()

    def test_leaving_battle_clears_the_session_for_the_next_boss(self):
        """Result and recovery transitions terminate the previous battle session."""
        self.machine.current_state = self.machine.STATE_LORD_BOSS
        self.machine.transition_to(self.machine.STATE_BATTLE)
        self.clock.advance(120.0)

        self.machine.transition_to(self.machine.STATE_RESULT)
        self.assertFalse(self.machine.battle_session.is_active)

        self.machine.transition_to(self.machine.STATE_LORD_BOSS)
        self.machine.transition_to(self.machine.STATE_BATTLE)
        self.assertEqual(self.machine.battle_elapsed_seconds(), 0.0)
        self.assertEqual(
            self.machine.battle_session.entry_state,
            self.machine.STATE_LORD_BOSS,
        )

    def test_relaunch_recovery_clears_then_recreates_a_bounded_session(self):
        """The UNKNOWN recovery boundary prevents the restart loop in the log."""
        self.machine.transition_to(self.machine.STATE_BATTLE)
        self.clock.advance(25_697.9)

        self.machine.transition_to(self.machine.STATE_UNKNOWN)
        self.assertFalse(self.machine.battle_session.is_active)

        self.clock.advance(30.0)
        self.machine.transition_to(self.machine.STATE_BATTLE)
        self.assertEqual(self.machine.battle_elapsed_seconds(), 0.0)

    @patch("states.handlers.battle.os.path.exists", return_value=True)
    @patch("states.handlers.battle.time.sleep")
    @patch("states.handlers.battle.extract_health_bar_signature")
    def test_battle_stall_triggers_restart_subflow(self, mock_extract, _sleep, _exists):
        """When HP signature remains unchanged for 30s, handler triggers in-place restart."""
        self.machine.transition_to(self.machine.STATE_BATTLE)
        handler = BattleHandler(self.machine)
        handler._check_and_handle_nemesis_encounter = MagicMock(return_value=False)
        handler._run_restart_battle_subflow = MagicMock(return_value=True)

        mock_extract.return_value = 1500  # constant HP signature
        
        # 第一次採樣
        handler.handle(MagicMock(), {"left": 0, "top": 0})
        handler._run_restart_battle_subflow.assert_not_called()

        # 模擬時間前進 31 秒 (血條簽章完全沒變)
        self.clock.advance(31.0)
        handler.handle(MagicMock(), {"left": 0, "top": 0})

        handler._run_restart_battle_subflow.assert_called_once()
        self.process_port.relaunch.assert_not_called()

    @patch("states.handlers.battle.os.path.exists", return_value=True)
    @patch("states.handlers.battle.time.sleep")
    @patch("states.handlers.battle.extract_health_bar_signature")
    def test_battle_stall_max_retries_escalates_to_relaunch(self, mock_extract, _sleep, _exists):
        """When in-place restart exceeds max_retries (2), escalate to request_relaunch."""
        self.machine.transition_to(self.machine.STATE_BATTLE)
        handler = BattleHandler(self.machine)
        handler._check_and_handle_nemesis_encounter = MagicMock(return_value=False)

        # 模擬已重試 2 次
        self.machine.battle_session.restart_battle_attempts = 2
        mock_extract.return_value = 1500

        handler.handle(MagicMock(), {"left": 0, "top": 0})
        self.clock.advance(31.0)
        handler.handle(MagicMock(), {"left": 0, "top": 0})

        self.process_port.relaunch.assert_called_once_with(self.machine, "battle_stall_max_retries_exceeded")

    def test_extract_health_bar_signature_from_fixture_sample(self):
        """Extract health bar signature from a real fixture image and verify debug output."""
        import cv2
        from pathlib import Path
        from utils.battle_stall_detector import extract_health_bar_signature

        fixture_path = Path("tests/fixtures/battle_stall_sample.png")
        if not fixture_path.exists():
            self.skipTest("Fixture image not found")

        img = cv2.imread(str(fixture_path))
        self.assertIsNotNone(img)

        # 驗證能正確提取血條特徵（大於 0）且產生 debug 圖片
        sig = extract_health_bar_signature(img, save_debug=True)
        self.assertGreater(sig, 1000)

        roi_debug_path = Path("scratch/debug/debug_battle_stall_roi.png")
        mask_debug_path = Path("scratch/debug/debug_battle_stall_mask.png")
        self.assertTrue(roi_debug_path.exists())
        self.assertTrue(mask_debug_path.exists())


if __name__ == "__main__":
    unittest.main()
