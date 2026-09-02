import unittest
from unittest.mock import MagicMock

from runtime.ports import CapturePort, InputPort
from states.navigation_intent import (
    ActionId,
    ActiveIntent,
    IntentId,
    PostconditionId,
    PrimaryPayload,
)
from states.navigation_progress import ProgressStatus
from states.navigation_routing import (
    NavigationDecisionExecutor,
    resolve_navigation_context,
)
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

    def test_relaunch_clears_transient_action_but_preserves_navigation_intent(self):
        active_intent = ActiveIntent(
            IntentId.PRIMARY_NAVIGATION,
            PrimaryPayload("stage", "level4"),
        )
        self.machine.active_navigation_intent = active_intent
        self.machine.need_diamond_collection = True
        self.machine.navigation_progress.begin(
            IntentId.PRIMARY_NAVIGATION,
            ActionId.ENTER_LOBBY,
            PostconditionId.LOBBY,
            1,
            42.5,
        )

        self.machine.request_relaunch("navigation_recovery")

        self.assertIsNone(self.machine.navigation_progress.in_flight)
        self.assertEqual(self.machine.active_navigation_intent, active_intent)
        self.assertTrue(self.machine.need_diamond_collection)

    def test_in_flight_wait_has_specific_reason_and_diagnostic_context(self):
        self.machine.navigation_progress.begin(
            IntentId.PRIMARY_NAVIGATION,
            ActionId.ENTER_LOBBY,
            PostconditionId.LOBBY,
            0,
            42.0,
        )

        context = resolve_navigation_context(
            self.machine,
            SceneInfo(scene_type=SceneType.UNKNOWN),
        )
        handler = MagicMock()
        handler.machine = self.machine

        with self.assertLogs(level="INFO") as captured:
            NavigationDecisionExecutor(handler).execute(context, None, {})

        self.assertEqual(context.progress_status, ProgressStatus.WAITING)
        self.assertEqual(context.decision.reason.value, "in_flight_action_waiting")
        log = "\n".join(captured.output)
        self.assertIn("in_flight=enter_lobby", log)
        self.assertIn("expected=lobby", log)
        self.assertIn("deadline=", log)

    def test_timed_out_action_is_reported_as_a_retry(self):
        self.machine.navigation_progress.begin(
            IntentId.PRIMARY_NAVIGATION,
            ActionId.ENTER_LOBBY,
            PostconditionId.LOBBY,
            0,
            30.0,
        )

        context = resolve_navigation_context(
            self.machine,
            SceneInfo(
                scene_type=SceneType.TOWN,
                is_town=True,
                matched_elements={"common/door.png": ((10, 20), 0.99)},
            ),
        )

        self.assertEqual(context.progress_status, ProgressStatus.TIMED_OUT)
        self.assertEqual(context.decision.action, ActionId.ENTER_LOBBY)
        self.assertEqual(context.decision.reason.value, "action_timeout_retry")


if __name__ == "__main__":
    unittest.main()
