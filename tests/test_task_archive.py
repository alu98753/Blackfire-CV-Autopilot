import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_NAMES = ("task_archive.ps1", "task_package_resolver.ps1")


class ArchiveBehavioralTests(unittest.TestCase):
    def git(self, cwd, *args, check=True, env=None):
        return subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, check=check, env=env)

    def fixture(self, integrated=True, integration_date=None):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name); bare = root / "origin.git"; main = root / "main"; wt = root / "task-wt"
        self.git(root, "init", "--bare", bare); self.git(root, "clone", bare, main)
        self.git(main, "config", "user.name", "Test"); self.git(main, "config", "user.email", "test@example.com")
        self.git(main, "checkout", "-b", "main"); (main / "README.md").write_text("init\n")
        (main / "scripts").mkdir()
        for name in SCRIPT_NAMES: shutil.copy2(ROOT / "scripts" / name, main / "scripts" / name)
        self.git(main, "add", "."); self.git(main, "commit", "-m", "initial"); self.git(main, "push", "-u", "origin", "main")
        task = "archive-fixture"; self.git(main, "checkout", "-b", task)
        pkg = main / "docs" / "tasks" / "active" / task; pkg.mkdir(parents=True)
        (pkg / "SPEC.md").write_text("# fixture\n"); (pkg / "task.json").write_text(json.dumps({"id": task}))
        self.git(main, "add", "."); self.git(main, "commit", "-m", "task implementation"); task_head=self.git(main,"rev-parse","HEAD").stdout.strip(); self.git(main,"push","-u","origin",task)
        if integrated:
            self.git(main, "checkout", "main")
            merge_env = None
            if integration_date:
                merge_env = os.environ.copy(); merge_env["GIT_AUTHOR_DATE"] = integration_date; merge_env["GIT_COMMITTER_DATE"] = integration_date
            self.git(main, "merge", "--no-ff", task, "-m", "merge fixture task", env=merge_env); self.git(main, "push", "origin", "main")
            self.git(main, "worktree", "add", wt, task)
        if not integrated:
            self.git(main, "checkout", "main")
            main_pkg = main / "docs" / "tasks" / "active" / task; main_pkg.mkdir(parents=True)
            (main_pkg / "SPEC.md").write_text("# divergent fixture\n"); (main_pkg / "task.json").write_text(json.dumps({"id": task}))
            self.git(main, "add", "."); self.git(main, "commit", "-m", "unrelated active package"); self.git(main, "push", "origin", "main")
            self.git(main, "worktree", "add", wt, task)
        return td, main, wt, task, task_head

    def run_archive(self, main, task):
        return subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(main / "scripts" / "task_archive.ps1"), "-Task", task], cwd=main, text=True, capture_output=True)

    def test_proven_integration_and_remote_closeout(self):
        td, main, wt, task, _ = self.fixture(True)
        try:
            p = self.run_archive(main, task)
            self.assertEqual(p.returncode, 0, p.stderr)
            payload = json.loads(p.stdout.strip().splitlines()[-1]); self.assertEqual(payload["outcome"], "ARCHIVE_CLOSEOUT_READY")
            self.assertIn(payload["closeout_branch"], self.git(main, "ls-remote", "--heads", "origin").stdout)
            self.assertNotEqual(self.git(main, "show-ref", "--verify", f"refs/heads/{payload['closeout_branch']}", check=False).returncode, 0)
            self.assertEqual(self.git(main, "status", "--porcelain").stdout, "")
            self.assertEqual(self.git(main, "rev-parse", "HEAD").stdout.strip(), self.git(main, "rev-parse", "origin/main").stdout.strip())
        finally: self.git(main, "worktree", "remove", wt, check=False); td.cleanup()

    def test_unproven_and_missing_fail_closed(self):
        td, main, wt, task, _ = self.fixture(False)
        try:
            p = self.run_archive(main, task); self.assertNotEqual(p.returncode, 0); self.assertIn("ARCHIVE_INTEGRATION_UNPROVEN", p.stderr)
            self.git(main, "worktree", "remove", wt); shutil.rmtree(main / "docs" / "tasks" / "active" / task)
            p = self.run_archive(main, task); self.assertNotEqual(p.returncode, 0); self.assertIn("TASK_MISSING", p.stderr)
        finally: self.git(main, "worktree", "remove", wt, check=False); td.cleanup()

    def test_archive_contract_rejects_collision_and_branch_collision(self):
        text = (ROOT / "scripts" / "task_archive.ps1").read_text(encoding="utf-8")
        for token in ("ARCHIVE_DESTINATION_COLLISION", "ARCHIVE_CLOSEOUT_BRANCH_COLLISION", "ARCHIVE_TASK_WORKTREE_DIRTY", "ARCHIVE_INTEGRATION_COMMIT_AMBIGUOUS", "ARCHIVE_CLOSEOUT_READY"):
            self.assertIn(token, text)
        self.assertNotIn("git worktree remove --force", text)

    def test_archive_year_uses_utc_boundary_year(self):
        td, main, wt, task, _ = self.fixture(True, "2026-01-01T00:30:00+14:00")
        try:
            p = self.run_archive(main, task); self.assertEqual(p.returncode, 0, p.stderr)
            payload = json.loads(p.stdout.strip().splitlines()[-1]); self.assertEqual(payload["integration_year"], "2025")
        finally: self.git(main, "worktree", "remove", wt, check=False); td.cleanup()


if __name__ == "__main__": unittest.main()
