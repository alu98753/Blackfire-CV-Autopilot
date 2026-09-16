import unittest
from unittest.mock import MagicMock

from ports.notification_port import DeleteResult, NotificationResult
from states.nemesis_intervention import (
    InterventionOutcome,
    NemesisIntervention,
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
        results = [self.lifecycle.acknowledge(), self.timers[0].fire()]
        self.assertEqual(sum(results), 1)
        self.assertLessEqual(self.flee.call_count, 1)
        if self.lifecycle.outcome is InterventionOutcome.ACKNOWLEDGED:
            self.flee.assert_not_called()


if __name__ == "__main__":
    unittest.main()
