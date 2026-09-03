"""Behavioral coverage for Demon Lord Start → insufficient-stamina recovery."""

import unittest
from unittest.mock import MagicMock, patch

from states.handlers.demon_lords import DemonLordsHandler
from states.stamina_flow import handle_insufficient_stamina
from states.state_machine import GameStateMachine


class TestDemonStaminaRetreat(unittest.TestCase):
    def setUp(self):
        self.machine = GameStateMachine(
            capturer=MagicMock(),
            matcher=MagicMock(),
            mouse=MagicMock(),
            preload_ocr=False,
        )
        self.machine.current_state = self.machine.STATE_DEMON_LORDS
        self.machine.primary_config = {"name": "Daily", "type": "daily"}
        self.machine.config = {
            "name": "Demon Lords",
            "type": "demon_lords",
            "start_btn": "stages/start.png",
            "target_boss": "voidborn_elres",
            "result_buttons": [],
            "dungeon_battle_results": [],
        }
        self.rect = {"left": 0, "top": 0}

        def match(screen, template, **_kwargs):
            if template in screen:
                return ((100, 200), 0.95)
            return (None, 0.0)

        self.machine.matcher.match.side_effect = match

    @patch("states.stamina_retreat.os.path.exists", return_value=True)
    def test_demon_overlay_uses_confirm_then_three_bounded_quits(self, _exists):
        """A no_bread2 Start outcome defers Demon work and reaches COLLECT_ONLY."""
        frames = [
            {"no_bread/no_bread2.png", "common/confirm.png"},
            set(),
            {"common/quit.png"},
            {"common/quit.png"},
            {"common/quit.png"},
            {"common/quit.png"},
            {"common/quit.png"},
            {"common/quit.png"},
            set(),
        ]

        for frame in frames:
            self.assertTrue(handle_insufficient_stamina(self.machine, frame, self.rect))

        self.assertEqual(self.machine.current_state, self.machine.STATE_COLLECT_ONLY)
        self.assertEqual(self.machine.config["type"], "collect_only")
        self.assertEqual(self.machine.original_config, self.machine.primary_config)
        self.assertEqual(
            self.machine.mouse.click.call_count,
            4,
        )

    @patch("states.handlers.demon_lords.os.path.exists", return_value=True)
    def test_start_is_committed_once_without_handler_recapture_loop(self, _exists):
        """Demon Start waits for a later frame rather than polling/clicking in-place."""
        handler = DemonLordsHandler(self.machine)
        handler.current_target_boss = "voidborn_elres"

        handled = handler._launch_demon_battle(self.rect, (100, 200), 0.95)

        self.assertTrue(handled)
        self.assertTrue(handler.launch_pending)
        self.machine.mouse.click.assert_called_once_with(100, 200)
        self.machine.capturer.capture.assert_not_called()

    @patch("os.path.exists", return_value=True)
    def test_state_machine_prioritizes_demon_stamina_overlay_before_handler(self, _exists):
        """The Demon profile sees no_bread before its generic confirm guard can consume it."""
        frame = {"no_bread/no_bread2.png", "common/confirm.png"}
        self.machine.capturer.get_window_rect.return_value = self.rect
        self.machine.capturer.capture.return_value = frame

        self.machine.step()

        self.assertTrue(self.machine.stamina_recovery.is_active)
        self.machine.mouse.click.assert_called_once_with(100, 200)


if __name__ == "__main__":
    unittest.main()
