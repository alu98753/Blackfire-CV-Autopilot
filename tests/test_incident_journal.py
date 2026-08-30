import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from runtime import incident_journal


class TestIncidentJournal(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.directory.name) / "user_data"
        self.patch_user_data = patch.object(incident_journal, "USER_DATA_DIR", self.data_dir)
        self.patch_user_data.start()
        self.addCleanup(self.patch_user_data.stop)
        self.addCleanup(self.directory.cleanup)

    def test_incident_is_profile_isolated_and_keeps_nullable_startup_context(self):
        event = incident_journal.write_incident(
            "sandbox",
            incident_journal.CRASH,
            "child_exit_without_handoff",
            state=None,
            run_count=0,
            details={"exit_code": 1},
        )

        self.assertIsNotNone(event)
        path = incident_journal.incident_path("sandbox")
        stored = json.loads(path.read_text(encoding="utf-8").strip())
        self.assertEqual(stored["profile"], "sandbox")
        self.assertEqual(stored["category"], "CRASH")
        self.assertIsNone(stored["state"])
        self.assertEqual(stored["run_count"], 0)
        self.assertFalse(incident_journal.incident_path("native").exists())

    def test_handoff_requires_the_current_child_pid(self):
        event = incident_journal.write_incident("native", incident_journal.CRASH, "unhandled_python_exception", pid=123)
        self.assertTrue(incident_journal.write_child_termination("native", event))

        self.assertIsNone(incident_journal.read_child_termination("native", expected_pid=999))
        handoff = incident_journal.read_child_termination("native", expected_pid=123)
        self.assertEqual(handoff["reason_code"], "unhandled_python_exception")

    def test_unhandled_exception_writes_event_and_supervisor_handoff(self):
        machine = MagicMock()
        machine.restart_profile = "native"
        machine.incident_session_id = "session-1"
        machine.current_state = "BATTLE"
        machine.run_count = 9
        try:
            raise ValueError("broken matcher")
        except ValueError as exc:
            event = incident_journal.record_unhandled_exception(machine, exc)

        self.assertEqual(event["reason_code"], "unhandled_python_exception")
        self.assertEqual(event["details"]["exception_type"], "ValueError")
        handoff = incident_journal.read_child_termination("native", expected_pid=event["pid"])
        self.assertEqual(handoff["event_id"], event["event_id"])

    def test_write_failure_is_non_fatal(self):
        with patch("runtime.incident_journal.os.open", side_effect=OSError("disk full")):
            event = incident_journal.write_incident("native", incident_journal.CRASH, "unhandled_python_exception")

        self.assertIsNone(event)

    def test_explicit_profile_requires_a_nonblank_value(self):
        self.assertEqual(
            incident_journal.explicit_profile_from_command(["python", "main.py", "--profile", "sandbox"]),
            "sandbox",
        )
        self.assertIsNone(incident_journal.explicit_profile_from_command(["python", "main.py"]))
        self.assertIsNone(incident_journal.explicit_profile_from_command(["python", "main.py", "--profile", ""]))
        self.assertIsNone(incident_journal.explicit_profile_from_command(["python", "main.py", "--profile", "   "]))
        self.assertIsNone(
            incident_journal.explicit_profile_from_command(
                ["python", "main.py", "--profile", "native", "--profile", "sandbox"]
            )
        )
        self.assertIsNone(
            incident_journal.explicit_profile_from_command(["python", "main.py", "--profile", "--target", "sandbox"])
        )
        self.assertIsNone(incident_journal.explicit_profile_from_command(["python", "main.py", "--profile"]))

    def test_profile_paths_reject_path_traversal(self):
        with self.assertRaises(ValueError):
            incident_journal.runtime_data_dir("../outside")
        with self.assertRaises(ValueError):
            incident_journal.runtime_data_dir("native\\other")

    def test_exception_details_redact_sensitive_values_before_persistence(self):
        machine = MagicMock(restart_profile="native", incident_session_id="session-1", current_state="BATTLE", run_count=1)
        try:
            raise RuntimeError("token=abc123 password: hunter2 Bearer secret-value {\"token\": \"json-secret\"} api key: key-secret")
        except RuntimeError as exc:
            event = incident_journal.record_unhandled_exception(machine, exc)

        serialized = json.dumps(event, ensure_ascii=False)
        self.assertNotIn("abc123", serialized)
        self.assertNotIn("hunter2", serialized)
        self.assertNotIn("secret-value", serialized)
        self.assertNotIn("json-secret", serialized)
        self.assertNotIn("key-secret", serialized)

    def test_recovery_is_not_written_before_machine_identity_is_initialized(self):
        machine = MagicMock()
        machine.restart_profile = None
        machine.incident_session_id = None

        self.assertIsNone(incident_journal.record_recovery(machine, "watchdog_timeout_detected"))
        self.assertFalse((self.data_dir / "native" / "runtime").exists())

    def test_summary_groups_four_categories_and_limits_reason_details(self):
        for reason_code in ("unhandled_python_exception", "unhandled_python_exception", "unexpected_clean_exit"):
            incident_journal.write_incident("native", incident_journal.CRASH, reason_code)
        incident_journal.write_incident("native", incident_journal.HEARTBEAT_TIMEOUT, "heartbeat_stale")

        summary = incident_journal.summarize_incidents("native", top_limit=1)

        self.assertEqual(summary["category_counts"]["CRASH"], 3)
        self.assertEqual(summary["category_counts"]["HEARTBEAT_TIMEOUT"], 1)
        self.assertEqual(summary["category_counts"]["SCHEDULED_MAINTENANCE"], 0)
        self.assertEqual(summary["top_reasons"]["CRASH"], [{"reason_code": "unhandled_python_exception", "count": 2}])

    def test_summary_skips_a_corrupt_line_without_losing_later_events(self):
        incident_journal.write_incident("native", incident_journal.CRASH, "unhandled_python_exception")
        path = incident_journal.incident_path("native")
        with path.open("a", encoding="utf-8") as handle:
            handle.write("{not-json}\n")
        incident_journal.write_incident("native", incident_journal.HEARTBEAT_TIMEOUT, "heartbeat_stale")

        summary = incident_journal.summarize_incidents("native")

        self.assertEqual(summary["category_counts"]["CRASH"], 1)
        self.assertEqual(summary["category_counts"]["HEARTBEAT_TIMEOUT"], 1)


if __name__ == "__main__":
    unittest.main()
