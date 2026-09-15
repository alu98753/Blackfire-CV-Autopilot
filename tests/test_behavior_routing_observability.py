import unittest
from unittest.mock import MagicMock

from states.navigation_intent import (
    ActionDecision,
    ActionId,
    ActiveIntent,
    DecisionKind,
    IntentId,
    IntentSnapshot,
    PostconditionId,
    PrimaryPayload,
    ReasonCode,
)
from states.navigation_progress import InFlightAction, ProgressStatus
from states.navigation_routing import (
    NavigationDecisionExecutor,
    NavigationRoutingContext,
    RoutingDiagnostic,
    RoutingInFlightDiagnostic,
    resolve_navigation_context,
)
from states.state_machine import GameStateMachine
from utils.scene_detector import SceneInfo, SceneType
from utils.scene_snapshot import SceneId, SceneSnapshot


class FakeClock:
    def __init__(self, now):
        self.now = now

    def monotonic(self):
        return self.now


class TestBehaviorRoutingObservability(unittest.TestCase):
    def setUp(self):
        self.capturer = MagicMock()
        self.mouse = MagicMock()
        self.clock = FakeClock(100.0)
        self.machine = GameStateMachine(
            self.capturer,
            MagicMock(),
            self.mouse,
            preload_ocr=False,
            clock=self.clock,
        )
        self.machine.config = {"type": "stage"}

    def test_idle_normal_routing_context_diagnostic_has_no_in_flight(self):
        context = resolve_navigation_context(
            self.machine,
            SceneInfo(scene_type=SceneType.TOWN, is_town=True, matched_elements={"common/door.png": ((10, 20), 0.99)}),
        )
        diag = context.to_diagnostic()

        self.assertIsInstance(diag, RoutingDiagnostic)
        self.assertEqual(diag.intent_id, IntentId.PRIMARY_NAVIGATION)
        self.assertEqual(diag.scene, SceneId.TOWN)
        self.assertEqual(diag.decision_kind, DecisionKind.CLICK)
        self.assertEqual(diag.decision_action, ActionId.ENTER_LOBBY)
        self.assertEqual(diag.decision_reason, ReasonCode.PRIMARY_ENTER_LOBBY)
        self.assertEqual(diag.progress_status, ProgressStatus.IDLE)
        self.assertIsNone(diag.in_flight)

        msg = diag.format_log_message(100.0)
        self.assertIn("intent=primary_navigation", msg)
        self.assertIn("scene=town", msg)
        self.assertIn("action=enter_lobby", msg)
        self.assertIn("reason=primary_enter_lobby", msg)
        self.assertIn("progress=idle", msg)
        self.assertNotIn("in_flight=", msg)

    def test_waiting_with_in_flight_action_diagnostic(self):
        self.machine.navigation_progress.begin(
            IntentId.PRIMARY_NAVIGATION,
            ActionId.ENTER_LOBBY,
            PostconditionId.LOBBY,
            1,
            95.0,
        )
        context = resolve_navigation_context(
            self.machine,
            SceneInfo(scene_type=SceneType.UNKNOWN),
        )
        diag = context.to_diagnostic()

        self.assertEqual(diag.intent_id, IntentId.PRIMARY_NAVIGATION)
        self.assertEqual(diag.progress_status, ProgressStatus.WAITING)
        self.assertEqual(diag.decision_kind, DecisionKind.WAIT)
        self.assertEqual(diag.decision_reason, ReasonCode.IN_FLIGHT_ACTION_WAITING)
        self.assertIsNone(diag.decision_action)

        self.assertIsNotNone(diag.in_flight)
        self.assertIsInstance(diag.in_flight, RoutingInFlightDiagnostic)
        self.assertEqual(diag.in_flight.action_id, ActionId.ENTER_LOBBY)
        self.assertEqual(diag.in_flight.expected, PostconditionId.LOBBY)
        self.assertEqual(diag.in_flight.attempt, 1)
        self.assertEqual(diag.in_flight.issued_at, 95.0)

        msg = diag.format_log_message(100.0)
        self.assertIn("intent=primary_navigation", msg)
        self.assertIn("reason=in_flight_action_waiting", msg)
        self.assertIn("progress=waiting", msg)
        self.assertIn("in_flight=enter_lobby", msg)
        self.assertIn("expected=lobby", msg)
        self.assertIn("age=5.0s", msg)
        self.assertIn("attempt=1", msg)

    def test_timed_out_action_retains_observed_action_in_diagnostic(self):
        self.machine.navigation_progress.begin(
            IntentId.PRIMARY_NAVIGATION,
            ActionId.ENTER_LOBBY,
            PostconditionId.LOBBY,
            0,
            30.0,
        )
        context = resolve_navigation_context(
            self.machine,
            SceneInfo(scene_type=SceneType.TOWN, is_town=True, matched_elements={"common/door.png": ((10, 20), 0.99)}),
        )
        diag = context.to_diagnostic()

        self.assertEqual(diag.progress_status, ProgressStatus.TIMED_OUT)
        self.assertEqual(diag.decision_reason, ReasonCode.ACTION_TIMEOUT_RETRY)
        self.assertEqual(diag.decision_action, ActionId.ENTER_LOBBY)
        self.assertIsNotNone(diag.in_flight)
        self.assertEqual(diag.in_flight.action_id, ActionId.ENTER_LOBBY)

        # Confirm context.observed_action was preserved from before observe mutated progress
        self.assertIsNotNone(context.observed_action)
        self.assertEqual(context.observed_action.action_id, ActionId.ENTER_LOBBY)

    def test_deferred_recovery_context_diagnostic(self):
        # Manually construct or trigger a DEFERRED context
        scene_snap = SceneSnapshot(frame_id=1, captured_at=100.0, scene=SceneId.TOWN)
        intent_snap = IntentSnapshot(
            diamond_pending=True,
            bread_pending=False,
            primary_payload=PrimaryPayload("stage"),
        )
        active_intent = ActiveIntent(IntentId.COLLECT_DIAMOND)
        decision = ActionDecision.wait(ReasonCode.SCENE_EVIDENCE_INSUFFICIENT)
        in_flight = InFlightAction(
            intent_id=IntentId.COLLECT_DIAMOND,
            action_id=ActionId.OPEN_DIAMOND,
            expected=PostconditionId.DIAMOND_WINDOW,
            source_frame_id=1,
            issued_at=80.0,
            deadline=90.0,
            attempt=3,
        )
        context = NavigationRoutingContext(
            scene=scene_snap,
            intent_snapshot=intent_snap,
            active_intent=active_intent,
            decision=decision,
            progress_status=ProgressStatus.DEFERRED,
            observed_action=in_flight,
        )

        diag = context.to_diagnostic()
        self.assertEqual(diag.intent_id, IntentId.COLLECT_DIAMOND)
        self.assertEqual(diag.progress_status, ProgressStatus.DEFERRED)
        self.assertEqual(diag.decision_kind, DecisionKind.WAIT)
        self.assertIsNotNone(diag.in_flight)
        self.assertEqual(diag.in_flight.action_id, ActionId.OPEN_DIAMOND)
        self.assertEqual(diag.in_flight.attempt, 3)

    def test_executor_logs_sourced_from_structured_diagnostic_without_changing_behavior(self):
        context = resolve_navigation_context(
            self.machine,
            SceneInfo(scene_type=SceneType.TOWN, is_town=True, matched_elements={"common/door.png": ((10, 20), 0.99)}),
        )
        handler = MagicMock()
        handler.machine = self.machine
        handler.mouse = MagicMock()
        rect = {"left": 0, "top": 0}

        with self.assertLogs(level="INFO") as captured:
            result = NavigationDecisionExecutor(handler).execute(context, None, rect)

        self.assertTrue(result)
        log = "\n".join(captured.output)
        expected_log = context.to_diagnostic().format_log_message(100.0)
        self.assertIn(expected_log, log)


if __name__ == "__main__":
    unittest.main()
