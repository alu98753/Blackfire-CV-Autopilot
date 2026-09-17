import unittest
import threading
from unittest.mock import MagicMock

from ports.notification_port import DeleteResult, NotificationResult
from states.nemesis_intervention import (
    InterventionOutcome,
    NemesisIntervention,
    UserResumeDecision,
)


class ManualTimer:
    def __init__(self, callback):
        self.callback = callback
        self.started = False
        self.cancelled = False

    def start(self):
        self.started = True

    def cancel(self):
        self.cancelled = True

    def fire(self):
        return self.callback()


class InterventionTests(unittest.TestCase):
    def setUp(self):
        self.machine = MagicMock()
        self.machine.is_paused = False
        self.notifier = MagicMock()
        self.sent = 0

        def send(*args, **kwargs):
            self.sent += 1
            return NotificationResult(True, f"m{self.sent}")

        self.notifier.notify_alarm.side_effect = send
        self.notifier.delete_message.return_value = DeleteResult(True)
        self.machine.notification_port = self.notifier
        self.timers = []

        def timer_factory(delay, callback):
            timer = ManualTimer(callback)
            self.timers.append(timer)
            return timer

        self.flee = MagicMock()
        self.lifecycle = NemesisIntervention(
            self.machine, self.notifier, timer_factory=timer_factory
        )

    def start(self, **kwargs):
        return self.lifecycle.start("encounter-1", self.flee, **kwargs)

    def test_start_default_and_duplicate_suppression(self):
        self.assertTrue(self.start())
        self.assertFalse(self.start())
        self.assertEqual(self.notifier.notify_alarm.call_count, 5)
        self.assertEqual(len(self.timers), 1)
        self.machine.pause.assert_called_once_with()

    def test_configurable_count_and_partial_failure_track_only_usable_ids(self):
        self.notifier.notify_alarm.side_effect = [
            NotificationResult(True, "m1"),
            NotificationResult(False),
            NotificationResult(True, None),
            NotificationResult(True, "m4"),
        ]
        self.start(notification_count=4)
        self.assertEqual(self.lifecycle.tracked_message_ids, ("m1", "m4"))

    def test_ack_deletes_all_and_cancels_timeout(self):
        self.start(notification_count=3)
        self.machine.is_paused = True
        self.assertTrue(self.lifecycle.acknowledge())
        self.assertEqual(self.lifecycle.outcome, InterventionOutcome.ACKNOWLEDGED)
        self.assertEqual(self.notifier.delete_message.call_count, 3)
        self.assertTrue(self.timers[0].cancelled)
        self.assertFalse(self.timers[0].fire())
        self.flee.assert_not_called()

    def test_timeout_flees_resumes_programmatically_and_retains_one(self):
        self.start(notification_count=4)
        self.machine.is_paused = True
        self.assertTrue(self.timers[0].fire())
        self.flee.assert_not_called()
        self.assertTrue(self.lifecycle.has_pending_timeout_recovery())
        self.lifecycle.run_pending_timeout_recovery()
        self.assertEqual(self.lifecycle.outcome, InterventionOutcome.TIMED_OUT)
        self.flee.assert_called_once_with()
        self.assertEqual(
            [call.args[0] for call in self.notifier.delete_message.call_args_list],
            ["m2", "m3", "m4"],
        )
        self.machine.resume.assert_called_once_with(user_initiated=False)

    def test_timeout_with_no_ids_still_flees_and_resumes(self):
        self.notifier.notify_alarm.return_value = NotificationResult(False)
        self.start(notification_count=2)
        self.machine.is_paused = True
        self.timers[0].fire()
        self.lifecycle.run_pending_timeout_recovery()
        self.flee.assert_called_once_with()
        self.machine.resume.assert_called_once_with(user_initiated=False)
        self.notifier.delete_message.assert_not_called()

    def test_delete_failure_does_not_block_terminal_resolution(self):
        self.notifier.delete_message.side_effect = RuntimeError("transport")
        self.start(notification_count=2)
        self.assertTrue(self.lifecycle.acknowledge())
        self.assertEqual(self.lifecycle.outcome, InterventionOutcome.ACKNOWLEDGED)

    def test_ack_timeout_race_has_one_winner(self):
        self.start(notification_count=2)
        barrier = threading.Barrier(2)
        results = []

        def ack():
            barrier.wait()
            results.append(self.lifecycle.acknowledge())

        def timeout():
            barrier.wait()
            results.append(self.timers[0].fire())

        threads = [threading.Thread(target=ack), threading.Thread(target=timeout)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=1.0)
        self.assertEqual(sum(results), 1)
        self.assertLessEqual(self.flee.call_count, 1)
        if self.lifecycle.outcome is InterventionOutcome.ACKNOWLEDGED:
            self.flee.assert_not_called()

    def test_late_user_resume_is_blocked_until_timeout_side_effects_finish(self):
        started = threading.Event()
        release = threading.Event()

        def blocked_flee():
            started.set()
            release.wait(timeout=1.0)

        self.start(notification_count=2)
        self.lifecycle._active.flee_callback = blocked_flee
        self.machine.is_paused = True
        timeout_thread = threading.Thread(target=self.timers[0].fire)
        timeout_thread.start()
        timeout_thread.join(timeout=1.0)
        self.assertFalse(started.is_set())
        self.assertTrue(self.lifecycle.has_pending_timeout_recovery())

        recovery_thread = threading.Thread(
            target=self.lifecycle.run_pending_timeout_recovery
        )
        recovery_thread.start()
        self.assertTrue(started.wait(timeout=1.0))

        self.assertEqual(
            self.lifecycle.request_user_resume(),
            UserResumeDecision.BLOCKED_TIMEOUT,
        )
        self.machine.resume.assert_called_once_with(user_initiated=False)
        self.assertEqual(self.lifecycle.outcome, InterventionOutcome.TIMED_OUT)

        release.set()
        recovery_thread.join(timeout=1.0)
        self.machine.resume.assert_called_once_with(user_initiated=False)

    def test_timer_factory_failure_converges_through_timeout(self):
        machine = self.machine
        machine.is_paused = True

        def failing_factory(delay, callback):
            raise RuntimeError("factory")

        lifecycle = NemesisIntervention(
            machine, self.notifier, timer_factory=failing_factory
        )
        lifecycle.start("encounter-1", self.flee, notification_count=1)
        self.assertEqual(lifecycle.outcome, InterventionOutcome.TIMED_OUT)
        self.assertTrue(lifecycle.has_pending_timeout_recovery())
        self.flee.assert_not_called()
        lifecycle.run_pending_timeout_recovery()
        self.flee.assert_called_once_with()
        machine.resume.assert_called_once_with(user_initiated=False)

    def test_timer_start_failure_converges_through_timeout(self):
        machine = self.machine
        machine.is_paused = True

        class BrokenTimer(ManualTimer):
            def start(self):
                raise RuntimeError("start")

        lifecycle = NemesisIntervention(
            machine,
            self.notifier,
            timer_factory=lambda delay, callback: BrokenTimer(callback),
        )
        lifecycle.start("encounter-1", self.flee, notification_count=1)
        self.assertEqual(lifecycle.outcome, InterventionOutcome.TIMED_OUT)
        self.assertTrue(lifecycle.has_pending_timeout_recovery())
        self.flee.assert_not_called()
        lifecycle.run_pending_timeout_recovery()
        self.flee.assert_called_once_with()
        machine.resume.assert_called_once_with(user_initiated=False)

    def test_runtime_owned_recovery_releases_real_pause_gate_before_flee(self):
        from actions.mouse import MouseController

        resume_event = threading.Event()
        resume_event.clear()
        gated_mouse = MouseController(human_like=False, resume_event=resume_event)
        machine = MagicMock()
        machine.is_paused = False
        machine.notification_port = self.notifier
        order = []

        def pause():
            machine.is_paused = True
            resume_event.clear()

        def resume(*, user_initiated):
            order.append(("resume", user_initiated))
            machine.is_paused = False
            resume_event.set()

        machine.pause.side_effect = pause
        machine.resume.side_effect = resume
        lifecycle = NemesisIntervention(
            machine, self.notifier, timer_factory=self._timer_factory
        )

        def flee():
            order.append("flee")
            gated_mouse._wait_if_paused()
            order.append("flee_done")

        lifecycle.start("gated-encounter", flee, notification_count=1)
        self.assertFalse(resume_event.is_set())
        self.timers[-1].fire()
        self.assertEqual(order, [])
        self.assertTrue(lifecycle.has_pending_timeout_recovery())

        # This is the runtime-owned handoff: no normal step may run until the
        # serialized recovery call has returned.
        lifecycle.run_pending_timeout_recovery()
        self.assertEqual(
            order,
            [("resume", False), "flee", "flee_done"],
        )
        order.append("normal_step")
        self.assertEqual(order[-1], "normal_step")

    def _timer_factory(self, delay, callback):
        timer = ManualTimer(callback)
        self.timers.append(timer)
        return timer


if __name__ == "__main__":
    unittest.main()
