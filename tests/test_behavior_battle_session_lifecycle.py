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


if __name__ == "__main__":
    unittest.main()
