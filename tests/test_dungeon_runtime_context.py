import time
import unittest
from unittest.mock import MagicMock

import numpy as np

from states.handlers.collect_only import CollectOnlyHandler
from states.state_machine import GameStateMachine


class TestDungeonRuntimeContext(unittest.TestCase):
    def test_selected_dungeon_status_does_not_require_greedy_indices(self):
        machine = GameStateMachine(MagicMock(), MagicMock(), MagicMock())
        machine.set_config({
            "type": "dungeon",
            "greedy_dungeon": False,
            "dungeon_index": 2,
            "dungeon_names": ["A", "B", "C"],
            "dungeon_entries": ["a.png", "b.png", "c.png"],
            "navigation_path": ["door.png", "c.png"],
        })

        status, available = machine.get_dungeon_cooldown_status()

        self.assertIn("C", status)
        self.assertEqual(available, ["C"])

    def test_collect_only_skips_status_for_incomplete_dungeon_context(self):
        machine = GameStateMachine(MagicMock(), MagicMock(), MagicMock())
        machine.set_config({"type": "collect_only", "enable_dungeon": True})
        machine.enable_bread = False
        machine.last_diamond_collection_time = time.time()

        handler = CollectOnlyHandler(machine)
        handler.matcher.match.return_value = (None, 0.0)
        handler.handle(
            np.zeros((100, 100, 3), dtype=np.uint8),
            {"left": 0, "top": 0, "width": 100, "height": 100},
        )


if __name__ == "__main__":
    unittest.main()
