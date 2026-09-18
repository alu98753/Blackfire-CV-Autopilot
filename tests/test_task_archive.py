import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TaskArchiveContractTests(unittest.TestCase):
    def test_archive_is_post_integration_and_not_cleanup(self):
        archive = (ROOT / "scripts" / "task_archive.ps1").read_text(encoding="utf-8")
        cleanup = (ROOT / "scripts" / "task_cleanup.ps1").read_text(encoding="utf-8")
        self.assertIn("origin/main", archive)
        self.assertIn("integration_year", archive)
        self.assertIn("ARCHIVE_CLOSEOUT_READY", archive)
        self.assertIn("pushed closeout branch", archive)
        self.assertNotIn("task_archive.ps1", cleanup)
        self.assertIn("git worktree add", archive.lower())

    def test_archive_fails_closed_for_unsafe_states(self):
        text = (ROOT / "scripts" / "task_archive.ps1").read_text(encoding="utf-8")
        for token in ("TASK_$($resolved.Classification)", "ARCHIVE_REQUIRES_CLEAN_MAIN", "ARCHIVE_INTEGRATION_UNPROVEN", "ARCHIVE_DESTINATION_COLLISION"):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()
