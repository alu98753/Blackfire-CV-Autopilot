import unittest
from unittest.mock import MagicMock

from runtime.ports import CapturePort, InputPort
from states.navigation_routing import resolve_navigation_context
from states.state_machine import GameStateMachine
from utils.scene_detector import SceneInfo, SceneType


class FakeClock:
    def __init__(self, now):
        self.now = now

    def monotonic(self):
        return self.now


class FakeProcessPort:
    def __init__(self):
        self.calls = []

    def relaunch(self, machine, reason):
        self.calls.append((machine, reason))
        return True


class TestBehaviorRuntimePorts(unittest.TestCase):
    def setUp(self):
        self.capturer = MagicMock()
        self.mouse = MagicMock()
        self.clock = FakeClock(42.5)
        self.process = FakeProcessPort()
        self.machine = GameStateMachine(
            self.capturer,
            MagicMock(),
            self.mouse,
            preload_ocr=False,
            clock=self.clock,
            process_port=self.process,
        )
        self.machine.config = {"type": "stage"}

    def test_legacy_adapters_are_exposed_through_minimal_ports(self):
        self.assertIs(self.machine.capture_port, self.capturer)
        self.assertIs(self.machine.input_port, self.mouse)
        self.assertIsInstance(self.machine.capture_port, CapturePort)
        self.assertIsInstance(self.machine.input_port, InputPort)

    def test_scene_snapshot_uses_injected_monotonic_clock(self):
        context = resolve_navigation_context(
            self.machine,
            SceneInfo(scene_type=SceneType.UNKNOWN),
        )

        self.assertEqual(context.scene.captured_at, 42.5)

    def test_relaunch_is_delegated_to_process_port(self):
        result = self.machine.request_relaunch("test_recovery")

        self.assertTrue(result)
        self.assertEqual(self.process.calls, [(self.machine, "test_recovery")])


if __name__ == "__main__":
    unittest.main()
